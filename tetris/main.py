import curses
import sys


RESIZE_EXIT = 2
SIZE_EXIT = 1
MIN_ROWS = 30
MIN_COLUMNS = 54
SIZE_MESSAGE = "Terminal must be at least 30 rows and 54 columns."
CONTROL_MESSAGE = "E: exit"
INNER_WIDTH = 21
INNER_HEIGHT = 22


def _draw_grid(
    stdscr: curses.window,
    rows: int,
    columns: int,
    white_pair: int,
    message_pair: int,
) -> None:
    logical_columns = columns // 2
    left = 1
    right = logical_columns - 2
    top = 2
    bottom = rows - 3

    stdscr.erase()
    _draw_rectangle(stdscr, left, top, right, bottom, white_pair)

    outer_interior_width = right - left - 1
    outer_interior_height = bottom - top - 1
    inner_left = left + 1 + (outer_interior_width - INNER_WIDTH) // 2
    inner_top = top + 1 + (outer_interior_height - INNER_HEIGHT) // 2
    inner_right = inner_left + INNER_WIDTH - 1
    inner_bottom = inner_top + INNER_HEIGHT - 1
    _draw_rectangle(
        stdscr, inner_left, inner_top, inner_right, inner_bottom, white_pair
    )

    divider_column = inner_left + 11
    for row in range(inner_top + 1, inner_bottom):
        stdscr.addstr(
            row, divider_column * 2, "  ", curses.color_pair(white_pair)
        )

    panel_left = divider_column + 1
    panel_divider_row = inner_top + 11
    for column in range(panel_left, inner_right):
        stdscr.addstr(
            panel_divider_row,
            column * 2,
            "  ",
            curses.color_pair(white_pair),
        )

    stdscr.addnstr(
        inner_top + 2,
        (panel_left + 1) * 2,
        "NEXT",
        (inner_right - panel_left - 1) * 2,
        curses.color_pair(message_pair),
    )
    stdscr.addnstr(
        panel_divider_row + 2,
        (panel_left + 1) * 2,
        "SCORE",
        (inner_right - panel_left - 1) * 2,
        curses.color_pair(message_pair),
    )
    stdscr.addnstr(0, 0, CONTROL_MESSAGE, columns, curses.color_pair(message_pair))
    stdscr.refresh()


def _draw_rectangle(
    stdscr: curses.window,
    left: int,
    top: int,
    right: int,
    bottom: int,
    white_pair: int,
) -> None:
    white = curses.color_pair(white_pair)
    for column in range(left, right + 1):
        stdscr.addstr(top, column * 2, "  ", white)
        stdscr.addstr(bottom, column * 2, "  ", white)
    for row in range(top + 1, bottom):
        stdscr.addstr(row, left * 2, "  ", white)
        stdscr.addstr(row, right * 2, "  ", white)


def _run(stdscr: curses.window) -> int:
    rows, columns = stdscr.getmaxyx()
    if rows < MIN_ROWS or columns < MIN_COLUMNS:
        return SIZE_EXIT

    try:
        cursor_visibility = curses.curs_set(0)
    except curses.error:
        cursor_visibility = None

    try:
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        stdscr.bkgd(" ", curses.color_pair(1))
        _draw_grid(stdscr, rows, columns, 2, 5)

        while True:
            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                return RESIZE_EXIT
            if key in (ord("e"), ord("E")):
                return 0
    finally:
        if cursor_visibility is not None:
            curses.curs_set(cursor_visibility)


def main() -> int:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return 0

    try:
        result = curses.wrapper(_run)
    except KeyboardInterrupt:
        return 0

    if result == RESIZE_EXIT:
        print("Exiting because the terminal was resized.", file=sys.stderr)
        return 0
    if result == SIZE_EXIT:
        print(SIZE_MESSAGE, file=sys.stderr)
        return SIZE_EXIT
    return result


if __name__ == "__main__":
    raise SystemExit(main())
