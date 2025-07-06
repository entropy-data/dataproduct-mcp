import pytest
import os
from dataproduct_mcp.server import dataproduct_get, dataproduct_list, datacontract_get, dataproduct_search


class TestIntegration:
    """Integration tests that make real API calls to the Data Mesh Manager service."""
    
    @pytest.fixture(autouse=True)
    def check_api_key(self):
        """Check if API key is available, skip tests if not."""
        api_key = os.getenv("DATAMESH_MANAGER_API_KEY")
        if not api_key:
            pytest.skip("DATAMESH_MANAGER_API_KEY environment variable not set - skipping integration tests")
    
    @pytest.mark.asyncio
    async def test_dataproduct_get_real_api_call(self):
        """Test dataproduct_get with a real API call."""
        # First get a list of available data products to find a valid ID
        products = await dataproduct_list()
        
        # Skip if no products available
        if not products or len(products) == 0:
            pytest.skip("No data products available for testing")
        
        # Use the first product ID for testing
        product_id = products[0].get("id")
        if not product_id:
            pytest.skip("No valid product ID found in the first product")
        
        # Test getting the specific data product
        result = await dataproduct_get(product_id)
        
        # Verify the result
        assert isinstance(result, str)
        assert len(result) > 0
        assert product_id in result
        
        # Should contain YAML-like structure
        assert "id:" in result or "title:" in result
    
