import curses
import unittest
from unittest.mock import Mock, call, patch

from main import RESIZE_EXIT, _run


class PongTest(unittest.TestCase):
    def test_runner_paints_white_and_handles_new_game_and_exit(self) -> None:
        stdscr = Mock()
        stdscr.getch.side_effect = [ord("n"), ord("e")]
        with patch("main.curses.start_color") as start_color:
            with patch("main.curses.init_pair") as init_pair:
                with patch("main.curses.color_pair", return_value=7):
                    with patch("main.curses.curs_set", return_value=1) as cursor_set:
                        self.assertEqual(_run(stdscr), 0)

        start_color.assert_called_once_with()
        init_pair.assert_called_once_with(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        stdscr.bkgd.assert_called_once_with(" ", 7)
        self.assertEqual(stdscr.erase.call_count, 2)
        self.assertEqual(stdscr.refresh.call_count, 2)
        cursor_set.assert_has_calls([call(0), call(1)])

    def test_runner_returns_resize_status(self) -> None:
        stdscr = Mock()
        stdscr.getch.return_value = curses.KEY_RESIZE
        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=7):
                with patch("main.curses.curs_set", return_value=1):
                    self.assertEqual(_run(stdscr), RESIZE_EXIT)


if __name__ == "__main__":
    unittest.main()
