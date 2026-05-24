from typing import Any, Dict

from .graph import build_layout_design_graph
from .state import LayoutDesignState


def run_layout_design(
    resume_obj: Dict[str, Any],
    layout_preferences: Dict[str, Any] | None = None,
    raw_resume_obj: Dict[str, Any] | None = None,
    suggestion_resume_obj: Dict[str, Any] | None = None,
    refined_resume_obj: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    graph = build_layout_design_graph()
    initial_state: LayoutDesignState = {
        "resume_obj": resume_obj if isinstance(resume_obj, dict) else {},
        "layout_preferences": layout_preferences if isinstance(layout_preferences, dict) else {},
        "raw_resume_obj": raw_resume_obj if isinstance(raw_resume_obj, dict) else {},
        "suggestion_resume_obj": suggestion_resume_obj if isinstance(suggestion_resume_obj, dict) else {},
        "refined_resume_obj": refined_resume_obj if isinstance(refined_resume_obj, dict) else {},
    }

    final_state = graph.invoke(initial_state)
    return {
        "design_spec": final_state.get("design_spec", {}),
        "output_markdown": str(final_state.get("output_markdown", "")),
        "output_html": str(final_state.get("output_html", "")),
    }
