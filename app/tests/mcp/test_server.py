import pytest
import jsonschema
from unittest.mock import AsyncMock, patch
from mcp import ClientSession
from app.mcp.server import MCPServer, Tool

@pytest.fixture
def mock_config():
    return {
        "command": "npx",
        "args": ["test-server"],
        "env": {"TEST": "value"}
    }

@pytest.fixture
def mock_tool():
    return Tool(
        name="test-tool",
        description="A test tool",
        input_schema={
            "type": "object",
            "properties": {
                "function": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "arguments": {"type": "object"}
                    },
                    "required": ["name", "arguments"]
                }
            }
        }
    )

@pytest.mark.asyncio
async def test_server_initialization():
    with patch('app.mcp.server.stdio_client') as mock_stdio, \
        patch('app.mcp.server.ClientSession') as mock_session:
        
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        mock_session_instance = AsyncMock(spec=ClientSession)
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session_instance.initialize = AsyncMock()
        mock_session_instance.list_tools = AsyncMock(return_value=[("tools", [])])

        server = MCPServer("test", {"command": "npx", "args": []})
        await server.initialize()

        assert server.session is not None
        assert server.tools == []
        assert mock_session_instance.list_tools.called

@pytest.mark.asyncio
async def test_execute_tool_success():
    server = MCPServer("test", {"command": "npx", "args": []})
    server.session = AsyncMock()
    test_tool = Tool("test-tool", "test description", {
        "type": "object",
        "properties": {
            "function": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "arguments": {"type": "object"}
                },
                "required": ["name", "arguments"]
            }
        }
    })
    server.tools = [test_tool]

    _ = await server.execute_tool(
        "test-tool",
        {"test": "arg"},
        retries=1
    )

    assert server.session.call_tool.called
    server.session.call_tool.assert_called_once_with("test-tool", {"test": "arg"})

@pytest.mark.asyncio
async def test_execute_tool_retry():
    server = MCPServer("test", {"command": "npx", "args": []})
    server.session = AsyncMock()
    server.session.call_tool.side_effect = [Exception("First failure"), "success"]
    test_tool = Tool("test-tool", "test description", {
        "type": "object",
        "properties": {
            "function": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "arguments": {"type": "object"}
                },
                "required": ["name", "arguments"]
            }
        }
    })
    server.tools = [test_tool]

    result = await server.execute_tool(
        "test-tool",
        {"test": "arg"},
        retries=2,
        delay=0.1
    )

    assert result == "success"
    assert server.session.call_tool.call_count == 2

def test_tool_validation_success(mock_tool):
    valid_args = {
        "function": {
            "name": "test-tool",
            "arguments": {"param": "value"}
        }
    }
    mock_tool.validate_tool_call(valid_args)

def test_tool_validation_failure(mock_tool):
    invalid_args = {
        "function": {
            "name": "test-tool"
            # missing required 'arguments' field
        }
    }
    with pytest.raises(jsonschema.ValidationError):
        mock_tool.validate_tool_call(invalid_args)
