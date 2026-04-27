"""flapi/routing.py

Contains routing functions for setting up API routes/pages on the server.
Includes URL preparation and endpoint registration.
"""

from __future__ import annotations

import re
import urllib.parse
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from dash import Dash
from fastapi.middleware.wsgi import WSGIMiddleware

from ionbus_utils.exceptions import exception_to_string
from ionbus_utils.logging_utils import logger
from ionbus_utils.regex_utils import SPACE_RE

from ionbus_flapi.config import get_config
from ionbus_flapi.errors import InitializationError
from ionbus_flapi.response import wrap_fastapi_func, wrap_flask_func

if TYPE_CHECKING:
    from ionbus_flapi.app import FlapiApp

# Module-level state
ROUTING_PROVIDER: RoutingProvider
FLAPI_APP: FlapiApp
HTML_DOCS: dict[str, str] = {}


# ---------------------------------------------------------------------------
# URL Utilities
# ---------------------------------------------------------------------------


def prepare_url(
    url: str, prefix: bool = True, use_trailing_slash: bool = False
) -> str:
    """Prepare a URL string for use with FlapiApp.

    This function should be used WHENEVER an absolute URL is referenced.

    Args:
        url: The URL to prepare.
        prefix: Whether to add the proxy prefix.
        use_trailing_slash: Whether to add a trailing slash.

    Returns:
        The prepared URL string.
    """
    proxy_prefix = get_config("proxy_prefix")
    if url.startswith("/") and proxy_prefix and prefix:
        url = url.rstrip("/")
        return f"/{proxy_prefix}{url}{'/' if use_trailing_slash else ''}"
    return url


def prepare_route(
    group: str | None,
    name: str,
    prefix: bool = True,
    use_trailing_slash: bool = False,
) -> str:
    """Generate a URL route from a group and name.

    Args:
        group: The endpoint group name (e.g., "Forms").
        name: The endpoint name within the group.
        prefix: Whether to add the proxy prefix.
        use_trailing_slash: Whether to add a trailing slash.

    Returns:
        The full route string.
    """
    name = name.strip("/")
    if group is not None:
        name = f"{group.strip('/')}/{name}"
    address = f"/{name}/"
    return prepare_url(address, prefix, use_trailing_slash=use_trailing_slash)


# Regex patterns for extract_variables_from_address
_UP_TO_SLASH_RE = re.compile(r".*/")
_AMP_RE = re.compile(r"&")
_EQUAL_RE = re.compile(r"(\S+)=(.*)")


def extract_variables_from_address(address: str) -> dict[str, str]:
    """Extract query parameters from a URL/address string.

    Useful inside Dash callbacks when parsing the URL from dcc.Location.

    Args:
        address: The URL or address string containing query params.

    Returns:
        A dict mapping parameter names to their values.
    """
    address = urllib.parse.unquote(address)
    address = _UP_TO_SLASH_RE.sub("", address)
    ret_dict: dict[str, str] = {}
    if not address:
        return ret_dict
    for part in _AMP_RE.split(address):
        match = _EQUAL_RE.search(part)
        if match:
            ret_dict[match.group(1)] = match.group(2)
        else:
            logger.warning(f'Cannot parse key, value from "{part}"')
    return ret_dict


# ---------------------------------------------------------------------------
# URL Registration
# ---------------------------------------------------------------------------


class URLreg:
    """Wrapper for a registered URL with metadata.

    Keeps track of all registered endpoints in class-level dicts.
    """

    address_set: ClassVar[set] = set()
    trailing_re: ClassVar[re.Pattern] = re.compile(r"/$")
    endpoints: ClassVar[dict] = {}
    api_docs: ClassVar[dict] = {}

    def __init__(
        self,
        address: str,
        name: str,
        group: str | None,
        description: str | None,
        show_in_dir: bool = True,
    ):
        if address in URLreg.address_set:
            raise RuntimeError(f"Address {address} already used")
        URLreg.address_set.add(address)
        self.name = name
        self.address = address
        self.description = description
        self.show_in_dir = show_in_dir
        if group:
            to_add = URLreg.endpoints.setdefault(group, {})
        else:
            to_add = URLreg.endpoints
        to_add[name] = self


