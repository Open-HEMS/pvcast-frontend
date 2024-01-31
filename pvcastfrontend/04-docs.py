"""Refers to the swagger documentation for the pvcast API."""
from __future__ import annotations

from typing import TYPE_CHECKING

import solara

if TYPE_CHECKING:
    from reacton.core import ValueElement


@solara.component
def Page() -> ValueElement:
    """Swagger documentation page for pvcast."""
    with solara.Column():
        solara.Title("API documentation")
        solara.Info(
            """This page contains the swagger documentation for the pvcast API."""
        )
