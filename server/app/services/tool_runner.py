# ==============================================================================
# File: server/app/services/tool_runner.py
# Purpose: Basic Gemini function/tool calling runner for web search.
#
# What this service does:
# 1. Declares `search_web` as a tool to Gemini (name, description, parameters).
# 2. Sends the user's research query to Gemini with the tool definition attached.
# 3. Inspects Gemini's response:
#    - If Gemini calls `search_web`:
#      a. Extracts the model's requested query string.
#      b. Executes our existing backend Python `search_web(query)` function.
#      c. Formats and sends the tool results back to Gemini.
#      d. Tells Gemini to synthesize the final response based on those results.
#    - If Gemini DOES NOT call a tool:
#      a. Returns the model's direct text response immediately.
# 4. Returns a clean `ResearchResponse` containing query, answer, and sources consulted.
#
# Important Architecture Note:
# The LLM never runs Python code directly. It simply emits a structured JSON request
# saying "I would like to call function X with argument Y". The backend securely runs
# the actual Python function and feeds the structured data back into the prompt context.
# ==============================================================================

import os
from typing import List, Optional
from google import genai
from google.genai import types

from app.schemas import ResearchResponse, SearchResult
from app.services.llm import get_gemini_client
from app.services.search import search_web


# ------------------------------------------------------------------------------
# 1. Define the search_web Tool for Gemini
# ------------------------------------------------------------------------------
# This tells Gemini:
# - Function Name: search_web
# - What it does: Search the web for relevant learning resources and information.
# - Parameters required: query (a string)
# ------------------------------------------------------------------------------
SEARCH_WEB_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_web",
            description="Search the web for relevant learning resources and information.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="The search keywords or technical topic to search on the web.",
                    )
                },
                required=["query"],
            ),
        )
    ]
)


def extract_text_from_response(response: types.GenerateContentResponse) -> str:
    """
    Safely extracts the human-readable text from a Gemini response,
    filtering out internal model thought signatures or empty non-text parts.
    """
    if getattr(response, "text", None):
        return response.text.strip()

    if not response or not response.candidates:
        return ""

    texts: List[str] = []
    for candidate in response.candidates:
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if getattr(part, "text", None) and not getattr(part, "thought", False):
                    texts.append(part.text)

    return "\n\n".join(texts).strip()


def research_topic(query: str) -> ResearchResponse:
    """
    Executes the manual Gemini tool-calling flow for researching a topic.

    Flow:
    1. Send user request + search_web tool declaration to Gemini.
    2. Inspect Gemini's response for function_calls.
    3. If search_web is requested:
       - Extract query argument.
       - Execute backend search_web(query).
       - Send search results back to Gemini.
       - Disable further tool calls (mode="NONE") so Gemini synthesizes the final answer.
       - Return answer + sources.
    4. If no tool is requested:
       - Directly return Gemini's answer + empty sources.

    Raises:
        ValueError: If query is blank or an API key is missing.
        RuntimeError: If Gemini or Tavily API communication fails.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Research query cannot be empty.")

    # 1. Initialize Gemini client (loads GEMINI_API_KEY from server/.env)
    client = get_gemini_client()
    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
    candidate_models = [primary_model, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"]
    # De-duplicate while preserving order
    fallback_models = list(dict.fromkeys(candidate_models))

    last_error: Optional[Exception] = None

    for model_name in fallback_models:
        try:
            # 2. Create chat session with search_web tool available
            # Automatic function calling (AFC) is disabled so OUR backend controls execution
            chat = client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    tools=[SEARCH_WEB_TOOL],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    temperature=0.2,
                    system_instruction=(
                        "You are PathAI's Research Assistant. When researching a technical topic, "
                        "use the search_web tool to find up-to-date courses, documentation, and tutorials. "
                        "Incorporate the findings directly into your final structured answer."
                    ),
                ),
            )
            response = chat.send_message(cleaned_query)

            # 3. Check if Gemini decided to request a tool call
            if not response.function_calls:
                # Gemini did NOT call a tool -> Produce direct answer
                direct_text = extract_text_from_response(response) or "No answer could be generated."
                return ResearchResponse(
                    query=cleaned_query,
                    answer=direct_text,
                    sources=[],
                )

            # 4. Gemini requested tool execution!
            # Inspect the requested function
            function_call = response.function_calls[0]
            if function_call.name != "search_web":
                raise RuntimeError(f"Unexpected tool requested by model: '{function_call.name}'")

            # Extract and validate query arguments requested by the model
            requested_query = (
                function_call.args.get("query", "").strip()
                if isinstance(function_call.args, dict)
                else ""
            )
            if not requested_query:
                # Fallback to the original user query if arguments were malformed
                requested_query = cleaned_query

            # 5. Backend executes Python function (search_web)
            # The LLM does NOT run this code — our Python server does!
            search_results: List[SearchResult] = search_web(requested_query, max_results=5)

            # 6. Format search results and send back to Gemini
            # Convert Pydantic models to dicts for serialization into FunctionResponse
            serialized_results = [result.model_dump() for result in search_results]

            tool_response_part = types.Part.from_function_response(
                name=function_call.name,
                response={"results": serialized_results},
            )

            # 7. Switch mode to NONE so Gemini produces final answer and does not loop
            chat._config.tool_config = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.NONE
                )
            )

            final_response = chat.send_message(tool_response_part)
            final_answer = extract_text_from_response(final_response)
            if not final_answer:
                final_answer = "Gemini processed the search results but did not return text."

            return ResearchResponse(
                query=cleaned_query,
                answer=final_answer,
                sources=search_results,
            )

        except Exception as exc:
            last_error = exc
            # If rate limited (429) or model issue, try next model in fallback list
            continue

    raise RuntimeError(f"All LLM models failed during tool execution: {str(last_error)}") from last_error

