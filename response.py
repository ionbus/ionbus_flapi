"""flapi/response.py

Specialized Response classes and endpoint wrappers for Flask/FastAPI.
"""

from __future__ import annotations

import socket
from datetime import datetime, timedelta
from typing import Any, Callable, ClassVar, Iterable

import fastapi
import flask
import starlette.responses
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import RedirectResponse as FastAPIRedirect
from fastapi.responses import StreamingResponse
from flask import redirect

from ionbus_utils.exceptions import exception_to_string
from ionbus_utils.logging_utils import logger

from ionbus_flapi.config import FlapiEnum, get_config
from ionbus_flapi.request import (
    HTTPRequest,
    get_request_context,
    set_request_context,
)


def _get_any_from_dict(target_dict: dict[Any, Any], keys: list[Any]) -> Any:
    """Return first value found for any key in keys, or None."""
    for key in keys:
        if value := target_dict.get(key):
            return value
    return None


# ---------------------------------------------------------------------------
# Response Classes
# ---------------------------------------------------------------------------


class BaseEndpointResponse:
    """Abstract base Endpoint Response.

    Gets caught by Endpoint and converted to proper type when returned
    by an endpoint_func.
    """

    def get_flask(self) -> flask.Response:
        """Return the flask.Response version."""
        raise NotImplementedError

    def get_fastapi(self) -> fastapi.Response:
        """Return the fastapi.Response version."""
        raise NotImplementedError


class EventStreamResponse(BaseEndpointResponse):
    """Response that keeps connection open and yields data.

    See EventStreamManager for usage.
    """

    def __init__(self, stream_func: Iterable[str] | Iterable[bytes]):
        self.stream_func = stream_func

    def get_flask(self) -> flask.Response:
        return flask.Response(self.stream_func, mimetype="text/event-stream")

    def get_fastapi(self) -> fastapi.Response:
        return StreamingResponse(
            self.stream_func, media_type="text/event-stream"
        )


class RedirectResponse(BaseEndpointResponse):
    """Response that redirects to a different address."""

    def __init__(self, location: str):
        self.location = location

    def get_flask(self) -> flask.Response:
        return redirect(self.location)

    def get_fastapi(self) -> fastapi.Response:
        return FastAPIRedirect(self.location)


# ---------------------------------------------------------------------------
# Error Pages
# ---------------------------------------------------------------------------


def error_page(
    message: str,
    error: str | Exception | None = None,
    back_url: str | None = None,
) -> str:
    """Return HTML for displaying an error in a nice format."""
    back_html = "history.back();"
    if back_url:
        back_html = back_url

    error_html = ""
    if error:
        if not isinstance(error, str):
            error = exception_to_string(error)
        error_html = f"""
        <div id="show" onclick="toggleError();">Show More</div>
        <div id="greybox" style="display: none;">
            <pre id="error">{error}</pre>
        </div>
        <script>
            function toggleError() {{
                obj = document.getElementById("show");
                if (obj.innerHTML == "Show More") {{
                    obj.innerHTML = "Show Less";
                    document.getElementById("greybox").style.display = "";
                }} else {{
                    obj.innerHTML = "Show More";
                    document.getElementById("greybox").style.display = "none";
                }}
            }}
        </script>
        <style>
            #show {{ cursor: pointer; width: fit-content; margin-bottom: 15px; }}
            #greybox {{ background-color: lightgrey; padding: 15px; width: fit-content; }}
            #error {{ margin: 0; }}
        </style>
        """

    return f"""
    <head><title>{message}</title></head>
    <div>
        <h1>Error</h1>
        <h3>{message}</h3>
        <br>
        {error_html}
        <button title="test" id="goback" onclick="{back_html}"
            style="margin-top: 20px;">Go Back</button>
    </div>
    """


# ---------------------------------------------------------------------------
# Authentication Errors
# ---------------------------------------------------------------------------


class AuthenticationError(RuntimeError):
    """Request not properly authenticated."""

    user_email: str | None
    host_from: str

    def __init__(self, user_email: str | None, host_from: str):
        self.user_email = user_email
        self.host_from = host_from

    def error_page(self) -> str:
        return (
            "<head><title>Authentication Failed</title></head>"
            f"Authentication failed. Ensure your account "
            f"({self.user_email}) has access to this page."
        )


class BadAccessError(RuntimeError):
    """Request did not come from a proxy server."""

    def __init__(self):
        pass

    @staticmethod
    def error_page() -> str:
        return (
            "<head><title>Proxy Not Found</title></head>"
            "Access to this server is blocked except through a reverse proxy."
        )


# ---------------------------------------------------------------------------
# Endpoint Classes
# ---------------------------------------------------------------------------


