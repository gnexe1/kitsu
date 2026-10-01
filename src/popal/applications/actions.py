"""Application actions — defines the allowlisted actions for the application system.

Every application action must be in this registry.
The AI can only request actions that exist here.
"""

from __future__ import annotations

from popal.applications.types import AppAction, AppActionCategory
from popal.tools.base import RiskLevel

# Global action definitions — reusable across adapters
# Format: action_id -> (name, description, category, risk_level, requires_target)

_ACTION_DEFS: dict[str, tuple[str, str, AppActionCategory, RiskLevel, bool]] = {
    # Safe actions
    "inspect": ("Inspect", "Get application state and info", AppActionCategory.FOCUS, RiskLevel.SAFE, False),
    "list_windows": ("List Windows", "List application windows", AppActionCategory.WINDOW, RiskLevel.SAFE, False),
    "get_state": ("Get State", "Get current application state", AppActionCategory.FOCUS, RiskLevel.SAFE, False),

    # Controlled actions
    "launch": ("Launch", "Start the application", AppActionCategory.LAUNCH, RiskLevel.CONTROLLED, False),
    "focus": ("Focus", "Bring application to foreground", AppActionCategory.FOCUS, RiskLevel.CONTROLLED, False),
    "open_project": ("Open Project", "Open a project directory", AppActionCategory.FILE, RiskLevel.CONTROLLED, True),
    "open_file": ("Open File", "Open a specific file", AppActionCategory.FILE, RiskLevel.CONTROLLED, True),
    "new_window": ("New Window", "Open a new window", AppActionCategory.WINDOW, RiskLevel.CONTROLLED, False),
    "save": ("Save", "Save the current file/project", AppActionCategory.SAVE, RiskLevel.CONTROLLED, False),
    "new_tab": ("New Tab", "Open a new browser tab", AppActionCategory.NAVIGATION, RiskLevel.CONTROLLED, False),
    "close_tab": ("Close Tab", "Close the current tab", AppActionCategory.NAVIGATION, RiskLevel.CONTROLLED, False),
    "switch_tab": ("Switch Tab", "Switch to a specific tab", AppActionCategory.NAVIGATION, RiskLevel.CONTROLLED, True),
    "open_url": ("Open URL", "Navigate to a URL", AppActionCategory.NAVIGATION, RiskLevel.CONTROLLED, True),
    "refresh": ("Refresh", "Refresh the current page/view", AppActionCategory.NAVIGATION, RiskLevel.SAFE, False),
    "go_back": ("Go Back", "Navigate back", AppActionCategory.NAVIGATION, RiskLevel.SAFE, False),
    "go_forward": ("Go Forward", "Navigate forward", AppActionCategory.NAVIGATION, RiskLevel.SAFE, False),

    # Destructive/high-risk actions
    "close": ("Close", "Close the application", AppActionCategory.CLOSE, RiskLevel.DESTRUCTIVE, False),
    "run_project": ("Run Project", "Run/build the current project", AppActionCategory.RUN, RiskLevel.DESTRUCTIVE, False),
    "stop_run": ("Stop Run", "Stop a running project", AppActionCategory.RUN, RiskLevel.CONTROLLED, False),
}


def get_action_def(action_id: str) -> AppAction | None:
    """Look up an action definition by ID."""
    defn = _ACTION_DEFS.get(action_id)
    if defn is None:
        return None
    name, desc, cat, risk, req_target = defn
    return AppAction(
        action_id=action_id, name=name, description=desc,
        category=cat, risk_level=risk, requires_target=req_target,
    )


def get_all_actions() -> tuple[AppAction, ...]:
    """Return all defined actions."""
    return tuple(get_action_def(aid) for aid in _ACTION_DEFS)


def get_actions_for_risk(risk: RiskLevel) -> tuple[AppAction, ...]:
    """Return all actions at a given risk level."""
    return tuple(a for a in get_all_actions() if a.risk_level == risk)