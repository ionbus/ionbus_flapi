"""flapi/components/text.py

Text-based components for displaying markdown and other text content.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import markdown as md

from ionbus_flapi.components.base import BaseComponent
from ionbus_flapi.config import get_config

if TYPE_CHECKING:
    from ionbus_flapi.page import FlapiPage

# Regex patterns for markdown processing
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
HTTP_LIKE_RE = re.compile(r"^\w+://")
SLASH_UNDER_RE = re.compile(r"[/_-]")
DOT_MD_RE = re.compile(r"\.md$", re.IGNORECASE)
DOT_MD_PLUS_RE = re.compile(r"\.md(\#.+)?$", re.IGNORECASE)

# Cache for markdown objects
MD_OBJ_DICT: dict[str, MarkdownComponent] = {}


class MarkdownComponent(BaseComponent):
    """Markdown text component.

    Renders markdown content to HTML with support for:
    - Fenced code blocks
    - Tables
    - Code highlighting
    - Table of contents
    """

    class_name: ClassVar[str] = "MarkdownComponent"
    markdown_path: ClassVar[str] = "static"
    _text: str | None = None
    file_path: Path | None = None
    prefix: str
    parts: list[str]

    def __init__(
        self,
        filename: str | None = None,
        text: str | None = None,
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ) -> None:
        """Initialize Markdown component.

        Args:
            filename: Path to markdown file (relative to markdown_path)
            text: Raw markdown text (alternative to filename)
            page: Parent FlapiPage
            name: Component name
        """
        super().__init__(page, name, **kwargs)
        self.prefix = get_config("proxy_prefix", "")
        if not filename and not text:
            raise ValueError("Either filename or text must be provided.")
        if filename:
            self.file_path = Path(f"{self.markdown_path}") / Path(filename)
            self.parts = ([self.prefix] if self.prefix else []) + list(
                self.file_path.parent.parts
            )
        else:
            self.file_path = None
            self.parts = []
        self._text = text

    @property
    def text(self) -> str:
        """Return the text content."""
        if self._text:
            return self._text
        if not self.file_path:
            raise RuntimeError(
                "text or filename must be specified for MarkdownComponent"
            )
        with open(self.file_path, "r", encoding="utf-8") as file:
            text = file.read()
        text = MD_LINK_RE.sub(self.cleanup_markdown, text)
        self._text = text
        return self._text

    def set_requirements(self) -> None:
        """Set page requirements for markdown rendering."""
        if self.page is None:
            return
        # Enable codehilite CSS if page supports it
        if hasattr(self.page, "codehilite_css"):
            self.page.codehilite_css = True

    def get_html(self) -> str:
        """Return HTML for the Markdown component."""
        if not self.text:
            raise RuntimeError(
                "text must be set for MarkdownComponent"
            )
        return md.markdown(
            self.text,
            extensions=["fenced_code", "tables", "codehilite", "toc"],
        )

    def cleanup_markdown(self, match: re.Match) -> str:
        """Process markdown links for proper URL handling."""
        text, url = match.groups()
        # Is this a link for full path or just an anchor?
        if (
            url.startswith("/")
            or url.startswith("#")
            or HTTP_LIKE_RE.search(url)
        ):
            return f"[{text}]({url})"

        url_parts = list(Path(url.strip()).parts)
        parts = self.parts[:]

        # Is this a markdown file
        if DOT_MD_PLUS_RE.search(url):
            # we want to call with the `markdown?filename` endpoint
            if self.prefix:
                parts.pop(0)  # remove the prefix
            if parts:
                parts.pop(0)  # remove static
            while url_parts and parts and url_parts[0] == "..":
                parts.pop()
                url_parts.pop(0)
            new_readme = "/".join(parts + url_parts)
            new_url = f"markdown?filename={new_readme}"
            return f"[{text}]({new_url})"

        while url_parts and parts and url_parts[0] == "..":
            parts.pop()
            url_parts.pop(0)
        parts = parts + url_parts
        new_url = "/" + "/".join(parts)
        return f"[{text}]({new_url})"


def markdown_endpoint() -> "FlapiPage":
    """Endpoint to serve markdown content.

    Query parameters:
    - filename: Path to the markdown file
    - with_title: If present, show the title
    """
    from ionbus_flapi.page import FlapiPage
    from ionbus_flapi.request import get_request_context

    params = get_request_context().args
    filename = params.get("filename")
    if not filename:
        raise RuntimeError("Markdown endpoint requires a 'filename' param.")

    with_title = params.get("with_title")
    title = SLASH_UNDER_RE.sub(" ", DOT_MD_RE.sub("", filename)).title()
    component = MD_OBJ_DICT.get(
        filename,
        MarkdownComponent(filename=filename),
    )
    return FlapiPage(
        f"{title} Markdown" if with_title else "",
        [component],
    )


def register_markdown_endpoint() -> None:
    """Registers the markdown endpoint at `/markdown`."""
    from ionbus_flapi.routing import register_endpoint

    register_endpoint(
        None,
        "markdown",
        markdown_endpoint,
        show_in_dir=False,
    )
