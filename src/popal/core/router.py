"""Command router — maps command intents to their tool names.

In Phase 0 the mapping is static. In future phases, the AI planner
will produce structured commands that are routed through here.
"""

from __future__ import annotations

from popal.utils.errors import CommandError
from popal.utils.logger import get_logger

logger = get_logger("core.router")

# Intent → tool name mapping
_INTENT_TO_TOOL: dict[str, str] = {
    "system_info": "system_info",
    "open_application": "open_application",
    "close_application": "close_application",
    "list_applications": "list_applications",
}


def resolve_tool(intent: str) -> str:
    """Resolve a command intent to its registered tool name.

    Args:
        intent: The command intent string.

    Returns:
        The tool name to execute.

    Raises:
        CommandError: If no tool is mapped for the given intent.
    """
    tool_name = _INTENT_TO_TOOL.get(intent)
    if tool_name is None:
        raise CommandError(f"No tool mapped for intent: '{intent}'")
    logger.debug("Intent '%s' resolved to tool '%s'", intent, tool_name)
    return tool_name


def register_intent_mapping(intent: str, tool_name: str) -> None:
    """Register or update an intent-to-tool mapping.

    Args:
        intent: The command intent.
        tool_name: The tool name in the registry.
    """
    _INTENT_TO_TOOL[intent] = tool_name
    logger.debug("Intent mapping registered: '%s' -> '%s'", intent, tool_name)