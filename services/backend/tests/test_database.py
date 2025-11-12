import ssl

import pytest

from app.core.database import prepare_engine_arguments, _sslmode_to_asyncpg_ssl


def test_prepare_engine_arguments_moves_sslmode_to_connect_args():
    sanitized_url, connect_args = prepare_engine_arguments(
        "postgresql+asyncpg://user:pass@host/db?sslmode=require&application_name=test"
    )

    assert "sslmode" not in sanitized_url
    assert "application_name=test" in sanitized_url
    assert connect_args == {"ssl": True}


def test_prepare_engine_arguments_ignores_non_asyncpg_drivers():
    original = "postgresql://user:pass@host/db?sslmode=require"
    sanitized_url, connect_args = prepare_engine_arguments(original)

    assert sanitized_url == original
    assert connect_args == {}


@pytest.mark.parametrize(
    ("sslmode", "expected"),
    [
        ("disable", False),
        ("require", True),
        ("verify-full", True),
    ],
)
def test_sslmode_to_asyncpg_ssl_simple_modes(sslmode, expected):
    assert _sslmode_to_asyncpg_ssl(sslmode) == expected


def test_sslmode_to_asyncpg_ssl_verify_ca():
    ssl_value = _sslmode_to_asyncpg_ssl("verify-ca")
    assert isinstance(ssl_value, ssl.SSLContext)
    assert ssl_value.check_hostname is False
