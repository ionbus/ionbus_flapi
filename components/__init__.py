"""flapi/components/__init__.py

UI components for building flapi pages.
"""

from __future__ import annotations

from ionbus_flapi.components.base import (
    BaseComponent,
    DashComponent,
    HtmlComponent,
    ImageComponent,
    PlotlyComponent,
)
from ionbus_flapi.components.dataframe import (
    ClickHook,
    FrameComponent,
    SELECTION_MODES,
    cleanup_frame_values_for_js,
    get_javascript_aggregation,
    guess_width_for_column,
)
from ionbus_flapi.components.form import (
    CHECK_BOX_ENUM,
    ELEMENT_ENUM,
    FormComponent,
    FormElement,
    is_form_update,
)
from ionbus_flapi.components.layout import (
    ColumnsContainer,
    Container,
    IframeComponent,
    banner_html,
    component_factory,
    pop_banner_js,
)
from ionbus_flapi.components.text import (
    MarkdownComponent,
    markdown_endpoint,
    register_markdown_endpoint,
)

__all__ = [
    # base
    "BaseComponent",
    "DashComponent",
    "HtmlComponent",
    "ImageComponent",
    "PlotlyComponent",
    # dataframe
    "ClickHook",
    "FrameComponent",
    "SELECTION_MODES",
    "cleanup_frame_values_for_js",
    "get_javascript_aggregation",
    "guess_width_for_column",
    # form
    "CHECK_BOX_ENUM",
    "ELEMENT_ENUM",
    "FormComponent",
    "FormElement",
    "is_form_update",
    # layout
    "ColumnsContainer",
    "Container",
    "IframeComponent",
    "banner_html",
    "component_factory",
    "pop_banner_js",
    # text
    "MarkdownComponent",
    "markdown_endpoint",
    "register_markdown_endpoint",
]
