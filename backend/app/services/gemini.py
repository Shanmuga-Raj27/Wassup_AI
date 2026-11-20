
# Gemini Interactions API chatbot
from app.services.prompt import SYSTEM_PROMPT, augmented_prompt
from app.services.web_search import search_web, format_search_results
from app.core.config import settings
from google import genai


# Connect to the Gemini API
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Store the previous interaction ID for conversation memory
previous_id = None

try:
    while True:
        # Get input from the user
        prompt = input("User: ").strip()

        # Exit the chatbot
        if prompt.lower() == "exit":
            print("Exiting...")
            break

        if not prompt:
            continue

        # 1. Fetch live web search results using ddgs & format context
        print("🔍 Searching the web...")
        search_data = search_web(prompt, max_results=3)
        search_context = format_search_results(search_data)

        # 2. CALL the function with arguments to get the string
        final_input = augmented_prompt(user_question=prompt, search_context=search_context)


        # Send the message and continue the previous conversation
        response = client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=final_input,
            system_instruction=SYSTEM_PROMPT,
            previous_interaction_id=previous_id
        )

        # Save this interaction ID for the next message
        previous_id = response.id

        print("\n--- [DEBUG: Search Context Sent to Gemini] ---")
        print(search_context)
        print("---------------------------------------------\n")

        # Display the AI response
        print("AI:", response.output_text)

except Exception as error:
    print("Error:", error)

finally:
    # Close the API client
    client.close()