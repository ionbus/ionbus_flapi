"""flapi/shutdown.py

Server shutdown functionality with callback registration.
"""

from __future__ import annotations

import os
import threading
from typing import Callable

from ionbus_utils.logging_utils import logger

from ionbus_flapi.config import get_config


def _get_client_addr() -> str:
    """Get client address, handling both Flask and FastAPI."""
    from ionbus_flapi.request import get_request_context

    ctx = get_request_context()
    try:
        return ctx.remote_addr
    except AttributeError:
        # FastAPI doesn't have remote_addr in our implementation
        return "unknown"

# Module-level state
_shutdown_callbacks: list[Callable[[], None]] = []
_shutdown_flag = threading.Event()


def is_shutting_down() -> bool:
    """Check if the server is shutting down.

    Returns:
        True if shutdown has been initiated, False otherwise.

    Example:
        while not is_shutting_down():
            # Do work
            time.sleep(0.5)
    """
    return _shutdown_flag.is_set()


def get_shutdown_event() -> threading.Event:
    """Get the shutdown event for use in wait() calls.

    Returns:
        The threading.Event that gets set when shutdown is initiated.

    Example:
        # Wait up to 1 second, or until shutdown
        shutdown_event = get_shutdown_event()
        shutdown_event.wait(timeout=1.0)
    """
    return _shutdown_flag


def register_shutdown_callback(callback: Callable[[], None]) -> None:
    """Register a function to be called when the server shuts down.

    Args:
        callback: A callable that takes no arguments. Will be called
            during shutdown before the server exits.

    Example:
        def cleanup():
            print("Cleaning up resources...")

        register_shutdown_callback(cleanup)
    """
    _shutdown_callbacks.append(callback)
    logger.info(f"Registered shutdown callback: {callback.__name__}")


def _run_shutdown_callbacks() -> None:
    """Execute all registered shutdown callbacks."""
    for callback in _shutdown_callbacks:
        try:
            logger.info(f"Running shutdown callback: {callback.__name__}")
            callback()
        except Exception as e:
            logger.error(f"Error in shutdown callback {callback.__name__}: {e}")


def shutdown_endpoint() -> str:
    """Handle shutdown requests.

    Checks the shutdown code from query params against config.
    If valid, runs callbacks and initiates server shutdown.

    Returns:
        HTML response indicating success or failure.
    """
    from ionbus_flapi.request import get_request_context

    ctx = get_request_context()
    provided_code = ctx.args.get("code", "")
    expected_code = get_config("shutdown_code")

    if not expected_code:
        return _shutdown_response(
            "Shutdown Disabled",
            "Shutdown endpoint is not configured. "
            "Set 'shutdown_code' in your config file.",
            success=False,
        )

    if provided_code != expected_code:
        logger.warning(
            f"Invalid shutdown code attempt: {provided_code!r} "
            f"from {_get_client_addr()}"
        )
        return _shutdown_response(
            "Invalid Code",
            "The provided shutdown code is incorrect.",
            success=False,
        )

    logger.info(f"Shutdown initiated from {_get_client_addr()}")

    # Set global shutdown flag so threads can check it
    _shutdown_flag.set()

    # Run callbacks
    _run_shutdown_callbacks()

    # Schedule shutdown in a separate thread to allow response to be sent
    def delayed_shutdown():
        import time

        time.sleep(0.5)  # Allow response to be sent
        logger.info("Server shutting down...")
        os._exit(0)  # Force exit - works for both Flask and FastAPI

    threading.Thread(target=delayed_shutdown, daemon=True).start()

    return _shutdown_response(
        "Shutting Down",
        "Server is shutting down. Goodbye!",
        success=True,
    )


def _shutdown_response(title: str, message: str, success: bool) -> str:
    """Generate HTML response for shutdown endpoint."""
    from ionbus_flapi.routing import prepare_url

    color = "green" if success else "red"
    home_url = prepare_url("/")

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <link rel="stylesheet" type="text/css"
        href="{prepare_url('/static/base.css')}">
</head>
<body>
    <h1 style="color: {color};">{title}</h1>
    <p>{message}</p>
    <p><a href="{home_url}">Go home</a></p>
</body>
</html>
"""
