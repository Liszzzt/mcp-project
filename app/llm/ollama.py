from app.llm.client import LLMClient
from app.llm.schemas import LLMResponse, ToolCall
from app.mcp.server import Tool


class OllamaClient(LLMClient):
    """
    A client for interacting with the Ollama LLM API.
    This class extends the LLMClient base class and implements the methods for Ollama-specific functionality.
    """


    def _format_tool(self, tool: Tool) -> dict[str, any]:
        """
        Format a tool for Ollama API usage.
        
        Args:
            tool_call: The tool call data to format.
        
        Returns:
            A dictionary representing the formatted tools field for Ollama.

        Example:
            ```json
            {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The location to get the weather for, e.g. San Francisco, CA"
                            },
                            "format": {
                                "type": "string",
                                "description": "The format to return the weather in, e.g. 'celsius' or 'fahrenheit'",
                                "enum": ["celsius", "fahrenheit"]
                            }
                        },
                        "required": ["location", "format"]
                    }
                }
            }
            ```
        """
        
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema
            }
        }


    def _format_response(self, response: dict) -> LLMResponse:
        """
        Format the response from the Ollama API to standardized format.
        
        Args:
            response: The response data from the Ollama API.

        Returns:
            An LLMResponse object representing the formatted response.

        Raises:
            ValueError: If the response does not contain a valid role or if the role is not 'assistant'.

        Example: 
            ```json
            {
                "model": "llama3.2",
                "created_at": "2024-07-22T20:33:28.123648Z",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                            "name": "get_current_weather",
                            "arguments": {
                                    "format": "celsius",
                                    "location": "Paris, FR"
                                }
                            }
                        }
                    ]
                },
                "done_reason": "stop",
                "done": true,
                "total_duration": 885095291,
                "load_duration": 3753500,
                "prompt_eval_count": 122,
                "prompt_eval_duration": 328493000,
                "eval_count": 33,
                "eval_duration": 552222000
            }
            ```
        """

        message: dict = response.get("message", {})

        if "role" not in message.keys():
            raise ValueError("No role in response data, something went wrong.")

        # raise an error if the response role is not 'assistant'
        if message["role"] != "assistant":
            raise ValueError("Response role is not 'assistant', something went wrong.")
        
        # format tool calls if present
        if "tool_calls" in message:
            tool_calls: list[ToolCall] = [self._format_tool_call(tool_call) for tool_call in message["tool_calls"]]
        else:
            tool_calls = None
        
        return LLMResponse(
            role=message["role"],
            content=message.get("content", ""),
            tool_calls=tool_calls
        )
    

    def _format_tool_call(self, tool_call: dict[str, any]) -> ToolCall:
        """
        Parse a tool call from Ollama response.
        This method extracts the function name and arguments from the tool call data.
        
        Args:
            tool_call: The tool call data from the response.
        
        Returns:
            A ToolCall object representing the parsed tool call.
        """

        if "function" not in tool_call or "name" not in tool_call["function"]:
            raise ValueError("Invalid tool call format, missing 'function' or 'name'.")
        
        return ToolCall(
            name=tool_call["function"]["name"],
            arguments=tool_call["function"].get("arguments", {})
        )