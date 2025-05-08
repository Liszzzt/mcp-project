from typing import Literal
from dataclasses import dataclass

@dataclass
class Tool:
    """
    Represents a tool that can be called by the LLM.
    This will be converted to LLM Provider API format.
    It can also be formatted for LLMs that do not support tools field in their API
    """
    name: str
    description: str
    parameters: dict[str, any] | None = None


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, any]


@dataclass
class LLMResponse:
    """Response from the LLM API converted to MCP message format."""
    role: Literal["assistant", "user", "system", "tool"]
    content: str
    tool_calls: list[ToolCall] | None = None

    