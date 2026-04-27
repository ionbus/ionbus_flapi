"""flapi/errors.py

Error types used for clarity by different parts of Flapi.
"""

from __future__ import annotations


class FlapiError(RuntimeError):
    """Base class for errors thrown by the Flapi package."""


class NotInitializedError(FlapiError):
    """Error raised when the FlapiApp is accessed before initialization."""


class InitializationError(FlapiError):
    """Error raised when data initialization fails."""


class NoContextError(FlapiError):
    """Error raised when Request Context is accessed outside an active
    request."""
