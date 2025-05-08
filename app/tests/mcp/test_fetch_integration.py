import pytest
import pytest_asyncio
from app.mcp.server import MCPServer

@pytest_asyncio.fixture
async def fetch_server(mcp_config):
    """Initialize and provide a fetch server instance."""
    server_config = mcp_config.get_server_config("fetch")
    server = MCPServer("fetch", server_config)
    await server.initialize()
    try:
        yield server
    finally:
        await server.cleanup()

@pytest.mark.fetch
@pytest.mark.asyncio
async def test_basic_fetch(fetch_server: MCPServer):
    """Test basic URL fetching with markdown conversion."""
    result = await fetch_server.execute_tool(
        "fetch",
        {
            "url": "https://httpbin.org/html"
        }
    )
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.fetch
@pytest.mark.asyncio
async def test_fetch_with_length_limit(fetch_server: MCPServer):
    """Test fetching with max_length parameter."""
    max_length = 100
    result = await fetch_server.execute_tool(
        "fetch",
        {
            "url": "https://httpbin.org/html",
            "max_length": max_length
        }
    )
    assert len(result) <= max_length

@pytest.mark.fetch
@pytest.mark.asyncio
async def test_fetch_raw_content(fetch_server: MCPServer):
    """Test fetching raw content without markdown conversion."""
    result = await fetch_server.execute_tool(
        "fetch",
        {
            "url": "https://httpbin.org/html",
            "raw": True
        }
    )
    assert "<html" in result.lower()

@pytest.mark.fetch
@pytest.mark.asyncio
async def test_fetch_error_handling(fetch_server: MCPServer):
    """Test error handling for invalid URLs."""
    try:
        result = await fetch_server.execute_tool(
            "fetch",
            {
                "url": "https://invalid-url-that-does-not-exist-123456.com"
            }
        )
        # Only check result if no exception was raised
        result_str = str(result).lower()
        assert any(err in result_str for err in [
            "error", "failed", "connection", "invalid", "not found"
        ]), "Expected error in response"
    except Exception as e:
        # Verify that the exception message indicates an error condition
        error_str = str(e).lower()
        assert any(err in error_str for err in [
            "error", "failed", "connection", "invalid", "not found"
        ]), "Expected error in exception"
