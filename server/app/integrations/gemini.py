# ==============================================================================
# File: server/app/integrations/gemini.py
# Purpose: Google Gemini SDK initialization and low-level API communication.
# ==============================================================================

import os
from pathlib import Path
from typing import List, Optional, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Resolve path to server directory
SERVER_DIR = Path(__file__).resolve().parent.parent.parent


def get_gemini_client() -> genai.Client:
    """
    Dynamically reloads server/.env and initializes the Google Gemini SDK client.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not configured or is a placeholder.
    """
    load_dotenv(SERVER_DIR / ".env", override=True)
    load_dotenv(override=True)
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not set. Please create a .env file in the server/ directory "
            "with a valid Google Gemini API key: GEMINI_API_KEY=your_key"
        )
        
    return genai.Client(api_key=api_key)


def generate_structured_content(
    client: genai.Client,
    prompt: str,
    schema: Any,
    system_instruction: str,
    temperature: float = 0.2,
    fallback_models: Optional[List[str]] = None,
) -> str:
    """
    Calls the Gemini API using structured JSON output mode (response_schema).
    Automatically iterates through fallback models if the primary model fails.
    
    Returns:
        str: Raw JSON response text from Gemini.
        
    Raises:
        RuntimeError: If all candidate models fail to generate content.
    """
    if fallback_models is None:
        primary_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        fallback_models = list(dict.fromkeys([
            primary_model,
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-flash-latest",
        ]))

    response = None
    last_error = None

    for model_name in fallback_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    system_instruction=system_instruction,
                    temperature=temperature,
                ),
            )
            if response and response.text:
                return response.text
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"Gemini API structured content generation failed across models: {str(last_error)}")

