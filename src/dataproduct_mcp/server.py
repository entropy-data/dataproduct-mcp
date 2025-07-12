from typing import Any, List, Dict, Optional
from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
from .datameshmanager.datamesh_manager_client import DataMeshManagerClient
from .connections.snowflake_client import execute_snowflake_query
from .connections.databricks_client import execute_databricks_query
from .connections.bigquery_client import execute_bigquery_query
from .safeguards import validate_readonly_query, sanitize_prompt_injection

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP(
    name="DataProductServer",
    instructions="""
You are connected to the Data Product MCP server, which provides access to business data.
Use this MCP server if you need access to internal business data, such as customers, orders...

## Available Tools

### 1. dataproduct_search
- **Purpose**: Find and explore data products in the organization
- **Parameters**: 
  - `search_term` (optional): Keywords to search for in data product names/descriptions
- **Returns**: List of data products with basic information
- **Use**: First use a generic search term like "sales", "customers", "marketing" to find relevant data products. Use more specific terms if the results are too broad.

### 2. dataproduct_get
- **Purpose**: Get detailed information about a specific data product
- **Parameters**: `data_product_id` (required)
- **Returns**: Complete data product details including:
  - All output ports with server connection information
  - Access status for each port (active, pending, rejected, etc.)
  - Inlined data contracts with schemas and terms of use
- **Use**: Get this info before requesting access or querying data

### 3. dataproduct_request_access
- **Purpose**: Request access to a specific data product output port
- **Parameters**: 
  - `data_product_id` (required)
  - `output_port_id` (required) 
  - `purpose` (required): Business justification for access. Use a high-level description of the kind of usage.
- **Returns**: Access request status (may be auto-approved or require manual review)

### 4. dataproduct_query
- **Purpose**: Execute SQL queries on data product output ports
- **Requirements**: Must have active access to the output port
- **Parameters**:
  - `data_product_id` (required)
  - `output_port_id` (required)
  - `query` (required): SQL query to execute
- **Supports**: Snowflake, Databricks, and BigQuery platforms
- **Returns**: Query results as structured data (limited to 100 rows)

## Typical Workflow

1. **Discover**: Use `dataproduct_search` to find relevant data products
2. **Evaluate**: Use `dataproduct_get` to understand structure, access status, and schemas
3. **Request Access**: Use `dataproduct_request_access` if you don't have active access
4. **Query Data**: Use `dataproduct_query` to execute SQL queries once you have access for typical server types. For other server types, you may need to use server-specific tools.
    """
)


