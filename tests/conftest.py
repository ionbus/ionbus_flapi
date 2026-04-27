"""Pytest fixtures for flapi tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_config() -> dict:
    """Return a sample configuration dictionary."""
    return {
        "app_type": "fastapi",
        "port": 5080,
        "host": "0.0.0.0",
        "max_threads": 10,
        "use_proxy": False,
        "proxy_prefix": "Example_Flapi",
    }
