# backend/app/services/gemini.py
# Central AI Agent Service and Standalone Terminal CLI

import sys
from pathlib import Path
from google import genai
from google.genai import types
from google.genai import errors

# Add backend root directory to sys.path so imports resolve in both CLI and app modes
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
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
    # Factory creating a fresh chat session with dual tools and retry rules
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
    # Core agent runner executing one conversational turn and resolving multi-step tool calls
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

                    # Execute DDGS metasearch
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

                    # Wrap tool output in a function response part
                    response_parts.append(
                        types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": search_context},
                        )
                    )

                elif tool_call.name == "scrape_url_tool":
                    tool_executed = True
                    target_url = tool_call.args.get("url", "")

                    # Execute Trafilatura webpage extraction
                    scraped_content = scrape_url_tool(url=target_url)
                    tool_history.append({
                        "tool_name": tool_call.name,
                        "url": target_url,
                        "output": scraped_content,
                    })

                    # Wrap scraped output in a function response part
                    response_parts.append(
                        types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": scraped_content},
                        )
                    )

            if response_parts:
                # Send tool results back to Gemini for next decision or final synthesis
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
        return f"Gemini API Error ({error.code}): {error.message}", False, None

    except Exception as error:
        handle_unexpected_error(error)
        return f"Unexpected error: {error}", False, None


# =====================================================================
# Standalone CLI Entrypoint (Runs ONLY when executed directly in terminal)
# =====================================================================
if __name__ == "__main__":
    print("=== Web Agent CLI (Unified Service Mode) ===")
    print("Type 'exit' to quit.\n")

    # Start a fresh chat session for the terminal
    cli_chat = create_agent_chat()

    try:
        while True:
            user_input = input("User: ").strip()
            if user_input.lower() == "exit":
                print("Exiting...")
                break
            if not user_input:
                continue

            # Run the turn using the shared function
            ai_text, tool_used, tool_info = run_chat_turn(cli_chat, user_input)

            # Print debug info for every tool step executed in this turn
            if tool_used and tool_info and tool_info.get("steps"):
                for step in tool_info["steps"]:
                    if step["tool_name"] == "search_web_tool":
                        cat = step.get("category", "text")
                        tl = step.get("timelimit")
                        tl_info = f", timelimit: '{tl}'" if tl else ""
                        print(f"\n[Tool Executed] {step['tool_name']} (category: '{cat}'{tl_info}) with query: '{step['query']}'")
                    elif step["tool_name"] == "scrape_url_tool":
                        print(f"\n[Tool Executed] {step['tool_name']} on URL: '{step['url']}'")

            # Print final AI response
            print(f"\nAI: {ai_text}")
            print("-" * 50 + "\n")

    except KeyboardInterrupt:
        print("\nSession interrupted. Exiting...")
    finally:
        client.close()