# ---------------------------------------------------------------------------
# Routing Providers
# ---------------------------------------------------------------------------


class RoutingProvider:
    """Abstract class for handling routing.

    Subclasses implement server-specific functionality.
    """

    url_dict: dict

    def __init__(self):
        self.url_dict = {}

    @abstractmethod
    def register_endpoint_page(
        self,
        address: str,
        name: str,
        func: Callable,
        json_return: bool = False,
        *args,
        **kwargs,
    ) -> None:
        """Register the actual page via this server's app."""

    def register_endpoint(
        self,
        group: str | None,
        name: str,
        func: Callable,
        *args,
        ep_description: str | None = None,
        url_dict: dict[str, Any] | None = None,
        show_in_dir: bool = True,
        show_in_dropdown: bool | None = None,
        use_trailing_slash: bool = False,
        **kwargs,
    ) -> None:
        """Register an endpoint under a specific group."""
        if url_dict is None:
            url_dict = self.url_dict
        address = self.register_url(
            name,
            group,
            ep_description,
            show_in_dir,
            show_in_dropdown,
            use_trailing_slash,
        )
        self.register_endpoint_page(
            address, name or "", func, *args, **kwargs
        )

    @abstractmethod
    def register_dash_endpoint(
        self,
        group: str,
        name: str,
        *args,
        ep_description: str | None = None,
        show_in_dir: bool = False,
        show_in_dropdown: bool | None = None,
        external_stylesheets: list[str] | None = None,
        **kwargs,
    ) -> Dash:
        """Register an endpoint that starts up a Dash server."""

    def register_url(
        self,
        name: str,
        group: str | None,
        ep_description: str | None = None,
        show_in_dir: bool = True,
        show_in_dropdown: bool | None = None,
        use_trailing_slash: bool = False,
    ) -> str:
        """Register URL and create URLreg entry."""
        local_name = name = name.strip("/")

        address = prepare_route(
            group, name, use_trailing_slash=use_trailing_slash
        )
        if name.startswith("_") or (group and group.startswith("_")):
            raise InitializationError(
                f"URL names cannot start with underscore, as the "
                f"namespace is reserved. (Issue: {address})"
            )
        if show_in_dropdown is None:
            show_in_dropdown = show_in_dir

        if show_in_dropdown and ep_description is None:
            raise InitializationError(
                f"Endpoints shown in dropdown must have ep_description. "
                f"(Issue: {address})"
            )
        if show_in_dropdown:
            self.url_dict[ep_description] = address
        URLreg(
            address,
            local_name,
            group,
            ep_description,
            show_in_dir=show_in_dir,
        )
        logger.info(f"Registered endpoint at '{address}'")
        return address

    @staticmethod
    def create(app_type: str) -> RoutingProvider:
        """Create a RoutingProvider for the given app_type."""
        class_dict = {
            "flask": FlaskRoutingProvider,
            "fastapi": FastAPIRoutingProvider,
        }
        class_type = class_dict.get(app_type)
        if not class_type:
            raise InitializationError(
                "Server must be running as 'flask' or 'fastapi'."
            )
        return class_type()


