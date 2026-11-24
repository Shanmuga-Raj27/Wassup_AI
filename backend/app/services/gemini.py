# backend/app/services/gemini.py
# Terminal CLI orchestration using Google GenAI SDK with manual tool calling

import sys
from pathlib import Path
from google import genai
from google.genai import types
from google.genai import errors

# Add backend directory to sys.path so app imports resolve reliably
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.services.prompt import SYSTEM_PROMPT
from app.services.web_search import search_web_tool
from app.services.error_handler import (
    get_default_http_options,
    handle_api_error,
    handle_unexpected_error,
)

# Initialize GenAI client with validated API key and retry options
client = genai.Client(
    api_key=settings.GEMINI_API_KEY,
    http_options=get_default_http_options(),
)

# Configure chat session with tool declaration, manual execution, and retry options
config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[search_web_tool],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    http_options=get_default_http_options(),
)

# Create multi-turn chat session using gemini-3.5-flash-lite
chat = client.chats.create(
    model="gemini-3.5-flash-lite",
    config=config
)

print("=== Web Agent CLI (Manual Tool Calling Mode) ===")
print("Type 'exit' to quit.\n")

try:
    while True:
        user_prompt = input("User: ").strip()
        if user_prompt.lower() == "exit":
            print("Exiting...")
            break
        if not user_prompt:
            continue

        # Turn 1: Send user prompt to Gemini
        response = chat.send_message(user_prompt)

        # Turn 2+: Iterative tool resolution loop (handles multiple tool turns if needed)
        max_tool_turns = 3
        current_turn = 0

        while response.function_calls and current_turn < max_tool_turns:
            current_turn += 1
            response_parts = []

            for tool_call in response.function_calls:
                print(f"\n[Tool Requested #{current_turn}] Function: {tool_call.name}")
                print(f"[Tool Arguments] {tool_call.args}")

                # Match and execute local tool function
                if tool_call.name == "search_web_tool":
                    search_query = tool_call.args.get("query", user_prompt)
                    max_res = int(tool_call.args.get("max_results", 3))

                    print(f"[Executing DDGS] Searching for: '{search_query}'...")
                    tool_output = search_web_tool(query=search_query, max_results=max_res)

                    # Prepare function response part
                    response_parts.append(
                        types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": tool_output}
                        )
                    )

            if response_parts:
                # Send tool execution results back to Gemini
                response = chat.send_message(response_parts)
            else:
                break

        # Deliver final grounded response
        if response.text:
            print("\nAI:", response.text)
        else:
            print("\nAI: Completed tool requests, but no final text response was returned.")
        print("-" * 50 + "\n")

except errors.APIError as error:
    handle_api_error(error)

except KeyboardInterrupt:
    print("\nSession interrupted. Exiting...")

except Exception as error:
    handle_unexpected_error(error)

finally:
    # Close the API client
    client.close()
