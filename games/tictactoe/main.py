from __future__ import annotations

import curses
import time

from terminal_games.controls import draw_control_message
from terminal_games.runtime import RESIZE_EXIT, run_game


SIZE_EXIT = 1
MIN_ROWS = 15
MIN_COLUMNS = 30
SIZE_MESSAGE = "Terminal must be at least 15 rows and 30 columns."
CONTROL_MESSAGE = "↑/↓/←/→ move; Enter/Space mark; N new; E exit"
BOARD_SIZE = 3
CELL_WIDTH = 4
CELL_HEIGHT = 2
BOARD_WIDTH = BOARD_SIZE * CELL_WIDTH + BOARD_SIZE + 1
BOARD_HEIGHT = BOARD_SIZE * CELL_HEIGHT + BOARD_SIZE + 1
EMPTY = None
PLAYERS = ("X", "O")
PLAYER_COLORS = {"X": 2, "O": 3}
WIN_FLASH_INTERVAL_MS = 500


def _new_board() -> list[list[str | None]]:
    return [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


def _winning_cells(
    board: list[list[str | None]],
) -> tuple[tuple[int, int], ...] | None:
    lines = [
        tuple((row, column) for column in range(BOARD_SIZE))
        for row in range(BOARD_SIZE)
    ]
    lines.extend(
        tuple((row, column) for row in range(BOARD_SIZE))
        for column in range(BOARD_SIZE)
    )
    lines.extend(
        (
            tuple((index, index) for index in range(BOARD_SIZE)),
            tuple((index, BOARD_SIZE - index - 1) for index in range(BOARD_SIZE)),
        )
    )
    for cells in lines:
        marks = [board[row][column] for row, column in cells]
        if marks[0] is not None and marks.count(marks[0]) == BOARD_SIZE:
            return cells
    return None


def _winner(board: list[list[str | None]]) -> str | None:
    cells = _winning_cells(board)
    if cells is None:
        return None
    return board[cells[0][0]][cells[0][1]]


def _draw_screen(
    stdscr: curses.window,
    rows: int,
    columns: int,
    board: list[list[str | None]],
    current_player: str,
    cursor: tuple[int, int],
    winner: str | None = None,
    draw: bool = False,
    winning_cells: tuple[tuple[int, int], ...] | None = None,
    flash_winning_cells: bool = False,
) -> None:
    stdscr.erase()
    draw_control_message(stdscr, CONTROL_MESSAGE, columns, curses.color_pair(5))
    white = curses.color_pair(5)
    gray = _gray_color()
    board_left = (columns - BOARD_WIDTH) // 2
    board_top = max(CELL_HEIGHT + 1, (rows - BOARD_HEIGHT) // 2)

    for row_boundary in range(BOARD_SIZE + 1):
        row = board_top + row_boundary * (CELL_HEIGHT + 1)
        internal_row = 0 < row_boundary < BOARD_SIZE
        divider_color = gray if internal_row else white
        for column_boundary in range(BOARD_SIZE + 1):
            column = board_left + column_boundary * (CELL_WIDTH + 1)
            edge = column_boundary in (0, BOARD_SIZE)
            stdscr.addstr(row, column, "+", white if edge or not internal_row else gray)
            if column_boundary < BOARD_SIZE:
                stdscr.addstr(row, column + 1, "-" * CELL_WIDTH, divider_color)

    for board_row in range(BOARD_SIZE):
        for cell_row in range(1, CELL_HEIGHT + 1):
            row = board_top + board_row * (CELL_HEIGHT + 1) + cell_row
            for column_boundary in range(BOARD_SIZE + 1):
                column = board_left + column_boundary * (CELL_WIDTH + 1)
                edge = column_boundary in (0, BOARD_SIZE)
                stdscr.addstr(row, column, "|", white if edge else gray)

    for row in range(BOARD_SIZE):
        for column in range(BOARD_SIZE):
            mark = board[row][column]
            selected = cursor == (row, column) and winner is None and not draw
            winning = winning_cells is not None and (row, column) in winning_cells
            if winning:
                color = curses.color_pair(
                    4 if flash_winning_cells else PLAYER_COLORS[mark]
                )
                selected = True
            else:
                color = (
                    curses.color_pair(PLAYER_COLORS[mark])
                    if mark
                    else curses.A_NORMAL
                )
            attributes = color | (curses.A_REVERSE if selected else curses.A_NORMAL)
            cell_x = board_left + column * (CELL_WIDTH + 1) + 1
            cell_y = board_top + row * (CELL_HEIGHT + 1) + 1
            for cell_row in range(CELL_HEIGHT):
                stdscr.addstr(cell_y + cell_row, cell_x, " " * CELL_WIDTH, attributes)
            if mark is not None:
                stdscr.addstr(
                    cell_y + CELL_HEIGHT // 2,
                    cell_x + (CELL_WIDTH - len(mark)) // 2,
                    mark,
                    attributes,
                )

    if winner is not None:
        message = f"{winner} wins!"
    elif draw:
        message = "Draw!"
    else:
        message = f"{current_player}'s turn"
    message_x = max(0, (columns - len(message)) // 2)
    stdscr.addnstr(
        rows - 2,
        message_x,
        message,
        max(0, columns - message_x),
        white,
    )
    stdscr.refresh()


def _run(stdscr: curses.window) -> int:
    rows, columns = stdscr.getmaxyx()
    if rows < MIN_ROWS or columns < MIN_COLUMNS:
        return SIZE_EXIT

    stdscr.keypad(True)
    stdscr.timeout(50)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
    gray_color = 244 if getattr(curses, "COLORS", 0) >= 256 else curses.COLOR_WHITE
    curses.init_pair(6, gray_color, curses.COLOR_BLACK)
    board = _new_board()
    player_index = 0
    cursor = (0, 0)
    winner = None
    draw = False
    winning_cells = None
    flash_winning_cells = True
    next_winner_toggle = None

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
            PLAYERS[player_index],
            cursor,
            winner,
            draw,
            winning_cells,
            flash_winning_cells if winner is not None else False,
        )

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            return RESIZE_EXIT
        if key in (ord("e"), ord("E")):
            return 0
        if key in (ord("n"), ord("N")):
            board = _new_board()
            player_index = 0
            cursor = (0, 0)
            winner = None
            draw = False
            winning_cells = None
            flash_winning_cells = True
            next_winner_toggle = None
            continue
        if winner is not None or draw:
            continue

        row, column = cursor
        if key == curses.KEY_UP:
            cursor = (max(0, row - 1), column)
        elif key == curses.KEY_DOWN:
            cursor = (min(BOARD_SIZE - 1, row + 1), column)
        elif key == curses.KEY_LEFT:
            cursor = (row, max(0, column - 1))
        elif key == curses.KEY_RIGHT:
            cursor = (row, min(BOARD_SIZE - 1, column + 1))
        elif key in (curses.KEY_ENTER, 10, 13, ord(" ")) and board[row][column] is None:
            board[row][column] = PLAYERS[player_index]
            winning_cells = _winning_cells(board)
            winner = (
                board[winning_cells[0][0]][winning_cells[0][1]]
                if winning_cells is not None
                else None
            )
            draw = winner is None and all(
                cell is not None for line in board for cell in line
            )
            if winner is not None:
                flash_winning_cells = True
                next_winner_toggle = time.monotonic() + WIN_FLASH_INTERVAL_MS / 1000
            elif not draw:
                player_index = 1 - player_index


def main() -> int:
    return run_game(_run, SIZE_MESSAGE, SIZE_EXIT)


def _gray_color() -> int:
    if getattr(curses, "COLORS", 0) >= 256:
        return curses.color_pair(6)
    return curses.color_pair(6) | curses.A_DIM


if __name__ == "__main__":
    raise SystemExit(main())
