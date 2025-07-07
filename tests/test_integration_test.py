import pytest
import os
from unittest.mock import AsyncMock

# Import from src directory
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dataproduct_mcp.server import dataproduct_get, dataproduct_search


class TestIntegration:
    """Integration tests that make real API calls to the Data Mesh Manager service."""
    
    @pytest.fixture(autouse=True)
    def check_api_key(self):
        """Check if API key is available, skip tests if not."""
        api_key = os.getenv("DATAMESH_MANAGER_API_KEY")
        if not api_key:
            pytest.skip("DATAMESH_MANAGER_API_KEY environment variable not set - skipping integration tests")
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        ctx = AsyncMock()
        ctx.info = AsyncMock()
        ctx.warning = AsyncMock()
        ctx.error = AsyncMock()
        return ctx

    @pytest.mark.asyncio
    async def test_dataproduct_get_real_api_call(self, mock_context):
        """Test dataproduct_get with a real API call."""
        # First get a list of available data products to find a valid ID
        products = await dataproduct_search(mock_context)
        
        # Skip if no products available
        if not products or len(products) == 0:
            pytest.skip("No data products available for testing")
        
        # Use the first product ID for testing
        product_id = products[0].get("id")
        if not product_id:
            pytest.skip("No valid product ID found in the first product")
        
        # Test getting the specific data product
        result = await dataproduct_get(mock_context, product_id)
        
        # Verify the result
        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == product_id


