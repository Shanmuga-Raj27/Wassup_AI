# backend/streamlit/stream_ai.py
# AI generation service for Streamlit UI using Google GenAI Interactions API and DDGS metasearch

import sys
from pathlib import Path
from google import genai

# Ensure backend root directory is in sys.path so app imports work reliably
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.services.prompt import SYSTEM_PROMPT, augmented_prompt
from app.services.web_search import search_web, format_search_results

# Initialize Google GenAI client with validated API key
client = genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_agent_response(prompt: str, previous_interaction_id: str | None = None, max_results: int = 3):
    # 1. Query DDGS metasearch engine for live web data
    search_data = search_web(prompt, max_results=max_results)
    search_context = format_search_results(search_data)

    # 2. Build the final augmented prompt string fusing search context and user query
    final_input = augmented_prompt(user_question=prompt, search_context=search_context)

    # 3. Call Google GenAI Interactions API with session continuation
    response = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=final_input,
        system_instruction=SYSTEM_PROMPT,
        previous_interaction_id=previous_interaction_id
    )

    # 4. Return tuple containing the text output, raw search context for debugging, and new interaction id
    return response.output_text, search_context, response.id
