import curses
import sys


RESIZE_EXIT = 2
SIZE_EXIT = 1
MIN_ROWS = 8
MIN_COLUMNS = 14
SIZE_MESSAGE = "Terminal must be at least 8 rows and 14 columns."
CONTROL_MESSAGE = "E: exit"


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
    for logical_column in range(left, right + 1):
        stdscr.addstr(top, logical_column * 2, "  ", curses.color_pair(white_pair))
        stdscr.addstr(bottom, logical_column * 2, "  ", curses.color_pair(white_pair))
    for row in range(top + 1, bottom):
        stdscr.addstr(row, left * 2, "  ", curses.color_pair(white_pair))
        stdscr.addstr(row, right * 2, "  ", curses.color_pair(white_pair))
    stdscr.addnstr(0, 0, CONTROL_MESSAGE, columns, curses.color_pair(message_pair))
    stdscr.refresh()


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
