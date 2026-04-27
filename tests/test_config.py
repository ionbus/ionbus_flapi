"""Tests for flapi/config.py."""

from __future__ import annotations

import pytest

from ionbus_flapi.config import (
    FlapiEnum,
    get_app_name,
    get_config,
    get_group_config,
    set_app_name,
    set_config,
)


class TestFlapiEnum:
    """Tests for FlapiEnum."""

    def test_enum_values(self):
        """Test that enum values are correct strings."""
        assert FlapiEnum.STATUS == "status"
        assert FlapiEnum.MESSAGE == "message"
        assert FlapiEnum.SUCCESS == "success"
        assert FlapiEnum.ERROR == "error"

    def test_enum_is_string(self):
        """Test that enum values behave as strings."""
        assert isinstance(FlapiEnum.STATUS, str)
        assert FlapiEnum.STATUS.upper() == "STATUS"


class TestConfig:
    """Tests for config functions."""

    def test_set_and_get_config(self):
        """Test setting and getting config values."""
        test_config = {"port": 5080, "host": "localhost"}
        set_config(test_config)

        assert get_config("port") == 5080
        assert get_config("host") == "localhost"

    def test_get_config_default(self):
        """Test get_config returns default for missing keys."""
        set_config({})
        assert get_config("missing_key") is None
        assert get_config("missing_key", "default") == "default"

    def test_get_group_config(self):
        """Test getting group-specific config."""
        test_config = {
            "port": 5080,
            "Grids": {"grid_style": "default", "page_size": 50},
        }
        set_config(test_config)

        assert get_group_config("Grids", "grid_style") == "default"
        assert get_group_config("Grids", "page_size") == 50

    def test_get_group_config_default(self):
        """Test get_group_config returns default for missing values."""
        set_config({})
        assert get_group_config("Missing", "field") is None
        assert get_group_config("Missing", "field", "default") == "default"


class TestAppName:
    """Tests for app name functions."""

    def test_set_and_get_app_name(self):
        """Test setting and getting app name."""
        set_app_name("FastAPI")
        assert get_app_name() == "FastAPI"

        set_app_name("Flask")
        assert get_app_name() == "Flask"
