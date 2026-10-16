import curses
import sys


RESIZE_EXIT = 2


def _run(stdscr: curses.window) -> int:
    try:
        cursor_visibility = curses.curs_set(0)
    except curses.error:
        cursor_visibility = None

    try:
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        white_background = curses.color_pair(1)
        stdscr.bkgd(" ", white_background)
        stdscr.timeout(50)
        stdscr.erase()
        stdscr.refresh()

        while True:
            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                return RESIZE_EXIT
            if key in (ord("e"), ord("E")):
                return 0
            if key in (ord("n"), ord("N")):
                stdscr.erase()
                stdscr.refresh()
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
    return result


if __name__ == "__main__":
    raise SystemExit(main())
