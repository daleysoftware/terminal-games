import curses
import random
import time
from terminal_games.controls import draw_control_message
from terminal_games.runtime import RESIZE_EXIT, run_game
from terminal_games.rendering import draw_cell, draw_rectangle


SIZE_EXIT = 1
MIN_ROWS = 30
MIN_COLUMNS = 54
SIZE_MESSAGE = "Terminal must be at least 30 rows and 54 columns."
CONTROL_MESSAGE = "←/→ move; ↓ drop; R rotate; Space pause; N new; E exit"
INNER_WIDTH = 21
INNER_HEIGHT = 22
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
GRAVITY_INTERVAL = 0.5
TETROMINO_SHAPES = {
    "I": ((0, 0), (0, 1), (0, 2), (0, 3)),
    "O": ((0, 0), (0, 1), (1, 0), (1, 1)),
    "T": ((0, 1), (1, 0), (1, 1), (1, 2)),
    "S": ((0, 1), (0, 2), (1, 0), (1, 1)),
    "Z": ((0, 0), (0, 1), (1, 1), (1, 2)),
    "J": ((0, 0), (1, 0), (1, 1), (1, 2)),
    "L": ((0, 2), (1, 0), (1, 1), (1, 2)),
}
TETROMINO_COLOR_PAIRS = {
    "I": 6,
    "O": 7,
    "T": 8,
    "S": 9,
    "Z": 10,
    "J": 11,
    "L": 12,
}


def _layout(rows: int, columns: int) -> tuple[int, int, int, int, int]:
    logical_columns = columns // 2
    left = 1
    right = logical_columns - 2
    top = 2
    bottom = rows - 3
    outer_interior_width = right - left - 1
    outer_interior_height = bottom - top - 1
    inner_left = left + 1 + (outer_interior_width - INNER_WIDTH) // 2
    inner_top = top + 1 + (outer_interior_height - INNER_HEIGHT) // 2
    divider_column = inner_left + 11
    return inner_left, inner_top, divider_column, inner_top + 11, right


def _draw_piece(
    stdscr: curses.window,
    piece: tuple[str, tuple[tuple[int, int], ...], int, int],
    board_left: int,
    board_top: int,
    color_pair: int,
) -> None:
    _, cells, piece_row, piece_column = piece
    color = curses.color_pair(color_pair)
    for row, column in cells:
        draw_cell(
            stdscr,
            board_top + piece_row + row,
            board_left + piece_column + column,
            color,
        )


def _draw_next_piece(
    stdscr: curses.window,
    piece: tuple[str, tuple[tuple[int, int], ...]],
    panel_left: int,
    panel_right: int,
    area_top: int,
    area_bottom: int,
) -> None:
    piece_name, cells = piece
    min_row = min(row for row, _ in cells)
    max_row = max(row for row, _ in cells)
    min_column = min(column for _, column in cells)
    max_column = max(column for _, column in cells)
    piece_height = max_row - min_row + 1
    piece_width = max_column - min_column + 1
    panel_width = panel_right - panel_left
    area_height = area_bottom - area_top + 1
    piece_left = panel_left + (panel_width - piece_width) // 2 - min_column
    piece_top = area_top + (area_height - piece_height) // 2 - min_row
    color = curses.color_pair(TETROMINO_COLOR_PAIRS[piece_name])

    for row, column in cells:
        draw_cell(stdscr, piece_top + row, piece_left + column, color)


