
# Gemini Interactions API chatbot

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

        # Send the message and continue the previous conversation
        response = client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=prompt,
            previous_interaction_id=previous_id
        )

        # Save this interaction ID for the next message
        previous_id = response.id

        # Display the AI response
        print("AI:", response.output_text)

except Exception as error:
    print("Error:", error)

finally:
    # Close the API client
    client.close()