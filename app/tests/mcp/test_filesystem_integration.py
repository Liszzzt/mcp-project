import pytest
import pytest_asyncio
import logging
import os
from pathlib import Path

from app.mcp.server import MCPServer

logger = logging.getLogger(__name__)

@pytest.fixture
def test_dir(mcp_config):
    """Create a test directory within the allowed root."""
    root = Path(os.environ["FILESYSTEM_ROOT"])
    test_dir = root / "test_files"
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    # Cleanup test directory
    if test_dir.exists():
        for f in test_dir.glob("**/*"):
            if f.is_file():
                f.unlink()
        test_dir.rmdir()

@pytest_asyncio.fixture
async def fs_server(mcp_config):
    """Initialize and provide a filesystem server instance."""
    server_config = mcp_config.get_server_config("filesystem")
    server = MCPServer("filesystem", server_config)
    await server.initialize()
    yield server

@pytest.mark.integration
@pytest.mark.filesystem
@pytest.mark.asyncio
async def test_write_file(fs_server: MCPServer, test_dir):
    """Test writing a file."""
    test_file = test_dir / "test.txt"
    result = await fs_server.execute_tool(
        "write_file",
        {
            "path": str(test_file),
            "content": "Hello, World!"
        }
    )
    assert "error" not in str(result).lower()
    assert test_file.exists()

@pytest.mark.integration
@pytest.mark.filesystem
@pytest.mark.asyncio
async def test_read_file(fs_server: MCPServer, test_dir):
    """Test reading a file."""
    test_file = test_dir / "test.txt"
    # Setup
    await fs_server.execute_tool(
        "write_file",
        {
            "path": str(test_file),
            "content": "Hello, World!"
        }
    )
    
    # Test
    content = await fs_server.execute_tool(
        "read_file",
        {"path": str(test_file)}
    )
    assert content == "Hello, World!"

@pytest.mark.integration
@pytest.mark.filesystem
@pytest.mark.asyncio
async def test_edit_file(fs_server: MCPServer, test_dir):
    """Test editing a file."""
    test_file = test_dir / "test.txt"
    # Setup
    await fs_server.execute_tool(
        "write_file",
        {
            "path": str(test_file),
            "content": "Hello, World!"
        }
    )
    
    # Test
    result = await fs_server.execute_tool(
        "edit_file",
        {
            "path": str(test_file),
            "edits": [{
                "oldText": "Hello",
                "newText": "Hi"
            }]
        }
    )
    assert "error" not in str(result).lower()
    
    # Verify
    content = await fs_server.execute_tool(
        "read_file",
        {"path": str(test_file)}
    )
    assert content == "Hi, World!"

@pytest.mark.integration
@pytest.mark.filesystem
@pytest.mark.asyncio
async def test_get_file_info(fs_server: MCPServer, test_dir):
    """Test getting file metadata."""
    test_file = test_dir / "test.txt"
    # Setup
    await fs_server.execute_tool(
        "write_file",
        {
            "path": str(test_file),
            "content": "Hello, World!"
        }
    )
    
    # Test
    info = await fs_server.execute_tool(
        "get_file_info",
        {"path": str(test_file)}
    )
    assert "error" not in str(info).lower()
    assert info["type"] == "file"
    assert "size" in info
    assert "modifiedTime" in info
