"""API package."""

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None


def _load_environment() -> None:
    """Load environment variables from common local .env locations."""
    if load_dotenv is None:
        return

    src_dir = Path(__file__).resolve().parent
    candidates = (
        src_dir.parent / ".env",
        src_dir.parent.parent.parent / ".env",
    )

    for env_file in candidates:
        if env_file.exists():
            load_dotenv(env_file, override=False)


_load_environment()
