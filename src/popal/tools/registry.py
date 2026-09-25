"""Tool registry — central lookup for all registered POPAL tools."""

from __future__ import annotations

from popal.tools.base import BaseTool
from popal.utils.errors import ToolDuplicateError, ToolNotFoundError
from popal.utils.logger import get_logger

logger = get_logger("tools.registry")


class ToolRegistry:
    """Registry that stores and retrieves tool instances by name."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Args:
            tool: The tool instance to register.

        Raises:
            ToolDuplicateError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ToolDuplicateError(
                f"Tool '{tool.name}' is already registered."
            )
        self._tools[tool.name] = tool
        logger.info("Tool registered: %s (risk=%s)", tool.name, tool.risk_level.value)

    def get(self, name: str) -> BaseTool:
        """Retrieve a tool by name.

        Args:
            name: The tool name.

        Returns:
            The registered tool instance.

        Raises:
            ToolNotFoundError: If no tool with that name is registered.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool '{name}' is not registered.")
        return tool

    def list_tools(self) -> list[BaseTool]:
        """Return a list of all registered tools."""
        return list(self._tools.values())

    def has(self, name: str) -> bool:
        """Check whether a tool is registered."""
        return name in self._tools

    def clear(self) -> None:
        """Remove all registered tools. Primarily for testing."""
        self._tools.clear()
        logger.debug("Tool registry cleared.")