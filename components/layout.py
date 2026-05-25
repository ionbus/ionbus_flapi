"""flapi/components/layout.py

Layout components for organizing content.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import pandas as pd
import plotly.graph_objects as go

from ionbus_flapi.components.base import (
    BaseComponent,
    HtmlComponent,
    PlotlyComponent,
)

if TYPE_CHECKING:
    from ionbus_flapi.page import FlapiPage


def component_factory(
    page: FlapiPage | None,
    obj: Any,
    name: str | int | None = None,
) -> BaseComponent:
    """Factory function to create appropriate component from object.

    Automatically converts common types to components:
    - BaseComponent: returns as-is (sets page and name if needed)
    - str: HtmlComponent
    - list/tuple: Container
    - pd.DataFrame: FrameComponent (imported dynamically)
    - go.Figure: PlotlyComponent
    """
    if isinstance(obj, BaseComponent):
        obj.page = page
        if not obj.name:
            obj.set_name(name)
        return obj

    if isinstance(obj, (list, tuple)):
        return Container(list(obj), page, name)

    if isinstance(obj, str):
        return HtmlComponent(obj, page, name)

    if isinstance(obj, pd.DataFrame):
        # Import dynamically to avoid circular imports
        from ionbus_flapi.components.dataframe import FrameComponent
        return FrameComponent(obj, page, name)

    if isinstance(obj, go.Figure):
        return PlotlyComponent(obj, page, name)

    raise RuntimeError(f"Unknown type for component factory: {type(obj)}")


class Container(BaseComponent):
    """A component that contains other components."""

    class_name: ClassVar[str] = "Container"
    component_objs: list[BaseComponent]

    def __init__(
        self,
        components: list[Any],
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        self.component_objs = [
            component_factory(None, x) for x in components
        ]
        super().__init__(page, name, **kwargs)

    def get_document_ready_js(self) -> str:
        """Returns combined JavaScript from all components."""
        ret_str = ""
        for component in self.component_objs:
            ret_str += component.get_document_ready_js()
        return ret_str

    def get_html(self) -> str:
        """Returns combined HTML from all components."""
        ret_str = ""
        for component in self.component_objs:
            ret_str += component.get_html()
        return ret_str

    def set_requirements(self) -> None:
        """Sets requirements for all components."""
        for component in self.component_objs:
            component.set_requirements()

    @BaseComponent.page.setter
    def page(self, value: FlapiPage | None) -> None:
        self._page = value
        for component in self.component_objs:
            component.page = value


class ColumnsContainer(Container):
    """A component that places other components in columns using CSS grid."""

    class_name: ClassVar[str] = "ColumnsContainer"
    column_desc: str | None = None
    no_break: bool = False

    def __init__(
        self,
        *columns: Any,
        column_desc: str | None = None,
        no_break: bool = False,
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        self.column_desc = column_desc
        self.no_break = no_break
        super().__init__(list(columns), page, name, **kwargs)

    def get_html(self) -> str:
        """Returns HTML with columns in a CSS grid layout."""
        if not self.column_desc:
            self.column_desc = " 1fr" * len(self.component_objs)

        nobr_start = "<nobr>" if self.no_break else ""
        nobr_end = "</nobr>" if self.no_break else ""

        ret_str = (
            f'<div class="grid-container" '
            f'style="grid-template-columns: {self.column_desc};">\n'
            f"{nobr_start}"
        )
        for component in self.component_objs:
            ret_str += f"<div>\n{component.get_html()}\n</div>\n"
        ret_str += f"{nobr_end}</div>"
        return ret_str


class IframeComponent(BaseComponent):
    """Named iframe component for use as a ClickHook target.

    The `frame_name` attribute becomes the HTML `name=""` on the iframe;
    set the same string as a ClickHook's `target` to make grid clicks
    load URLs into this iframe.
    """

    class_name: ClassVar[str] = "IframeComponent"
    frame_name: str = ""
    src: str = "about:blank"
    width: str | None = None
    height: str | None = None
    style: str | None = None

    def __init__(
        self,
        frame_name: str,
        src: str = "about:blank",
        width: str | None = None,
        height: str | None = None,
        style: str | None = None,
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        if not frame_name:
            raise ValueError("IframeComponent requires a non-empty frame_name")
        self.frame_name = frame_name
        self.src = src
        self.width = width
        self.height = height
        self.style = style
        super().__init__(page, name, **kwargs)

    def get_html(self) -> str:
        style_bits = []
        if self.width is not None:
            style_bits.append(f"width: {self.width}")
        if self.height is not None:
            style_bits.append(f"height: {self.height}")
        if self.style:
            style_bits.append(self.style)
        style_attr = (
            f' style="{"; ".join(style_bits)}"' if style_bits else ""
        )
        return (
            f'<iframe id="iframe{self.name}" name="{self.frame_name}" '
            f'src="{self.src}"{style_attr}></iframe>'
        )


def pop_banner_js(duration: int | float = 3) -> str:
    """Returns the JavaScript for the pop banner."""
    return f"""
        function popup_banner(msg) {{
            $('#popupBanner').fadeIn();
            document.getElementById('popupBanner').innerHTML = msg;
            setTimeout(function() {{
                $('#popupBanner').fadeOut();
            }}, {duration * 1000})
        }}\n"""


def banner_html() -> str:
    """Returns the HTML for a popup banner."""
    return """<div id="popupBanner" style="position: absolute; right: 10px;
        top: 10px; padding: 4px 12px 4px 8px; background-color: yellow;
        height: 15px; font-size: 13px; border: 1px solid darkgrey;
        border-radius: 4px; display: none; line-height: normal;"></div>"""
