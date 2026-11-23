# backend/app/services/error_handler.py
# Dedicated error handling and HTTP retry configuration for Google GenAI services

from google.genai import errors
from google.genai import types


def get_default_http_options() -> types.HttpOptions:
    # Standard HTTP retry configuration for Google GenAI model requests
    return types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=4,
            initial_delay=2.0,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        )
    )


def handle_api_error(error: errors.APIError) -> None:
    # Handles Gemini API errors with specific status code and user guidance
    print(f"Gemini API error ({error.code}): {error.message}")
    print("The required model did not return a response. Please try again later.")


def handle_unexpected_error(error: Exception) -> None:
    # Handles unexpected runtime exceptions
    print(f"Unexpected error: {error}")


def handle_gemini_error(error: Exception) -> None:
    # Unified dispatcher routing Gemini API errors and generic exceptions
    if isinstance(error, errors.APIError):
        handle_api_error(error)
    elif isinstance(error, KeyboardInterrupt):
        print("\nSession interrupted. Exiting...")
    else:
        handle_unexpected_error(error)
