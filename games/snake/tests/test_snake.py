import unittest
from unittest.mock import Mock, patch

from main import _draw_screen, _new_apple


class SnakeTest(unittest.TestCase):
    def test_apple_uses_an_empty_interior_cell(self) -> None:
        rng = Mock()
        rng.choice.side_effect = lambda cells: cells[0]
        snake = [(4, 4), (4, 3)]

        apple = _new_apple(10, 20, snake, rng)

        self.assertEqual(apple, (3, 2))
        self.assertNotIn(apple, snake)

    def test_renderer_draws_border_body_head_and_apple_as_logical_cells(self) -> None:
        window = Mock()
        window.getmaxyx.return_value = (10, 20)
        snake = [(4, 4), (4, 3)]

        with patch("main.curses.color_pair", side_effect=lambda pair: pair):
            _draw_screen(window, 10, 20, snake, (5, 5), False, False, 1)

        window.addstr.assert_any_call(4, 8, "  ", 3)
        window.addstr.assert_any_call(4, 6, "  ", 4)
        window.addstr.assert_any_call(5, 10, "  ", 6)
        self.assertTrue(any(call.args[3] == 2 for call in window.addstr.call_args_list))


if __name__ == "__main__":
    unittest.main()
