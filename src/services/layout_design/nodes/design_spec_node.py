from typing import Any, Dict

from ..state import LayoutDesignState
from .common import get_metadata, get_theme


def assemble_design_spec(state: LayoutDesignState) -> Dict[str, Any]:
    preferences = state.get("layout_preferences", {})
    metadata = get_metadata(preferences)
    theme = get_theme(preferences)

    layout_plan = state.get("layout_plan", {})
    styles = state.get("style_options", [])

    selected_style_id = str(metadata.get("style_id") or "").strip()
    active_style = next((s for s in styles if str(s.get("id", "")) == selected_style_id), styles[0] if styles else {})

    design_spec = {
        "theme": theme,
        "layout_plan": layout_plan,
        "styles": styles,
        "selected_style_id": active_style.get("id", ""),
        "active_style": active_style,
        "generation_mode": "parallel_agents",
    }
    return {
        "selected_style_id": str(design_spec.get("selected_style_id") or ""),
        "active_style": active_style,
        "design_spec": design_spec,
    }
