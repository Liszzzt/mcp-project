
# Pseudo code for chat application using LLM and tools
# 1. initialize server
# 2. get tools 
# 3. loop for chat
    # 1. get user input
    # 2. get response from LLM
    # 3. while tool call in response
        # execute the tool, 
        # get response from LLM,
    # 4. print the response 

import logging

from app.mcp.server import Tool
from app.llm.client import LLMClient


logger = logging.getLogger(__name__)

# Global variable
message_history: list[dict[str, str]] = []

def initialize_message_history(system_prompt: str = "You are a helpful assistant.") -> None:
    """
    Initializes the message history with a system prompt.
    
    Args:
        system_prompt (str): The initial system prompt to set the context for the conversation.
    """
    global message_history
    message_history = [{"role": "system", "content": system_prompt}]


async def get_llm_response(
        llm_client: LLMClient,
        user_input: str,
        tools: list[Tool] = None
    ) -> str:
    """
    Orchestrates the chat loop with the LLM client and tools.

    It updates the global variables:
    - `message_history`: to keep track of the conversation history. 
    """

    global message_history
    
    message_history.append({"role": "user", "content": user_input})
    try:
        llm_response = await llm_client.get_response(
            messages=message_history,
            tools=tools
        )
    except Exception as e:
        logger.error(f"Error getting response from LLM: {e}")
        raise

    message_history.append({"role": "assistant", "content": llm_response.content})
    logger.info(f"LLM response: {llm_response.content}")

    # Keep processing tool calls until there are none left
    while llm_response.tool_calls:
        for tool_call in llm_response.tool_calls:
            logger.info(f"Tool call detected: {tool_call.name} with arguments {tool_call.arguments}")
            
            # find the tool call in tools
            for tool in tools:
                if tool.name == tool_call.name:
                    try:
                        result = await tool.execute_tool(tool_call.arguments)
                        logger.info(f"Tool {tool_call.name} executed successfully: {result}")
                        message_history.append({"role": "tool", "content": result})
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_call.name}: {e}")
                        message_history.append({"role": "tool", "content": f"Error: {e}"})
            else:
                logger.warning(f"Tool {tool_call.name} not found on any server.")
        
        # Get the next response from LLM after tool execution
        try:
            llm_response = await llm_client.get_response(
                messages=message_history,
                tools=tools
            )
        except Exception as e:
            logger.error(f"Error getting response from LLM: {e}")
            raise

        message_history.append({"role": "assistant", "content": llm_response.content})
        logger.info(f"LLM response: {llm_response.content}")

    return llm_response.content