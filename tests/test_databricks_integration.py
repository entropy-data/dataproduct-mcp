import pytest
import os
import sys

# Import from src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dataproduct_mcp.connections.databricks_client import execute_databricks_query


@pytest.mark.skipif(not all(os.getenv(var) for var in ["DATABRICKS_HOST", "DATABRICKS_HTTP_PATH", "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET"]), reason="Databricks environment variables not set")
class TestDatabricksIntegration:
    """Integration tests for Databricks client connectivity and functionality."""

    @pytest.mark.asyncio
    async def test_databricks_simple_query_execution(self):
        """Test executing a simple query through the Databricks client."""
        # Use a simple query that should work on any Databricks environment
        test_query = "SELECT 1 as test_column"
        
        # Inline server info for testing
        databricks_server_info = {
            "catalog": "sales_customers_demo",
            "schema": "dp_customers_v1"
        }

        # Execute the query
        results = await execute_databricks_query(databricks_server_info, test_query)

        # Verify the results
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert "test_column" in results[0]
        assert results[0]["test_column"] == 1
            
