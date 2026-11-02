# ==============================================================================
# File: server/app/services/research_graph.py
# Purpose: Compatibility shim — re-exports from app.workflows.research_graph.
#
# NOTE: The LangGraph implementation has moved to app.workflows.research_graph
#       (Stage 5). This shim preserves all existing import paths and test mock
#       targets (e.g. "app.services.research_graph._generate_with_fallback").
#
#       Tests patch symbols at the module where they are DEFINED. Since all
#       symbols are imported into this namespace, patches on this module will
#       NOT intercept calls made from within app.workflows.research_graph.
#       Tests that need to intercept those calls must patch at:
#         app.workflows.research_graph.<symbol>
#
#       For backward compatibility, run_research_workflow is re-exported from
#       app.services.research_service (which uses the workflow graph).
# ==============================================================================

# Re-export entire workflow API for backward-compatible imports
from app.workflows.research_graph import (  # noqa: F401
    MAX_RETRIES,
    _generate_with_fallback,
    analyze_goal,
    build_research_graph,
    evaluate_resources,
    generate_response,
    research_graph,
    route_after_evaluation,
    search_resources,
)
from app.workflows.states import ResearchState  # noqa: F401

# run_research_workflow lives in research_service (uses the compiled graph)
from app.services.research_service import run_research_workflow  # noqa: F401
