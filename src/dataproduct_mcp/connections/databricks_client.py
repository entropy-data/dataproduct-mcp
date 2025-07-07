from typing import Any, Dict, List
import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from databricks.sdk.core import Config, oauth_service_principal
from databricks import sql

logger = logging.getLogger(__name__)


class DatabricksClient:
    """Databricks database client for executing SQL queries."""
    
    def __init__(self, server_hostname: str, http_path: str, client_id: str, client_secret: str, catalog: str = None, schema: str = None):
        self.server_hostname = self._validate_required_param(server_hostname, "server_hostname")
        self.http_path = self._validate_required_param(http_path, "http_path")
        self.client_id = self._validate_required_param(client_id, "client_id")
        self.client_secret = self._validate_required_param(client_secret, "client_secret")
        self.catalog = catalog
        self.schema = schema
        self.connection = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def _validate_required_param(self, value: str, param_name: str) -> str:
        """Validate required parameter."""
        if not value or value is None:
            raise ValueError(f"Missing required parameter: {param_name}")
        return value
    
    def _create_credential_provider(self):
        """Create OAuth service principal credential provider."""
        def credential_provider():
            config = Config(
                host=f"https://{self.server_hostname}",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            return oauth_service_principal(config)
        return credential_provider
    
    async def connect(self) -> None:
        """Establish Databricks connection."""
        if self.connection:
            return
            
        try:
            logger.info("Connecting to Databricks...")
            logger.info(f"Connection details - hostname: {self.server_hostname}, http_path: {self.http_path}, catalog: {self.catalog}, schema: {self.schema}, client_id: {self.client_id[:8]}***")
            loop = asyncio.get_event_loop()
            credential_provider = self._create_credential_provider()
            self.connection = await loop.run_in_executor(
                self.executor,
                lambda: sql.connect(
                    server_hostname=self.server_hostname,
                    http_path=self.http_path,
                    credentials_provider=credential_provider,
                    catalog=self.catalog,
                    schema=self.schema
                )
            )
            logger.info("Successfully connected to Databricks")
        except ImportError:
            logger.error("databricks-sql-connector and databricks-sdk are not installed")
            raise ValueError("databricks-sql-connector and databricks-sdk packages are required for Databricks connections")
        except Exception as e:
            logger.error(f"Failed to connect to Databricks: {str(e)}")
            raise
    
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query on Databricks."""
        if not self.connection:
            await self.connect()
        
        try:
            logger.info(f"Executing Databricks query: {query[:100]}...")
            loop = asyncio.get_event_loop()
            
            def _execute():
                cursor = self.connection.cursor()
                try:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                finally:
                    cursor.close()
            
            results = await loop.run_in_executor(self.executor, _execute)
            logger.info(f"Databricks query executed successfully, returned {len(results)} rows")
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute query on Databricks: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close Databricks connection."""
        if self.connection:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, self.connection.close)
                logger.info("Databricks connection closed")
            except Exception as e:
                logger.error(f"Error closing Databricks connection: {str(e)}")
            finally:
                self.connection = None
        
        self.executor.shutdown(wait=False)
    
    @staticmethod
    def parse_connection_params(server_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Databricks connection parameters from server info."""
        server_hostname = server_info.get("hostname") or server_info.get("host") or os.getenv("DATABRICKS_HOST")
        
        # Clean hostname by removing https:// prefix and / suffix
        if server_hostname:
            if server_hostname.startswith("https://"):
                server_hostname = server_hostname[8:]
            if server_hostname.endswith("/"):
                server_hostname = server_hostname[:-1]
        http_path = server_info.get("http_path") or server_info.get("path") or os.getenv("DATABRICKS_HTTP_PATH")
        client_id = server_info.get("client_id") or os.getenv("DATABRICKS_CLIENT_ID")
        client_secret = server_info.get("client_secret") or os.getenv("DATABRICKS_CLIENT_SECRET")
        
        # Check for missing required parameters and provide setup instructions
        missing_params = []
        env_instructions = []
        
        if not server_hostname:
            missing_params.append("• Databricks server hostname")
            env_instructions.append("export DATABRICKS_HOST=your_databricks_host")
        if not http_path or not http_path.startswith("/"):
            missing_params.append("• Databricks HTTP path (cluster/warehouse path)")
            env_instructions.append("export DATABRICKS_HTTP_PATH=your_http_path")
        if not client_id:
            missing_params.append("• Databricks client ID")
            env_instructions.append("export DATABRICKS_CLIENT_ID=your_client_id")
        if not client_secret:
            missing_params.append("• Databricks client secret")
            env_instructions.append("export DATABRICKS_CLIENT_SECRET=your_client_secret")
        
        if missing_params:
            setup_msg = ""
            if env_instructions:
                setup_msg = f"\n\nTo set up environment variables, run:\n{chr(10).join(env_instructions)}"
                setup_msg += "\n\nTo get your Databricks OAuth credentials:"
                setup_msg += "\n1. Go to your Databricks workspace"
                setup_msg += "\n2. Click on your username in the top right"
                setup_msg += "\n3. Select 'Settings' > 'Developer' > 'App connections'"
                setup_msg += "\n4. Create a new OAuth app or use existing credentials"
            
            raise ValueError(
                f"Missing required Databricks connection parameters:\n"
                f"{chr(10).join(missing_params)}\n"
                f"Please provide these either in the data product server configuration or as environment variables."
                f"{setup_msg}"
            )
        
        return {
            "server_hostname": server_hostname,
            "http_path": http_path,
            "client_id": client_id,
            "client_secret": client_secret,
            "catalog": server_info.get("catalog"),
            "schema": server_info.get("schema")
        }


# Global connection pool for Databricks connections
_databricks_connections: Dict[str, DatabricksClient] = {}


async def execute_databricks_query(server_info: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Execute query on Databricks using connection pooling."""
    connection_params = DatabricksClient.parse_connection_params(server_info)
    connection_key = f"databricks_{hash(frozenset(connection_params.items()))}"
    
    if connection_key not in _databricks_connections:
        _databricks_connections[connection_key] = DatabricksClient(
            server_hostname=connection_params["server_hostname"],
            http_path=connection_params["http_path"],
            client_id=connection_params["client_id"],
            client_secret=connection_params["client_secret"],
            catalog=connection_params.get("catalog"),
            schema=connection_params.get("schema")
        )
    
    client = _databricks_connections[connection_key]
    return await client.execute_query(query)