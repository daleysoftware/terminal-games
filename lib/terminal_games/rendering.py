"""Drawing helpers for games that use two terminal columns per logical cell."""

from typing import Any


def draw_cell(window: Any, row: int, column: int, color: int) -> None:
    """Draw one logical cell as a two-column terminal block."""
    window.addstr(row, column * 2, "  ", color)


def draw_rectangle(
    window: Any,
    left: int,
    top: int,
    right: int,
    bottom: int,
    color: int,
) -> None:
    """Draw the outline of an inclusive rectangle in logical-cell coordinates."""
    for column in range(left, right + 1):
        draw_cell(window, top, column, color)
        draw_cell(window, bottom, column, color)
    for row in range(top + 1, bottom):
        draw_cell(window, row, left, color)
        draw_cell(window, row, right, color)
