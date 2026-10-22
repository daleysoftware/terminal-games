"""Formatting helpers for compact, wrapped game controls."""

from typing import Any


CONTROL_SEPARATOR = "; "


def wrap_control_message(message: str, columns: int) -> list[str]:
    """Wrap semicolon-separated controls without splitting a key/action pair."""
    if columns <= 0:
        return []

    lines: list[str] = []
    current_line = ""
    for control in message.split(CONTROL_SEPARATOR):
        candidate = (
            f"{current_line}{CONTROL_SEPARATOR}{control}" if current_line else control
        )
        if current_line and len(candidate) > columns:
            lines.append(current_line)
            current_line = control
        else:
            current_line = candidate
    if current_line:
        lines.append(current_line)
    return lines


def draw_control_message(
    window: Any, message: str, columns: int, color: int
) -> int:
    """Draw wrapped control lines from the top left and return their row count."""
    lines = wrap_control_message(message, columns)
    for row, line in enumerate(lines):
        window.addnstr(row, 0, line, columns, color)
    return len(lines)
