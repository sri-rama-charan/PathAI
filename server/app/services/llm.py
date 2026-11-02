# ==============================================================================
# File: server/app/services/llm.py
# Purpose: Compatibility shim — re-exports from plan_service and integrations.
#
# NOTE: Business logic has moved to app.services.plan_service (Stage 5).
#       This module is preserved so existing test patches targeting
#       "app.services.llm.get_gemini_client" continue to work without changes.
# ==============================================================================

# Re-export get_gemini_client for test compatibility
# (tests patch "app.services.llm.get_gemini_client")
from app.integrations.gemini import get_gemini_client, generate_structured_content  # noqa: F401

# Re-export plan business logic from plan_service
from app.services.plan_service import (  # noqa: F401
    MODIFY_SYSTEM_INSTRUCTION,
    SYSTEM_INSTRUCTION,
    _serialise_existing_plan,
    build_user_prompt,
    generate_learning_plan,
    modify_learning_plan,
    validate_and_fix_plan_deterministically,
    validate_modified_plan,
)
