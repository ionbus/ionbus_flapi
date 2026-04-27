"""flapi/request.py

The HTTPRequest class and functions for managing request context.

Note: This module is not safe to use anywhere, since the Request Context
will only exist during an active HTTP request.
"""

from __future__ import annotations

import json
from contextvars import ContextVar
from enum import Enum
from typing import Any, ClassVar

import fastapi
import flask

from ionbus_utils.base_utils import is_windows
from ionbus_utils.group_utils import get_user_name

from ionbus_flapi.errors import NoContextError

_request_context: ContextVar[HTTPRequest] = ContextVar("request_context")


def _get_any_from_dict(target_dict: dict[Any, Any], keys: list[Any]) -> Any:
    """Return first value found for any key in keys, or None."""
    for key in keys:
        if value := target_dict.get(key):
            return value
    return None


class RequestProvider(Enum):
    """Enum for the provider type that filled this HTTPRequest."""

    FastAPI = 1
    Flask = 2

    def __str__(self):
        return self.name


class HTTPRequest:
    """A generic Request object for Flask or FastAPI requests.

    Enable enable_unsafe_attributes at class or instance level to allow
    unregistered fields. These are not guaranteed to work for all providers.

    NOTE: Some fields have been renamed for clarity:
        - flask.request.url -> HTTPRequest.full_url
    """

    values_missing: ClassVar[dict[RequestProvider, list[str]]] = {
        RequestProvider.FastAPI: [],
        RequestProvider.Flask: [],
    }

    request_provider: RequestProvider
    enable_unsafe_attributes: bool = False
    request: Any

    args: dict  # combined args, query + path params
    query_params: dict
    path_params: dict

    method: str
    full_url: str  # flask.request.url
    base_url: str  # full_url without query params
    full_path: str
    base_path: str  # flask.request.path, path without query params
    url_root: str
    headers: dict[str, str]
    json: dict
    form_data: dict
    cookies: dict
    _new_cookies: dict
    body: bytes
    theme: str
    username: str | None
    username_extra: str | None
    user: str  # used for authentication

    def __init__(self):
        """Initialize an empty HTTPRequest."""

    @classmethod
    def from_flask(cls) -> HTTPRequest:
        """Generate HTTPRequest from Flask's context-managed request."""
        req = HTTPRequest()
        req.request_provider = RequestProvider.Flask
        req.request = flask.request

        req.query_params = dict(flask.request.args)
        req.path_params = (
            flask.request.view_args if flask.request.view_args else {}
        )
        req.args = req.path_params
        req.args.update(req.query_params)

        req.method = flask.request.method
        req.full_url = flask.request.url
        req.base_url = flask.request.base_url
        req.full_path = flask.request.full_path
        req.base_path = flask.request.path
        req.url_root = flask.request.url_root
        req.headers = {
            x.lower(): y for x, y in flask.request.headers.items()
        }
        req.username = cls.get_username(req)
        req.username_extra = cls.usually_get_username(req)
        req.form_data = dict(flask.request.form)
        req.cookies = flask.request.cookies
        req._new_cookies = {}
        req.theme = req.cookies.get("flapi_theme", "system")

        body_bytes = flask.request.get_data()
        req.body = body_bytes
        json_result = None
        if body_bytes:
            try:
                json_result = json.loads(body_bytes, strict=False)
            except Exception:
                pass
        req.json = json_result if json_result is not None else {}

        return req

    @classmethod
    async def from_fastapi(cls, request: fastapi.Request) -> HTTPRequest:
        """Generate HTTPRequest from a FastAPI Request object."""
        req = HTTPRequest()
        req.request_provider = RequestProvider.FastAPI
        req.request = request

        req.query_params = dict(request.query_params.items())
        req.path_params = dict(request.path_params.items())
        req.args = req.path_params
        req.args.update(req.query_params)

        req.method = request.method
        req.url_root = request.url.netloc
        req.base_path = request.url.path
        req.full_path = f"{req.base_path}?{request.url.query}"
        req.base_url = (
            f"{request.url.scheme}://{req.url_root}{req.base_path}"
        )
        req.full_url = (
            f"{request.url.scheme}://{req.url_root}{req.full_path}"
        )
        req.headers = dict(request.headers.items())
        req.username = cls.get_username(req)
        req.username_extra = cls.usually_get_username(req)
        req.form_data = dict(await request.form())
        req.cookies = request.cookies
        req._new_cookies = {}
        req.theme = req.cookies.get("flapi_theme", "system")

        body_bytes = await request.body()
        req.body = body_bytes
        json_result = None
        if body_bytes:
            try:
                json_result = await request.json()
            except Exception:
                pass
        req.json = json_result if json_result is not None else {}

        return req

    @classmethod
    def get_username(cls, request: HTTPRequest) -> str | None:
        """Get the request username from headers."""
        return _get_any_from_dict(
            request.headers,
            [
                "x-webauth-user",
                "X-Webauth-User",
                "X_WEBAUTH_USER",
                "remote_user",
            ],
        )

    @classmethod
    def usually_get_username(cls, request: HTTPRequest) -> str | None:
        """Get username from headers, or Windows username as fallback.

        Returns None on non-Windows systems if no proxy username found.
        """
        if username := cls.get_username(request):
            return username
        if is_windows():
            return (get_user_name() or "").lower()
        return None

    def __getattr__(self, name: str) -> Any:
        """Get undefined attribute, with provider-specific error messages."""
        if self.enable_unsafe_attributes:
            return getattr(self.request, name)

        providers_defined = []
        for provider, missing_defs in self.values_missing.items():
            if provider != self.request_provider and name not in missing_defs:
                providers_defined.append(provider)

        if not providers_defined:
            error = (
                f"Attribute {name} is not defined for any endpoint provider."
            )
        else:
            formatted_providers = (
                str(providers_defined[0])
                if len(providers_defined) == 1
                else (
                    f"{', '.join(str(p) for p in providers_defined[:-1])} "
                    f"and {providers_defined[-1]}"
                )
            )
            error = (
                f"Attribute {name} is not defined when using "
                f"{self.request_provider}, but is defined for "
                f"{formatted_providers} requests."
            )

        raise AttributeError(error)


def set_request_context(request: HTTPRequest) -> None:
    """Set the request context ContextVar.

    This should never be called outside of response wrappers.
    """
    _request_context.set(request)


def get_request_context() -> HTTPRequest:
    """Get the current request context, if available.

    Note: This function CAN ONLY be used as part of an endpoint function,
    or a function called by an endpoint function. Do not use it in separate
    threads or during initialization.

    Raises:
        NoContextError: If called outside of an active request context.
    """
    try:
        context = _request_context.get()
    except LookupError:
        raise NoContextError(
            "get_request_context() was called outside of an active request "
            "context."
        ) from None
    return context


def set_cookie(key: str, value: str) -> None:
    """Set a cookie to be returned with the response.

    Use this to store state between requests.
    """
    get_request_context()._new_cookies.update({key: value})
