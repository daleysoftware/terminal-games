import unittest
from unittest.mock import Mock, patch

from terminal_games.rendering import draw_cell, draw_rectangle
from terminal_games.runtime import RESIZE_EXIT, run_game


class RenderingTest(unittest.TestCase):
    def test_draw_cell_maps_a_logical_column_to_two_terminal_columns(self) -> None:
        window = Mock()

        draw_cell(window, 4, 7, 3)

        window.addstr.assert_called_once_with(4, 14, "  ", 3)

    def test_rectangle_draws_inclusive_edges_without_repeating_corners(self) -> None:
        window = Mock()

        draw_rectangle(window, 2, 3, 4, 5, 9)

        self.assertEqual(
            window.addstr.call_args_list,
            [
                unittest.mock.call(3, 4, "  ", 9),
                unittest.mock.call(5, 4, "  ", 9),
                unittest.mock.call(3, 6, "  ", 9),
                unittest.mock.call(5, 6, "  ", 9),
                unittest.mock.call(3, 8, "  ", 9),
                unittest.mock.call(5, 8, "  ", 9),
                unittest.mock.call(4, 4, "  ", 9),
                unittest.mock.call(4, 8, "  ", 9),
            ],
        )


class RuntimeTest(unittest.TestCase):
    def test_non_terminal_run_skips_curses(self) -> None:
        with patch("terminal_games.runtime.sys.stdin.isatty", return_value=False):
            with patch("terminal_games.runtime.curses.wrapper") as wrapper:
                self.assertEqual(run_game(Mock(), "Too small"), 0)

        wrapper.assert_not_called()

    def test_resize_and_size_results_are_reported(self) -> None:
        with patch("terminal_games.runtime.sys.stdin.isatty", return_value=True), patch(
            "terminal_games.runtime.sys.stdout.isatty", return_value=True
        ), patch("terminal_games.runtime.curses.wrapper", return_value=RESIZE_EXIT), patch(
            "builtins.print"
        ) as print_message:
            self.assertEqual(run_game(Mock(), "Too small"), 0)
            print_message.assert_called_once()

        with patch("terminal_games.runtime.sys.stdin.isatty", return_value=True), patch(
            "terminal_games.runtime.sys.stdout.isatty", return_value=True
        ), patch("terminal_games.runtime.curses.wrapper", return_value=1), patch(
            "builtins.print"
        ) as print_message:
            self.assertEqual(run_game(Mock(), "Too small", 1), 1)
            print_message.assert_called_once()

    def test_keyboard_interrupt_returns_success(self) -> None:
        with patch("terminal_games.runtime.sys.stdin.isatty", return_value=True), patch(
            "terminal_games.runtime.sys.stdout.isatty", return_value=True
        ), patch(
            "terminal_games.runtime.curses.wrapper", side_effect=KeyboardInterrupt
        ):
            self.assertEqual(run_game(Mock(), "Too small"), 0)


if __name__ == "__main__":
    unittest.main()
