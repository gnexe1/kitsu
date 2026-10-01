"""Application registry — central lookup for application adapters."""

from __future__ import annotations

from popal.applications.base import ApplicationAdapter
from popal.applications.errors import AppNotFoundError
from popal.utils.logger import get_logger

logger = get_logger("applications.registry")


class ApplicationRegistry:
    """Registry that stores and retrieves application adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, ApplicationAdapter] = {}

    def register(self, adapter: ApplicationAdapter) -> None:
        """Register an application adapter.

        Args:
            adapter: The adapter to register.
        """
        app_id = adapter.app_id
        if app_id in self._adapters:
            logger.warning("Overwriting adapter for '%s'", app_id)
        self._adapters[app_id] = adapter
        logger.info("Application adapter registered: %s (%s)",
                     app_id, adapter.app_info.name)

    def get(self, app_id: str) -> ApplicationAdapter:
        """Retrieve an adapter by application ID.

        Args:
            app_id: The application identifier.

        Returns:
            The registered adapter.

        Raises:
            AppNotFoundError: If no adapter is registered for this app.
        """
        adapter = self._adapters.get(app_id)
        if adapter is None:
            raise AppNotFoundError(
                f"No adapter registered for application '{app_id}'. "
                f"Available: {', '.join(sorted(self._adapters.keys()))}"
            )
        return adapter

    def has(self, app_id: str) -> bool:
        """Check whether an adapter is registered for an app."""
        return app_id in self._adapters

    def list_registered(self) -> list[str]:
        """Return all registered application IDs."""
        return sorted(self._adapters.keys())

    def list_all_info(self) -> list:
        """Return AppInfo for all registered adapters."""
        return [a.app_info for a in self._adapters.values()]

    def identify(self, name_or_process: str) -> ApplicationAdapter | None:
        """Try to identify an adapter from a name or process string.

        Checks app_id, name, process_names, and executable_names.
        Returns None if no match.
        """
        lower = name_or_process.lower().strip()

        # Direct ID match
        if lower in self._adapters:
            return self._adapters[lower]

        # Check aliases
        aliases = {
            "vs code": "vscode", "vscode": "vscode", "visual studio code": "vscode",
            "code": "vscode",
            "chrome": "chrome", "google chrome": "chrome", "chromium": "chrome",
            "android studio": "android_studio",
            "firefox": "firefox",
            "terminal": "terminal", "gnome-terminal": "terminal",
        }
        alias_match = aliases.get(lower)
        if alias_match and alias_match in self._adapters:
            return self._adapters[alias_match]

        # Check each adapter's info
        for adapter in self._adapters.values():
            info = adapter.app_info
            if lower == info.name.lower():
                return adapter
            for pn in info.process_names:
                if lower == pn.lower():
                    return adapter
            for en in info.executable_names:
                if lower == en.lower():
                    return adapter

        return None