import curses
import unittest
from unittest.mock import Mock, call, patch

from main import (
    CONTROL_MESSAGE,
    PLAYERS,
    _draw_screen,
    _new_board,
    _run,
    _winner,
    _winning_cells,
)


class TicTacToeTest(unittest.TestCase):
    def test_draws_connect_four_style_grid_and_controls(self) -> None:
        window = Mock()

        with patch("main.curses.color_pair", side_effect=lambda pair: pair):
            _draw_screen(window, 20, 80, _new_board(), "X", (0, 0))

        self.assertTrue(
            any(call.args[2] == "+" for call in window.addstr.call_args_list)
        )
        self.assertTrue(
            any(call.args[2] == "|" for call in window.addstr.call_args_list)
        )
        self.assertTrue(
            any(call.args[2] == "----" for call in window.addstr.call_args_list)
        )
        self.assertTrue(
            any(
                call.args[2] == "    " and call.args[3] & curses.A_REVERSE
                for call in window.addstr.call_args_list
            )
        )
        window.addnstr.assert_any_call(
            0, 0, CONTROL_MESSAGE, 80, 5
        )
        window.refresh.assert_called_once()

    def test_winner_detects_each_row_column_and_diagonal(self) -> None:
        cases = (
            ([["X", "X", "X"], [None, "O", None], ["O", None, "O"]], "X"),
            ([["O", "X", None], ["O", "X", None], ["O", None, "X"]], "O"),
            ([["X", None, "O"], [None, "X", "O"], ["O", None, "X"]], "X"),
            ([["O", None, "X"], [None, "X", "O"], ["X", None, "O"]], "X"),
        )
        for board, expected in cases:
            with self.subTest(board=board):
                self.assertEqual(_winner(board), expected)

    def test_winner_returns_none_without_a_three_in_a_row(self) -> None:
        board = [["X", "O", "X"], ["X", "O", "O"], ["O", "X", "X"]]
        self.assertIsNone(_winner(board))

    def test_winning_cells_returns_completed_line_coordinates(self) -> None:
        board = [["X", "X", "X"], [None, "O", None], ["O", None, "O"]]
        self.assertEqual(_winning_cells(board), ((0, 0), (0, 1), (0, 2)))

    def test_draws_winning_cells_in_yellow_during_flash_phase(self) -> None:
        window = Mock()
        board = [["X", "X", "X"], [None, "O", None], ["O", None, "O"]]

        with patch("main.curses.color_pair", side_effect=lambda pair: pair):
            _draw_screen(
                window,
                20,
                80,
                board,
                "O",
                (2, 2),
                winner="X",
                winning_cells=((0, 0), (0, 1), (0, 2)),
                flash_winning_cells=True,
            )

        yellow_cells = [
            call
            for call in window.addstr.call_args_list
            if call.args[2] == "    "
            and call.args[3] == (4 | curses.A_REVERSE)
        ]
        self.assertEqual(len(yellow_cells), 2 * 3)

    def test_winning_cells_return_to_winner_color_between_flashes(self) -> None:
        cases = (
            ([['X', 'X', 'X'], [None, 'O', None], [None, None, 'O']], 'X', 2),
            ([['O', None, 'X'], ['O', 'X', None], ['O', None, 'X']], 'O', 3),
        )
        for board, winner, color_pair in cases:
            with self.subTest(winner=winner):
                window = Mock()
                cells = _winning_cells(board)
                with patch("main.curses.color_pair", side_effect=lambda pair: pair):
                    _draw_screen(
                        window,
                        20,
                        80,
                        board,
                        winner,
                        (2, 2),
                        winner=winner,
                        winning_cells=cells,
                        flash_winning_cells=False,
                    )

                for row, column in cells:
                    cell_y = 5 + row * 3 + 1
                    cell_x = 32 + column * 5 + 1
                    self.assertIn(
                        call(
                            cell_y,
                            cell_x,
                            " " * 4,
                            color_pair | curses.A_REVERSE,
                        ),
                        window.addstr.call_args_list,
                    )

    def test_win_starts_flash_and_new_game_clears_winning_cells(self) -> None:
        window = Mock()
        window.getmaxyx.return_value = (20, 40)
        window.getch.side_effect = [
            10,
            curses.KEY_DOWN,
            10,
            curses.KEY_UP,
            curses.KEY_RIGHT,
            10,
            curses.KEY_DOWN,
            10,
            curses.KEY_UP,
            curses.KEY_RIGHT,
            10,
            ord("n"),
            ord("e"),
        ]

        with patch("main._draw_screen") as draw_screen, patch(
            "main.curses.start_color"
        ), patch("main.curses.init_pair"), patch(
            "main.time.monotonic", return_value=1
        ), patch("main.random.choice", return_value=0):
            self.assertEqual(_run(window), 0)

        win_frame = next(
            call for call in draw_screen.call_args_list if call.args[6] == "X"
        )
        self.assertEqual(win_frame.args[8], ((0, 0), (0, 1), (0, 2)))
        self.assertTrue(win_frame.args[9])
        restarted = draw_screen.call_args_list[-1]
        self.assertIsNone(restarted.args[6])
        self.assertIsNone(restarted.args[8])

    def test_runner_places_marks_switches_turns_and_exits(self) -> None:
        window = Mock()
        window.getmaxyx.return_value = (20, 40)
        window.getch.side_effect = [10, curses.KEY_RIGHT, ord(" "), ord("e")]

        with patch("main._draw_screen") as draw_screen, patch(
            "main.curses.start_color"
        ), patch("main.curses.init_pair"), patch("main.random.choice", return_value=0):
            self.assertEqual(_run(window), 0)

        self.assertEqual(draw_screen.call_args_list[1].args[3][0][0], "X")
        self.assertEqual(draw_screen.call_args_list[3].args[3][0][1], "O")
        self.assertEqual(draw_screen.call_args_list[3].args[4], "X")
        self.assertEqual(PLAYERS, ("X", "O"))

    def test_runner_restarts_with_n_and_exits_with_e(self) -> None:
        window = Mock()
        window.getmaxyx.return_value = (20, 40)
        window.getch.side_effect = [10, ord("n"), ord("e")]

        with patch("main._draw_screen") as draw_screen, patch(
            "main.curses.start_color"
        ), patch("main.curses.init_pair"), patch(
            "main.random.choice", side_effect=[1, 0]
        ):
            self.assertEqual(_run(window), 0)

        self.assertEqual(draw_screen.call_args_list[0].args[4], "O")
        restarted = draw_screen.call_args_list[2]
        self.assertEqual(restarted.args[3], _new_board())
        self.assertEqual(restarted.args[4], "X")


if __name__ == "__main__":
    unittest.main()
