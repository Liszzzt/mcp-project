import pytest
from pathlib import Path
from app.mcp.config import Config
from app.mcp.server import MCPServer

@pytest.fixture
def config_paths():
    base_dir = Path(__file__).parent.parent.parent.parent
    return {
        'config': base_dir / 'mcp_config.json',
        'env': base_dir / '.env'
    }

@pytest.fixture
def mcp_config(config_paths):
    return Config(config_paths['config'], config_paths['env'])

@pytest.mark.integration
@pytest.mark.asyncio
async def test_filesystem_server(mcp_config):
    """Test filesystem MCP server initialization and basic operations."""
    server_config = mcp_config.get_server_config("filesystem")
    server = MCPServer("filesystem", server_config)
    
    try:
        await server.initialize()
        assert server.session is not None
        assert len(server.tools) > 0
        
        # Test listing a directory
        result = await server.execute_tool(
            "list_directory",
            {"path": "."}
        )
        # Check for string content instead of list
        assert isinstance(result, str)
        assert "[FILE]" in result or "[DIR]" in result
        
    finally:
        await server.cleanup()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_server(mcp_config):
    """Test fetch MCP server initialization and basic operations."""
    server_config = mcp_config.get_server_config("fetch")
    server = MCPServer("fetch", server_config)
    await server.initialize()
    
    try:
        assert server.session is not None
        assert len(server.tools) > 0

        # Test fetching a URL
        result = await server.execute_tool(
            "fetch",
            {"url": "https://httpbin.org/get"}
        )
        assert isinstance(result, str)  # Result is text content
        assert "httpbin.org" in result
    finally:
        await server.cleanup()
