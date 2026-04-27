"""Tests for flapi/page.py."""

from __future__ import annotations

import pytest

from ionbus_flapi.config import set_config
from ionbus_flapi.page import (
    DEFAULT_CSS,
    FlapiForwardPage,
    FlapiPage,
    _css_style,
    _jump_to_dropdown,
    _theme_toggle_button,
)


class TestCssStyle:
    """Tests for _css_style function."""

    def test_generates_css(self):
        """Test CSS generation from dict."""
        rules = {".test": {"color": "red", "font-size": "12px"}}
        result = _css_style(rules)
        assert "<style" in result
        assert ".test" in result
        assert "color: red" in result

    def test_empty_rules(self):
        """Test with empty rules."""
        result = _css_style({})
        assert "<style" in result
        assert "</style>" in result


class TestJumpToDropdown:
    """Tests for _jump_to_dropdown function."""

    def setup_method(self):
        """Set up test config."""
        set_config({"proxy_prefix": "Example_Flapi"})

    def test_generates_dropdown(self):
        """Test dropdown HTML generation."""
        result = _jump_to_dropdown()
        assert "<select" in result
        assert "Jump to related page" in result
        assert "Table of Contents" in result


class TestThemeToggleButton:
    """Tests for _theme_toggle_button function."""

    def setup_method(self):
        """Set up test config."""
        set_config({"proxy_prefix": "Example_Flapi"})

    def test_generates_button(self):
        """Test theme toggle button HTML."""
        result = _theme_toggle_button("system")
        assert "themeButton" in result
        assert "system-mode.svg" in result


class TestFlapiPage:
    """Tests for FlapiPage class."""

    def setup_method(self):
        """Set up test config."""
        set_config({"proxy_prefix": "Example_Flapi"})

    def test_init_with_title(self):
        """Test initialization with title."""
        page = FlapiPage("Test Page")
        assert page.title == "Test Page"

    def test_init_with_objects(self):
        """Test initialization with objects."""
        page = FlapiPage("Test", objects=["<p>Hello</p>", "<p>World</p>"])
        assert len(page.objects) == 2

    def test_add_object(self):
        """Test adding a single object."""
        page = FlapiPage("Test")
        page.add("<p>Content</p>")
        assert len(page.objects) == 1

    def test_add_ignores_none(self):
        """Test that add ignores None."""
        page = FlapiPage("Test")
        page.add(None)
        page.add("")
        assert len(page.objects) == 0

    def test_add_many(self):
        """Test adding multiple objects."""
        page = FlapiPage("Test")
        page.add_many(["<p>One</p>", "<p>Two</p>"])
        assert len(page.objects) == 2

    def test_str_generates_html(self):
        """Test __str__ generates valid HTML."""
        page = FlapiPage("Test Page", objects=["<p>Content</p>"])
        html = str(page)

        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "<title>Test Page</title>" in html
        assert "<h1>Test Page</h1>" in html
        assert "<p>Content</p>" in html

    def test_str_includes_base_css(self):
        """Test that base CSS is included."""
        page = FlapiPage("Test")
        html = str(page)
        assert "base.css" in html

    def test_str_includes_theme_css(self):
        """Test that theme CSS is included."""
        page = FlapiPage("Test")
        html = str(page)
        assert "themes/" in html

    def test_encode(self):
        """Test encode to bytes."""
        page = FlapiPage("Test")
        result = page.encode()
        assert isinstance(result, bytes)

    def test_theme_toggle(self):
        """Test theme toggle button."""
        page = FlapiPage("Test", theme_toggle=True)
        html = str(page)
        assert "themeButton" in html

    def test_custom_css(self):
        """Test custom CSS."""
        page = FlapiPage("Test", css={".custom": {"color": "blue"}})
        html = str(page)
        assert ".custom" in html
        assert "color: blue" in html


class TestFlapiForwardPage:
    """Tests for FlapiForwardPage class."""

    def test_generates_redirect(self):
        """Test redirect HTML generation."""
        page = FlapiForwardPage("/new/location")
        html = str(page)

        assert "meta http-equiv=\"refresh\"" in html
        assert "/new/location" in html

    def test_includes_link(self):
        """Test that redirect includes clickable link."""
        page = FlapiForwardPage("/new/location")
        html = str(page)
        assert 'href="/new/location"' in html
