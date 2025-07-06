from typing import Any, List, Dict, Optional
import logging
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from .datameshmanager.datamesh_manager_client import DataMeshManagerClient
from .connections.snowflake_client import execute_snowflake_query
from .connections.databricks_client import execute_databricks_query

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("dataproduct")


@mcp.tool()
async def dataproduct_search(
    search_term: Optional[str] = None,
    archetype: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search data products based on the search term. Only returns active data products.

    Args:
        search_term: Search term to filter data products. Multiple search terms are supported, separated by space.
        archetype: Filter for specific data product types. Typical values are: consumer-aligned, 
                  aggregate, source-aligned, application, dataconsumer
    """
    logger.info(f"dataproduct_search called with search_term={search_term}, archetype={archetype}")
    
    try:
        client = DataMeshManagerClient()
        results = []
        
        # First, try the list endpoint (supports archetype and status filters)
        try:
            logger.info("Trying list endpoint first")
            data_products = await client.get_data_products(
                query=search_term,
                archetype=archetype,
                status="active"
            )
            
            if data_products:
                # Format results from list endpoint
                for dp in data_products:
                    formatted_product = {
                        "id": dp.get("id", "N/A"),
                        "name": dp.get("title") or dp.get("info", {}).get("title") or "N/A",
                        "description": dp.get("description") or dp.get("info", {}).get("description") or "N/A",
                        "owner": dp.get("owner") or dp.get("info", {}).get("owner") or "N/A",
                        "source": "simple_search"
                    }
                    results.append(formatted_product)
                
                logger.info(f"List endpoint returned {len(results)} data products")
        
        except Exception as e:
            logger.warning(f"List endpoint failed: {str(e)}")
        
        # If no results from list endpoint or search_term provided, try semantic search
        if (not results and search_term) or (search_term and not archetype):
            try:
                logger.info("Trying semantic search endpoint")
                search_results = await client.search(search_term, resource_type="DATA_PRODUCT")
                search_data_products = search_results.get("results", [])
                
                # Add results from search endpoint (avoid duplicates)
                existing_ids = {dp["id"] for dp in results}
                
                for dp in search_data_products:
                    dp_id = dp.get("id", "N/A")
                    if dp_id not in existing_ids:
                        formatted_product = {
                            "id": dp_id,
                            "name": dp.get("name") or "N/A",
                            "description": dp.get("description") or dp.get("info", {}).get("description") or "N/A",
                            "ownerId": dp.get("ownerId") or "N/A",
                            "ownerName": dp.get("ownerName") or "N/A",
                            "source": "semantic_search"
                        }
                        results.append(formatted_product)
                
                logger.info(f"Search endpoint added {len(search_data_products)} additional data products")
            
            except Exception as e:
                logger.warning(f"Search endpoint failed: {str(e)}")
        
        # If still no results, try getting all active data products without search query
        if not results:
            try:
                logger.info("No results from list or search endpoints, trying to get all active data products")
                data_products = await client.get_data_products(
                    query=None,
                    archetype=archetype,
                    status="active"
                )
                
                if data_products:
                    # Format results from fallback list endpoint
                    for dp in data_products:
                        formatted_product = {
                            "id": dp.get("id", "N/A"),
                            "name": dp.get("title") or dp.get("info", {}).get("title") or "N/A",
                            "description": dp.get("description") or dp.get("info", {}).get("description") or "N/A",
                            "owner": dp.get("owner") or dp.get("info", {}).get("owner") or "N/A",
                            "source": "all_data_products"
                        }
                        results.append(formatted_product)
                    
                    logger.info(f"Fallback list endpoint returned {len(results)} data products")
            
            except Exception as e:
                logger.warning(f"Fallback list endpoint failed: {str(e)}")
        
        if not results:
            logger.info("No data products found from any endpoint")
            return []
        
        logger.info(f"dataproduct_search returned {len(results)} total data products")
        return results
        
    except ValueError as e:
        logger.error(f"dataproduct_search ValueError: {str(e)}")
        return [{"error": str(e)}]
    except Exception as e:
        logger.error(f"dataproduct_search Exception: {str(e)}")
        return [{"error": f"Error searching data products: {str(e)}"}]


@mcp.tool()
async def dataproduct_get(data_product_id: str) -> str:
    """
    Get a data product by its ID. The data product contains all its output ports and server information.
    The response includes access status for each output port and may include a data contract ID.
    You can use the datacontract_get tool to get the details of the data contract for more semantic information and terms of use.
    
    Args:
        data_product_id: The data product ID.
    """
    logger.info(f"dataproduct_get called with data_product_id={data_product_id}")
    
    try:
        client = DataMeshManagerClient()
        data_product = await client.get_data_product(data_product_id)
        
        if not data_product:
            logger.info(f"dataproduct_get: data product {data_product_id} not found")
            return "Data product not found"
        
        # todo make null safe
        access_lifecycle_status = "You do not have access to this output port"

        # Add access status to each output port
        output_ports = data_product.get("outputPorts", [])
        for output_port in output_ports:
            try:
                output_port_id = output_port.get("id")
                if output_port_id:
                    logger.info(f"Checking access status for output port {output_port_id}")
                    access_status = await client.get_access_status(data_product_id, output_port_id)

                    # Set output_port["accessStatus"] based on the result of access_status
                    lifecycle_status = access_status.access_lifecycle_status if access_status else None
                    access_status_value = access_status.access_status if access_status else None
                    
                    if not lifecycle_status:
                        output_port["accessStatus"] = "You do not have access to this output port, you can request access. You may not access the data directly for data governance reasons without an approved access request."
                    elif lifecycle_status == "requested":
                        output_port["accessStatus"] = f"Your access request is pending approval (status: {access_status_value}, lifecycle: {lifecycle_status}). You may not access the data directly for data governance reasons without an approved access request."
                    elif lifecycle_status == "rejected":
                        output_port["accessStatus"] = f"Your access request was rejected (status: {access_status_value}, lifecycle: {lifecycle_status})"
                    elif lifecycle_status == "upcoming":
                        output_port["accessStatus"] = f"Your access is upcoming (status: {access_status_value}, lifecycle: {lifecycle_status}). You may not access the data directly for data governance reasons without an approved access request."
                    elif lifecycle_status == "active":
                        output_port["accessStatus"] = f"You have access to this output port (status: {access_status_value}, lifecycle: {lifecycle_status})"
                    elif lifecycle_status == "expired":
                        output_port["accessStatus"] = f"Your access request is expired (status: {access_status_value}, lifecycle: {lifecycle_status})"
                    else:
                        output_port["accessStatus"] = f"Access status: {access_status_value}, lifecycle: {lifecycle_status}"

                    logger.info(f"Added access status for output port {output_port_id}")
                else:
                    logger.warning(f"Output port missing externalId/id, skipping access status")
                    output_port["accessStatus"] = None
            except Exception as e:
                logger.warning(f"Failed to get access status for output port {output_port.get('externalId', 'unknown')}: {str(e)}")
                output_port["accessStatus"] = None
        
        # Convert the enhanced data product to YAML format
        import yaml
        yaml_data = yaml.dump(data_product, default_flow_style=False, sort_keys=False)
        logger.info(f"dataproduct_get successfully retrieved data product {data_product_id} with access status")
        return yaml_data
        
    except ValueError as e:
        logger.error(f"dataproduct_get ValueError: {str(e)}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"dataproduct_get Exception: {str(e)}")
        return f"Error fetching data product: {str(e)}"


@mcp.tool()
async def datacontract_get(data_contract_id: str) -> str:
    """
    Get a data contract by its ID.
    
    Args:
        data_contract_id: The data contract ID.
    """
    logger.info(f"datacontract_get called with data_contract_id={data_contract_id}")
    
    try:
        client = DataMeshManagerClient()
        data_contract = await client.get_data_contract(data_contract_id)
        
        if not data_contract:
            logger.info(f"datacontract_get: data contract {data_contract_id} not found")
            return "Data contract not found"
        
        # Convert the data contract to YAML format
        import yaml
        yaml_data = yaml.dump(data_contract, default_flow_style=False, sort_keys=False)
        logger.info(f"datacontract_get successfully retrieved data contract {data_contract_id}")
        return yaml_data
        
    except ValueError as e:
        logger.error(f"datacontract_get ValueError: {str(e)}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"datacontract_get Exception: {str(e)}")
        return f"Error fetching data contract: {str(e)}"


@mcp.tool()
async def dataproduct_request_access(data_product_id: str, output_port_id: str, purpose: str) -> str:
    """
    Request access to a specific output port of a data product.
    This creates an access request. Based on the data product configuration, purpose, and data governance rules,
    the access will be automatically granted, or it will be reviewed by the data product owner.
    
    Args:
        data_product_id: The ID of the data product.
        output_port_id: The ID of the output port to request access to.
        purpose: The business purpose/reason for requesting access to this data.
    """
    logger.info(f"dataproduct_request_access called with data_product_id={data_product_id}, output_port_id={output_port_id}, purpose={purpose}")
    
    try:
        client = DataMeshManagerClient()
        result = await client.post_request_access(data_product_id, output_port_id, purpose)
        
        # Check if access was automatically granted based on status
        status_lower = result.status.lower()
        
        if status_lower in ["active"]:
            # Access was automatically granted
            response = f"""🎉 Access granted automatically!

Access Request Details:
- Access ID: {result.access_id}
- Status: {result.status}
- Data Product: {data_product_id}
- Output Port: {output_port_id}
- Purpose: {purpose}

Your access request was automatically approved. You now have access to this data product output port using the server details and can start using the data immediately."""
        else:
            # Access requires manual approval
            response = f"""Access request submitted successfully!

Access Request Details:
- Access ID: {result.access_id}
- Status: {result.status}
- Data Product: {data_product_id}
- Output Port: {output_port_id}
- Purpose: {purpose}

Your access request has been submitted and is now {result.status}. You will be notified when the data product owner reviews your request. You can check the status in dataproduct details in the output port."""
        
        logger.info(f"dataproduct_request_access successfully submitted for data_product_id={data_product_id}, access_id={result.access_id}, status={result.status}")
        return response
        
    except ValueError as e:
        logger.error(f"dataproduct_request_access ValueError: {str(e)}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"dataproduct_request_access Exception: {str(e)}")
        return f"Error requesting access: {str(e)}"


@mcp.tool()
async def dataproduct_query(data_product_id: str, output_port_id: str, query: str) -> str:
    """
    Execute a SQL query on a data product's output port.
    This tool connects to the underlying data platform (Snowflake, Databricks) and executes the provided SQL query.
    You must have access to the output port to execute queries.
    
    Args:
        data_product_id: The ID of the data product.
        output_port_id: The ID of the output port to query.
        query: The SQL query to execute.
    """
    logger.info(f"dataproduct_query called with data_product_id={data_product_id}, output_port_id={output_port_id}")
    
    try:
        # First, get the data product details to retrieve server information
        client = DataMeshManagerClient()
        data_product = await client.get_data_product(data_product_id)
        
        if not data_product:
            logger.error(f"Data product {data_product_id} not found")
            return "Error: Data product not found"
        
        # Find the specified output port
        output_ports = data_product.get("outputPorts", [])
        target_output_port = None
        
        for output_port in output_ports:
            if output_port.get("id") == output_port_id:
                target_output_port = output_port
                break
        
        if not target_output_port:
            logger.error(f"Output port {output_port_id} not found in data product {data_product_id}")
            return "Error: Output port not found"
        
        # Check access status
        try:
            access_status = await client.get_access_status(data_product_id, output_port_id)
            if not access_status or access_status.access_lifecycle_status != "active":
                current_status = access_status.access_lifecycle_status if access_status else "unknown"
                logger.error(f"No active access to output port {output_port_id}, current status: {current_status}")
                return f"Error: You do not have active access to this output port. Current access status: {current_status}. Please request access first using dataproduct_request_access."
        except Exception as e:
            logger.error(f"Failed to check access status: {str(e)}")
            return "Error: Unable to verify access status. Please ensure you have access to this output port."

        # Check that the query is in line with the purpose of the access agreement (dont be strict)
        # this check can be performed using a callback to the llm
        # todo


        # In the future, we can also check that the query is not violating any global policies


        # Get server information and type
        server_info = target_output_port.get("server", {})
        if not server_info:
            logger.error(f"No server information found for output port {output_port_id}")
            return "Error: No server information available for this output port"
        
        # Get server type from output port type field
        server_type = target_output_port.get("type", "").lower()
        if server_type not in ["snowflake", "databricks"]:
            logger.error(f"Unsupported server type: {server_type}")
            return f"Error: Unsupported server type '{server_type}'. Supported types: snowflake, databricks"

        # Execute the query based on server type
        try:
            if server_type == "snowflake":
                results = await execute_snowflake_query(server_info, query)
            elif server_type == "databricks":
                results = await execute_databricks_query(server_info, query)
            else:
                return f"Error: Server type '{server_type}' is not yet supported by dataproduct-mcp. Supported types: snowflake, databricks"
            
            # Format results for display
            if not results:
                return "Query executed successfully, but returned no results."
            
            # Convert results to YAML format for consistent output
            import yaml
            formatted_results = {
                "query": query,
                "row_count": len(results),
                "results": results[:100]  # Limit to first 100 rows to avoid overwhelming output
            }
            
            if len(results) > 100:
                formatted_results["note"] = f"Results truncated to first 100 rows. Total rows: {len(results)}"
            
            yaml_output = yaml.dump(formatted_results, default_flow_style=False, sort_keys=False)

            # check that that there are no prompt injections in the results
            # todo

            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return yaml_output
            
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            return f"Error executing query: {str(e)}"
        
    except ValueError as e:
        logger.error(f"dataproduct_query ValueError: {str(e)}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"dataproduct_query Exception: {str(e)}")
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Set up logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting DataMesh Manager MCP server")
    
    # Initialize and run the server
    mcp.run(transport='stdio')