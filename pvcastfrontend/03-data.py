"""Data page for pvcast."""
from __future__ import annotations

from typing import TYPE_CHECKING

import solara

if TYPE_CHECKING:
    from reacton.core import ValueElement


@solara.component
def Page() -> ValueElement:
    """Build the configuration page.

    This page is used to configure the pvcast application.

    It will consist of two columns, one for the active configuration we are editing,
    and one for the current field we are modifying.
    """
    solara.Title("Data visualization")
    with solara.Column():
        solara.Info("This page displays the forecasted power data for your PV plant.")
