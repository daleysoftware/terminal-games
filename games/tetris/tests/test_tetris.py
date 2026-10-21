import unittest
from unittest.mock import Mock, patch

from main import _collides, _draw_piece, _rotate_clockwise


class TetrisTest(unittest.TestCase):
    def test_rotation_and_collision_use_board_coordinates(self) -> None:
        cells = ((0, 0), (1, 0), (1, 1))
        self.assertEqual(_rotate_clockwise(cells), ((0, 0), (0, 1), (1, 0)))
        self.assertFalse(_collides(cells, 0, 0, {}))
        self.assertTrue(_collides(cells, 0, 0, {(1, 1): "O"}))
        self.assertTrue(_collides(cells, 0, -1, {}))

    def test_piece_renderer_maps_board_columns_to_terminal_columns(self) -> None:
        window = Mock()
        piece = ("T", ((0, 1), (1, 0), (1, 1), (1, 2)), 3, 4)

        with patch("main.curses.color_pair", side_effect=lambda pair: pair):
            _draw_piece(window, piece, 5, 6, 8)

        window.addstr.assert_any_call(9, 20, "  ", 8)
        window.addstr.assert_any_call(10, 18, "  ", 8)
        self.assertEqual(window.addstr.call_count, 4)


if __name__ == "__main__":
    unittest.main()
