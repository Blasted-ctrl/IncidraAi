"""Configuration helpers for runtime services."""

import os
from typing import Any


def get_env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable with optional default."""
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def get_int_env(name: str, default: int) -> int:
    """Read an integer environment variable with fallback."""
    value = get_env(name)
    if value is None:
        return default
    return int(value)


def get_database_config() -> dict[str, Any]:
    """Return database connection settings without embedding secrets in code."""
    return {
        "host": get_env("DB_HOST", "localhost"),
        "database": get_env("DB_NAME", "incident_triage"),
        "user": get_env("DB_USER", "postgres"),
        "password": get_env("DB_PASSWORD"),
        "port": get_int_env("DB_PORT", 5432),
    }
