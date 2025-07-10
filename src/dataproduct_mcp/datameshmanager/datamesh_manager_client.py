import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from .models import AccessStatusResult, RequestAccessRequest, RequestAccessResult


class DataMeshManagerClient:
    """Client for interacting with the Data Mesh Manager API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the Data Mesh Manager client.
        
        Args:
            api_key: API key for authentication. If not provided, will try to get from DATAMESH_MANAGER_API_KEY env var.
            base_url: Base URL for the API. If not provided, will try to get from DATAMESH_MANAGER_HOST env var,
                     otherwise defaults to the production API.
        """
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        self.api_key = api_key or os.getenv("DATAMESH_MANAGER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DATAMESH_MANAGER_API_KEY is required but not found.\n\n"
                "To set up your API key:\n"
                "1. Go to Data Mesh Manager (https://app.datamesh-manager.com)\n"
                "2. Select 'Organization Settings'\n"
                "3. Go to 'API Keys'\n"
                "4. Create a new API Key with scope 'User'\n"
                "5. Copy the Secret API Key\n"
                "6. Add DATAMESH_MANAGER_API_KEY to your MCP configuration environment variables\n\n"
                "Example MCP configuration:\n"
                "{\n"
                '  "mcpServers": {\n'
                '    "dataproduct": {\n'
                '      "command": "uv",\n'
                '      "args": ["run", "--directory", "<path_to_folder>/dataproduct-mcp", "python", "-m", "dataproduct_mcp.server"],\n'
                '      "env": {\n'
                '        "DATAMESH_MANAGER_API_KEY": "dmm_live_..."\n'
                '      }\n'
                '    }\n'
                '  }\n'
                "}"
            )
        
        # Use provided base_url, or fall back to DATAMESH_MANAGER_HOST env var if set and not empty, or default
        env_host = os.getenv("DATAMESH_MANAGER_HOST")
        if base_url:
            self.base_url = base_url.rstrip('/')
        elif env_host and env_host.strip():
            self.base_url = env_host.rstrip('/')
        else:
            self.base_url = "https://api.datamesh-manager.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_data_products(
        self, 
        query: Optional[str] = None,
        archetype: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        sort: Optional[str] = None,
        page: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all data products of an organization.
        
        Args:
            query: Search term to filter data products. Searches in id, title, and description.
            archetype: Filter for specific types.
            status: Filter for specific status.
            tag: Filter for specific tags.
            sort: Field to sort by, default is creation date.
            page: The number of the requested page, starting from 0.
            
        Returns:
            List of data products.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        params = {}
        if query:
            params["q"] = query
        if archetype:
            params["archetype"] = archetype
        if status:
            params["status"] = status
        if tag:
            params["tag"] = tag
        if sort:
            params["sort"] = sort
        if page is not None:
            params["p"] = page
            
        url = f"{self.base_url}/api/dataproducts"
        
        self.logger.info(f"Making GET request to {url} with params: {params}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"GET request to {url} successful, status: {response.status_code}")
            return data
    
    async def get_data_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get a specific data product by its ID.
        
        Args:
            product_id: The ID of the data product.
            
        Returns:
            The data product details.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        url = f"{self.base_url}/api/dataproducts/{product_id}"
        
        self.logger.info(f"Making GET request to {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"GET request to {url} successful, status: {response.status_code}")
            return data
    
    async def create_or_update_data_product(self, data_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new data product or update an existing one.
        
        Args:
            data_product: The data product to create or update.
            
        Returns:
            The created or updated data product.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        product_id = data_product.get("id")
        if not product_id:
            raise ValueError("Data product must have an 'id' field")
            
        url = f"{self.base_url}/api/dataproducts/{product_id}"
        
        self.logger.info(f"Making PUT request to {url}")
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=self.headers, json=data_product)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"PUT request to {url} successful, status: {response.status_code}")
            return data
    
    async def delete_data_product(self, product_id: str) -> bool:
        """
        Delete a data product by its ID.
        
        Args:
            product_id: The ID of the data product to delete.
            
        Returns:
            True if the data product was deleted successfully.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        url = f"{self.base_url}/api/dataproducts/{product_id}"
        
        self.logger.info(f"Making DELETE request to {url}")
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers)
            response.raise_for_status()
            self.logger.info(f"DELETE request to {url} successful, status: {response.status_code}")
            return True
    
    async def get_data_contracts(
        self,
        query: Optional[str] = None,
        owner: Optional[str] = None,
        domain: Optional[str] = None,
        tag: Optional[str] = None,
        sort: Optional[str] = None,
        page: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all data contracts.
        
        Args:
            query: Search term to filter data contracts.
            owner: Filter for specific owners (team name).
            domain: Filter for specific domain (domain name).
            tag: Filter for specific tags.
            sort: Field to sort by, default is creation date.
            page: The number of the requested page, starting from 0.
            
        Returns:
            List of data contracts.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        params = {}
        if query:
            params["q"] = query
        if owner:
            params["owner"] = owner
        if domain:
            params["domain"] = domain
        if tag:
            params["tag"] = tag
        if sort:
            params["sort"] = sort
        if page is not None:
            params["p"] = page
            
        url = f"{self.base_url}/api/datacontracts"
        
        self.logger.info(f"Making GET request to {url} with params: {params}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"GET request to {url} successful, status: {response.status_code}")
            return data
    
    async def get_data_contract(self, contract_id: str) -> Dict[str, Any]:
        """
        Get a specific data contract by its ID.
        
        Args:
            contract_id: The ID of the data contract.
            
        Returns:
            The data contract details.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        url = f"{self.base_url}/api/datacontracts/{contract_id}"
        
        self.logger.info(f"Making GET request to {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"GET request to {url} successful, status: {response.status_code}")
            return data
    
    async def search(self, search_term: str, resource_type: str = "DATA_PRODUCT") -> List[Dict[str, Any]]:
        """
        Perform semantic search for data products based on a user question or use case.
        
        Args:
            search_term: The search query/question to find relevant data products.
            resource_type: The type of resource to search for. Defaults to "DATA_PRODUCT".
            
        Returns:
            List of relevant data products based on semantic search.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        if not search_term:
            raise ValueError("Search term is required for semantic search")
            
        url = f"{self.base_url}/api/search"
        params = {
            "query": search_term,
            "resourceType": resource_type
        }
        
        self.logger.info(f"Making GET request to {url} with params: {params}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"GET request to {url} successful, status: {response.status_code}")
            return data
    
    async def get_access_status(self, data_product_external_id: str, output_port_external_id: str) -> AccessStatusResult:
        """
        Get access status for a specific output port of a data product.
        This is a private endpoint that requires internal API access.
        
        Args:
            data_product_external_id: The external ID of the data product.
            output_port_external_id: The external ID of the output port.
            
        Returns:
            Access status information including data product ID, output port ID, 
            data contract ID, output port type, auto-approve status, access ID, 
            access status, and access lifecycle status.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        if not data_product_external_id:
            raise ValueError("Data product external ID is required")
        if not output_port_external_id:
            raise ValueError("Output port external ID is required")
            
        url = f"{self.base_url}/api/dataproducts/{data_product_external_id}/outputports/{output_port_external_id}/access-status"
        
        # Add the internal API header required for this private endpoint
        headers = self.headers.copy()
        headers["x-internal-api"] = "true"
        
        self.logger.info(f"Making GET request to {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"GET request to {url} successful, status: {response.status_code}")
            return AccessStatusResult(**data)
    
    async def post_request_access(
        self, 
        data_product_external_id: str, 
        output_port_external_id: str, 
        purpose: str
    ) -> RequestAccessResult:
        """
        Request access to a specific output port of a data product.
        This is a private endpoint that requires internal API access and user scope.
        
        Args:
            data_product_external_id: The external ID of the data product.
            output_port_external_id: The external ID of the output port.
            purpose: The purpose/reason for requesting access to the data.
            
        Returns:
            Request access result containing access ID and status.
            
        Raises:
            httpx.HTTPStatusError: If the API request fails.
            ValueError: If required parameters are missing.
        """
        if not data_product_external_id:
            raise ValueError("Data product external ID is required")
        if not output_port_external_id:
            raise ValueError("Output port external ID is required")
        if not purpose:
            raise ValueError("Purpose is required for access request")
            
        url = f"{self.base_url}/api/dataproducts/{data_product_external_id}/outputports/{output_port_external_id}/request-access"
        
        # Add the internal API header required for this private endpoint
        headers = self.headers.copy()
        headers["x-internal-api"] = "true"
        
        # Create the request payload
        request_data = RequestAccessRequest(purpose=purpose)
        
        self.logger.info(f"Making POST request to {url} with purpose: {purpose}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=request_data.model_dump(by_alias=True))
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"POST request to {url} successful, status: {response.status_code}")
            return RequestAccessResult(**data)