@mcp.tool()
async def dataproduct_search(
    ctx: Context,
    search_term: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search data products based on the search term. Only returns active data products.

    Args:
        search_term: Search term to filter data products. Multiple search terms are supported, separated by space.
                  
    Returns:
        List of data product summaries with basic information.
    """
    await ctx.info(f"dataproduct_search called with search_term={search_term}")
    
    try:
        client = DataMeshManagerClient()
        results = []
        
        # First, try the list endpoint (supports archetype and status filters)
        try:
            await ctx.info("Trying list endpoint first")
            data_products = await client.get_data_products(
                query=search_term,
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
                
                await ctx.info(f"List endpoint returned {len(results)} data products")
        
        except Exception as e:
            await ctx.warning(f"List endpoint failed: {str(e)}")
        
        # If no results from list endpoint or search_term provided, try semantic search
        if not results and search_term:
            try:
                await ctx.info("Trying semantic search endpoint")
                search_term_for_semantic_search = "Find data products related to " + search_term
                search_results = await client.search(search_term_for_semantic_search, resource_type="DATA_PRODUCT")
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
                
                await ctx.info(f"Search endpoint added {len(search_data_products)} additional data products")
            
            except Exception as e:
                await ctx.warning(f"Search endpoint failed: {str(e)}")

        if not results:
            await ctx.info("No data products found matching your search criteria")
            return []
        
        # Sanitize response for prompt injections
        results = sanitize_prompt_injection(results, "search_response")
        
        await ctx.info(f"dataproduct_search returned {len(results)} total data products")
        return results
        
    except ValueError as e:
        await ctx.error(f"dataproduct_search ValueError: {str(e)}")
        return [{"error": str(e)}]
    except Exception as e:
        await ctx.error(f"dataproduct_search Exception: {str(e)}")
        return [{"error": f"Error searching data products: {str(e)}"}]


@mcp.tool()
async def dataproduct_get(ctx: Context, data_product_id: str) -> Dict[str, Any]:
    """
    Get a data product by its ID. The data product contains all its output ports and server information.
    The response includes access status for each output port and inlines any data contracts.
    
    Args:
        data_product_id: The data product ID.
        
    Returns:
        Dict containing the data product details with enhanced output ports.
    """
    await ctx.info(f"dataproduct_get called with data_product_id={data_product_id}")
    
    try:
        client = DataMeshManagerClient()
        data_product = await client.get_data_product(data_product_id)
        
        if not data_product:
            await ctx.info(f"dataproduct_get: data product {data_product_id} not found")
            return {"error": "Data product not found"}
        
        # todo make null safe
        access_lifecycle_status = "You do not have access to this output port"

        # Add access status to each output port
        output_ports = data_product.get("outputPorts", [])
        for output_port in output_ports:
            try:
                output_port_id = output_port.get("id")
                if output_port_id:
                    await ctx.info(f"Checking access status for output port {output_port_id}")
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
                        output_port["accessStatus"] = f"You already have access to this output port (status: {access_status_value}, lifecycle: {lifecycle_status})"
                    elif lifecycle_status == "expired":
                        output_port["accessStatus"] = f"Your access request is expired (status: {access_status_value}, lifecycle: {lifecycle_status})"
                    else:
                        output_port["accessStatus"] = f"Access status: {access_status_value}, lifecycle: {lifecycle_status}"

                    await ctx.info(f"Added access status for output port {output_port_id}")
                else:
                    await ctx.warning(f"Output port missing externalId/id, skipping access status")
                    output_port["accessStatus"] = None
            except Exception as e:
                await ctx.warning(f"Failed to get access status for output port {output_port.get('externalId', 'unknown')}: {str(e)}")
                output_port["accessStatus"] = None
            
            # Resolve and inline data contract if dataContractId exists
            data_contract_id = output_port.get("dataContractId")
            if data_contract_id:
                try:
                    await ctx.info(f"Resolving data contract {data_contract_id} for output port {output_port.get('id', 'unknown')}")
                    data_contract = await client.get_data_contract(data_contract_id)
                    
                    if data_contract:
                        output_port["dataContract"] = data_contract
                        await ctx.info(f"Successfully inlined data contract {data_contract_id}")
                    else:
                        await ctx.warning(f"Data contract {data_contract_id} not found")
                        output_port["dataContract"] = None
                except Exception as e:
                    await ctx.warning(f"Failed to resolve data contract {data_contract_id}: {str(e)}")
                    output_port["dataContract"] = None
        
        # Sanitize response for prompt injections
        data_product = sanitize_prompt_injection(data_product, "get_response")
        
        # Return the enhanced data product directly as structured data
        await ctx.info(f"dataproduct_get successfully retrieved data product {data_product_id} with access status")
        return data_product
        
    except ValueError as e:
        await ctx.error(f"dataproduct_get ValueError: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        await ctx.error(f"dataproduct_get Exception: {str(e)}")
        return {"error": f"Error fetching data product: {str(e)}"}



@mcp.tool()
async def dataproduct_request_access(ctx: Context, data_product_id: str, output_port_id: str, purpose: str) -> Dict[str, Any]:
    """
    Request access to a specific output port of a data product.
    This creates an access request. Based on the data product configuration, purpose, and data governance rules,
    the access will be automatically granted, or it will be reviewed by the data product owner.
    
    Args:
        data_product_id: The ID of the data product.
        output_port_id: The ID of the output port to request access to.
        purpose: The business purpose/reason for requesting access to this data. Use a high-level description of why you need this data.
        
    Returns:
        Dict containing access request details including access_id, status, and approval information.
    """
    await ctx.info(f"dataproduct_request_access called with data_product_id={data_product_id}, output_port_id={output_port_id}, purpose={purpose}")
    
    try:
        client = DataMeshManagerClient()
        result = await client.post_request_access(data_product_id, output_port_id, purpose)
        
        # Check if access was automatically granted based on status
        status_lower = result.status.lower()
        auto_approved = status_lower in ["active"]
        
        # Return structured response data
        response = {
            "access_id": result.access_id,
            "status": result.status,
            "data_product_id": data_product_id,
            "output_port_id": output_port_id,
            "purpose": purpose,
            "auto_approved": auto_approved,
            "message": "Access granted automatically! You now have access to this data product output port using the server details and can start using the data immediately." if auto_approved else f"Access request submitted successfully and is now {result.status}. You will be notified when the data product owner reviews your request. You can check the status in dataproduct details in the output port."
        }
        
        await ctx.info(f"dataproduct_request_access successfully submitted for data_product_id={data_product_id}, access_id={result.access_id}, status={result.status}")
        return response
        
    except ValueError as e:
        await ctx.error(f"dataproduct_request_access ValueError: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        await ctx.error(f"dataproduct_request_access Exception: {str(e)}")
        return {"error": f"Error requesting access: {str(e)}"}


@mcp.tool()
async def dataproduct_query(ctx: Context, data_product_id: str, output_port_id: str, query: str) -> Dict[str, Any]:
    """
    Execute an SQL query on a data product's output port.
    This tool connects to the underlying data platform (Snowflake, Databricks) and executes the provided SQL query.
    You must have access to the output port to execute queries.
    
    Args:
        data_product_id: The ID of the data product.
        output_port_id: The ID of the output port to query.
        query: The SQL query to execute.
        
    Returns:
        Dict containing query results with row count and data (limited to 100 rows).
    """
    await ctx.info(f"dataproduct_query called with data_product_id={data_product_id}, output_port_id={output_port_id}")
    
    try:
        # First, get the data product details to retrieve server information
        client = DataMeshManagerClient()
        data_product = await client.get_data_product(data_product_id)
        
        if not data_product:
            await ctx.error(f"Data product {data_product_id} not found")
            return {"error": "Data product not found"}
        
        # Find the specified output port
        output_ports = data_product.get("outputPorts", [])
        target_output_port = None
        
        for output_port in output_ports:
            if output_port.get("id") == output_port_id:
                target_output_port = output_port
                break
        
        if not target_output_port:
            await ctx.error(f"Output port {output_port_id} not found in data product {data_product_id}")
            return {"error": "Output port not found"}
        
        # Check access status
        try:
            access_status = await client.get_access_status(data_product_id, output_port_id)
            if not access_status or access_status.access_lifecycle_status != "active":
                current_status = access_status.access_lifecycle_status if access_status else "unknown"
                await ctx.error(f"No active access to output port {output_port_id}, current status: {current_status}")
                return {"error": f"You do not have active access to this output port. Current access status: {current_status}. Please request access first using dataproduct_request_access."}
        except Exception as e:
            await ctx.error(f"Failed to check access status: {str(e)}")
            return {"error": "Unable to verify access status. Please ensure you have access to this output port."}

        # Apply security safeguards to prevent write operations and dangerous patterns
        if not validate_readonly_query(query):
            await ctx.error("Query validation failed: Query rejected for security reasons")
            return {"error": "Query rejected for security reasons"}
        
        await ctx.info("Query passed read-only validation")

        # Check that the query is in line with the purpose of the access agreement, and the data contract terms (dont be strict)
        # this check can be performed using a callback to the llm
        # todo

        # In the future, we can also check that the query is not violating any global policies


        # Get server information and type
        server_info = target_output_port.get("server", {})
        if not server_info:
            await ctx.error(f"No server information found for output port {output_port_id}")
            return {"error": "No server information available for this output port"}
        
        # Get server type from output port type field
        server_type = target_output_port.get("type", "").lower()
        if server_type not in ["snowflake", "databricks", "bigquery"]:
            await ctx.error(f"Unsupported server type: {server_type}")
            return {"error": f"Unsupported server type '{server_type}'. Supported types: snowflake, databricks, bigquery"}

        # Execute the query based on server type
        try:
            if server_type == "snowflake":
                results = await execute_snowflake_query(server_info, query)
            elif server_type == "databricks":
                results = await execute_databricks_query(server_info, query)
            elif server_type == "bigquery":
                results = await execute_bigquery_query(server_info, query)
            else:
                return {"error": f"Server type '{server_type}' is not yet supported by dataproduct-mcp. Supported types: snowflake, databricks, bigquery"}
            
            # Format results for display
            if not results:
                return {
                    "query": query,
                    "row_count": 0,
                    "results": [],
                    "message": "Query executed successfully, but returned no results."
                }
            
            # Return structured results data
            formatted_results = {
                "query": query,
                "row_count": len(results),
                "results": results[:100]  # Limit to first 100 rows to avoid overwhelming output
            }
            
            if len(results) > 100:
                formatted_results["note"] = f"Results truncated to first 100 rows. Total rows: {len(results)}"

            # Sanitize query results for prompt injections
            formatted_results = sanitize_prompt_injection(formatted_results, "query_results")

            await ctx.info(f"Query executed successfully, returned {len(results)} rows")
            return formatted_results
            
        except Exception as e:
            await ctx.error(f"Failed to execute query: {str(e)}")
            return {"error": f"Error executing query: {str(e)}"}
        
    except ValueError as e:
        await ctx.error(f"dataproduct_query ValueError: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        await ctx.error(f"dataproduct_query Exception: {str(e)}")
        return {"error": str(e)}


def main():
    """Entry point for the executable."""
    from importlib.metadata import version
    version("dataproduct-mcp")
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()