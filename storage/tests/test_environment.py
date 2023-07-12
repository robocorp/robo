"""
Unittests for testing fallback behaviour for missing Asset Storage
endpoint and token in local runs.
"""
import os
from unittest.mock import patch

import pytest

from robocorp.storage._environment import get_endpoint, get_token

ENDPOINTS = [
    ("https://api.eu1.robocloud.eu/", "https://api.eu1.robocorp.com/v1/"),
    ("https://api.ci.robocloud.dev/", "https://api.ci.robocorp.dev/v1/"),
    ("https://api.eu2.robocorp.com/", "https://api.eu2.robocorp.com/v1/"),
    ("https://api.us1.robocorp.com/", "https://api.us1.robocorp.com/v1/"),
    ("https://api.us1.robocorp.com/v1", "https://api.us1.robocorp.com/v1"),
    ("https://api.us1.robocorp.com/v1/", "https://api.us1.robocorp.com/v1/"),
    ("api.us1.robocorp.com", "api.us1.robocorp.com/v1/"),
    ("https://api.eu1.robocorp.com/v1/", "https://api.eu1.robocorp.com/v1/"),
    (
        "https://api.robocloud.dev.enterprise.com/v1/",
        "https://api.robocloud.dev.enterprise.com/v1/",
    ),
    ("https://api.eu1.robocloud.eu:8080/", "https://api.eu1.robocorp.com:8080/v1/"),
]


def test_endpoint_expected():
    with patch.dict(
        os.environ,
        {"RC_API_URL_V1": "correct", "RC_API_SECRET_HOST": "wrong"},
        clear=True,
    ):
        result = get_endpoint()
        assert result == "correct"


@pytest.mark.parametrize("value,expected", ENDPOINTS)
def test_endpoint_fallback(value, expected):
    with patch.dict(os.environ, {"RC_API_SECRET_HOST": value}, clear=True):
        result = get_endpoint()
        assert result == expected


def test_endpoint_none():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError):
            get_endpoint()


def test_token_expected():
    with patch.dict(
        os.environ,
        {"RC_API_TOKEN_V1": "correct", "RC_API_SECRET_TOKEN": "wrong"},
        clear=True,
    ):
        result = get_token()
        assert result == "correct"


def test_token_fallback():
    with patch.dict(os.environ, {"RC_API_SECRET_TOKEN": "correct"}, clear=True):
        result = get_token()
        assert result == "correct"


def test_token_none():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError):
            get_token()
