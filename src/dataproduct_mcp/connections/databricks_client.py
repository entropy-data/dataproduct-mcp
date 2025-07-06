from typing import Any, Dict, List
import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class DatabricksClient:
    """Databricks database client for executing SQL queries."""
    
    def __init__(self, connection_params: Dict[str, Any]):
        self.connection_params = self._validate_and_clean_params(connection_params)
        self.connection = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def _validate_and_clean_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean connection parameters."""
        cleaned_params = {}
        missing_params = []
        
        # Required parameters with user-friendly names
        required_params = {
            'server_hostname': 'Databricks server hostname',
            'http_path': 'Databricks HTTP path (cluster/warehouse path)',
            'access_token': 'Databricks access token'
        }
        
        for param, description in required_params.items():
            if param not in params or params[param] is None:
                env_var = "DATABRICKS_ACCESS_TOKEN" if param == 'access_token' else f"DATABRICKS_{param.upper()}"
                missing_params.append(f"• {description} (set via server info or {env_var} environment variable)")
            else:
                cleaned_params[param] = params[param]
        
        if missing_params:
            env_vars = "Environment variables: DATABRICKS_ACCESS_TOKEN"
            raise ValueError(
                f"Missing required Databricks connection parameters:\n"
                f"{chr(10).join(missing_params)}\n\n"
                f"Please provide these either in the data product server configuration or as environment variables.\n"
                f"{env_vars}"
            )
        
        # Optional parameters
        optional_params = ['catalog', 'schema']
        for param in optional_params:
            if param in params and params[param] is not None:
                cleaned_params[param] = params[param]
        
        return cleaned_params
    
    async def connect(self) -> None:
        """Establish Databricks connection."""
        if self.connection:
            return
            
        try:
            from databricks import sql
            
            logger.info("Connecting to Databricks...")
            loop = asyncio.get_event_loop()
            self.connection = await loop.run_in_executor(
                self.executor,
                lambda: sql.connect(**self.connection_params)
            )
            logger.info("Successfully connected to Databricks")
        except ImportError:
            logger.error("databricks-sql-connector is not installed")
            raise ValueError("databricks-sql-connector package is required for Databricks connections")
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
        server_hostname = server_info.get("hostname") or server_info.get("host")
        http_path = server_info.get("http_path") or server_info.get("path")
        access_token = server_info.get("access_token") or os.getenv("DATABRICKS_ACCESS_TOKEN")
        
        # Check for missing required parameters and provide setup instructions
        missing_params = []
        env_instructions = []
        
        if not server_hostname:
            missing_params.append("• Databricks server hostname")
        if not http_path:
            missing_params.append("• Databricks HTTP path (cluster/warehouse path)")
        if not access_token:
            missing_params.append("• Databricks access token")
            env_instructions.append("export DATABRICKS_ACCESS_TOKEN=your_access_token")
        
        if missing_params:
            setup_msg = ""
            if env_instructions:
                setup_msg = f"\n\nTo set up environment variables, run:\n{chr(10).join(env_instructions)}"
                setup_msg += "\n\nTo get your Databricks access token:"
                setup_msg += "\n1. Go to your Databricks workspace"
                setup_msg += "\n2. Click on your username in the top right"
                setup_msg += "\n3. Select 'Settings' > 'Developer' > 'Access tokens'"
                setup_msg += "\n4. Click 'Generate new token'"
            
            raise ValueError(
                f"Missing required Databricks connection parameters:\n"
                f"{chr(10).join(missing_params)}\n"
                f"Please provide these either in the data product server configuration or as environment variables."
                f"{setup_msg}"
            )
        
        return {
            "server_hostname": server_hostname,
            "http_path": http_path,
            "access_token": access_token,
            "catalog": server_info.get("catalog"),
            "schema": server_info.get("schema"),
        }


# Global connection pool for Databricks connections
_databricks_connections: Dict[str, DatabricksClient] = {}


async def execute_databricks_query(server_info: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Execute query on Databricks using connection pooling."""
    connection_params = DatabricksClient.parse_connection_params(server_info)
    connection_key = f"databricks_{hash(frozenset(connection_params.items()))}"
    
    if connection_key not in _databricks_connections:
        _databricks_connections[connection_key] = DatabricksClient(connection_params)
    
    client = _databricks_connections[connection_key]
    return await client.execute_query(query)