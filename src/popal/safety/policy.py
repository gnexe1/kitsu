"""Safety policy engine.

Determines whether a tool is allowed to run based on its risk level
and the current safety configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from popal.tools.base import BaseTool, RiskLevel
from popal.utils.config import get as config_get
from popal.utils.logger import get_logger

logger = get_logger("safety.policy")


class Decision(str, Enum):
    """Safety engine decision for a command."""

    ALLOW = "allow"
    """Action is permitted without further checks."""

    CONFIRM = "confirm"
    """Action requires user confirmation before execution."""

    DENY = "deny"
    """Action is not permitted under any circumstances."""


@dataclass(frozen=True)
class SafetyDecision:
    """Result of a safety policy evaluation."""

    decision: Decision
    reason: str
    risk_level: RiskLevel


class SafetyPolicy:
    """Evaluates whether a tool execution should be allowed.

    The policy is driven by the tool's declared risk level and the
    safety configuration in config.yaml.
    """

    def evaluate(self, tool: BaseTool) -> SafetyDecision:
        """Evaluate the safety policy for a given tool.

        Args:
            tool: The tool that is about to be executed.

        Returns:
            A SafetyDecision indicating allow, confirm, or deny.
        """
        risk = tool.risk_level
        confirmation_required = config_get("safety.confirmation_required", True)

        if risk == RiskLevel.SAFE:
            logger.info("Safety decision: ALLOW (tool=%s, risk=%s)", tool.name, risk.value)
            return SafetyDecision(
                decision=Decision.ALLOW,
                reason="Tool is classified as SAFE.",
                risk_level=risk,
            )

        if risk == RiskLevel.CONTROLLED:
            if confirmation_required:
                logger.info("Safety decision: CONFIRM (tool=%s, risk=%s)", tool.name, risk.value)
                return SafetyDecision(
                    decision=Decision.CONFIRM,
                    reason="Tool is CONTROLLED — confirmation required.",
                    risk_level=risk,
                )
            logger.info("Safety decision: ALLOW (tool=%s, risk=%s, confirmation disabled)", tool.name, risk.value)
            return SafetyDecision(
                decision=Decision.ALLOW,
                reason="Tool is CONTROLLED — confirmation disabled in config.",
                risk_level=risk,
            )

        if risk == RiskLevel.DESTRUCTIVE:
            logger.warning("Safety decision: CONFIRM (tool=%s, risk=%s)", tool.name, risk.value)
            return SafetyDecision(
                decision=Decision.CONFIRM,
                reason="Tool is DESTRUCTIVE — confirmation always required.",
                risk_level=risk,
            )

        # Unknown risk level — deny by default
        logger.warning("Safety decision: DENY (tool=%s, unknown risk=%s)", tool.name, risk)
        return SafetyDecision(
            decision=Decision.DENY,
            reason="Unknown risk level — denying by default.",
            risk_level=risk,
        )