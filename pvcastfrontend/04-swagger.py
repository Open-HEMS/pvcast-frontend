"""Refers to the swagger documentation for the pvcast API."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import solara

if TYPE_CHECKING:
    from reacton.core import ValueElement
import requests


@solara.component
def Page() -> ValueElement:
    """Swagger documentation page for pvcast."""
    with solara.Column():
        solara.Title("API documentation")
        solara.Info(
            """This page contains the swagger documentation for the pvcast API."""
        )

        # get the port from the environment variable
        host = os.environ.get("SERVER_NAME", "localhost")
        port = os.environ.get("SERVER_PORT", 8099)
        url = f"http://{host}:{port}/docs"

        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Swagger Documentation</title>
        </head>
        <body>

            <h1>Swagger API docs</h1>
            <iframe src="/docs" width="100%" height="100%"></iframe>

        </body>
        </html>
        """

        # if localhost/docs is not available we will render an error message
        def raise_request_exception() -> None:
            """Raise a request exception."""
            raise requests.exceptions.RequestException

        try:
            response = requests.get(url, timeout=2)
            if response.status_code != 200:
                raise_request_exception()
        except requests.exceptions.RequestException:
            solara.Error(f"Could not load API docs from {url}")
        finally:
            solara.HTML(tag="div", unsafe_innerHTML=html)
