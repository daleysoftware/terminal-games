import curses
import random
import sys
import time
from typing import Optional


RESIZE_EXIT = 2
SIZE_EXIT = 1
MIN_ROWS = 8
MIN_COLUMNS = 18
SIZE_MESSAGE = "Terminal must be at least 8 rows and 18 columns."
CONTROL_MESSAGE = "Arrows: change direction; N: new game; E: exit"
SCORE_MESSAGE = "Score: {}"
GAME_OVER_MESSAGE = "Game over: {}"
WIN_MESSAGE = "You win: {}"
MOVE_INTERVAL_SECONDS = 0.5
DIRECTIONS = {
    curses.KEY_UP: (-1, 0),
    curses.KEY_DOWN: (1, 0),
    curses.KEY_LEFT: (0, -1),
    curses.KEY_RIGHT: (0, 1),
}


def _draw_screen(
    stdscr: curses.window,
    rows: int,
    columns: int,
    snake: list[tuple[int, int]],
    apple: Optional[tuple[int, int]],
    game_over: bool,
    won: bool,
    score: int,
) -> None:
    logical_columns = columns // 2
    left = 1
    right = logical_columns - 2
    top = 2
    bottom = rows - 3
    stdscr.erase()
    for logical_column in range(left, right + 1):
        stdscr.addstr(top, logical_column * 2, "  ", curses.color_pair(2))
        stdscr.addstr(bottom, logical_column * 2, "  ", curses.color_pair(2))
    for row in range(top + 1, bottom):
        stdscr.addstr(row, left * 2, "  ", curses.color_pair(2))
        stdscr.addstr(row, right * 2, "  ", curses.color_pair(2))
    for row, column in snake[1:]:
        stdscr.addstr(row, column * 2, "  ", curses.color_pair(4))
    head_row, head_column = snake[0]
    stdscr.addstr(head_row, head_column * 2, "  ", curses.color_pair(3))
    if apple is not None:
        apple_row, apple_column = apple
        stdscr.addstr(apple_row, apple_column * 2, "  ", curses.color_pair(6))
    stdscr.addnstr(0, 0, CONTROL_MESSAGE, columns, curses.color_pair(5))
    if game_over:
        message = WIN_MESSAGE if won else GAME_OVER_MESSAGE
    else:
        message = SCORE_MESSAGE
    stdscr.addnstr(
        rows - 1,
        0,
        message.format(score),
        columns,
        curses.color_pair(5),
    )
    stdscr.refresh()


def _play_sound() -> None:
    try:
        curses.beep()
    except curses.error:
        pass


def _new_snake(rows: int, columns: int) -> list[tuple[int, int]]:
    logical_columns = columns // 2
    left = 1
    right = logical_columns - 2
    top = 2
    bottom = rows - 3
    head_column = ((left + 1) + (right - 1)) // 2
    head_row = ((top + 1) + (bottom - 1)) // 2
    return [
        (head_row, head_column),
        (head_row, head_column - 1),
        (head_row, head_column - 2),
    ]


def _new_apple(
    rows: int,
    columns: int,
    snake: list[tuple[int, int]],
    rng: random.Random,
) -> Optional[tuple[int, int]]:
    logical_columns = columns // 2
    left = 1
    right = logical_columns - 2
    top = 2
    bottom = rows - 3
    empty_cells = [
        (row, column)
        for row in range(top + 1, bottom)
        for column in range(left + 1, right)
        if (row, column) not in snake
    ]
    return rng.choice(empty_cells) if empty_cells else None


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
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_BLUE)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_RED)
        stdscr.bkgd(" ", curses.color_pair(1))
        logical_columns = columns // 2
        left = 1
        right = logical_columns - 2
        top = 2
        bottom = rows - 3
        rng = random.Random()
        snake = _new_snake(rows, columns)
        apple = _new_apple(rows, columns, snake, rng)
        direction = DIRECTIONS[curses.KEY_RIGHT]
        game_over = False
        won = False
        score = 0
        last_move = time.monotonic()
        stdscr.timeout(50)
        _draw_screen(stdscr, rows, columns, snake, apple, game_over, won, score)

        while True:
            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                return RESIZE_EXIT
            if key in (ord("e"), ord("E")):
                return 0
            if key in (ord("n"), ord("N")):
                snake = _new_snake(rows, columns)
                apple = _new_apple(rows, columns, snake, rng)
                direction = DIRECTIONS[curses.KEY_RIGHT]
                game_over = False
                won = False
                score = 0
                last_move = time.monotonic()
                _draw_screen(stdscr, rows, columns, snake, apple, game_over, won, score)
                continue
            if not game_over and key in DIRECTIONS:
                direction = DIRECTIONS[key]
                _play_sound()

            now = time.monotonic()
            if not game_over and now - last_move >= MOVE_INTERVAL_SECONDS:
                last_move = now
                head_row, head_column = snake[0]
                next_cell = (head_row + direction[0], head_column + direction[1])
                if (
                    next_cell[0] <= top
                    or next_cell[0] >= bottom
                    or next_cell[1] <= left
                    or next_cell[1] >= right
                    or next_cell in snake
                ):
                    game_over = True
                    _play_sound()
                else:
                    eating_apple = next_cell == apple
                    snake.insert(0, next_cell)
                    if eating_apple:
                        score += 1
                        apple = _new_apple(rows, columns, snake, rng)
                        if apple is None:
                            game_over = True
                            won = True
                            _play_sound()
                    else:
                        snake.pop()
                _draw_screen(stdscr, rows, columns, snake, apple, game_over, won, score)
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
