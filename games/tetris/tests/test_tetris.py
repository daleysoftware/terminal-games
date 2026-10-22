import curses
import unittest
from unittest.mock import Mock, patch

from main import (
    BOARD_HEIGHT,
    BOARD_WIDTH,
    RESIZE_EXIT,
    TETROMINO_SHAPES,
    _collides,
    _draw_grid,
    _draw_piece,
    _layout,
    _rotate_clockwise,
    _run,
)


class TetrisTest(unittest.TestCase):
    def _run_with_keys(self, keys, times, collides=False):
        window = Mock()
        window.getmaxyx.return_value = (30, 54)
        window.getch.side_effect = keys
        drawn_frames = []

        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=1):
                with patch("main.curses.curs_set", return_value=1):
                    with patch("main.random.choice", side_effect=lambda items: items[0]):
                        with patch("main.time.monotonic", side_effect=times):
                            with patch(
                                "main._draw_grid",
                                side_effect=lambda *args, **kwargs: drawn_frames.append(
                                    (args, kwargs)
                                ),
                            ):
                                with patch("main._collides", return_value=collides):
                                    result = _run(window)

        return result, window, drawn_frames

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

    def test_paused_message_is_centered_over_the_visible_active_piece(self) -> None:
        window = Mock()
        rows, columns = 30, 54
        active = ("O", TETROMINO_SHAPES["O"], 0, 3)
        next_piece = ("I", TETROMINO_SHAPES["I"])
        inner_left, inner_top, _, _, _ = _layout(rows, columns)
        board_left = inner_left + 1
        board_top = inner_top + 1
        message_row = board_top + BOARD_HEIGHT // 2
        message_column = board_left * 2 + (BOARD_WIDTH * 2 - len("PAUSED")) // 2

        with patch("main.curses.color_pair", side_effect=lambda pair: pair):
            with patch("main._draw_piece") as draw_piece:
                _draw_grid(
                    window,
                    rows,
                    columns,
                    2,
                    5,
                    {},
                    active,
                    next_piece,
                    False,
                    0,
                    paused=True,
                )

        draw_piece.assert_called_once()
        window.addstr.assert_any_call(
            message_row, message_column, "PAUSED", 5
        )

    def test_pause_freezes_controls_and_preserves_remaining_gravity_delay(self) -> None:
        result, _, frames = self._run_with_keys(
            [
                ord(" "),
                curses.KEY_LEFT,
                ord("r"),
                curses.KEY_DOWN,
                ord(" "),
                -1,
                -1,
                -1,
                ord("e"),
            ],
            [0.0, 0.1, 5.0, 5.3, 5.5, 5.6],
        )

        self.assertEqual(result, 0)
        self.assertEqual(
            [kwargs.get("paused", False) for _, kwargs in frames],
            [False, True, True, True, True, False, False, False, False],
        )
        active_rows = [args[6][2] for args, _ in frames]
        self.assertEqual(active_rows, [0, 0, 0, 0, 0, 0, 0, 1, 1])
        active_columns = [args[6][3] for args, _ in frames]
        self.assertEqual(active_columns, [3] * 9)
        active_shapes = [args[6][1] for args, _ in frames]
        self.assertTrue(all(shape == active_shapes[0] for shape in active_shapes))

    def test_new_game_clears_pause_and_game_over_cannot_be_paused(self) -> None:
        _, _, restart_frames = self._run_with_keys(
            [ord(" "), ord("n"), ord("e")],
            [0.0, 0.1, 1.0],
        )
        self.assertEqual(
            [kwargs.get("paused", False) for _, kwargs in restart_frames],
            [False, True, False],
        )

        _, _, game_over_frames = self._run_with_keys(
            [ord(" "), ord("e")],
            [0.0],
            collides=True,
        )
        self.assertTrue(all(not kwargs.get("paused", False) for _, kwargs in game_over_frames))

    def test_exit_and_resize_still_work_while_paused(self) -> None:
        exit_result, _, _ = self._run_with_keys(
            [ord(" "), ord("e")],
            [0.0, 0.1],
        )
        resize_result, _, _ = self._run_with_keys(
            [ord(" "), curses.KEY_RESIZE],
            [0.0, 0.1],
        )

        self.assertEqual(exit_result, 0)
        self.assertEqual(resize_result, RESIZE_EXIT)


if __name__ == "__main__":
    unittest.main()
