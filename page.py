"""flapi/page.py

FlapiPage class for building HTML pages with components.
"""

from __future__ import annotations

from typing import Any

from ionbus_utils.logging_utils import logger

from ionbus_flapi.components.layout import component_factory
from ionbus_flapi.config import get_config
from ionbus_flapi.request import get_request_context
from ionbus_flapi.routing import get_url_dict, prepare_url

# Default CSS classes for pages
DEFAULT_CSS = {
    ".redcell": {"color": "red !important"},
    ".greencell": {"color": "green !important"},
    ".totalcell": {"font-weight": "bold"},
    ".grid-container": {
        "display": "grid",
        "gap": "10px",
    },
    ".flex-container-row": {
        "display": "flex",
        "flex-direction": "row",
        "gap": "10px",
    },
    ".flex-container-column": {
        "display": "flex",
        "flex-direction": "column",
        "gap": "10px",
    },
}


def _css_style(class_rules: dict[str, dict[str, Any]]) -> str:
    """Render a dictionary of CSS class rules as CSS code."""
    ret_string = '\n<style type="text/css">\n'
    for name, rules in class_rules.items():
        ret_string += f"    {name} {{\n"
        for key, value in rules.items():
            ret_string += f"        {key}: {value};\n"
        ret_string += "    }\n"
    ret_string += "</style>\n"
    return ret_string


def _jump_to_dropdown() -> str:
    """Return HTML for a dropdown listing all registered routes."""
    html = """<script language="JavaScript">
        function goto(form) {
            var index = form.select.selectedIndex;
            if (form.select.options[index].value != "0") {
                window.top.location.href = form.select.options[index].value;
            }
        }
    </script>\n"""

    options = f'<option value="{prepare_url("/")}">Table of Contents</option>\n'
    for name, url in get_url_dict().items():
        if url:
            display_name = "&nbsp;" * 4 + name
        else:
            display_name = name
        options += f'<option value="{url}">{display_name}</option>\n'

    html += f"""<form name="jumpForm">
        <select name="select" onchange="goto(this.form)">
            <option value="">Jump to related page</option>
            {options}
        </select>
    </form>\n"""
    return html


def _theme_toggle_button(theme: str) -> str:
    """Return HTML for a theme toggle button that cycles themes."""
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
    return f"""
    {theme_js}
    <div style="position: absolute; right: 10px; top: 10px;">
        <div id="themeDiv">
            <span>Theme: </span>
            <img src="{prepare_url(f'/static/assets/{theme}-mode.svg')}"
                class="icon" id="themeButton" onclick="cycleTheme()"
                title="Click to cycle: system -> light -> dark" />
        </div>
    </div>
    """


