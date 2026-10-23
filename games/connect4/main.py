from __future__ import annotations

import curses
import random
import time

from terminal_games.controls import draw_control_message
from terminal_games.runtime import RESIZE_EXIT, run_game


SIZE_EXIT = 1
MIN_ROWS = 23
MIN_COLUMNS = 38
SIZE_MESSAGE = "Terminal must be at least 23 rows and 38 columns."
CONTROL_MESSAGE = "←/→ move; Space drop; N new; E exit"
BOARD_COLUMNS = 7
BOARD_ROWS = 6
CELL_WIDTH = 4
CELL_HEIGHT = 2
BOARD_WIDTH = BOARD_COLUMNS * CELL_WIDTH + BOARD_COLUMNS + 1
BOARD_HEIGHT = BOARD_ROWS * CELL_HEIGHT + BOARD_ROWS + 1
DROP_INTERVAL_MS = 300
WIN_FLASH_INTERVAL_MS = 500
LANDING_FLASHES = 2
EMPTY = None
RED = "red"
BLUE = "blue"
TEAM_COLORS = {RED: 2, BLUE: 3}


def _draw_screen(
    stdscr: curses.window,
    rows: int,
    columns: int,
    board: list[list[str | None]] | None = None,
    current_team: str | None = None,
    selected_column: int = 0,
    falling_cell: tuple[int, int] | None = None,
    show_selector: bool = True,
    winning_cells: tuple[tuple[int, int], ...] | None = None,
    flash_winning_cells: bool = False,
    winner: str | None = None,
) -> None:
    stdscr.erase()
    board = board if board is not None else _empty_board()
    board_left = (columns - BOARD_WIDTH) // 2
    board_top = max(CELL_HEIGHT + 1, (rows - BOARD_HEIGHT) // 2)
    white = curses.color_pair(5)
    gray = _gray_color()

    for row_boundary in range(BOARD_ROWS + 1):
        row = board_top + row_boundary * (CELL_HEIGHT + 1)
        internal_row = 0 < row_boundary < BOARD_ROWS
        divider_color = gray if internal_row else white
        for column_boundary in range(BOARD_COLUMNS + 1):
            column = board_left + column_boundary * (CELL_WIDTH + 1)
            edge = column_boundary in (0, BOARD_COLUMNS)
            stdscr.addstr(row, column, "+", white if edge or not internal_row else gray)
            if column_boundary < BOARD_COLUMNS:
                stdscr.addstr(
                    row,
                    column + 1,
                    "-" * CELL_WIDTH,
                    divider_color,
                )

    for board_row in range(BOARD_ROWS):
        for cell_row in range(1, CELL_HEIGHT + 1):
            row = board_top + board_row * (CELL_HEIGHT + 1) + cell_row
            for column_boundary in range(BOARD_COLUMNS + 1):
                column = board_left + column_boundary * (CELL_WIDTH + 1)
                edge = column_boundary in (0, BOARD_COLUMNS)
                stdscr.addstr(row, column, "|", white if edge else gray)

    for board_row, board_line in enumerate(board):
        for column, team in enumerate(board_line):
            if team is not None and (board_row, column) != falling_cell:
                highlight = (
                    curses.color_pair(4)
                    if flash_winning_cells
                    and winning_cells is not None
                    and (board_row, column) in winning_cells
                    else None
                )
                _draw_cell(
                    stdscr, board_top, board_left, board_row, column, team, highlight
                )

    if falling_cell is not None:
        _draw_cell(
            stdscr,
            board_top,
            board_left,
            falling_cell[0],
            falling_cell[1],
            current_team,
        )

    draw_control_message(stdscr, _instruction_message(winner), columns, white)
    if winner is not None:
        winner_message = f"{winner.title()} Wins!"
        winner_x = max(0, (columns - len(winner_message)) // 2)
        stdscr.addnstr(
            rows - 1,
            winner_x,
            winner_message,
            max(0, columns - winner_x),
            curses.color_pair(TEAM_COLORS[winner]),
        )
    if show_selector and current_team is not None and winner is None:
        selector_color = curses.color_pair(TEAM_COLORS[current_team])
        selector_y = board_top - CELL_HEIGHT
        selector_x = board_left + selected_column * (CELL_WIDTH + 1) + 1
        for cell_row in range(CELL_HEIGHT):
            stdscr.addstr(
                selector_y + cell_row,
                selector_x,
                " " * CELL_WIDTH,
                selector_color | curses.A_REVERSE,
            )
    stdscr.refresh()


def _draw_cell(
    stdscr: curses.window,
    board_top: int,
    board_left: int,
    row: int,
    column: int,
    team: str,
    color_override: int | None = None,
) -> None:
    color = (
        color_override
        if color_override is not None
        else curses.color_pair(TEAM_COLORS[team])
    ) | curses.A_REVERSE
    cell_y = board_top + row * (CELL_HEIGHT + 1) + 1
    cell_x = board_left + column * (CELL_WIDTH + 1) + 1
    for cell_row in range(CELL_HEIGHT):
        stdscr.addstr(cell_y + cell_row, cell_x, " " * CELL_WIDTH, color)


def _instruction_message(winner: str | None = None) -> str:
    if winner is not None:
        return "N new; E exit"
    return CONTROL_MESSAGE


def _empty_board() -> list[list[str | None]]:
    return [[EMPTY for _ in range(BOARD_COLUMNS)] for _ in range(BOARD_ROWS)]


def _landing_row(board: list[list[str | None]], column: int) -> int | None:
    for row in range(BOARD_ROWS - 1, -1, -1):
        if board[row][column] is None:
            return row
    return None


def _find_winning_cells(
    board: list[list[str | None]],
) -> tuple[tuple[int, int], ...] | None:
    directions = ((0, 1), (1, 0), (1, 1), (1, -1))
    winning_cells = set()
    for row in range(BOARD_ROWS):
        for column in range(BOARD_COLUMNS):
            team = board[row][column]
            if team is None:
                continue
            for row_step, column_step in directions:
                cells = tuple(
                    (row + offset * row_step, column + offset * column_step)
                    for offset in range(4)
                )
                if all(
                    0 <= cell_row < BOARD_ROWS
                    and 0 <= cell_column < BOARD_COLUMNS
                    and board[cell_row][cell_column] == team
                    for cell_row, cell_column in cells
                ):
                    winning_cells.update(cells)
    return tuple(sorted(winning_cells)) if winning_cells else None


def _gray_color() -> int:
    if getattr(curses, "COLORS", 0) >= 256:
        return curses.color_pair(6)
    return curses.color_pair(6) | curses.A_DIM


def _draw_animation_frame(
    stdscr: curses.window,
    board: list[list[str | None]],
    current_team: str,
    selected_column: int,
    falling_row: int | None,
    show_piece: bool,
) -> None:
    rows, columns = stdscr.getmaxyx()
    animated_board = [line[:] for line in board]
    falling_cell = None
    if show_piece and falling_row is not None:
        animated_board[falling_row][selected_column] = current_team
        falling_cell = (falling_row, selected_column)
    _draw_screen(
        stdscr,
        rows,
        columns,
        animated_board,
        current_team,
        selected_column,
        falling_cell,
        show_selector=False,
    )


def _animate_drop(
    stdscr: curses.window,
    board: list[list[str | None]],
    current_team: str,
    selected_column: int,
    landing_row: int,
) -> None:
    for row in range(BOARD_ROWS):
        if row > landing_row:
            break
        _draw_animation_frame(
            stdscr, board, current_team, selected_column, row, show_piece=True
        )
        curses.napms(DROP_INTERVAL_MS)
        if row < landing_row:
            _draw_animation_frame(
                stdscr, board, current_team, selected_column, row, show_piece=False
            )

    for _ in range(LANDING_FLASHES):
        _draw_animation_frame(
            stdscr,
            board,
            current_team,
            selected_column,
            landing_row,
            show_piece=True,
        )
        curses.napms(DROP_INTERVAL_MS)
        _draw_animation_frame(
            stdscr,
            board,
            current_team,
            selected_column,
            landing_row,
            show_piece=False,
        )
        curses.napms(DROP_INTERVAL_MS)


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
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        gray = 244 if getattr(curses, "COLORS", 0) >= 256 else curses.COLOR_WHITE
        curses.init_pair(6, gray, curses.COLOR_BLACK)
        stdscr.bkgd(" ", curses.color_pair(1))
        stdscr.keypad(True)
        stdscr.timeout(50)

        board = _empty_board()
        current_team = random.choice((RED, BLUE))
        selected_column = 0
        winner = None
        winning_cells = None
        flash_winning_cells = True
        next_winner_toggle = None
        pending_key = None

        while True:
            rows, columns = stdscr.getmaxyx()
            if rows < MIN_ROWS or columns < MIN_COLUMNS:
                return SIZE_EXIT
            now = time.monotonic()
            if winner is not None and now >= next_winner_toggle:
                flash_winning_cells = not flash_winning_cells
                next_winner_toggle = now + WIN_FLASH_INTERVAL_MS / 1000
            _draw_screen(
                stdscr,
                rows,
                columns,
                board,
                current_team,
                selected_column,
                winning_cells=winning_cells,
                flash_winning_cells=flash_winning_cells if winner is not None else False,
                winner=winner,
            )

            if pending_key is None:
                key = stdscr.getch()
            else:
                key = pending_key
                pending_key = None
            if key == curses.KEY_RESIZE:
                return RESIZE_EXIT
            if key in (ord("e"), ord("E")):
                return 0
            if key in (ord("n"), ord("N")):
                board = _empty_board()
                current_team = random.choice((RED, BLUE))
                selected_column = 0
                winner = None
                winning_cells = None
                flash_winning_cells = True
                next_winner_toggle = None
                continue
            if winner is not None:
                continue
            if key == curses.KEY_LEFT:
                selected_column = max(0, selected_column - 1)
            elif key == curses.KEY_RIGHT:
                selected_column = min(BOARD_COLUMNS - 1, selected_column + 1)
            elif key == ord(" "):
                landing_row = _landing_row(board, selected_column)
                if landing_row is None:
                    curses.beep()
                    continue
                _animate_drop(
                    stdscr, board, current_team, selected_column, landing_row
                )
                while True:
                    queued_key = stdscr.getch()
                    if queued_key == -1:
                        break
                    if queued_key != ord(" "):
                        pending_key = queued_key
                        break
                board[landing_row][selected_column] = current_team
                winning_cells = _find_winning_cells(board)
                if winning_cells is not None:
                    winner = current_team
                    flash_winning_cells = True
                    next_winner_toggle = (
                        time.monotonic() + WIN_FLASH_INTERVAL_MS / 1000
                    )
                    continue
                current_team = BLUE if current_team == RED else RED
                selected_column = 0
    finally:
        if cursor_visibility is not None:
            curses.curs_set(cursor_visibility)


def main() -> int:
    return run_game(_run, SIZE_MESSAGE, SIZE_EXIT)


if __name__ == "__main__":
    raise SystemExit(main())