class FlaskRoutingProvider(RoutingProvider):
    """Handles routing through Flask WSGI application."""

    def register_dash_endpoint(
        self,
        group: str,
        name: str,
        *args,
        ep_description: str | None = None,
        show_in_dir: bool = False,
        show_in_dropdown: bool | None = None,
        external_stylesheets: list[str] | None = None,
        **kwargs,
    ) -> Dash:
        if external_stylesheets is None:
            external_stylesheets = [prepare_url("/static/base.css")]
        address = super().register_url(
            name,
            group,
            ep_description=ep_description,
            show_in_dir=show_in_dir,
            show_in_dropdown=show_in_dropdown,
            use_trailing_slash=True,
        )
        return Dash(
            __name__,
            *args,
            server=FLAPI_APP.app,
            url_base_pathname=address,
            external_stylesheets=external_stylesheets,
            **kwargs,
        )

    @staticmethod
    def register_endpoint_page(
        address: str,
        name: str,
        func: Callable,
        json_return: bool = False,
        *args,
        **kwargs,
    ) -> None:
        # strict_slashes=False allows both /path and /path/ to work
        FLAPI_APP.app.add_url_rule(
            address,
            name,
            wrap_flask_func(name, func, json_return=json_return),
            strict_slashes=False,
            *args,
            **kwargs,
        )


