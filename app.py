"""flapi/app.py

Core Flapi classes including FlapiApp and initialization functions.
"""

from __future__ import annotations

import inspect
import os
from functools import partial
from typing import Any

import uvicorn
import waitress
import yaml
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from flask import Flask

from ionbus_utils.logging_utils import logger

from ionbus_flapi.config import (
    get_app_name,
    get_config,
    set_app_name,
    set_config,
)
from ionbus_flapi.errors import InitializationError, NotInitializedError
from ionbus_flapi.response import wrap_fastapi_func, wrap_flask_func
from ionbus_flapi.routing import (
    HTML_DOCS,
    URLreg,
    initialize_routing,
    prepare_url,
    register_endpoint_page,
)
from ionbus_flapi.shutdown import shutdown_endpoint

# Module-level state
_flapi_app: FlapiApp | None = None
_server_initialized: bool = False


class FlapiApp:
    """Abstract base class for a Flapi App instance.

    Provides method stubs that should be implemented by each subclass.
    """

    app: Flask | FastAPI

    host: str
    port: int | str
    max_threads: int
    use_proxy: bool
    show_shutdown: bool
    proxy_prefix: str | None

    def __init__(self):
        self.host = get_config("host")
        self.port = get_config("port")
        self.max_threads = get_config("max_threads")
        self.use_proxy = get_config("use_proxy")
        self.proxy_prefix = get_config("proxy_prefix")

        initialize_routing(self)

    def serve(self) -> None:
        """Begin serving this FlapiApp.

        Instead of configuring the server here, supply config arguments
        to initialize().
        """
        logger.info(
            f"starting up {get_app_name()} server on "
            f"http://{self.host}:{self.port}"
        )

    @staticmethod
    def server_type() -> str:
        """Return the server type name."""
        return "NONE"

    def get_app(self) -> Flask | FastAPI:
        """Return the underlying Flask or FastAPI application."""
        return self.app


class FlaskFlapiApp(FlapiApp):
    """A FlapiApp running on the Flask library."""

    app: Flask

    def __init__(self):
        super().__init__()

        # Get the calling module's directory for static files
        frm = inspect.stack()[2]
        mod = inspect.getmodule(frm[0])
        if not mod:
            raise InitializationError(
                "Initialization must not occur from a headless file."
            )
        try:
            root_path = os.path.dirname(mod.__file__)  # type: ignore
        except AttributeError:
            root_path = ""

        self.app = Flask(
            mod.__name__,
            root_path=root_path,
            static_url_path=prepare_url("/static"),
        )
        self.app.register_error_handler(404, self.custom_404_handler)
        set_app_name("Flask")

    def serve(self) -> None:
        """Begin serving this application."""
        super().serve()

        proxy_args = {}
        if self.use_proxy:
            proxy_args = {
                "trusted_proxy": "localhost",
                "clear_untrusted_proxy_headers": False,
            }

        waitress.serve(
            self.app,
            host=self.host,
            port=self.port,
            threads=self.max_threads,
            **proxy_args,
        )

    @staticmethod
    def server_type() -> str:
        return "Flask"

    @staticmethod
    def custom_404_handler(excp: Exception) -> str:
        """Handle 404 errors with custom page."""
        return wrap_flask_func(
            "404 Not Found",
            partial(_not_found_handler, excp),
        )()

    def get_app(self) -> Flask:
        return self.app


class FastAPIFlapiApp(FlapiApp):
    """A FlapiApp running on the FastAPI library."""

    app: FastAPI

    def __init__(self):
        super().__init__()
        self.app = FastAPI(exception_handlers={404: self.custom_404_handler})
        set_app_name("FastAPI")

    def serve(self) -> None:
        """Begin serving this application."""
        super().serve()
        self.app.mount(
            prepare_url("/static"),
            StaticFiles(directory="static"),
            name="static",
        )
        uvicorn.run(self.app, host=self.host, port=int(self.port))

    @staticmethod
    def server_type() -> str:
        return "FastAPI"

    @staticmethod
    async def custom_404_handler(request: Request, excp: Any) -> HTMLResponse:
        """Handle 404 errors with custom page."""
        return await wrap_fastapi_func(
            "404 Not Found",
            partial(_not_found_handler, excp),
        )(request)

    def get_app(self) -> FastAPI:
        return self.app


def _not_found_handler(excp: Exception | None = None) -> str:
    """Simple 404 handler that returns HTML."""
    home_url = prepare_url("/")
    return f"""
    <html>
    <head><title>404 Not Found</title></head>
    <body>
        <h1>Page Not Found</h1>
        <p>The requested page could not be found.</p>
        <p><a href="{home_url}">Go home</a></p>
    </body>
    </html>
    """


