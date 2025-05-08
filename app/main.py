import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.mcp.server import MCPServer, initialize_servers
from app.llm.ollama import OllamaClient
from app.llm.client import LLMClient
from app.chat.chat import initialize_message_history, get_llm_response

# Central configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)

# global variables
servers: list[MCPServer] = []
llm_client: LLMClient | None = None 

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    This can be used to initialize resources or perform setup tasks.
    """
    # Startup logic
    logging.info("Starting application...")

    # global variables
    global servers, llm_client

    # initialize servers
    logging.info("Initializing MCP servers...")
    servers = await initialize_servers(config_path=Path("mcp_config.json"), env_path=Path(".env"))
    logging .info(f"Initialized {len(servers)} servers.")

    # initlize LLM client
    # TODO: load LLM configuration from a file or user input
    logging.info("Initializing LLM client...")
    llm_client = OllamaClient(
        domain="http://localhost:11434",
        model_name="llama3.1",
        chat_endpoint="/api/chat",
        timeout=30.0,
        content_type="application/json",
        api_key=None  # Set your API key if required
    )

    # Initialize message history with system prompt
    # TODO: load system prompt from a configuration file
    initialize_message_history(
        system_prompt="You are a helpful assistant. You can call tools to get information."
    )
    logging.info("Message history initialized.")

    logging.info("Application initialized successfully.")

    yield

    # Cleanup logic can be added here if needed
    logging.info("Shutting down application...")
    for server in servers:
        await server.cleanup()


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    user_input: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat")
async def complete_chat(message: ChatRequest) -> ChatResponse:
    """
    Endpoint to handle chat messages.
    """

    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM client is not available")
    
    # Get response from LLM, tool calls handled internally
    llm_response: str = await get_llm_response(
        llm_client=llm_client,
        user_input=message.user_input,
        tools=[tool for server in servers for tool in server.tools]
    )

    return ChatResponse(response=llm_response)