class FastAPIRoutingProvider(RoutingProvider):
    """Handles routing through FastAPI ASGI application."""

    def register_dash_endpoint(
        self,
        group: str,
        name: str,
        *args,
        ep_description: str | None = None,
        show_in_dir: bool = False,
        show_in_dropdown: bool | None = None,
        external_stylesheets: list[str] | None = None,
        **kwargs,
    ) -> Dash:
        if external_stylesheets is None:
            external_stylesheets = [prepare_url("/static/base.css")]
        address = super().register_url(
            name,
            group,
            ep_description=ep_description,
            show_in_dir=show_in_dir,
            show_in_dropdown=show_in_dropdown,
            use_trailing_slash=True,
        )
        dash_app = Dash(
            __name__,
            *args,
            server=True,
            requests_pathname_prefix=address,
            routes_pathname_prefix="/",
            external_stylesheets=external_stylesheets,
            **kwargs,
        )
        FLAPI_APP.app.mount(address, WSGIMiddleware(dash_app.server))
        return dash_app

    @staticmethod
    def register_endpoint_page(
        address: str,
        name: str,
        func: Callable,
        json_return: bool = False,
        *args,
        **kwargs,
    ) -> None:
        FLAPI_APP.app.add_api_route(
            address,
            wrap_fastapi_func(name, func, json_return),
            *args,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Public Registration Functions
# ---------------------------------------------------------------------------


def register_url(
    name: str,
    group: str | None,
    ep_description: str | None = None,
    show_in_dir: bool = True,
    show_in_dropdown: bool | None = None,
    use_trailing_slash: bool = False,
) -> str:
    """Register URL for an endpoint on this server.

    Args:
        group: The group prefix for the endpoint.
        name: The name of the endpoint in the group.
            (full URLs look like host/proxy_prefix/group/name)
        ep_description: Descriptive name shown as tab title.
        show_in_dir: Set False to hide from endpoint list.
        show_in_dropdown: Set False to hide from jump_to dropdown.
        use_trailing_slash: If True, requires trailing slash.
    """
    return ROUTING_PROVIDER.register_url(
        name,
        group,
        ep_description,
        show_in_dir,
        show_in_dropdown,
        use_trailing_slash,
    )


def register_endpoint(
    group: str | None,
    name: str,
    func: Callable,
    *args,
    ep_description: str | None = None,
    url_dict: dict[str, Any] | None = None,
    show_in_dir: bool = True,
    show_in_dropdown: bool | None = None,
    use_trailing_slash: bool = False,
    **kwargs,
) -> None:
    """Register a classic endpoint page on the server.

    The endpoint function should return string, dict, or BaseEndpointResponse.

    Args:
        group: The group prefix for the endpoint.
        name: The name of the endpoint in the group.
        func: Function called when request is sent to endpoint.
        ep_description: Descriptive name shown as tab title.
        show_in_dir: Set False to hide from endpoint list.
        show_in_dropdown: Set False to hide from jump_to dropdown.
        use_trailing_slash: If True, requires trailing slash.
    """
    return ROUTING_PROVIDER.register_endpoint(
        group,
        SPACE_RE.sub("_", name),
        func,
        *args,
        ep_description=ep_description,
        url_dict=url_dict,
        show_in_dir=show_in_dir,
        show_in_dropdown=show_in_dropdown,
        use_trailing_slash=use_trailing_slash,
        **kwargs,
    )


def register_endpoint_group(
    init_func: Callable | None,
    group_name: str,
    html_description: str | None = None,
) -> None:
    """Register a group of endpoints under a sub-url.

    Args:
        init_func: Should call register_endpoint for each endpoint in group.
        group_name: The name of the group to register.
        html_description: HTML description for the group.
    """
    sub_info = get_config(group_name, {})
    if not sub_info.get("RunModule", True):
        logger.info(f"Configured NOT to run {group_name}")
        return
    ROUTING_PROVIDER.url_dict[group_name] = ""
    if html_description:
        HTML_DOCS[group_name] = html_description
    try:
        if init_func:
            init_func()
    except Exception as e:
        logger.info(
            f"Failed to initialize endpoint group: {group_name}\n"
            f"{exception_to_string(e)}"
        )


def register_api_endpoint(
    group: str | None,
    name: str,
    api_func: Callable,
    methods: str | list[str] = "GET",
    register_api_docs: bool = True,
) -> str:
    """Register a JSON API endpoint.

    Args:
        group: The group prefix for the endpoint.
        name: The name of the endpoint in the group.
        api_func: Function to call when API is called.
        methods: HTTP methods the endpoint accepts.
        register_api_docs: If True, show docstring on main page.

    Returns:
        The registered address.
    """
    address = register_url(name, group, show_in_dir=False)
    methods = [methods] if isinstance(methods, str) else methods
    if register_api_docs:
        URLreg.api_docs[f"{group}/{name}"] = (api_func.__doc__ or "").rstrip()
    register_endpoint_page(
        address,
        name,
        api_func,
        methods=methods,
        json_return=True,
    )
    return address


def register_endpoint_page(
    address: str,
    name: str,
    func: Callable,
    json_return: bool = False,
    *args,
    **kwargs,
) -> None:
    """Register a page via the underlying WSGI/ASGI application.

    This is useful when routing is handled elsewhere (e.g., mounted server).

    Args:
        address: Full absolute URL for this endpoint.
        name: Name for registering on underlying server.
        func: Endpoint function that handles requests.
        json_return: If True, return JSON instead of HTML on error.
    """
    ROUTING_PROVIDER.register_endpoint_page(
        address,
        name,
        func,
        json_return=json_return,
        *args,
        **kwargs,
    )


def register_dash_endpoint(
    group: str,
    name: str,
    *args,
    ep_description: str | None = None,
    show_in_dir: bool = False,
    show_in_dropdown: bool | None = None,
    external_stylesheets: list[str] | None = None,
    **kwargs,
) -> Dash:
    """Register an endpoint that displays a Dash page.

    Args:
        group: The group prefix for the endpoint.
        name: The name of the endpoint in the group.
        ep_description: Descriptive name shown as tab title.
        show_in_dir: Set False to hide from endpoint list.
        show_in_dropdown: Set False to hide from jump_to dropdown.
        external_stylesheets: CSS stylesheet URLs to include.

    Returns:
        The Dash object to configure (set dash_obj.layout).
    """
    return ROUTING_PROVIDER.register_dash_endpoint(
        group,
        name,
        *args,
        ep_description=ep_description,
        show_in_dir=show_in_dir,
        show_in_dropdown=show_in_dropdown,
        external_stylesheets=external_stylesheets,
        **kwargs,
    )


def get_url_dict() -> dict:
    """Return the nested dictionary of registered URLs."""
    return ROUTING_PROVIDER.url_dict


def initialize_routing(flapi_app: FlapiApp) -> None:
    """Initialize module from FlapiApp. Must be called before using routing."""
    global ROUTING_PROVIDER, FLAPI_APP  # noqa: PLW0603
    ROUTING_PROVIDER = RoutingProvider.create(get_config("app_type"))
    FLAPI_APP = flapi_app
