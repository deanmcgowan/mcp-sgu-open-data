"""Tests for application configuration."""

from __future__ import annotations


def test_default_settings() -> None:
    """Settings load correctly with defaults."""
    import mcp_sgu.config as cfg_module

    cfg_module._settings = None  # Force fresh load
    settings = cfg_module.get_settings()

    assert settings.sgu_base_url.startswith("https://")
    assert settings.max_inline_results == 100
    assert settings.max_export_records == 1000  # overridden in conftest
    assert settings.max_upstream_concurrency == 4
    assert settings.export_ttl_seconds == 3600


def test_settings_from_env(monkeypatch) -> None:
    """Settings read values from environment variables."""
    import mcp_sgu.config as cfg_module

    monkeypatch.setenv("MAX_INLINE_RESULTS", "200")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_ENV", "production")
    cfg_module._settings = None

    settings = cfg_module.get_settings()
    assert settings.max_inline_results == 200
    assert settings.log_level == "DEBUG"
    assert settings.app_env == "production"
    assert settings.is_production is True


def test_settings_is_production() -> None:
    """is_production returns False for non-production environments."""
    import mcp_sgu.config as cfg_module

    cfg_module._settings = None
    settings = cfg_module.get_settings()
    # APP_ENV is 'development' by default in tests
    assert settings.is_production is False


def test_mcp_bearer_token_set() -> None:
    """****** is set from environment."""
    import mcp_sgu.config as cfg_module

    settings = cfg_module.get_settings()
    assert settings.mcp_bearer_token == "test-token-12345"


def test_settings_singleton() -> None:
    """get_settings returns the same instance on subsequent calls."""
    import mcp_sgu.config as cfg_module

    cfg_module._settings = None
    s1 = cfg_module.get_settings()
    s2 = cfg_module.get_settings()
    assert s1 is s2
