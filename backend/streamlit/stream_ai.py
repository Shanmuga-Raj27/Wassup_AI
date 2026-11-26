# backend/streamlit/stream_ai.py
# AI generation service for Streamlit UI using Google GenAI SDK, DDGS, and Trafilatura

import sys
from pathlib import Path
from google import genai
from google.genai import types
from google.genai import errors

# Ensure backend root directory is in sys.path so app imports work reliably
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.services.prompt import SYSTEM_PROMPT
from app.services.web_search import search_web_tool
from app.services.web_scrap import scrape_url_tool
from app.services.error_handler import (
    get_default_http_options,
    handle_api_error,
    handle_unexpected_error,
)

# Initialize Google GenAI client with validated API key and retry options
client = genai.Client(
    api_key=settings.GEMINI_API_KEY,
    http_options=get_default_http_options(),
)


def create_agent_chat():
    # Factory instantiating a fresh chat session with dual tools, manual execution, and retry options
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[search_web_tool, scrape_url_tool],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        http_options=get_default_http_options(),
    )
    return client.chats.create(
        model="gemini-3.5-flash-lite",
        config=config,
    )


def run_chat_turn(chat, user_prompt: str):
    # Execution handler for a user turn with manual multi-step tool resolution
    tool_executed = False
    tool_history = []
    max_tool_turns = 4
    current_turn = 0

    try:
        # Turn 1: Dispatch user prompt to Gemini
        response = chat.send_message(user_prompt)

        # Turn 2+: Iterative tool resolution loop
        while response.function_calls and current_turn < max_tool_turns:
            current_turn += 1
            response_parts = []

            for tool_call in response.function_calls:
                if tool_call.name == "search_web_tool":
                    tool_executed = True
                    query = tool_call.args.get("query", user_prompt)
                    category = tool_call.args.get("category", "text")
                    timelimit = tool_call.args.get("timelimit", None)
                    max_results = int(tool_call.args.get("max_results", 4))

                    # Execute DDGS metasearch locally
                    search_context = search_web_tool(
                        query=query,
                        category=category,
                        timelimit=timelimit,
                        max_results=max_results,
                    )
                    tool_history.append({
                        "tool_name": tool_call.name,
                        "query": query,
                        "category": category,
                        "timelimit": timelimit,
                        "output": search_context,
                    })

                    # Prepare function response payload
                    response_parts.append(
                        types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": search_context},
                        )
                    )

                elif tool_call.name == "scrape_url_tool":
                    tool_executed = True
                    target_url = tool_call.args.get("url", "")

                    # Execute Trafilatura webpage extraction locally
                    scraped_content = scrape_url_tool(url=target_url)
                    tool_history.append({
                        "tool_name": tool_call.name,
                        "url": target_url,
                        "output": scraped_content,
                    })

                    # Prepare function response payload
                    response_parts.append(
                        types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": scraped_content},
                        )
                    )

            if response_parts:
                # Send tool execution results back to Gemini for next decision
                response = chat.send_message(response_parts)
            else:
                break

        # Extract final answer text
        if response.text:
            ai_reply = response.text
        else:
            ai_reply = "Completed tool requests, but no final text response was returned."

        tool_details = {"steps": tool_history} if tool_history else None
        return ai_reply, tool_executed, tool_details

    except errors.APIError as error:
        handle_api_error(error)
        error_msg = f"Gemini API Error ({error.code}): {error.message}. Please try again later."
        return error_msg, False, None

    except Exception as error:
        handle_unexpected_error(error)
        return f"Unexpected error: {error}", False, None
