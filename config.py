"""flapi/config.py

Functions for storing and managing server config. Also contains
FlapiEnum with string constants used throughout the framework.
"""

from __future__ import annotations

from typing import Any

from ionbus_utils.enumerate import StrEnum

# Global config storage
_config: dict = {}
_app_name: str = "None"


class FlapiEnum(StrEnum):
    """String values used in various places in Flapi."""

    STATUS = "status"
    MESSAGE = "message"
    DATA = "data"
    REDIRECT_URL = "redirect_url"
    SUCCESS = "success"
    ERROR = "error"
    ERROR_CODE = "error_code"
    FORMATTED_HISTORY = "formatted_history"
    FORMATTED_RESPONSE = "formatted_response"
    QUESTION = "question"
    CHAT_ID = "chat_id"


def set_config(config: dict) -> None:
    """Set the config dict to be used globally.

    Do not call this function from outside of flapi.app.
    """
    global _config  # noqa: PLW0603
    _config = config


def get_config(field: str, default: Any = None) -> Any:
    """Get the value of a server configuration option.

    Args:
        field: The configuration field name.
        default: Default value if field is not found.

    Returns:
        The configuration value or default.

    Example:
        >>> get_config("port", 5000)
        5080
    """
    return _config.get(field, default)


def get_group_config(group: str, field: str, default: Any = None) -> Any:
    """Get configuration value for a specific endpoint group.

    Args:
        group: The endpoint group name (e.g., "Grids").
        field: The field name within that group.
        default: Default value if not found.

    Returns:
        The configuration value or default.

    Example:
        >>> get_group_config("Grids", "grid_style")

    In the YAML file, this would look like:
        Grids:
            grid_style: default
    """
    return _config.get(group, {}).get(field, default)


def set_app_name(name: str) -> None:
    """Set the app name, usually "Flask" or "FastAPI".

    Do not call this function from outside of flapi.app.
    """
    global _app_name  # noqa: PLW0603
    _app_name = name


def get_app_name() -> str:
    """Get the app name ("Flask" or "FastAPI").

    Useful for displaying which underlying server is in use.
    """
    return _app_name
