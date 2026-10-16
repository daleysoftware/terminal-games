import curses
import random
import unittest
from collections import deque
from unittest.mock import Mock, call, patch

from main import (
    GameState,
    _draw_game,
    _initialize_colors,
    _player_color,
    _run,
    _underlying_color,
    generate_maze,
)


class MazeTest(unittest.TestCase):
    def test_generated_maze_connects_entrances_at_even_and_odd_sizes(self) -> None:
        for height, width in ((3, 3), (4, 4), (5, 8), (8, 5), (12, 40)):
            for seed in range(5):
                with self.subTest(height=height, width=width, seed=seed):
                    maze, start, end = generate_maze(height, width, random.Random(seed))
                    self.assertEqual(len(maze), height)
                    self.assertTrue(all(len(row) == width for row in maze))
                    self.assertEqual(start[0], height - 1)
                    self.assertEqual(end[0], 0)
                    self.assertEqual(maze[start[0]][start[1]], " ")
                    self.assertEqual(maze[end[0]][end[1]], " ")
                    self.assertEqual(maze[0].count(" "), 1)
                    self.assertEqual(maze[-1].count(" "), 1)

                    visited = {start}
                    queue = deque([start])
                    while queue:
                        row, column = queue.popleft()
                        for next_row, next_column in (
                            (row - 1, column),
                            (row + 1, column),
                            (row, column - 1),
                            (row, column + 1),
                        ):
                            neighbor = (next_row, next_column)
                            if (
                                0 <= next_row < height
                                and 0 <= next_column < width
                                and maze[next_row][next_column] == " "
                                and neighbor not in visited
                            ):
                                visited.add(neighbor)
                                queue.append(neighbor)
                    self.assertIn(end, visited)

    def test_player_moves_through_passages_and_wins_at_exit(self) -> None:
        maze = ["# #", "# #", "# #"]
        start = (3, 1)
        end = (-1, 1)
        state = GameState(maze, start, end, start, 0.0)

        self.assertFalse(state.move((0, -1)))
        self.assertEqual(state.position, start)
        for expected in ((2, 1), (1, 1), (0, 1)):
            self.assertTrue(state.move((-1, 0)))
            self.assertEqual(state.position, expected)
            self.assertIn(expected, state.visited)
        self.assertTrue(state.move((-1, 0)))
        self.assertTrue(state.won)
        self.assertEqual(state.position, end)
        self.assertFalse(state.move((1, 0)))

    def test_player_flashes_on_markers_but_stays_blue_on_orange(self) -> None:
        state = GameState(["# #", "# #", "# #"], (3, 1), (-1, 1), (3, 1), 10.0)
        color_pairs = {"passage": 1, "green": 3, "red": 4, "orange": 5, "blue": 6}

        self.assertEqual(_underlying_color(state, color_pairs), 3)
        self.assertEqual(_player_color(state, color_pairs), 3)
        self.assertFalse(state.update_blink(10.49))
        self.assertFalse(state.blue_phase)
        self.assertTrue(state.update_blink(10.5))
        self.assertTrue(state.blue_phase)
        self.assertEqual(_player_color(state, color_pairs), 6)
        self.assertTrue(state.update_blink(11.0))
        self.assertFalse(state.blue_phase)
        self.assertEqual(_player_color(state, color_pairs), 3)

        self.assertTrue(state.move((-1, 0)))
        self.assertEqual(_underlying_color(state, color_pairs), 5)
        self.assertFalse(state.update_blink(11.1))
        self.assertEqual(_player_color(state, color_pairs), 6)
        self.assertFalse(state.blue_phase)
        self.assertFalse(state.update_blink(12.0))
        self.assertFalse(state.blue_phase)
        self.assertEqual(_player_color(state, color_pairs), 6)

    def test_color_pairs_use_256_color_values_or_basic_fallback(self) -> None:
        with patch("main.curses.start_color"), patch("main.curses.init_pair") as init_pair:
            with patch("main.curses.COLORS", 256, create=True):
                self.assertEqual(_initialize_colors()["orange"], 5)
                self.assertIn(call(5, curses.COLOR_BLACK, 208), init_pair.call_args_list)
                self.assertIn(call(6, curses.COLOR_BLACK, 21), init_pair.call_args_list)

            init_pair.reset_mock()
            with patch("main.curses.COLORS", 8, create=True):
                _initialize_colors()
                self.assertIn(
                    call(5, curses.COLOR_BLACK, curses.COLOR_YELLOW),
                    init_pair.call_args_list,
                )
                self.assertIn(
                    call(6, curses.COLOR_BLACK, curses.COLOR_BLUE),
                    init_pair.call_args_list,
                )

    def test_renderer_places_markers_outside_maze_with_reserved_margins(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (9, 19)
        stdscr.getch.return_value = curses.KEY_RESIZE
        maze = ["# #####", "#   # #", "### # #", "#     #", "##### #"]
        with patch("main.generate_maze", return_value=(maze, (4, 5), (0, 1))):
            with patch("main.curses.start_color"), patch("main.curses.init_pair"):
                with patch("main.curses.color_pair", side_effect=lambda color: color):
                    with patch(
                        "main.curses.curs_set", side_effect=lambda visibility: 1
                    ) as cursor_set:
                        self.assertEqual(_run(stdscr), 0)

        cursor_set.assert_has_calls([call(0), call(1)])
        stdscr.bkgd.assert_called_once_with(" ", 1)
        painted = stdscr.addstr.call_args_list
        self.assertTrue(all(item.args[0] not in (0, 1, 8) for item in painted))
        self.assertTrue(all(2 <= item.args[1] <= 15 for item in painted))
        self.assertTrue(all(item.args[2] == "  " for item in painted))
        self.assertIn(call(2, 4, "  ", 4), painted)
        self.assertIn(call(7, 12, "  ", 3), painted)
        self.assertIn(call(3, 2, "  ", 2), painted)
        stdscr.addnstr.assert_any_call(0, 0, "Arrows: move   N: new maze   E: exit", 19, 7)

    def test_win_renderer_blinks_completion_message_on_bottom_row(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (20, 60)
        state = GameState(["# #", "# #", "# #"], (3, 1), (-1, 1), (-1, 1), 0.0, won=True)
        color_pairs = {
            "passage": 1,
            "wall": 2,
            "green": 3,
            "red": 4,
            "orange": 5,
            "blue": 6,
            "message": 7,
        }
        with patch("main.curses.color_pair", side_effect=lambda color: color):
            _draw_game(stdscr, state, color_pairs)

        stdscr.addnstr.assert_any_call(19, 0, "Maze complete! Woot! ", 60, 7)
        stdscr.addnstr.assert_any_call(19, 21, "🎉", 39, 7)

        state.blue_phase = True
        stdscr.addnstr.reset_mock()
        with patch("main.curses.color_pair", side_effect=lambda color: color):
            _draw_game(stdscr, state, color_pairs)

        stdscr.addnstr.assert_any_call(19, 0, "Maze complete! Woot! ", 60, 7)
        self.assertNotIn(call(19, 21, "🎉", 39, 7), stdscr.addnstr.call_args_list)


if __name__ == "__main__":
    unittest.main()
