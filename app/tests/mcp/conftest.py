import pytest
import pytest_asyncio
from pathlib import Path
from app.mcp.config import Config
from app.mcp.server import MCPServer

@pytest.fixture
def mcp_config():
    """Provide configuration for MCP servers."""
    base_dir = Path(__file__).parent.parent.parent.parent
    return Config(
        config_path=base_dir / 'mcp_config.json',
        env_path=base_dir / '.env'
    )

@pytest_asyncio.fixture
async def fs_server(mcp_config):
    """Initialize and provide a filesystem server instance."""
    server_config = mcp_config.get_server_config("filesystem")
    server = MCPServer("filesystem", server_config)
    await server.initialize()
    yield server
    await server.cleanup()

@pytest_asyncio.fixture
async def fetch_server(mcp_config):
    """Initialize and provide a fetch server instance."""
    server_config = mcp_config.get_server_config("fetch")
    server = MCPServer("fetch", server_config)
    await server.initialize()
    yield server
    await server.cleanup()
