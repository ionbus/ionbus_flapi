"""flapi - A low-code framework for building web applications.

Flapi (FastAPI Low-code API) serves both human-facing webpages and APIs.
"""

from __future__ import annotations

try:
    from ionbus_flapi._version import __version__  # type: ignore
except ImportError:
    __version__ = "0.0.0"

from ionbus_flapi.app import (
    FlapiApp,
    get_flapi,
    initialize,
    serve,
)
from ionbus_flapi.config import (
    FlapiEnum,
    get_app_name,
    get_config,
    get_group_config,
    set_app_name,
    set_config,
)
from ionbus_flapi.errors import (
    FlapiError,
    InitializationError,
    NoContextError,
    NotInitializedError,
)
from ionbus_flapi.request import (
    HTTPRequest,
    RequestProvider,
    get_request_context,
    set_cookie,
    set_request_context,
)
from ionbus_flapi.response import (
    BaseEndpointResponse,
    EventStreamResponse,
    RedirectResponse,
)
from ionbus_flapi.page import (
    FlapiForwardPage,
    FlapiPage,
)
from ionbus_flapi.routing import (
    extract_variables_from_address,
    prepare_route,
    prepare_url,
    register_api_endpoint,
    register_dash_endpoint,
    register_endpoint,
    register_endpoint_group,
)
from ionbus_flapi.shutdown import (
    get_shutdown_event,
    is_shutting_down,
    register_shutdown_callback,
)
from ionbus_flapi.event_stream import (
    EventStreamManager,
    EventStreamTypes,
)
from ionbus_flapi.components import (
    BaseComponent,
    ClickHook,
    ColumnsContainer,
    Container,
    DashComponent,
    FormComponent,
    FormElement,
    FrameComponent,
    HtmlComponent,
    IframeComponent,
    ImageComponent,
    MarkdownComponent,
    PlotlyComponent,
    component_factory,
    is_form_update,
    register_markdown_endpoint,
)

__all__ = [
    "__version__",
    # app
    "FlapiApp",
    "get_flapi",
    "initialize",
    "serve",
    # config
    "FlapiEnum",
    "get_app_name",
    "get_config",
    "get_group_config",
    "set_app_name",
    "set_config",
    # errors
    "FlapiError",
    "InitializationError",
    "NoContextError",
    "NotInitializedError",
    # request
    "HTTPRequest",
    "RequestProvider",
    "get_request_context",
    "set_cookie",
    "set_request_context",
    # response
    "BaseEndpointResponse",
    "EventStreamResponse",
    "RedirectResponse",
    # page
    "FlapiForwardPage",
    "FlapiPage",
    # routing
    "extract_variables_from_address",
    "prepare_route",
    "prepare_url",
    "register_api_endpoint",
    "register_dash_endpoint",
    "register_endpoint",
    "register_endpoint_group",
    # shutdown
    "get_shutdown_event",
    "is_shutting_down",
    "register_shutdown_callback",
    # event_stream
    "EventStreamManager",
    "EventStreamTypes",
    # components
    "BaseComponent",
    "ClickHook",
    "ColumnsContainer",
    "Container",
    "DashComponent",
    "FormComponent",
    "FormElement",
    "FrameComponent",
    "HtmlComponent",
    "IframeComponent",
    "ImageComponent",
    "MarkdownComponent",
    "PlotlyComponent",
    "component_factory",
    "is_form_update",
    "register_markdown_endpoint",
]