def _index_page() -> str:
    """Generate the index/home page listing all endpoints."""
    from ionbus_flapi.request import get_request_context

    title = get_config("title", "Flapi Server")

    # Get current theme from cookie
    try:
        theme = get_request_context().theme
    except Exception:
        theme = "system"

    # Theme toggle JavaScript
    theme_js = """
    <script>
    function cycleTheme() {
        const themes = ['system', 'light', 'dark'];
        const currentTheme = document.cookie
            .split('; ')
            .find(row => row.startsWith('flapi_theme='))
            ?.split('=')[1] || 'system';
        const currentIndex = themes.indexOf(currentTheme);
        const nextTheme = themes[(currentIndex + 1) % themes.length];

        // Set cookie with 10 year expiry
        const expires = new Date();
        expires.setFullYear(expires.getFullYear() + 10);
        document.cookie = `flapi_theme=${nextTheme};expires=` +
            `${expires.toUTCString()};path=/`;

        // Reload to apply theme
        location.reload();
    }
    </script>
    """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <link rel="stylesheet" type="text/css"
        href="{prepare_url('/static/base.css')}">
    <link id="flapiTheme" rel="stylesheet" type="text/css"
        href="{prepare_url(f'/static/themes/{theme}.css')}">
    {theme_js}
    <style>
        .icon {{ height: 30px; width: 30px; cursor: pointer; }}
        #themeDiv {{ display: flex; gap: 5px; position: absolute;
            right: 10px; top: 10px; }}
        #themeDiv > div, #themeDiv > span {{ align-self: center; }}
    </style>
</head>
<body>
    <div id="themeDiv">
        <span>Theme: </span>
        <img src="{prepare_url(f'/static/assets/{theme}-mode.svg')}"
            class="icon" id="themeButton" onclick="cycleTheme()"
            title="Click to cycle: system -> light -> dark" />
    </div>
    <h1>{title}</h1>
"""

    # Add custom index body if configured
    index_body = get_config("index_body")
    if index_body:
        html += f"<div>{index_body}</div><hr>\n"

    # List endpoint groups
    html += "<h2>Available Endpoints</h2>\n"

    for group, endpoints in URLreg.endpoints.items():
        html += f"<h3>{group}</h3>\n"

        # Add group description if available
        if group in HTML_DOCS:
            html += HTML_DOCS[group]

        html += "<ul>\n"
        for name, urlreg in endpoints.items():
            if urlreg.show_in_dir:
                desc = urlreg.description or name
                html += f'<li><a href="{urlreg.address}">{desc}</a></li>\n'
        html += "</ul>\n"

    # List API endpoints if any
    if URLreg.api_docs:
        html += "<h2>API Endpoints</h2>\n"
        html += "<table border='1' cellpadding='8'>\n"
        html += "<tr><th>Endpoint</th><th>Description</th></tr>\n"
        for endpoint, doc in URLreg.api_docs.items():
            address = prepare_url(f"/{endpoint}")
            first_line = doc.split("\n")[0] if doc else ""
            html += f"<tr><td><code>{address}</code></td>"
            html += f"<td>{first_line}</td></tr>\n"
        html += "</table>\n"

    html += """
</body>
</html>
"""
    return html


def _register_core_routes() -> None:
    """Register the index and other core routes."""
    if _flapi_app is None:
        return

    index_address = prepare_url("/")
    register_endpoint_page(index_address, "index", _index_page)

    # Register shutdown endpoint if configured
    if get_config("shutdown_code"):
        shutdown_address = prepare_url("/shutdown")
        register_endpoint_page(
            shutdown_address, "shutdown", shutdown_endpoint
        )


def get_flapi() -> FlapiApp:
    """Get the FlapiApp instance set up via initialize()."""
    if not _server_initialized or not _flapi_app:
        raise NotInitializedError(
            "A FlapiApp must be initialized via initialize() before using."
        )
    return _flapi_app


def initialize(config: str | dict) -> None:
    """Initialize a FlapiApp based on configuration settings.

    Args:
        config: Either a filename of a YAML config file, or a Python
            dictionary with configuration settings.
    """
    global _flapi_app, _server_initialized  # noqa: PLW0603

    if isinstance(config, str):
        with open(config, encoding="utf-8") as f:
            config_obj: dict = yaml.safe_load(f)
    else:
        config_obj = config

    # Set defaults
    config_obj.setdefault("app_type", "flask")
    config_obj.setdefault("host", "127.0.0.1")
    config_obj.setdefault("port", 8000)
    config_obj.setdefault("max_threads", 10)
    config_obj.setdefault("use_proxy", False)
    config_obj.setdefault("proxy_prefix", None)
    config_obj.setdefault("show_shutdown", False)
    config_obj.setdefault("index_body", None)

    # Set title with app_name placeholder substitution
    app_name = config_obj.get("proxy_prefix") or config_obj.get("app_type")
    default_title = "{app_name} Pages Being Served"
    title = config_obj.get("title", default_title)
    if "{app_name}" in title:
        title = title.replace("{app_name}", app_name or "Flapi")
    config_obj["title"] = title

    set_config(config_obj)

    app_type = config_obj.get("app_type", "flask")

    if app_type == "flask":
        _flapi_app = FlaskFlapiApp()
    elif app_type == "fastapi":
        _flapi_app = FastAPIFlapiApp()
    else:
        raise RuntimeError(
            f"Failed to initialize server. Undefined server type: {app_type}"
        )

    _server_initialized = True


def serve() -> None:
    """Serve the current initialized Flapi app."""
    if _flapi_app is None:
        raise NotInitializedError(
            "A FlapiApp must be initialized via initialize() before using."
        )
    _register_core_routes()
    _flapi_app.serve()
