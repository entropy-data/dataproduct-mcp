from typing import Any, Dict, List
import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class SnowflakeClient:
    """Snowflake database client for executing SQL queries."""
    
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
            'account': 'Snowflake account identifier',
            'user': 'Snowflake username',
            'password': 'Snowflake password'
        }
        
        for param, description in required_params.items():
            if param not in params or params[param] is None:
                missing_params.append(f"• {description} (set via server info or {param.upper()} environment variable)")
            else:
                cleaned_params[param] = params[param]
        
        if missing_params:
            env_vars = "Environment variables: SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_ROLE"
            raise ValueError(
                f"Missing required Snowflake connection parameters:\n"
                f"{chr(10).join(missing_params)}\n\n"
                f"Please provide these either in the data product server configuration or as environment variables.\n"
                f"{env_vars}"
            )
        
        # Optional parameters
        optional_params = ['warehouse', 'database', 'schema', 'role']
        for param in optional_params:
            if param in params and params[param] is not None:
                cleaned_params[param] = params[param]
        
        return cleaned_params
    
    async def connect(self) -> None:
        """Establish Snowflake connection."""
        if self.connection:
            return
            
        try:
            import snowflake.connector
            
            logger.info("Connecting to Snowflake...")
            loop = asyncio.get_event_loop()
            self.connection = await loop.run_in_executor(
                self.executor,
                lambda: snowflake.connector.connect(**self.connection_params)
            )
            logger.info("Successfully connected to Snowflake")
        except ImportError:
            logger.error("snowflake-connector-python is not installed")
            raise ValueError("snowflake-connector-python package is required for Snowflake connections")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {str(e)}")
            raise
    
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query on Snowflake."""
        if not self.connection:
            await self.connect()
        
        try:
            logger.info(f"Executing Snowflake query: {query[:100]}...")
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
            logger.info(f"Snowflake query executed successfully, returned {len(results)} rows")
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute query on Snowflake: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close Snowflake connection."""
        if self.connection:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, self.connection.close)
                logger.info("Snowflake connection closed")
            except Exception as e:
                logger.error(f"Error closing Snowflake connection: {str(e)}")
            finally:
                self.connection = None
        
        self.executor.shutdown(wait=False)
    
    @staticmethod
    def parse_connection_params(server_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Snowflake connection parameters from server info."""
        account = server_info.get("account")
        user = server_info.get("user") or os.getenv("SNOWFLAKE_USER")
        password = server_info.get("password") or os.getenv("SNOWFLAKE_PASSWORD")
        warehouse = server_info.get("warehouse") or os.getenv("SNOWFLAKE_WAREHOUSE")
        role = server_info.get("role") or os.getenv("SNOWFLAKE_ROLE")
        
        # Validate account format (should be organization_identifier-account_identfier)
        if account and '-' not in account:
            raise ValueError(
                f"Invalid Snowflake account format: '{account}'. "
                f"Account should be in format 'organization_identifier-account_identfier' (e.g., 'lmabcde-xn12345'). "
                f"Please check your Snowflake account identifier."
            )
        
        # Check for missing required parameters and provide setup instructions
        missing_params = []
        env_instructions = []
        
        if not account:
            missing_params.append("• Snowflake account identifier")
        if not user:
            missing_params.append("• Snowflake username")
            env_instructions.append("export SNOWFLAKE_USER=your_username")
        if not password:
            missing_params.append("• Snowflake password")
            env_instructions.append("export SNOWFLAKE_PASSWORD=your_password")
        if not warehouse:
            missing_params.append("• Snowflake warehouse")
            env_instructions.append("export SNOWFLAKE_WAREHOUSE=your_warehouse")
        if not role:
            missing_params.append("• Snowflake role")
            env_instructions.append("export SNOWFLAKE_ROLE=your_role")
        
        if missing_params:
            setup_msg = ""
            if env_instructions:
                setup_msg = f"\n\nTo set up environment variables, run:\n{chr(10).join(env_instructions)}"
            
            raise ValueError(
                f"Missing required Snowflake connection parameters:\n"
                f"{chr(10).join(missing_params)}\n"
                f"Please provide these either in the data product server configuration or as environment variables."
                f"{setup_msg}"
            )
        
        return {
            "account": account,
            "user": user,
            "password": password,
            "warehouse": warehouse,
            "database": server_info.get("database"),
            "schema": server_info.get("schema"),
            "role": role,
        }


# Global connection pool for Snowflake connections
_snowflake_connections: Dict[str, SnowflakeClient] = {}


async def execute_snowflake_query(server_info: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Execute query on Snowflake using connection pooling."""
    connection_params = SnowflakeClient.parse_connection_params(server_info)
    connection_key = f"snowflake_{hash(frozenset(connection_params.items()))}"
    
    if connection_key not in _snowflake_connections:
        _snowflake_connections[connection_key] = SnowflakeClient(connection_params)
    
    client = _snowflake_connections[connection_key]
    return await client.execute_query(query)