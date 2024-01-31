"""Init file."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import solara

if TYPE_CHECKING:
    from reacton.core import ValueElement

@solara.component
def Layout(children: Any) -> ValueElement:
    """Solara app layout."""
    return solara.AppLayout(children=children, color="orange")
