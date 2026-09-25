"""POPAL configuration loader.

Loads configuration from YAML files and environment variables.
Configuration values can be overridden by POPAL_* environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from popal.utils.errors import ConfigError
from popal.utils.logger import get_logger

logger = get_logger("config")

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "config.yaml"

_config: dict[str, Any] | None = None


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(cfg: dict) -> dict:
    """Apply POPAL_* environment variables to override config values.

    Environment variable naming convention:
        POPAL_POPAL_ENVIRONMENT  ->  cfg["popal"]["environment"]
        POPAL_LOG_LEVEL          ->  cfg["popal"]["log_level"]
    """
    env_prefix = "POPAL_"
    for key, value in os.environ.items():
        if not key.startswith(env_prefix):
            continue
        parts = key[len(env_prefix):].lower().split("_")
        # Map well-known overrides to their correct config paths
        target = cfg
        if key == "POPAL_ENV":
            target.setdefault("popal", {})["environment"] = value
        elif key == "POPAL_LOG_LEVEL":
            target.setdefault("popal", {})["log_level"] = value
    return cfg


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and return the POPAL configuration.

    Args:
        path: Path to a YAML config file. If None, uses the default location.

    Returns:
        Merged configuration dictionary.

    Raises:
        ConfigError: If the config file cannot be found or parsed.
    """
    global _config  # noqa: PLW0603

    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse configuration file: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Configuration file must contain a YAML mapping at the top level.")

    cfg = _apply_env_overrides(raw)
    _config = cfg
    logger.info("Configuration loaded from %s", config_path)
    return cfg


def get_config() -> dict[str, Any]:
    """Return the currently loaded configuration.

    Returns:
        The configuration dictionary. Calls load_config() if not yet loaded.

    Raises:
        ConfigError: If no config has been loaded.
    """
    if _config is None:
        return load_config()
    return _config


def get(key: str, default: Any = None) -> Any:
    """Retrieve a top-level or dotted config key.

    Args:
        key: Dotted key path, e.g. 'safety.confirmation_required'.
        default: Value returned when the key is absent.

    Returns:
        The config value, or *default*.
    """
    cfg = get_config()
    for part in key.split("."):
        if isinstance(cfg, dict):
            cfg = cfg.get(part, default)
        else:
            return default
    return cfg