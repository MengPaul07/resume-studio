from typing import Any

from .nodes import render_html
from .state import LayoutDesignState


def build_layout_design_graph() -> Any:
    """Return a callable that runs the layout-design pipeline (single-node: render_html)."""
    class _Runner:
        def invoke(self, state: LayoutDesignState) -> LayoutDesignState:
            return {**state, **render_html(state)}

    return _Runner()
