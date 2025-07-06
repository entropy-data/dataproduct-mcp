import pytest
import asyncio
from dataproduct_mcp.server import dataproduct_list, dataproduct_get, datacontract_get, dataproduct_search, dataproduct_request_access


class TestServer:
    """Test cases for the datamesh-manager-mcp server functions."""
    
    @pytest.mark.asyncio
    async def test_dataproduct_list_returns_list(self):
        """Test that dataproduct_list returns a list."""
        result = await dataproduct_list()
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_dataproduct_list_not_none(self):
        """Test that dataproduct_list returns a non-None result."""
        result = await dataproduct_list()
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_dataproduct_get_returns_string(self):
        """Test that dataproduct_get returns a string."""
        result = await dataproduct_get("test-id")
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_dataproduct_get_not_none(self):
        """Test that dataproduct_get returns a non-None result."""
        result = await dataproduct_get("test-id")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_datacontract_get_returns_string(self):
        """Test that datacontract_get returns a string."""
        result = await datacontract_get("test-id")
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_datacontract_get_not_none(self):
        """Test that datacontract_get returns a non-None result."""
        result = await datacontract_get("test-id")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_dataproduct_request_access_returns_string(self):
        """Test that dataproduct_request_access returns a string."""
        result = await dataproduct_request_access("test-product", "test-port", "test purpose")
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_dataproduct_request_access_not_none(self):
        """Test that dataproduct_request_access returns a non-None result."""
        result = await dataproduct_request_access("test-product", "test-port", "test purpose")
        assert result is not None


class TestServerIntegration:
    """Integration tests for the server."""
    
    @pytest.mark.asyncio
    async def test_dataproduct_list_function_callable(self):
        """Test that dataproduct_list is callable and doesn't raise exceptions."""
        try:
            result = await dataproduct_list()
            assert result is not None
        except Exception as e:
            pytest.fail(f"dataproduct_list raised an exception: {e}")
    
    @pytest.mark.asyncio
    async def test_dataproduct_get_function_callable(self):
        """Test that dataproduct_get is callable and doesn't raise exceptions."""
        try:
            result = await dataproduct_get("test-id")
            assert result is not None
        except Exception as e:
            pytest.fail(f"dataproduct_get raised an exception: {e}")
    
    @pytest.mark.asyncio
    async def test_datacontract_get_function_callable(self):
        """Test that datacontract_get is callable and doesn't raise exceptions."""
        try:
            result = await datacontract_get("test-id")
            assert result is not None
        except Exception as e:
            pytest.fail(f"datacontract_get raised an exception: {e}")
    
    @pytest.mark.asyncio
    async def test_dataproduct_request_access_function_callable(self):
        """Test that dataproduct_request_access is callable and doesn't raise exceptions."""
        try:
            result = await dataproduct_request_access("test-product", "test-port", "test purpose")
            assert result is not None
        except Exception as e:
            pytest.fail(f"dataproduct_request_access raised an exception: {e}")