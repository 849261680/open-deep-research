from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_script(relative_path: str) -> str:
    """Return a development script from the repository root."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_backend_scripts_use_explicit_app_reload_dir() -> None:
    """Backend dev scripts should reload when backend app code changes."""
    for script_name in ("backend.sh", "scripts/dev.sh"):
        script = read_script(script_name)

        assert "--reload" in script
        assert "--reload-dir backend/app" in script


def test_frontend_scripts_enable_fast_refresh() -> None:
    """Frontend dev scripts should explicitly run CRA with hot refresh enabled."""
    for script_name in ("frontend.sh", "scripts/dev.sh"):
        script = read_script(script_name)

        assert "FAST_REFRESH" in script
        assert "WATCHPACK_POLLING" in script
        assert "CHOKIDAR_USEPOLLING" in script
