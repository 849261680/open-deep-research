from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    """Load environment variables from stable project locations.

    Service modules can be imported from different working directories during
    local runs, tests, or uvicorn reloads. This avoids relying on cwd.
    """

    app_dir = Path(__file__).resolve().parents[1]
    backend_env = app_dir.parents[1] / "backend" / ".env"
    root_env = app_dir.parents[1] / ".env"

    if backend_env.exists():
        load_dotenv(backend_env)
    if root_env.exists():
        load_dotenv(root_env)
