"""Homepage file."""
from __future__ import annotations

from typing import TYPE_CHECKING

import solara

if TYPE_CHECKING:
    from reacton.core import ValueElement


@solara.component
def Page() -> ValueElement:
    """Home page."""
    solara.Title("Home page")
    with solara.Column():
        solara.Info(
            """
                    This is the home page. You can navigate to the other pages using the bar at the top.
                    """
        )
