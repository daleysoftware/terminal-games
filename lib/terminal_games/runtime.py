"""Shared command-line and curses lifecycle behavior."""

import curses
import sys
from collections.abc import Callable


RESIZE_EXIT = 2


def run_game(
    run: Callable[[curses.window], int],
    size_message: str,
    size_exit: int = 1,
) -> int:
    """Run a curses game and handle non-terminal, resize, and interrupt exits."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return 0

    try:
        result = curses.wrapper(run)
    except KeyboardInterrupt:
        return 0

    if result == RESIZE_EXIT:
        print("Exiting because the terminal was resized.", file=sys.stderr)
        return 0
    if result == size_exit:
        print(size_message, file=sys.stderr)
        return size_exit
    return result