class FlapiPage:
    """Container for building HTML pages with components.

    Args:
        title: The page title (shown in browser tab and as h1).
        objects: List of content items (strings, components, etc.).
        css: Additional CSS class definitions.
        theme_toggle: Whether to show the theme toggle button.
        refresh_in_seconds: Auto-refresh interval (0 to disable).
        include_jquery: Whether to include jQuery headers.
        include_plotly: Whether to include Plotly headers.
        stream: Tuple of (EventStreamManager, ticker) for SSE streaming.
            When provided, automatically adds pause button and streaming JS.
    """

    def __init__(
        self,
        title: str = "",
        objects: list | None = None,
        css: dict | None = None,
        theme_toggle: bool = False,
        refresh_in_seconds: int = 0,
        include_jquery: bool = True,
        include_plotly: bool = True,
        stream: tuple | None = None,
    ):
        self.title = title
        self.objects = objects or []
        self.css = css or {}
        self.theme_toggle = theme_toggle
        self.refresh_in_seconds = refresh_in_seconds
        self.include_jquery = include_jquery
        self.include_plotly = include_plotly
        self.stream = stream  # (EventStreamManager, ticker) tuple
        self._theme = "system"
        self.jqx_headers = False  # Set by components that need JQX

    def add(self, obj: Any) -> None:
        """Add a content object to the page."""
        if obj is not None and obj != "":
            self.objects.append(obj)

    def add_many(self, objects: list | None) -> None:
        """Add multiple content objects to the page."""
        if objects:
            for obj in objects:
                self.add(obj)

    def _get_headers(self) -> str:
        """Generate HTML headers (CSS, JS includes)."""
        headers = ""

        # jQuery
        if self.include_jquery:
            headers += """
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
            """

        # Plotly - use local by default, CDN if plotly_local is False
        if self.include_plotly:
            plotly_local = get_config("plotly_local", True)
            plotly_version = get_config("plotly_version", "3.3.1")
            if plotly_local:
                plotly_js = prepare_url(
                    f"/static/plotly/plotly-{plotly_version}.min.js"
                )
                headers += f"""
            <script src="{plotly_js}" charset="utf-8"></script>
            """
            else:
                headers += f"""
            <script src="https://cdn.plot.ly/plotly-{plotly_version}.min.js" charset="utf-8"></script>
            """

        # JQX widgets (for grids)
        if self.jqx_headers:
            # Use local static files by default, CDN if jqx_local is False
            jqx_local = get_config("jqx_local", True)
            if jqx_local:
                jqx_base_css = prepare_url("/static/jqwidgets/styles/jqx.base.css")
                jqx_all_js = prepare_url("/static/jqwidgets/jqx-all.js")
                jqx_theme_css = prepare_url(
                    "/static/jqwidgets/styles/jqx.metrodark.css"
                )
                headers += f"""
            <link rel="stylesheet" href="{jqx_base_css}" type="text/css" />
            <script type="text/javascript" src="{jqx_all_js}"></script>
            <link rel="stylesheet" href="{jqx_theme_css}" type="text/css" />
            """
            else:
                headers += """
            <link rel="stylesheet" href="https://jqwidgets.com/public/jqwidgets/styles/jqx.base.css" type="text/css" />
            <script type="text/javascript" src="https://jqwidgets.com/public/jqwidgets/jqx-all.js"></script>
            """
            # Add renderAggregates function for grid aggregates
            headers += """
            <script type="text/javascript">
            function renderAggregates(aggregates) {
                let value = aggregates.sum;
                if (value === undefined) {
                    value = '0';
                }
                if (Number(value.replace(/,/g, '')) < 0){
                    return `<div class="redcell totalcell"
                        style="position: relative; margin: 4px;
                        overflow: hidden;">` + value + `</div>`;
                }
                else{
                    return `<div class="totalcell"
                        style="position: relative; margin: 4px;
                        overflow: hidden;">` + value + `</div>`;
                }
            }
            </script>
            """

        return headers

    def _get_css(self) -> str:
        """Generate CSS styles."""
        all_css = DEFAULT_CSS.copy()
        all_css.update(self.css)
        return _css_style(all_css)

    def _get_refresh_script(self) -> str:
        """Generate auto-refresh JavaScript if enabled."""
        if not self.refresh_in_seconds:
            return ""

        return f"""
        <script type="text/javascript">
            var pause = false;
            var count = {self.refresh_in_seconds};

            setInterval(function() {{
                if (!pause) {{
                    count--;
                    if (count < 0) {{
                        location.reload();
                        return;
                    }}
                    document.getElementById('timer').innerHTML = count;
                }}
            }}, 1000);

            document.getElementById('pause').addEventListener('click', function() {{
                pause = !pause;
            }});
        </script>
        <button id="pause">Pause/Resume</button>
        Seconds to reload: <span id="timer">{self.refresh_in_seconds}</span>
        <p>
        """

    def _render_object(self, obj: Any) -> str:
        """Render a single object to HTML."""
        # If it's a string, return as-is
        if isinstance(obj, str):
            return obj

        # If it has __str__, use that
        if hasattr(obj, "__str__"):
            return str(obj)

        # Otherwise convert to string
        return str(obj)

    def _prepare_components(self) -> None:
        """Prepare components by converting objects and setting requirements."""
        # Convert all objects to components using component_factory
        converted = []
        for i, obj in enumerate(self.objects):
            if obj is None:
                continue
            try:
                component = component_factory(self, obj, i)
                converted.append(component)
            except RuntimeError:
                # If component_factory can't handle it, keep as-is
                converted.append(obj)
        self.objects = converted

        # Now set page references and requirements
        for obj in self.objects:
            if obj is None:
                continue
            # Set page reference on component
            if hasattr(obj, "page"):
                obj.page = self
            # Call set_requirements to let component set page-level needs
            if hasattr(obj, "set_requirements"):
                obj.set_requirements()

        # If streaming is enabled, add pause button HTML to objects
        if self.stream:
            esm, _ = self.stream
            from ionbus_flapi.components.base import HtmlComponent

            self.objects.append(HtmlComponent(html=esm.html()))

    def _get_document_ready_js(self) -> str:
        """Collect document ready JavaScript from all components."""
        js_parts = []
        for obj in self.objects:
            if obj is None:
                continue
            if hasattr(obj, "get_document_ready_js"):
                js = obj.get_document_ready_js()
                if js:
                    js_parts.append(js)

        # Add streaming JavaScript if stream is configured
        if self.stream:
            esm, ticker = self.stream
            stream_address = esm.get_stream_address(ticker)
            stream_js = esm.javascript(stream_address)
            js_parts.append(stream_js)

        if not js_parts:
            return ""
        all_js = "\n".join(js_parts)
        return f"""
        <script type="text/javascript">
            $(document).ready(function() {{
                {all_js}
            }});
        </script>
        """

    def _get_body(self) -> str:
        """Generate HTML body content."""
        body = ""
        for obj in self.objects:
            body += self._render_object(obj)
        return body

    def __str__(self) -> str:
        """Generate the full HTML page."""
        # Get theme from request context if available
        try:
            self._theme = get_request_context().theme
        except Exception:
            self._theme = "system"

        # Prepare components (set page refs, collect requirements)
        self._prepare_components()

        base_css = f"""
            <link rel="stylesheet" type="text/css"
                href="{prepare_url('/static/base.css')}">
        """

        theme_css = f"""
            <link id="flapiTheme" rel="stylesheet"
                href="{prepare_url(f'/static/themes/{self._theme}.css')}"
                type="text/css" />
        """

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="no-cache">
    <meta http-equiv="Cache-Control" content="no-cache">
    <title>{self.title}</title>
    {base_css}
    {theme_css}
    {self._get_headers()}
    {self._get_css()}
</head>
<body>
    {_jump_to_dropdown()}
    <h1>{self.title}</h1>
    {self._get_refresh_script()}
    {self._get_body()}
    {self._get_document_ready_js()}
    {_theme_toggle_button(self._theme) if self.theme_toggle else ""}
</body>
</html>
"""
        return html

    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """Encode the page to bytes."""
        return self.__str__().encode(encoding, errors)


class FlapiForwardPage(FlapiPage):
    """A page that redirects to another URL."""

    def __init__(self, forward_address: str):
        super().__init__("")
        self.forward_address = forward_address

    def __str__(self) -> str:
        logger.info(f"Redirecting to {self.forward_address}")
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url={self.forward_address}" />
</head>
<body>
    <p>Redirecting to <a href="{self.forward_address}">{self.forward_address}</a></p>
</body>
</html>
"""
