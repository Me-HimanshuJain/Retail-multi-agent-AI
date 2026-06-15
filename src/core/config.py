"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "intermediate")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./retail.db")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    MLFLOW_EXPERIMENT_NAME: str = os.getenv("MLFLOW_EXPERIMENT_NAME", "retail_multi_agent")

    def __post_init__(self) -> None:
        if self.SECRET_KEY == "change-me":
            raise RuntimeError(
                "\n\n"
                "  ╔══════════════════════════════════════════════════════════╗\n"
                "  ║  SECURITY ERROR: Insecure SECRET_KEY detected            ║\n"
                "  ║                                                          ║\n"
                "  ║  SECRET_KEY is set to the default value 'change-me'.    ║\n"
                "  ║  This key is publicly known and must never be used.     ║\n"
                "  ║                                                          ║\n"
                "  ║  Generate a secure key:                                  ║\n"
                "  ║    python -c \"import secrets; print(secrets.token_hex(32))\" ║\n"
                "  ║                                                          ║\n"
                "  ║  Then set it in your .env file:                         ║\n"
                "  ║    SECRET_KEY=<generated-value>                          ║\n"
                "  ╚══════════════════════════════════════════════════════════╝\n"
            )


settings = Settings()



def _load_yaml_config() -> Dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    config_path = root / "configs" / f"{settings.ENVIRONMENT}.yaml"
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


yaml_config: Dict[str, Any] = _load_yaml_config()