def _draw_grid(
    stdscr: curses.window,
    rows: int,
    columns: int,
    white_pair: int,
    message_pair: int,
    locked: dict[tuple[int, int], str],
    active: tuple[str, tuple[tuple[int, int], ...], int, int],
    next_piece: tuple[str, tuple[tuple[int, int], ...]],
    game_over: bool,
    score: int,
    draw_active: bool = True,
    flashing_rows: tuple[int, ...] = (),
    flash_white: bool = False,
    paused: bool = False,
) -> None:
    inner_left, inner_top, divider_column, panel_divider_row, _ = _layout(rows, columns)
    inner_right = inner_left + INNER_WIDTH - 1
    inner_bottom = inner_top + INNER_HEIGHT - 1
    board_left = inner_left + 1
    board_top = inner_top + 1
    panel_left = divider_column + 1

    stdscr.erase()
    white = curses.color_pair(white_pair)
    draw_rectangle(stdscr, 1, 2, columns // 2 - 2, rows - 3, white)
    draw_rectangle(stdscr, inner_left, inner_top, inner_right, inner_bottom, white)

    for row in range(inner_top + 1, inner_bottom):
        draw_cell(stdscr, row, divider_column, curses.color_pair(white_pair))
    for column in range(panel_left, inner_right):
        draw_cell(stdscr, panel_divider_row, column, curses.color_pair(white_pair))

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
    stdscr.addnstr(
        panel_divider_row + 3,
        (panel_left + 1) * 2,
        str(score),
        (inner_right - panel_left - 1) * 2,
        curses.color_pair(message_pair),
    )

    for (row, column), piece_name in locked.items():
        if row in flashing_rows:
            color = curses.color_pair(2) if flash_white else _gray_color()
        else:
            color = _gray_color()
        draw_cell(stdscr, board_top + row, board_left + column, color)
    if not game_over and draw_active:
        _draw_piece(
            stdscr,
            active,
            board_left,
            board_top,
            TETROMINO_COLOR_PAIRS[active[0]],
        )
    _draw_next_piece(
        stdscr,
        next_piece,
        panel_left,
        inner_right,
        inner_top + 4,
        panel_divider_row - 1,
    )

    if game_over or paused:
        message = "GAME OVER" if game_over else "PAUSED"
        message_row = board_top + BOARD_HEIGHT // 2
        message_column = board_left * 2 + (BOARD_WIDTH * 2 - len(message)) // 2
        stdscr.addstr(message_row, message_column, message, curses.color_pair(message_pair))
    draw_control_message(
        stdscr, CONTROL_MESSAGE, columns, curses.color_pair(message_pair)
    )
    stdscr.refresh()


def _gray_color() -> int:
    color = curses.color_pair(13)
    if getattr(curses, "COLORS", 0) < 256:
        color |= curses.A_DIM
    return color


def _new_piece(
    name: str, cells: tuple[tuple[int, int], ...]
) -> tuple[str, tuple[tuple[int, int], ...], int, int]:
    width = max(column for _, column in cells) + 1
    return name, cells, 0, (BOARD_WIDTH - width) // 2


def _collides(
    cells: tuple[tuple[int, int], ...],
    row: int,
    column: int,
    locked: dict[tuple[int, int], str],
) -> bool:
    for cell_row, cell_column in cells:
        board_row = row + cell_row
        board_column = column + cell_column
        if (
            board_column < 0
            or board_column >= BOARD_WIDTH
            or board_row < 0
            or board_row >= BOARD_HEIGHT
            or (board_row, board_column) in locked
        ):
            return True
    return False


def _full_rows(locked: dict[tuple[int, int], str]) -> tuple[int, ...]:
    return tuple(
        row
        for row in range(BOARD_HEIGHT)
        if all((row, column) in locked for column in range(BOARD_WIDTH))
    )


def _remove_rows(
    locked: dict[tuple[int, int], str], full_rows: tuple[int, ...]
) -> dict[tuple[int, int], str]:
    full_rows_set = set(full_rows)
    remaining = {}
    for (row, column), piece_name in locked.items():
        if row in full_rows_set:
            continue
        shifted_row = row + sum(full_row > row for full_row in full_rows)
        remaining[(shifted_row, column)] = piece_name
    return remaining


def _rotate_clockwise(
    cells: tuple[tuple[int, int], ...]
) -> tuple[tuple[int, int], ...]:
    height = max(row for row, _ in cells) + 1
    return tuple(sorted((column, height - 1 - row) for row, column in cells))


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
        for pair, color in (
            (6, curses.COLOR_CYAN),
            (7, curses.COLOR_YELLOW),
            (8, curses.COLOR_MAGENTA),
            (9, curses.COLOR_GREEN),
            (10, curses.COLOR_RED),
            (11, curses.COLOR_BLUE),
        ):
            curses.init_pair(pair, curses.COLOR_BLACK, color)
        orange = 208 if getattr(curses, "COLORS", 0) >= 256 else curses.COLOR_WHITE
        curses.init_pair(12, curses.COLOR_BLACK, orange)
        gray = 244 if getattr(curses, "COLORS", 0) >= 256 else curses.COLOR_WHITE
        curses.init_pair(13, curses.COLOR_BLACK, gray)
        stdscr.bkgd(" ", curses.color_pair(1))
        stdscr.keypad(True)

        locked: dict[tuple[int, int], str] = {}
        next_piece = random.choice(tuple(TETROMINO_SHAPES.items()))
        active = _new_piece(*next_piece)
        next_piece = random.choice(tuple(TETROMINO_SHAPES.items()))
        game_over = _collides(active[1], active[2], active[3], locked)
        score = 0
        next_gravity = time.monotonic() + GRAVITY_INTERVAL
        paused = False
        paused_at: float | None = None
        stdscr.timeout(50)

        while True:
            _draw_grid(
                stdscr,
                rows,
                columns,
                2,
                5,
                locked,
                active,
                next_piece,
                game_over,
                score,
                paused=paused,
            )
            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                return RESIZE_EXIT
            if key in (ord("e"), ord("E")):
                return 0
            if key in (ord("n"), ord("N")):
                locked = {}
                active = _new_piece(*random.choice(tuple(TETROMINO_SHAPES.items())))
                next_piece = random.choice(tuple(TETROMINO_SHAPES.items()))
                game_over = False
                score = 0
                next_gravity = time.monotonic() + GRAVITY_INTERVAL
                paused = False
                paused_at = None
                continue

            if key == ord(" ") and not game_over:
                now = time.monotonic()
                if paused:
                    assert paused_at is not None
                    next_gravity += now - paused_at
                    paused = False
                    paused_at = None
                else:
                    paused = True
                    paused_at = now
                continue

            if game_over:
                continue
            if paused:
                continue

            name, cells, piece_row, piece_column = active
            if key in (ord("r"), ord("R")) and name != "O":
                rotated = _rotate_clockwise(cells)
                if not _collides(rotated, piece_row, piece_column, locked):
                    active = name, rotated, piece_row, piece_column
            elif key == curses.KEY_LEFT:
                if not _collides(cells, piece_row, piece_column - 1, locked):
                    active = name, cells, piece_row, piece_column - 1
            elif key == curses.KEY_RIGHT:
                if not _collides(cells, piece_row, piece_column + 1, locked):
                    active = name, cells, piece_row, piece_column + 1
            elif key == curses.KEY_DOWN:
                if not _collides(cells, piece_row + 1, piece_column, locked):
                    active = name, cells, piece_row + 1, piece_column

            now = time.monotonic()
            if now >= next_gravity:
                name, cells, piece_row, piece_column = active
                if _collides(cells, piece_row + 1, piece_column, locked):
                    for cell_row, cell_column in cells:
                        locked[(piece_row + cell_row, piece_column + cell_column)] = name
                    full_rows = _full_rows(locked)
                    score += len(full_rows)
                    if full_rows:
                        for flash_white in (True, False, True, False):
                            _draw_grid(
                                stdscr,
                                rows,
                                columns,
                                2,
                                5,
                                locked,
                                active,
                                next_piece,
                                False,
                                score,
                                draw_active=False,
                                flashing_rows=full_rows,
                                flash_white=flash_white,
                            )
                            curses.napms(120)
                        locked = _remove_rows(locked, full_rows)
                    active = _new_piece(*next_piece)
                    next_piece = random.choice(tuple(TETROMINO_SHAPES.items()))
                    game_over = _collides(active[1], active[2], active[3], locked)
                else:
                    active = name, cells, piece_row + 1, piece_column
                next_gravity = now + GRAVITY_INTERVAL
    finally:
        if cursor_visibility is not None:
            curses.curs_set(cursor_visibility)


def main() -> int:
    return run_game(_run, SIZE_MESSAGE, SIZE_EXIT)


if __name__ == "__main__":
    raise SystemExit(main())
