"""Vision privacy — controls for screenshot handling and sensitive data."""

from __future__ import annotations

from popal.utils.config import get as config_get
from popal.utils.logger import get_logger
from popal.vision.errors import PrivacyError

logger = get_logger("vision.privacy")

# Patterns that look like sensitive screen content
_SENSITIVE_PATTERNS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "credit card", "ssn", "social security", "private key",
)


def check_privacy_policy() -> None:
    """Check whether vision operations are permitted by configuration.

    Raises:
        PrivacyError: If vision is not enabled or external processing is disallowed.
    """
    if not config_get("vision.enabled", False):
        raise PrivacyError(
            "Vision is not enabled. Set vision.enabled=true in config.yaml to use vision."
        )


def allows_external_processing() -> bool:
    """Check whether external (cloud) processing is permitted."""
    return config_get("vision.allow_external_processing", False)


def allows_save_screenshots() -> bool:
    """Check whether saving screenshots to disk is permitted."""
    return config_get("vision.save_screenshots", False)


def redact_sensitive_text(text: str) -> str:
    """Redact potentially sensitive text found in OCR results.

    Args:
        text: Raw OCR text.

    Returns:
        Text with sensitive patterns replaced by [REDACTED].
    """
    redacted = text
    lower = text.lower()
    for pattern in _SENSITIVE_PATTERNS:
        if pattern in lower:
            redacted = "[REDACTED]"
            break
    return redacted


def validate_no_external_upload(image_data: bytes | None, provider_name: str) -> None:
    """Ensure image data is not sent to external providers when disallowed.

    Args:
        image_data: The image being processed.
        provider_name: Name of the provider that would receive it.

    Raises:
        PrivacyError: If external processing is not allowed.
    """
    if provider_name != "local" and not allows_external_processing():
        raise PrivacyError(
            f"External processing to '{provider_name}' is not allowed. "
            "Set vision.allow_external_processing=true to enable."
        )