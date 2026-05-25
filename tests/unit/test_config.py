from __future__ import annotations

from src.core.config import settings, yaml_config


def test_settings_loaded():
    assert settings.ENVIRONMENT in {"student", "intermediate", "production"}


def test_yaml_config_is_dict():
    assert isinstance(yaml_config, dict)
