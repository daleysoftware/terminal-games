import curses
import unittest
from unittest.mock import Mock, call, patch

from main import (
    BALL_TICK_SECONDS,
    COMPUTER_BEHAVIOR,
    COMPUTER_BEHAVIOR_PREDICT_INTERCEPT,
    COMPUTER_BEHAVIOR_SHORT_HORIZON,
    COMPUTER_BEHAVIOR_TRACK_CURRENT_ROW,
    COMPUTER_HYBRID_HORIZON_RATIO,
    MIN_BALL_TICK_SECONDS,
    DIRECTIONS,
    RESIZE_EXIT,
    SIZE_EXIT,
    Ball,
    _advance_ball,
    _computer_target_y,
    _draw_ball,
    _hybrid_horizon_ticks,
    _move_computer_paddle,
    _move_paddle,
    _new_ball,
    _paddle_height,
    _project_ball_y,
    _predict_ball_y,
    _run,
)


class PongTest(unittest.TestCase):
    def test_runner_draws_grid_and_redraws_on_new_game(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (11, 18)
        stdscr.getch.side_effect = [curses.KEY_DOWN, ord("n"), ord("e")]
        with patch("main.curses.start_color") as start_color:
            with patch("main.curses.init_pair") as init_pair:
                with patch("main.curses.color_pair", side_effect=lambda pair: pair):
                    with patch("main.curses.curs_set", return_value=1) as cursor_set:
                        with patch("main.time.monotonic", return_value=0.0):
                            self.assertEqual(_run(stdscr), 0)

        start_color.assert_called_once_with()
        self.assertEqual(init_pair.call_args_list, [
            call(1, curses.COLOR_BLACK, curses.COLOR_BLACK),
            call(2, curses.COLOR_BLACK, curses.COLOR_WHITE),
            call(3, curses.COLOR_BLACK, curses.COLOR_BLUE),
            call(4, curses.COLOR_BLACK, curses.COLOR_RED),
            call(5, curses.COLOR_WHITE, curses.COLOR_BLACK),
            call(6, curses.COLOR_BLACK, curses.COLOR_YELLOW),
        ])
        stdscr.bkgd.assert_called_once_with(" ", 1)
        self.assertEqual(stdscr.erase.call_count, 3)
        self.assertEqual(stdscr.refresh.call_count, 9)
        self.assertIn(call(2, 2, "  ", 2), stdscr.addstr.call_args_list)
        self.assertIn(call(3, 8, "  ", 1), stdscr.addstr.call_args_list)
        stdscr.addnstr.assert_any_call(
            0, 0, "Arrows: move; N: new game; E: exit", 18, 5
        )
        self.assertIn(call(3, 4, "  ", 3), stdscr.addstr.call_args_list)
        self.assertIn(call(4, 4, "  ", 3), stdscr.addstr.call_args_list)
        self.assertIn(call(3, 12, "  ", 4), stdscr.addstr.call_args_list)
        cursor_set.assert_has_calls([call(0), call(1)])

    def test_paddle_height_is_ten_percent_rounded_up_with_four_cell_minimum(self) -> None:
        self.assertEqual(_paddle_height(2), 2)
        self.assertEqual(_paddle_height(3), 3)
        self.assertEqual(_paddle_height(20), 4)
        self.assertEqual(_paddle_height(21), 4)
        self.assertEqual(_paddle_height(31), 4)
        self.assertEqual(_paddle_height(41), 5)

    def test_player_movement_is_one_cell_and_clamped_to_surface(self) -> None:
        self.assertEqual(_move_paddle(4, -1, 2, 9, 2), 3)
        self.assertEqual(_move_paddle(2, -1, 2, 9, 2), 2)
        self.assertEqual(_move_paddle(8, 1, 2, 9, 2), 8)
        self.assertEqual(_move_paddle(7, 1, 2, 9, 2), 8)

    def test_computer_predicts_ball_row_with_wall_reflections(self) -> None:
        self.assertEqual(_predict_ball_y(Ball(4, 4, 1, 1), 7, 2, 8), 7)
        self.assertEqual(_predict_ball_y(Ball(4, 7, 1, 1), 7, 2, 8), 6)
        self.assertEqual(_predict_ball_y(Ball(4, 4, 1, -1), 3, 2, 8), 4)
        self.assertEqual(_project_ball_y(Ball(4, 7, 1, 1), 3, 2, 8), 6)

    def test_computer_behavior_selector_supports_three_intelligence_layers(self) -> None:
        ball = Ball(8, 3, 1, 1)
        self.assertEqual(COMPUTER_BEHAVIOR, COMPUTER_BEHAVIOR_SHORT_HORIZON)
        self.assertEqual(COMPUTER_HYBRID_HORIZON_RATIO, 0.2)
        self.assertEqual(_hybrid_horizon_ticks(15), 3)
        self.assertEqual(_hybrid_horizon_ticks(35), 7)
        self.assertEqual(
            _computer_target_y(COMPUTER_BEHAVIOR_TRACK_CURRENT_ROW, ball, 12, 3, 8, 10),
            3,
        )
        self.assertEqual(
            _computer_target_y(COMPUTER_BEHAVIOR_PREDICT_INTERCEPT, ball, 12, 3, 8, 10),
            7,
        )
        longer_ball = Ball(8, 3, 1, 1)
        self.assertEqual(
            _computer_target_y(COMPUTER_BEHAVIOR_SHORT_HORIZON, longer_ball, 19, 3, 8, 17),
            7,
        )
        self.assertEqual(
            _computer_target_y(COMPUTER_BEHAVIOR_PREDICT_INTERCEPT, longer_ball, 19, 3, 8, 17),
            4,
        )
        with self.assertRaises(ValueError):
            _computer_target_y("unknown", ball, 12, 3, 8, 10)

    def test_computer_moves_one_cell_toward_predicted_row_and_stays_in_bounds(self) -> None:
        self.assertEqual(_move_computer_paddle(4, 3, 2, 9, 2), 3)
        self.assertEqual(_move_computer_paddle(4, 6, 2, 9, 2), 5)
        self.assertEqual(_move_computer_paddle(4, 5, 2, 9, 2), 4)
        self.assertEqual(_move_computer_paddle(2, 1, 2, 9, 2), 2)
        self.assertEqual(_move_computer_paddle(8, 10, 2, 9, 2), 8)
        self.assertEqual(_move_computer_paddle(4, 8, 2, 9, 3, 2), 6)
        self.assertEqual(_move_computer_paddle(6, 2, 2, 9, 3, 2), 4)

    def test_ball_starts_in_center_with_random_allowed_direction(self) -> None:
        rng = Mock()
        rng.choice.return_value = (1, -1)
        ball = _new_ball(10, 3, 12, rng)

        self.assertEqual((ball.x, ball.y, ball.dx, ball.dy), (5, 7, 1, -1))
        self.assertEqual(len(DIRECTIONS), 4)
        self.assertEqual(set(DIRECTIONS), {
            (-1, -1), (-1, 1), (1, -1), (1, 1)
        })
        rng.choice.assert_called_once_with(DIRECTIONS)
        self.assertEqual(BALL_TICK_SECONDS, 0.15)

    def test_ball_reflects_off_top_and_bottom_walls(self) -> None:
        ball = Ball(5, 3, 1, -1)
        _advance_ball(ball, 3, 7, 2, 10, 5, 5, 2)
        self.assertEqual((ball.x, ball.y, ball.dx, ball.dy), (6, 4, 1, 1))
        self.assertEqual(ball.tick_seconds, BALL_TICK_SECONDS)

        ball = Ball(5, 7, 1, 1)
        _advance_ball(ball, 3, 7, 2, 10, 5, 5, 2)
        self.assertEqual((ball.x, ball.y, ball.dx, ball.dy), (6, 6, 1, -1))

    def test_ball_bounces_from_player_and_computer_paddles(self) -> None:
        player_hit = Ball(3, 4, -1, 0)
        _advance_ball(player_hit, 3, 8, 2, 10, 3, 5, 2)
        self.assertEqual((player_hit.x, player_hit.y, player_hit.dx), (4, 4, 1))
        self.assertEqual(player_hit.tick_seconds, BALL_TICK_SECONDS * 0.95)

        computer_hit = Ball(9, 5, 1, 0)
        _advance_ball(computer_hit, 3, 8, 2, 10, 3, 5, 2)
        self.assertEqual((computer_hit.x, computer_hit.y, computer_hit.dx), (8, 5, -1))
        self.assertEqual(computer_hit.tick_seconds, BALL_TICK_SECONDS * 0.95)

    def test_ball_speedup_has_a_floor_and_new_ball_resets_speed(self) -> None:
        ball = Ball(3, 4, -1, 0, tick_seconds=MIN_BALL_TICK_SECONDS)
        _advance_ball(ball, 3, 7, 2, 8, 3, 4, 2)
        self.assertEqual(ball.tick_seconds, MIN_BALL_TICK_SECONDS)

        rng = Mock()
        rng.choice.return_value = (1, 1)
        restarted_ball = _new_ball(10, 3, 12, rng)
        self.assertEqual(restarted_ball.tick_seconds, BALL_TICK_SECONDS)

    def test_ball_miss_ends_round_at_horizontal_edge(self) -> None:
        ball = Ball(3, 3, -1, 0)
        original_tick_seconds = ball.tick_seconds
        _advance_ball(ball, 3, 8, 2, 10, 4, 5, 2)
        self.assertFalse(ball.game_over)
        self.assertEqual(ball.x, 2)

        _advance_ball(ball, 3, 8, 2, 10, 4, 5, 2)
        self.assertTrue(ball.game_over)
        self.assertEqual(ball.x, 2)
        self.assertEqual(ball.tick_seconds, original_tick_seconds)
        self.assertEqual(ball.winner, "Computer")

        frozen_position = (ball.x, ball.y, ball.dx, ball.dy)
        _advance_ball(ball, 3, 8, 2, 10, 4, 5, 2)
        self.assertEqual((ball.x, ball.y, ball.dx, ball.dy), frozen_position)

        right_miss = Ball(9, 3, 1, 0)
        _advance_ball(right_miss, 3, 8, 2, 10, 3, 4, 2)
        _advance_ball(right_miss, 3, 8, 2, 10, 3, 4, 2)
        self.assertTrue(right_miss.game_over)
        self.assertEqual(right_miss.winner, "Player")

    def test_ball_renderer_uses_yellow_and_shows_game_over_message(self) -> None:
        stdscr = Mock()
        with patch("main.curses.color_pair", side_effect=lambda pair: pair):
            _draw_ball(stdscr, Ball(4, 3, 1, 0), 10, 30, 6, 5)
            stdscr.addstr.assert_called_once_with(3, 8, "  ", 6)

            stdscr.reset_mock()
            winning_ball = Ball(4, 3, 1, 0, game_over=True, winner="Player")
            _draw_ball(stdscr, winning_ball, 10, 30, 6, 5)
            self.assertEqual(
                stdscr.addnstr.call_args_list[0], call(9, 0, "You win! ", 30, 5)
            )
            self.assertEqual(
                stdscr.addnstr.call_args_list[1],
                call(9, len("You win! "), "🎉", 30 - len("You win! "), 5),
            )
            stdscr.addstr.assert_called_once_with(3, 8, "  ", 6)

            winning_ball.flash_visible = False
            stdscr.reset_mock()
            _draw_ball(stdscr, winning_ball, 10, 30, 6, 5)
            stdscr.addstr.assert_not_called()
            stdscr.addnstr.assert_called_once_with(
                9, 0, "You win! ", 30, 5
            )

            computer_win = Ball(4, 3, 1, 0, game_over=True, winner="Computer")
            stdscr.reset_mock()
            _draw_ball(stdscr, computer_win, 10, 30, 6, 5)
            stdscr.addnstr.assert_called_once_with(9, 0, "Computer wins!", 30, 5)
            self.assertEqual(stdscr.addnstr.call_count, 1)

    def test_runner_returns_resize_status(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (9, 18)
        stdscr.getch.return_value = curses.KEY_RESIZE
        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=7):
                with patch("main.curses.curs_set", return_value=1):
                    self.assertEqual(_run(stdscr), RESIZE_EXIT)

    def test_runner_advances_ball_on_fixed_tick(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (9, 18)
        stdscr.getch.side_effect = [-1, ord("e")]
        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=7):
                with patch("main.curses.curs_set", return_value=1):
                    with patch("main.time.monotonic", side_effect=[0.0, 0.15]):
                        with patch("main._advance_ball") as advance_ball:
                            self.assertEqual(_run(stdscr), 0)

        advance_ball.assert_called_once()

    def test_runner_moves_tracking_computer_every_second_tick_when_approaching(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (12, 30)
        stdscr.getch.side_effect = [-1, -1, ord("e")]
        ball = Ball(8, 8, 1, 1)
        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=7):
                with patch("main.curses.curs_set", return_value=1):
                    with patch("main.time.monotonic", side_effect=[0.0, 0.15, 0.30]):
                        with patch("main.COMPUTER_BEHAVIOR", COMPUTER_BEHAVIOR_TRACK_CURRENT_ROW):
                            with patch("main._new_ball", return_value=ball):
                                with patch("main._advance_ball") as advance_ball:
                                    self.assertEqual(_run(stdscr), 0)

        computer_tops = [call.args[6] for call in advance_ball.call_args_list]
        self.assertEqual(computer_tops, [4, 5])

    def test_runner_uses_ratio_based_hybrid_target(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (20, 40)
        stdscr.getch.side_effect = [-1, -1, ord("e")]
        ball = Ball(8, 10, 1, 1)
        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=7):
                with patch("main.curses.curs_set", return_value=1):
                    with patch("main.time.monotonic", side_effect=[0.0, 0.15, 0.30]):
                        with patch("main._new_ball", return_value=ball):
                            with patch("main._advance_ball") as advance_ball:
                                self.assertEqual(_run(stdscr), 0)

        computer_tops = [call.args[6] for call in advance_ball.call_args_list]
        self.assertEqual(computer_tops, [8, 9])

    def test_runner_keeps_predictive_computer_on_two_tick_interval(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (12, 30)
        stdscr.getch.side_effect = [-1, -1, ord("e")]
        ball = Ball(8, 8, 1, 1)
        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=7):
                with patch("main.curses.curs_set", return_value=1):
                    with patch("main.time.monotonic", side_effect=[0.0, 0.15, 0.30]):
                        with patch("main.COMPUTER_BEHAVIOR", COMPUTER_BEHAVIOR_PREDICT_INTERCEPT):
                            with patch("main._new_ball", return_value=ball):
                                with patch("main._advance_ball") as advance_ball:
                                    self.assertEqual(_run(stdscr), 0)

        computer_tops = [call.args[6] for call in advance_ball.call_args_list]
        self.assertEqual(computer_tops, [4, 4])

    def test_new_game_resets_a_missed_round(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (9, 18)
        stdscr.getch.side_effect = [-1, ord("n"), ord("e")]
        serves = [Ball(4, 3, 1, 0), Ball(4, 3, -1, 0)]

        def miss_ball(ball, *args):
            ball.game_over = True
            ball.winner = "Computer"

        with patch("main.curses.start_color"), patch("main.curses.init_pair"):
            with patch("main.curses.color_pair", return_value=7):
                with patch("main.curses.curs_set", return_value=1):
                    with patch("main.time.monotonic", side_effect=[0.0, 0.15, 0.15]):
                        with patch("main._new_ball", side_effect=serves) as new_ball:
                            with patch("main._advance_ball", side_effect=miss_ball):
                                self.assertEqual(_run(stdscr), 0)

        self.assertEqual(new_ball.call_count, 2)
        self.assertGreaterEqual(stdscr.addnstr.call_count, 2)

    def test_runner_exits_when_terminal_is_too_small(self) -> None:
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (7, 14)
        self.assertEqual(_run(stdscr), SIZE_EXIT)
        stdscr.erase.assert_not_called()
        stdscr.getch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
