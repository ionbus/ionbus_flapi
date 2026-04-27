"""Tests for flapi/app.py."""

from __future__ import annotations

import pytest

from ionbus_flapi.app import (
    FlapiApp,
    _not_found_handler,
    get_flapi,
    initialize,
)
from ionbus_flapi.config import get_config, set_config
from ionbus_flapi.errors import NotInitializedError


class TestNotFoundHandler:
    """Tests for _not_found_handler."""

    def setup_method(self):
        """Set up test config."""
        set_config({"proxy_prefix": "Example_Flapi"})

    def test_returns_html(self):
        """Test that handler returns HTML."""
        result = _not_found_handler()
        assert "<html>" in result
        assert "404" in result
        assert "Not Found" in result

    def test_includes_home_link(self):
        """Test that handler includes home link."""
        result = _not_found_handler()
        assert "Go home" in result
        assert 'href="/Example_Flapi"' in result


class TestInitialize:
    """Tests for initialize function."""

    def test_initialize_with_dict(self):
        """Test initialization with dictionary config."""
        config = {
            "app_type": "fastapi",
            "host": "localhost",
            "port": 8080,
        }
        initialize(config)

        assert get_config("app_type") == "fastapi"
        assert get_config("host") == "localhost"
        assert get_config("port") == 8080

    def test_initialize_sets_defaults(self):
        """Test that defaults are set."""
        # Use fastapi since Flask requires module context from inspect
        initialize({"app_type": "fastapi"})

        # app_type was explicitly set, but other defaults should apply
        assert get_config("host") == "127.0.0.1"
        assert get_config("port") == 8000
        assert get_config("max_threads") == 10
        assert get_config("use_proxy") is False

    def test_get_flapi_after_initialize(self):
        """Test getting FlapiApp after initialization."""
        initialize({"app_type": "fastapi"})
        app = get_flapi()
        assert isinstance(app, FlapiApp)


class TestGetFlapi:
    """Tests for get_flapi function."""

    def test_raises_before_initialize(self):
        """Test that NotInitializedError is raised before init."""
        # Reset state
        import ionbus_flapi.app as app_module

        app_module._flapi_app = None
        app_module._server_initialized = False

        with pytest.raises(NotInitializedError):
            get_flapi()


class TestFlapiApp:
    """Tests for FlapiApp class."""

    def test_server_type(self):
        """Test server_type returns NONE for base class."""
        assert FlapiApp.server_type() == "NONE"
