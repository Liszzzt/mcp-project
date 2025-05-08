from contextlib import AsyncExitStack
import asyncio
import shutil
import os
import logging
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import jsonschema

from app.mcp.config import Config

logger = logging.getLogger(__name__)

class MCPServer:
    """Manages MCP server connections and tool execution."""

    def __init__(self, name: str, config: dict[str, any]) -> None:
        self.name: str = name
        self.config: dict[str, any] = config
        self.stdio_context: any | None = None
        self.session: ClientSession | None = None
        self.tools: list[Tool] = []
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """Initialize the server connection."""
        command = (
            shutil.which("npx")
            if self.config["command"] == "npx"
            else self.config["command"]
        )
        if command is None:
            raise ValueError("The command must be a valid string and cannot be None.")

        server_params = StdioServerParameters(
            command=command,
            args=self.config["args"],
            env={**os.environ, **self.config["env"]}
            if self.config.get("env")
            else None,
        )
        try:
            logger.debug(f"Initializing server {self.name} with command: {command} and args: {self.config['args']}")
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            logger.debug(f"Stdio transport established for server {self.name}.")
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
        except Exception as e:
            logger.error(f"Error initializing server {self.name}: {e}")
            await self.cleanup()
            raise

        # initialize tools
        await self.__update_tools()

    
    async def __update_tools(self) -> None:
        """Update tools from the server."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        try:
            tools_response = await self.session.list_tools()
            tools = []

            for item in tools_response:
                if isinstance(item, tuple) and item[0] == "tools":
                    tools.extend(
                        Tool(tool.name, tool.description, tool.inputSchema)
                        for tool in item[1]
                    )

            self.tools = tools
            logger.info(f"Server {self.name} tools updated: {[tool.name for tool in self.tools]}")
        except Exception as e:
            logger.error(f"Error updating tools for server {self.name}: {e}", exc_info=True)
            raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> any:
        """Execute a tool with retry mechanism.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            retries: Number of retry attempts.
            delay: Delay between retries in seconds.

        Returns:
            Tool execution result.

        Raises:
            RuntimeError: If server is not initialized.
            Exception: If tool execution fails after all retries.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")
        
        # find tools
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if tool is None:
            raise ValueError(f"Tool {tool_name} not found in server {self.name} tools.")

        # validate tool call
        tool.validate_tool_call(arguments)

        # execute tool with retries
        attempt = 0
        while attempt < retries:
            try:
                logger.info(f"Executing {tool_name}...")
                result = await self.session.call_tool(tool_name, arguments)
                
                # Extract content from MCP response
                if hasattr(result, 'content') and len(result.content) > 0:
                    content = result.content[0].text
                    # Try to parse as JSON if possible
                    try:
                        import json
                        return json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        return content
                return result

            except Exception as e:
                attempt += 1
                logger.warning(
                    f"Error executing tool: {e}. Attempt {attempt} of {retries}."
                )
                if attempt < retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached. Failing.")
                    raise

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            try:
                if self.exit_stack is not None:
                    await self.exit_stack.aclose()
                if self.session is not None:
                    self.session = None
                if self.stdio_context is not None:
                    self.stdio_context = None
            except Exception as e:
                logger.error(f"Error during cleanup of server {self.name}: {e}", exc_info=True)


class Tool:
    """Represents a tool with its properties and formatting."""

    def __init__(
        self, name: str, description: str, input_schema: dict[str, any]
    ) -> None:
        self.name: str = name
        self.description: str = description
        self.input_schema: dict[str, any] = input_schema

    
    def validate_tool_call(self, arguments: dict[str, any]) -> None:
        """Validate tool properties.

        Args:
            arguments: The arguments to validate, should conform to the input schema.

        Raises:
            jsonschema.ValidationError: If the tool call does not conform to the input schema.
            jsonscehma.SchemaError: If the input schema is invalid.
        """ 

        jsonschema.validate(arguments, self.input_schema)


async def initialize_servers(
        config_path: Path,
        env_path: Path | None = None,
    ) -> list[MCPServer]:
    """Initialize MCP servers based on configuration."""

    config = Config(config_path, env_path)
    servers: list[MCPServer] = []
    for server_name, server_config in config.raw_config.get("mcpServers", {}).items():
        logger.info(f"Initializing server: {server_name}")
        #server_name = server_config.get("name")
        if not server_name:
            logger.error("Server configuration missing 'name' field.")
            continue

        try:
            server = MCPServer(name=server_name, config=server_config)
            async with server.exit_stack:
                await server.initialize()
            logger.info(f"Server {server_name} initialized successfully.")
            servers.append(server)
        except Exception as e:
            logger.error(f"Failed to initialize server {server_name}: {e}")
            continue
    
    return servers