class Endpoint:
    """Base class for HTTP Endpoints defined by FlapiApp."""

    canon_name: ClassVar[str]
    name: str
    endpoint_func: Callable
    json_return: bool

    def __init__(
        self, name: str, endpoint_func: Callable, json_return: bool = False
    ):
        self.name = name
        self.endpoint_func = endpoint_func
        self.json_return = json_return

    def __call__(self):
        """Run endpoint_func, handle errors and return error page if needed."""
        try:
            response = self.endpoint_func()
        except Exception as exception:
            response = self._get_error_response(exception)

        if response is None:
            response = self._get_null_response()

        # Check for FlapiPage without importing it (avoid circular import)
        if (
            isinstance(response, object)
            and response.__class__.__name__ == "FlapiPage"
        ):
            return str(response)
        return response

    def _get_error_response(self, exception: Exception) -> str | dict:
        """Return error response if endpoint crashed."""
        if self.json_return:
            return {
                "endpoint_name": self.name,
                "exception": exception_to_string(exception),
            }
        return error_page(
            f"Exception on page {self.name}",
            error=exception_to_string(exception),
        )

    def _get_null_response(self) -> str:
        """Return error page if endpoint returned None."""
        return error_page(f"Null return for page {self.name}", error="None")

    @staticmethod
    def verify_request(request: HTTPRequest) -> str:
        """Verify request came through reverse proxy. Return username."""
        if not get_config("use_proxy"):
            return "admin"

        username = request.username
        host_from = _get_any_from_dict(
            request.headers,
            ["x-forwarded-host", "X-Forwarded-Host", "X_FORWARDED_HOST"],
        )

        if not host_from:
            raise BadAccessError()
        if not username or socket.gethostname() not in host_from:
            raise AuthenticationError(username, host_from)
        return username


class FlaskEndpoint(Endpoint):
    """Endpoint wrapper for Flask servers."""

    canon_name = "Flask"

    def __call__(self):
        """Handle JSON, str, BaseEndpointResponse -> Flask Response."""
        run_return = super().__call__()
        response: flask.Response

        if isinstance(run_return, BaseEndpointResponse):
            response = run_return.get_flask()
        elif isinstance(run_return, dict):
            response = flask.jsonify(run_return)
        else:
            response = flask.Response(run_return)

        new_cookies = get_request_context()._new_cookies
        if new_cookies:
            expires = datetime.now() + timedelta(days=365 * 10)
            for key, val in new_cookies.items():
                response.set_cookie(key, val, expires=expires.timestamp())
        return response


class FastAPIEndpoint(Endpoint):
    """Endpoint wrapper for FastAPI servers."""

    canon_name = "FastAPI"

    def __call__(self):
        """Handle JSON, str, BaseEndpointResponse -> FastAPI Response."""
        run_return = super().__call__()
        response: fastapi.Response

        if isinstance(run_return, BaseEndpointResponse):
            response = run_return.get_fastapi()
        elif isinstance(run_return, dict):
            if (
                run_return.get(FlapiEnum.ERROR)
                or run_return.get(FlapiEnum.STATUS) == FlapiEnum.ERROR
            ):
                error_message = run_return.get(FlapiEnum.MESSAGE) or "ERROR"
                logger.warning(f"Error in api endpoint {error_message=}")
                return JSONResponse(
                    status_code=run_return.get(FlapiEnum.ERROR_CODE, 400),
                    content={FlapiEnum.MESSAGE: error_message},
                )
            else:
                response = JSONResponse(content=run_return)
        else:
            response = HTMLResponse(run_return)

        new_cookies = get_request_context()._new_cookies
        if new_cookies:
            expires = datetime.now() + timedelta(days=365 * 10)
            for key, val in new_cookies.items():
                response.set_cookie(key, val, expires=expires.timestamp())
        return response


# ---------------------------------------------------------------------------
# Wrapper Functions
# ---------------------------------------------------------------------------


def wrap_flask_func(
    name: str,
    func: Callable,
    json_return: bool = False,
) -> Callable:
    """Wrap a Flask endpoint to setup Request object for each request."""

    def inner_func() -> Any:
        http_request = HTTPRequest.from_flask()
        return _run_and_verify_proxy(
            FlaskEndpoint(name, func, json_return), http_request
        )

    return inner_func


def wrap_fastapi_func(
    name: str,
    func: Callable,
    json_return: bool = False,
) -> Callable:
    """Wrap a FastAPI endpoint to setup Request object for each request."""

    async def inner_func(request: Request) -> starlette.responses.Response:
        http_request = await HTTPRequest.from_fastapi(request)
        return _run_and_verify_proxy(
            FastAPIEndpoint(name, func, json_return), http_request
        )

    return inner_func


def _run_and_verify_proxy(
    endpoint_func: Endpoint, request: HTTPRequest
) -> Any:
    """Verify request came from reputable source, then run endpoint."""
    try:
        request.user = endpoint_func.verify_request(request)
    except AuthenticationError as e:
        return e.error_page()
    except BadAccessError as e:
        return e.error_page()

    set_request_context(request)
    return endpoint_func()
