"""flapi/components/base.py

Base component classes for building HTML content.
"""

from __future__ import annotations

import base64
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, ClassVar

import plotly
import plotly.graph_objects as go
import plotly.io as pio

from ionbus_utils.general import package_version_tuple

if TYPE_CHECKING:
    from ionbus_flapi.page import FlapiPage


class BaseComponent:
    """Base component for building HTML content.

    Components are objects that can render themselves to HTML
    and optionally provide JavaScript for document ready events.
    """

    lock: ClassVar[Lock] = Lock()
    num_times: ClassVar[int] = 0
    class_name: ClassVar[str] = "BaseComponent"

    _page: FlapiPage | None = None

    def __init__(
        self,
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        self.page = page
        self.name = self._name_string(name)
        # Store any extra kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    def set_name(self, name: int | str | None) -> None:
        """Sets name from integer or string."""
        self.name = self._name_string(name)

    def get_document_ready_js(self) -> str:
        """Returns JavaScript to run when document is ready."""
        return ""

    def get_html(self) -> str:
        """Returns HTML content."""
        return ""

    def set_requirements(self) -> None:
        """Sets any needed page requirements (e.g., headers)."""
        pass

    @property
    def page(self) -> FlapiPage | None:
        return self._page

    @page.setter
    def page(self, value: FlapiPage | None) -> None:
        self._page = value

    @classmethod
    def _name_string(cls, name: int | str | None) -> str:
        """Generate a unique name string."""
        if name is None or name == "":
            with cls.lock:
                cls.num_times += 1
                return f"{cls.class_name}_{cls.num_times}_global"
        if isinstance(name, int):
            return f"{cls.class_name}_{name}"
        return name

    def __str__(self) -> str:
        """Render component as HTML string."""
        return self.get_html()


class HtmlComponent(BaseComponent):
    """Raw HTML component."""

    class_name: ClassVar[str] = "HtmlComponent"
    html: str = ""

    def __init__(
        self,
        html: str = "",
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        self.html = html
        super().__init__(page, name, **kwargs)

    def get_html(self) -> str:
        return self.html


class PlotlyComponent(BaseComponent):
    """Plotly chart component."""

    class_name: ClassVar[str] = "PlotlyComponent"
    min_advanced_plotly_version: ClassVar[tuple] = (5, 8)

    plotly_obj: go.Figure

    def __init__(
        self,
        plotly_obj: go.Figure,
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        self.plotly_obj = plotly_obj
        super().__init__(page, name, **kwargs)

    def get_html(self) -> str:
        return f"{self.place_single_plot()}<br>\n"

    def place_single_plot(self) -> str:
        """Places a single plotly plot."""
        if package_version_tuple(plotly) < self.min_advanced_plotly_version:
            raise RuntimeError(
                f"Need to update plotly version to provide an id. "
                f"Current: {plotly.__version__}, "
                f"Required: "
                f"{'.'.join(str(i) for i in self.min_advanced_plotly_version)}"
            )
        return (
            pio.to_html(
                self.plotly_obj,
                include_plotlyjs=False,
                full_html=False,
                div_id=self.name,
            )
            + "\n"
        )


class ImageComponent(BaseComponent):
    """Image component that displays encoded images.

    Either encoded_image or image_filename must be set.
    """

    class_name: ClassVar[str] = "ImageComponent"
    encoded_image: str | None = None
    image_filename: str | None = None
    image_type: str = "png"

    def __init__(
        self,
        encoded_image: str | None = None,
        image_filename: str | None = None,
        image_type: str = "png",
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        self.encoded_image = encoded_image
        self.image_filename = image_filename
        self.image_type = image_type

        if not self.encoded_image and not self.image_filename:
            raise RuntimeError(
                "Must include either encoded_image or image_filename"
            )
        if self.encoded_image and self.image_filename:
            raise RuntimeError(
                "Must include either encoded_image or image_filename, "
                "but not both"
            )
        if self.image_filename:
            self.image_type = Path(self.image_filename).suffix.lstrip(".")
            with open(self.image_filename, "rb") as source:
                self.encoded_image = base64.b64encode(source.read()).decode(
                    "utf-8"
                )

        super().__init__(page, name, **kwargs)

    def get_html(self) -> str:
        return (
            f'<img src="data:image/{self.image_type};base64,'
            f'{self.encoded_image}">'
        )


class DashComponent(BaseComponent):
    """Dash app embed component."""

    class_name: ClassVar[str] = "DashComponent"
    height: str = "800px"
    width: str = "100%"
    address: str

    def __init__(
        self,
        address: str,
        page: FlapiPage | None = None,
        name: str | int = "",
        height: str = "800px",
        width: str = "100%",
        **kwargs: Any,
    ):
        self.address = address.strip("/") + "/"
        self.height = height
        self.width = width
        # Add any additional kwargs as URL parameters
        if kwargs:
            params = "&".join(f"{k}={v}" for k, v in kwargs.items())
            self.address += "?" + params
            # Don't pass these to parent
            kwargs = {}
        super().__init__(page, name)

    def get_html(self) -> str:
        return (
            f'<iframe width="{self.width}" height="{self.height}" '
            f'src="{self.address}"></iframe>'
        )
