"""Shared pytest fixtures and configuration for datamesh-manager-mcp tests."""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_dataproduct_response():
    """Sample response for testing data product functionality."""
    return "No Data Products Found" 