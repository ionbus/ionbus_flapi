"""Tests for flapi/routing.py."""

from __future__ import annotations

import pytest

from ionbus_flapi.config import set_config
from ionbus_flapi.routing import (
    URLreg,
    prepare_route,
    prepare_url,
)


class TestPrepareUrl:
    """Tests for prepare_url function."""

    def setup_method(self):
        """Set up test config."""
        set_config({"proxy_prefix": "Example_Flapi"})

    def test_absolute_url_with_prefix(self):
        """Test absolute URL gets proxy prefix."""
        result = prepare_url("/static/file.css")
        assert result == "/Example_Flapi/static/file.css"

    def test_absolute_url_with_trailing_slash(self):
        """Test absolute URL with trailing slash."""
        result = prepare_url("/page", use_trailing_slash=True)
        assert result == "/Example_Flapi/page/"

    def test_relative_url_unchanged(self):
        """Test relative URL stays unchanged."""
        result = prepare_url("relative/path")
        assert result == "relative/path"

    def test_no_prefix(self):
        """Test URL without prefix."""
        result = prepare_url("/static/file.css", prefix=False)
        assert result == "/static/file.css"

    def test_no_proxy_prefix_configured(self):
        """Test with no proxy prefix in config."""
        set_config({})
        result = prepare_url("/static/file.css")
        assert result == "/static/file.css"


class TestPrepareRoute:
    """Tests for prepare_route function."""

    def setup_method(self):
        """Set up test config."""
        set_config({"proxy_prefix": "Example_Flapi"})

    def test_route_with_group(self):
        """Test route generation with group."""
        result = prepare_route("Forms", "submit")
        # Default: no trailing slash
        assert result == "/Example_Flapi/Forms/submit"

    def test_route_without_group(self):
        """Test route generation without group."""
        result = prepare_route(None, "index")
        assert result == "/Example_Flapi/index"

    def test_route_strips_slashes(self):
        """Test that slashes are stripped from name."""
        result = prepare_route("Forms", "/submit/")
        assert result == "/Example_Flapi/Forms/submit"

    def test_route_with_trailing_slash(self):
        """Test route generation with trailing slash."""
        result = prepare_route("Forms", "submit", use_trailing_slash=True)
        assert result == "/Example_Flapi/Forms/submit/"


class TestURLreg:
    """Tests for URLreg class."""

    def setup_method(self):
        """Clear URLreg state before each test."""
        URLreg.address_set.clear()
        URLreg.endpoints.clear()
        URLreg.api_docs.clear()

    def test_creates_url_registration(self):
        """Test basic URL registration."""
        reg = URLreg("/test/path", "path", "test", "Test Path")
        assert reg.address == "/test/path"
        assert reg.name == "path"
        assert reg.description == "Test Path"

    def test_prevents_duplicate_address(self):
        """Test that duplicate addresses raise error."""
        URLreg("/test/path", "path", "test", "Test Path")
        with pytest.raises(RuntimeError, match="already used"):
            URLreg("/test/path", "path2", "test", "Test Path 2")

    def test_adds_to_endpoints_dict(self):
        """Test registration adds to endpoints dict."""
        URLreg("/test/path", "path", "TestGroup", "Test Path")
        assert "TestGroup" in URLreg.endpoints
        assert "path" in URLreg.endpoints["TestGroup"]

    def test_no_group_adds_to_root(self):
        """Test registration without group adds to root."""
        URLreg("/root/path", "root_path", None, "Root Path")
        assert "root_path" in URLreg.endpoints
