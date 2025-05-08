from abc import ABC, abstractmethod
import logging

import httpx

from app.llm.schemas import LLMResponse
from app.mcp.server import Tool

logger = logging.getLogger(__name__)

class LLMClient(ABC):
    """
    A base class for interacting with a Large Language Model (LLM) API.
    This class is designed to be extended for specific LLM implementations.
    """
    def __init__(self, 
            domain: str, 
            model_name: str, 
            chat_endpoint: str = "/api/chat",
            timeout: float = 30.0,
            content_type: str = "application/json",
            api_key: str = None,
        ) -> None:
        
        self.url: str = domain + chat_endpoint
        self.model_name: str = model_name
        self.timeout: float = timeout

        # set headers for the request
        self.headers: dict[str, str] = {
            "Content-Type": content_type,
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }

        logger.info(f"Initialized LLM client for model {model_name} at {domain}")

    async def get_response(self, messages: list[dict[str, str]], tools: list[Tool] | None) -> LLMResponse:
        """
        Get a response from the LLM API.

        Args:
            messages: A list of message dictionaries representing the conversation history.
            tools: A list of Tool objects that can be used by the LLM.

        Returns:
            LLMResponse: A standardized response object containing the LLM's reply and any tool calls.

        Raises:
            httpx.RequestError: If the request to the LLM API fails.
            ValueError: If the response cannot be parsed into the expected format.

        """
        logger.info(f"Sending request to LLM API with {len(messages)} messages and {len(tools) if tools else 0} tools")

        # response to the LLM API request
        async with httpx.AsyncClient() as client:
            response: httpx.Resposne = await client.post(
                url=self.url,
                headers=self.headers, 
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,  # set to True for streaming responses
                    "tools": self._format_tools(tools) if tools else [], # format tools for LLM API usage
                },
                timeout=self.timeout,
            )

        try:
            response.raise_for_status()
        except httpx.RequestError as e:
            logger.error(f"LLM API request failed: {str(e)}")
            raise
        
        logger.info("Successfully received response from LLM API")
        # format the response
        try:
            return self._format_response(response.json())
        except ValueError as e:
            logger.error(f"Failed to parse LLM API response: {str(e)}")
            raise


    @abstractmethod
    def _format_response(self, response: dict) -> LLMResponse:
        """
        Format the response from the LLM API to standardized format.
        This method should be implemented by subclasses to handle specific LLM response formats.

        Args:
            response: The response data from the LLM API.
        
        Returns:
            LLMResponse: A standardized response object containing the LLM's reply and any tool calls.

        Raises:
            ValueError: If the response cannot be parsed into the expected format.
        """
        pass
    

    def _format_tools(self, tools: list[Tool]) -> list[dict[str, any]]:
        """
        Format a list of tools for LLM API usage.
        
        Args:
            tools: A list of Tool objects to format.
        
        Returns:
            A list of dictionaries representing the formatted tools.
        """
        logger.info(f"Formatting {len(tools)} tools for LLM API")
        return [self._format_tool(tool) for tool in tools]


    @abstractmethod
    def _format_tool(self, tool_call: dict[str, any]) -> dict[str, any]:
        """
        Parse a tool call from LLM provider response.
        This method extracts the function name and arguments from the tool call data.
        
        Args:
            tool_call: The tool call data from the response.
        
        Returns:
            A dictionary representing the parsed tool call.
        """
        pass
    

    def _format_tool_calls(self, tool_calls: list[dict[str, any]]) -> list[dict[str, any]]:
        """
        Format a list of tool calls from LLM provider response.
        
        Args:
            tool_calls: A list of tool call data from the response.
        
        Returns:
            A list of dictionaries representing the parsed tool calls.
        """
        logger.info(f"Formatting {len(tool_calls)} tool calls from LLM response")
        return [self._format_tool_call(tool_call) for tool_call in tool_calls]
    

    @abstractmethod
    def _format_tool_call(self, tool_call: dict[str, any]) -> dict[str, any]:
        """
        Parse a tool call from LLM provider response.
        This method extracts the function name and arguments from the tool call data.
        
        Args:
            tool_call: The tool call data from the response.
        
        Returns:
            A dictionary representing the parsed tool call.
        """
        pass


