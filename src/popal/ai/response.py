"""AI Response formatter — converts execution results into natural language.

Responses are ALWAYS based on actual execution results.
Never hallucinate success.
"""

from __future__ import annotations

from popal.ai.types import AIPlan, AIResult, AIResponseType
from popal.tools.base import ToolResult
from popal.utils.logger import get_logger

logger = get_logger("ai.response")


def format_response(plan: AIPlan, step_results: tuple[ToolResult, ...]) -> AIResult:
    """Format an execution result into a natural-language response.

    Args:
        plan: The AI plan that was executed.
        step_results: The actual tool results from execution.

    Returns:
        An AIResult with the response text.
    """
    if plan.is_clarification:
        return AIResult(
            success=False,
            plan=plan,
            step_results=step_results,
            response_text=plan.clarification or "Could you clarify your request?",
        )

    if plan.is_rejected:
        return AIResult(
            success=False,
            plan=plan,
            step_results=step_results,
            response_text=plan.rejection_reason or "I can't do that.",
        )

    if not step_results:
        return AIResult(
            success=False,
            plan=plan,
            step_results=step_results,
            response_text="No actions were executed.",
        )

    # Single command
    if len(step_results) == 1:
        text = _format_single_result(plan.steps[0] if plan.steps else None, step_results[0])
        return AIResult(
            success=step_results[0].success,
            plan=plan,
            step_results=step_results,
            response_text=text,
        )

    # Multi-step plan
    return _format_plan_results(plan, step_results)


def _format_single_result(step, result: ToolResult) -> str:
    """Format a single tool result into natural language."""
    if result.success:
        intent = step.intent if step else result.tool
        return _success_message(intent, step)
    else:
        return _failure_message(result, step)


def _success_message(intent: str, step) -> str:
    """Generate a success message based on the intent."""
    target = ""
    if step and step.parameters:
        target = step.parameters.get("application", step.parameters.get("target", ""))

    messages = {
        "open_application": f"Opening {target}.",
        "close_application": f"Closing {target}.",
        "system_info": "System information retrieved.",
        "list_applications": "Applications listed.",
        "mouse_position": "Mouse position retrieved.",
        "mouse_move": "Mouse moved.",
        "mouse_click": "Clicked.",
        "mouse_double_click": "Double-clicked.",
        "mouse_right_click": "Right-clicked.",
        "mouse_scroll": "Scrolled.",
        "keyboard_type": "Text typed.",
        "keyboard_press": "Key pressed.",
        "keyboard_hotkey": "Key combination pressed.",
        "screen_size": "Screen size retrieved.",
        "screen_screenshot": "Screenshot captured.",
        "window_list": "Windows listed.",
        "window_active": "Active window retrieved.",
        "window_focus": "Window focused.",
        "window_minimize": "Window minimized.",
        "window_maximize": "Window maximized.",
        "window_restore": "Window restored.",
        "window_close": "Window closed.",
        "application_open": f"Opening {target}.",
        "application_close": f"Closing {target}.",
        "application_list": "Applications listed.",
        "application_focus": f"Focused {target}.",
    }
    return messages.get(intent, "Done.")


def _failure_message(result: ToolResult, step) -> str:
    """Generate a failure message based on the error."""
    target = ""
    if step and step.parameters:
        target = step.parameters.get("application", step.parameters.get("target", ""))

    if result.error == "EMERGENCY_STOP":
        return "System is stopped."
    if result.error == "PERMISSION_DENIED":
        return "Permission denied."
    if result.error == "USER_CANCELLED":
        return "Cancelled."
    if result.error == "NOT_FOUND":
        return f"I couldn't find {target or 'the target'}."
    if result.error == "LAUNCH_FAILED":
        return f"I couldn't launch {target or 'the application'}."
    if result.error == "MISSING_TARGET":
        return "No target specified."
    return f"Action failed: {result.message}"


def _format_plan_results(plan: AIPlan, results: tuple[ToolResult, ...]) -> AIResult:
    """Format multi-step plan results."""
    all_success = all(r.success for r in results)
    any_success = any(r.success for r in results)

    if all_success:
        return AIResult(
            success=True,
            plan=plan,
            step_results=results,
            response_text=f"All {len(results)} steps completed.",
        )

    # Find the first failure
    for i, r in enumerate(results):
        if not r.success:
            step = plan.steps[i] if i < len(plan.steps) else None
            fail_text = _failure_message(r, step)
            completed = i
            if completed == 0:
                return AIResult(
                    success=False, plan=plan, step_results=results,
                    response_text=f"Step 1 failed: {fail_text}",
                )
            return AIResult(
                success=False, plan=plan, step_results=results,
                response_text=f"Completed {completed} of {len(results)} steps. Step {i + 1} failed: {fail_text}",
            )

    return AIResult(
        success=False, plan=plan, step_results=results,
        response_text="Plan execution failed.",
    )