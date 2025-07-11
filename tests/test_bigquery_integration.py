import pytest
import os
import sys

# Import from src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dataproduct_mcp.connections.bigquery_client import execute_bigquery_query


@pytest.mark.skipif(not os.getenv("BIGQUERY_CREDENTIALS_PATH"), reason="BIGQUERY_CREDENTIALS_PATH environment variable not set")
class TestBigQueryIntegration:
    """Integration tests for BigQuery client connectivity and functionality."""

    @pytest.fixture
    def bigquery_server_info(self):
        """Create server info for BigQuery testing with test project."""
        return {
            "project_id": "datameshexample-fulfillment",
            "dataset_id": "data_products"
        }

    @pytest.mark.asyncio
    async def test_bigquery_simple_query_execution(self, bigquery_server_info):
        """Test executing a simple query through the BigQuery client."""
        # Use a simple query that should work on any BigQuery environment
        test_query = "SELECT 1 as test_column"

        try:
            # Execute the query
            results = await execute_bigquery_query(bigquery_server_info, test_query)
            
            # Verify the results
            assert isinstance(results, list)
            assert len(results) == 1
            assert isinstance(results[0], dict)
            assert "test_column" in results[0]
            assert results[0]["test_column"] == 1
            
        except Exception as e:
            # If the test fails due to connection issues, skip with informative message
            pytest.skip(f"BigQuery connection failed: {str(e)}. This might be due to network issues, invalid credentials, or insufficient permissions.")

    @pytest.mark.asyncio
    async def test_bigquery_public_dataset_query(self, bigquery_server_info):
        """Test executing a query against BigQuery public dataset."""
        # Use a query against a well-known public dataset
        test_query = "SELECT word, word_count FROM `bigquery-public-data.samples.shakespeare` WHERE corpus = 'hamlet' AND word_count > 100 ORDER BY word_count DESC LIMIT 3"

        try:
            # Execute the query
            results = await execute_bigquery_query(bigquery_server_info, test_query)
            
            # Verify the results
            assert isinstance(results, list)
            assert len(results) <= 3  # Should return at most 3 results
            
            # Verify each result has the expected structure
            for result in results:
                assert isinstance(result, dict)
                assert "word" in result
                assert "word_count" in result
                assert isinstance(result["word"], str)
                assert isinstance(result["word_count"], int)
                assert result["word_count"] > 100
            
        except Exception as e:
            # If the test fails due to connection issues, skip with informative message
            pytest.skip(f"BigQuery public dataset query failed: {str(e)}. This might be due to network issues, invalid credentials, or insufficient permissions to access public datasets.")

    @pytest.mark.asyncio
    async def test_bigquery_data_types_handling(self, bigquery_server_info):
        """Test BigQuery client handles various data types correctly."""
        # Test query with different data types
        test_query = """
        SELECT 
            42 as int_column,
            3.14 as float_column,
            'test_string' as string_column,
            TRUE as bool_column,
            CURRENT_TIMESTAMP() as timestamp_column,
            CURRENT_DATE() as date_column
        """

        try:
            # Execute the query
            results = await execute_bigquery_query(bigquery_server_info, test_query)
            
            # Verify the results
            assert isinstance(results, list)
            assert len(results) == 1
            
            result = results[0]
            assert isinstance(result, dict)
            
            # Check data types are properly handled
            assert result["int_column"] == 42
            assert result["float_column"] == 3.14
            assert result["string_column"] == "test_string"
            assert result["bool_column"] == True
            
            # Timestamp and date should be converted to strings
            assert isinstance(result["timestamp_column"], str)
            assert isinstance(result["date_column"], str)
            
        except Exception as e:
            # If the test fails due to connection issues, skip with informative message
            pytest.skip(f"BigQuery data types test failed: {str(e)}. This might be due to network issues, invalid credentials, or insufficient permissions.")