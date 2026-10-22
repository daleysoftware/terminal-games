import curses
import unittest
from unittest.mock import Mock, call, patch

from main import (
    BLUE,
    BOARD_COLUMNS,
    BOARD_HEIGHT,
    BOARD_ROWS,
    BOARD_WIDTH,
    CELL_HEIGHT,
    CONTROL_MESSAGE,
    DROP_INTERVAL_MS,
    RED,
    RESIZE_EXIT,
    SIZE_EXIT,
    _animate_drop,
    _draw_screen,
    _empty_board,
    _find_winning_cells,
    _landing_row,
    _run,
)


class MainTest(unittest.TestCase):
    def test_draws_centered_board_with_white_perimeter_and_gray_dividers(self) -> None:
        window = Mock()
        rows, columns = 23, 42
        board_left = (columns - BOARD_WIDTH) // 2
        board_top = max(CELL_HEIGHT + 1, (rows - BOARD_HEIGHT) // 2)

        with patch("main.curses.COLORS", 256, create=True):
            with patch("main.curses.color_pair", side_effect=lambda pair: pair):
                _draw_screen(window, rows, columns)

        window.addstr.assert_has_calls(
            [
                call(board_top, board_left, "+", 5),
                call(board_top, board_left + 1, "----", 5),
                call(board_top + 3, board_left + 1, "----", 6),
                call(board_top + 3, board_left + 5, "+", 6),
                call(board_top + 1, board_left + 5, "|", 6),
                call(board_top + BOARD_HEIGHT - 1, board_left, "+", 5),
            ],
            any_order=True,
        )
        window.addnstr.assert_called_once_with(0, 0, CONTROL_MESSAGE, columns, 5)
        window.refresh.assert_called_once()

    def test_draws_team_cell_and_selector_above_selected_column(self) -> None:
        window = Mock()
        board = _empty_board()
        board[BOARD_ROWS - 1][2] = RED
        rows, columns = 23, 42
        board_left = (columns - BOARD_WIDTH) // 2
        board_top = max(CELL_HEIGHT + 1, (rows - BOARD_HEIGHT) // 2)

        with patch("main.curses.COLORS", 256, create=True):
            with patch("main.curses.color_pair", side_effect=lambda pair: pair):
                _draw_screen(window, rows, columns, board, BLUE, 2)

        window.addstr.assert_any_call(
            board_top + (BOARD_ROWS - 1) * 3 + 1,
            board_left + 2 * 5 + 1,
            "    ",
            2 | curses.A_REVERSE,
        )
        window.addstr.assert_any_call(
            board_top - CELL_HEIGHT,
            board_left + 2 * 5 + 1,
            "    ",
            3 | curses.A_REVERSE,
        )
        window.addstr.assert_any_call(
            board_top - 1,
            board_left + 2 * 5 + 1,
            "    ",
            3 | curses.A_REVERSE,
        )
        window.addnstr.assert_called_once_with(
            0, 0, CONTROL_MESSAGE, columns, 5
        )

    def test_landing_row_finds_lowest_empty_cell_or_full_column(self) -> None:
        board = _empty_board()
        self.assertEqual(_landing_row(board, 3), BOARD_ROWS - 1)
        board[BOARD_ROWS - 1][3] = RED
        self.assertEqual(_landing_row(board, 3), BOARD_ROWS - 2)
        for row in range(BOARD_ROWS - 1):
            board[row][3] = BLUE
        self.assertIsNone(_landing_row(board, 3))
        self.assertEqual(len(board[0]), BOARD_COLUMNS)

    def test_finds_horizontal_vertical_and_both_diagonal_wins(self) -> None:
        cases = (
            ([(5, column) for column in range(4)], RED),
            ([(row, 3) for row in range(2, 6)], BLUE),
            ([(row, row - 1) for row in range(2, 6)], RED),
            ([(row, 5 - row) for row in range(2, 6)], BLUE),
        )
        for winning_positions, team in cases:
            with self.subTest(winning_positions=winning_positions):
                board = _empty_board()
                for row, column in winning_positions:
                    board[row][column] = team
                self.assertEqual(
                    set(_find_winning_cells(board)), set(winning_positions)
                )

    def test_no_winner_on_short_or_mixed_sequences(self) -> None:
        board = _empty_board()
        for column in range(3):
            board[BOARD_ROWS - 1][column] = RED
        board[BOARD_ROWS - 1][3] = BLUE
        self.assertIsNone(_find_winning_cells(board))

    def test_draws_winning_cells_in_yellow_and_winner_message_at_bottom(self) -> None:
        window = Mock()
        board = _empty_board()
        winning_cells = tuple((5, column) for column in range(4))
        for row, column in winning_cells:
            board[row][column] = RED
        rows, columns = 23, 42
        board_left = (columns - BOARD_WIDTH) // 2
        board_top = max(CELL_HEIGHT + 1, (rows - BOARD_HEIGHT) // 2)

        with patch("main.curses.COLORS", 256, create=True):
            with patch("main.curses.color_pair", side_effect=lambda pair: pair):
                _draw_screen(
                    window,
                    rows,
                    columns,
                    board,
                    RED,
                    winning_cells=winning_cells,
                    flash_winning_cells=True,
                    winner=RED,
                )

        window.addstr.assert_any_call(
            board_top + 5 * 3 + 1,
            board_left + 1,
            "    ",
            4 | curses.A_REVERSE,
        )
        self.assertEqual(
            window.addnstr.call_args_list[-1].args[:3],
            (rows - 1, (columns - len("Red Wins!")) // 2, "Red Wins!"),
        )

    def test_drop_animation_flashes_each_cell_and_landing_twice(self) -> None:
        window = Mock()
        board = _empty_board()
        with patch("main._draw_animation_frame") as draw_frame, patch(
            "main.curses.napms"
        ) as napms:
            _animate_drop(window, board, RED, 1, 2)

        self.assertEqual(
            [
                (frame.args[4], frame.kwargs["show_piece"])
                for frame in draw_frame.call_args_list
            ],
            [
                (0, True),
                (0, False),
                (1, True),
                (1, False),
                (2, True),
                (2, True),
                (2, False),
                (2, True),
                (2, False),
            ],
        )
        self.assertEqual(napms.call_count, 7)
        napms.assert_called_with(DROP_INTERVAL_MS)

    def test_runner_selects_column_drops_piece_and_changes_team(self) -> None:
        window = Mock()
        window.getmaxyx.return_value = (23, 42)
        window.getch.side_effect = [curses.KEY_RIGHT, ord(" "), ord("e")]
        draw_screen = Mock()
        with patch("main.random.choice", return_value=RED), patch(
            "main._draw_screen", draw_screen
        ), patch("main._animate_drop") as animate_drop, patch(
            "main.curses.start_color"
        ), patch("main.curses.init_pair"), patch(
            "main.curses.color_pair", return_value=1
        ), patch("main.curses.curs_set", return_value=1):
            self.assertEqual(_run(window), 0)

        animate_drop.assert_called_once()
        board, team, column, landing_row = animate_drop.call_args.args[1:]
        self.assertEqual((team, column, landing_row), (RED, 1, BOARD_ROWS - 1))
        self.assertIs(board[BOARD_ROWS - 1][1], RED)
        self.assertEqual(draw_screen.call_args_list[-1].args[4], BLUE)
        self.assertEqual(draw_screen.call_args_list[-1].args[5], 0)

    def test_full_column_beeps_without_dropping_or_changing_turn(self) -> None:
        window = Mock()
        window.getmaxyx.return_value = (23, 42)
        window.getch.side_effect = [ord(" "), ord("e")]
        board = _empty_board()
        for row in range(BOARD_ROWS):
            board[row][0] = RED

        with patch("main.random.choice", return_value=BLUE), patch(
            "main._empty_board", return_value=board
        ), patch("main._draw_screen") as draw_screen, patch(
            "main._animate_drop"
        ) as animate_drop, patch("main.curses.beep") as beep, patch(
            "main.curses.start_color"
        ), patch("main.curses.init_pair"), patch(
            "main.curses.color_pair", return_value=1
        ), patch("main.curses.curs_set", return_value=1):
            self.assertEqual(_run(window), 0)

        beep.assert_called_once_with()
        animate_drop.assert_not_called()
        self.assertEqual(draw_screen.call_args_list[-1].args[4], BLUE)
        self.assertEqual(draw_screen.call_args_list[-1].args[5], 0)

    def test_n_starts_a_new_random_game_after_a_win(self) -> None:
        window = Mock()
        window.getmaxyx.return_value = (23, 42)
        window.getch.side_effect = [ord(" "), ord("n"), ord("e")]
        draw_screen = Mock()
        winning_cells = ((5, 0), (5, 1), (5, 2), (5, 3))

        with patch("main.random.choice", side_effect=(RED, BLUE)) as choose_team, patch(
            "main._draw_screen", draw_screen
        ), patch("main._animate_drop"), patch(
            "main._find_winning_cells", return_value=winning_cells
        ), patch("main.curses.start_color"), patch(
            "main.curses.init_pair"
        ), patch("main.curses.color_pair", return_value=1), patch(
            "main.curses.curs_set", return_value=1
        ):
            self.assertEqual(_run(window), 0)

        self.assertEqual(choose_team.call_count, 2)
        win_screen = draw_screen.call_args_list[1]
        self.assertEqual(win_screen.kwargs["winner"], RED)
        self.assertEqual(win_screen.kwargs["winning_cells"], winning_cells)
        new_game_screen = draw_screen.call_args_list[2]
        self.assertIsNone(new_game_screen.args[3][5][0])
        self.assertEqual(new_game_screen.args[4:6], (BLUE, 0))
        self.assertIsNone(new_game_screen.kwargs["winner"])

    def test_runner_exits_on_lowercase_or_uppercase_e(self) -> None:
        for key in (ord("e"), ord("E")):
            with self.subTest(key=key):
                window = Mock()
                window.getmaxyx.return_value = (23, 42)
                window.getch.return_value = key
                with patch("main.curses.start_color"), patch(
                    "main.curses.init_pair"
                ), patch("main.curses.color_pair", return_value=1), patch(
                    "main.curses.curs_set", return_value=1
                ):
                    self.assertEqual(_run(window), 0)

    def test_runner_returns_resize_and_small_terminal_statuses(self) -> None:
        window = Mock()
        window.getmaxyx.return_value = (23, 42)
        window.getch.return_value = curses.KEY_RESIZE
        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=1):
                with patch("main.curses.curs_set", return_value=1):
                    self.assertEqual(_run(window), RESIZE_EXIT)

        small_window = Mock()
        small_window.getmaxyx.return_value = (20, 37)
        self.assertEqual(_run(small_window), SIZE_EXIT)
        small_window.getch.assert_not_called()

        short_window = Mock()
        short_window.getmaxyx.return_value = (21, 38)
        self.assertEqual(_run(short_window), SIZE_EXIT)
        short_window.getch.assert_not_called()

        almost_tall_enough = Mock()
        almost_tall_enough.getmaxyx.return_value = (22, 38)
        self.assertEqual(_run(almost_tall_enough), SIZE_EXIT)
        almost_tall_enough.getch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
