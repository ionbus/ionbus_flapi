"""Tests for flapi/response.py."""

from __future__ import annotations

import pytest

from ionbus_flapi.response import (
    AuthenticationError,
    BadAccessError,
    BaseEndpointResponse,
    Endpoint,
    EventStreamResponse,
    RedirectResponse,
    _get_any_from_dict,
    error_page,
)


class TestGetAnyFromDict:
    """Tests for _get_any_from_dict helper."""

    def test_finds_first_key(self):
        """Test that first matching key is returned."""
        d = {"a": 1, "b": 2}
        assert _get_any_from_dict(d, ["x", "a"]) == 1

    def test_returns_none_if_no_match(self):
        """Test returns None when no keys match."""
        d = {"a": 1}
        assert _get_any_from_dict(d, ["x", "y"]) is None


class TestErrorPage:
    """Tests for error_page function."""

    def test_basic_error_page(self):
        """Test basic error page generation."""
        html = error_page("Test Error")
        assert "Test Error" in html
        assert "<title>Test Error</title>" in html
        assert "Error" in html

    def test_error_page_with_error_details(self):
        """Test error page with error string."""
        html = error_page("Test Error", error="Details here")
        assert "Details here" in html
        assert "Show More" in html

    def test_error_page_with_back_url(self):
        """Test error page with custom back URL."""
        html = error_page("Test Error", back_url="/custom/back")
        assert "/custom/back" in html


class TestBaseEndpointResponse:
    """Tests for BaseEndpointResponse."""

    def test_get_flask_not_implemented(self):
        """Test base class raises NotImplementedError."""
        resp = BaseEndpointResponse()
        with pytest.raises(NotImplementedError):
            resp.get_flask()

    def test_get_fastapi_not_implemented(self):
        """Test base class raises NotImplementedError."""
        resp = BaseEndpointResponse()
        with pytest.raises(NotImplementedError):
            resp.get_fastapi()


class TestEventStreamResponse:
    """Tests for EventStreamResponse."""

    def test_init(self):
        """Test initialization with stream function."""

        def gen():
            yield "data"

        resp = EventStreamResponse(gen())
        assert resp.stream_func is not None


class TestRedirectResponse:
    """Tests for RedirectResponse."""

    def test_init(self):
        """Test initialization with location."""
        resp = RedirectResponse("/new/location")
        assert resp.location == "/new/location"


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_init(self):
        """Test initialization."""
        err = AuthenticationError("user@example.com", "host.example.com")
        assert err.user_email == "user@example.com"
        assert err.host_from == "host.example.com"

    def test_error_page(self):
        """Test error page generation."""
        err = AuthenticationError("user@example.com", "host.example.com")
        html = err.error_page()
        assert "Authentication Failed" in html
        assert "user@example.com" in html


class TestBadAccessError:
    """Tests for BadAccessError."""

    def test_error_page(self):
        """Test error page generation."""
        html = BadAccessError.error_page()
        assert "Proxy Not Found" in html
        assert "reverse proxy" in html


class TestEndpoint:
    """Tests for Endpoint base class."""

    def test_init(self):
        """Test initialization."""

        def my_func():
            return "result"

        ep = Endpoint("test_endpoint", my_func, json_return=True)
        assert ep.name == "test_endpoint"
        assert ep.endpoint_func == my_func
        assert ep.json_return is True

    def test_call_returns_result(self):
        """Test __call__ returns function result."""

        def my_func():
            return "result"

        ep = Endpoint("test", my_func)
        result = ep()
        assert result == "result"

    def test_call_handles_none_return(self):
        """Test __call__ handles None return."""

        def my_func():
            return None

        ep = Endpoint("test", my_func)
        result = ep()
        assert "Null return" in result

    def test_call_handles_exception(self):
        """Test __call__ handles exceptions."""

        def my_func():
            raise ValueError("test error")

        ep = Endpoint("test", my_func)
        result = ep()
        assert "Exception" in result

    def test_json_error_response(self):
        """Test JSON error response format."""

        def my_func():
            raise ValueError("test error")

        ep = Endpoint("test", my_func, json_return=True)
        result = ep()
        assert isinstance(result, dict)
        assert "endpoint_name" in result
        assert "exception" in result
