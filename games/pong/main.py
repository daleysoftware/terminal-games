import curses
import math
import random
import time
from dataclasses import dataclass
from typing import Optional
from terminal_games.runtime import RESIZE_EXIT, run_game
from terminal_games.rendering import draw_cell, draw_rectangle


SIZE_EXIT = 1
MIN_ROWS = 8
MIN_COLUMNS = 14
SIZE_MESSAGE = "Terminal must be at least 8 rows and 14 columns."
CONTROL_MESSAGE = "Arrows: move; N: new game; E: exit"
BALL_TICK_SECONDS = 0.15
BALL_SPEEDUP_FACTOR = 0.95
MIN_BALL_TICK_SECONDS = 0.05
BALL_FLASH_INTERVAL_SECONDS = 0.5
PLAYER_WIN_MESSAGE = "You win! "
COMPUTER_WIN_MESSAGE = "Computer wins!"
WIN_EMOJI = "🎉"
DIRECTIONS = tuple((dx, dy) for dx in (-1, 1) for dy in (-1, 1))
COMPUTER_BEHAVIOR_TRACK_CURRENT_ROW = "track_current_row"
COMPUTER_BEHAVIOR_PREDICT_INTERCEPT = "predict_intercept"
COMPUTER_BEHAVIOR_SHORT_HORIZON = "short_horizon"
COMPUTER_BEHAVIOR = COMPUTER_BEHAVIOR_SHORT_HORIZON
COMPUTER_HYBRID_HORIZON_RATIO = 0.2
COMPUTER_TARGET_LOSS_TURNS = 5
COMPUTER_MOVE_INTERVAL_TICKS = 2
COMPUTER_PADDLE_STEP = 1


@dataclass
class Ball:
    x: int
    y: int
    dx: int
    dy: int
    game_over: bool = False
    tick_seconds: float = BALL_TICK_SECONDS
    winner: Optional[str] = None
    flash_visible: bool = True


def _new_ball(
    logical_columns: int,
    surface_top: int,
    surface_bottom: int,
    rng: random.Random,
) -> Ball:
    surface_height = surface_bottom - surface_top + 1
    dx, dy = rng.choice(DIRECTIONS)
    return Ball(
        x=logical_columns // 2,
        y=surface_top + (surface_height - 1) // 2,
        dx=dx,
        dy=dy,
    )


def _paddle_height(surface_height: int) -> int:
    return min(surface_height, max(4, math.ceil(surface_height * 0.1)))


def _move_paddle(
    top: int, amount: int, surface_top: int, surface_bottom: int, height: int
) -> int:
    return min(max(top + amount, surface_top), surface_bottom - height + 1)


def _project_ball_y(
    ball: Ball, ticks: int, surface_top: int, surface_bottom: int
) -> int:
    y = ball.y
    dy = ball.dy
    for _ in range(max(0, ticks)):
        next_y = y + dy
        if next_y < surface_top or next_y > surface_bottom:
            dy = -dy
            next_y = y + dy
        y = next_y
    return y


def _hybrid_horizon_ticks(
    horizontal_grid_size: int, ratio: float = COMPUTER_HYBRID_HORIZON_RATIO
) -> int:
    return max(1, math.ceil(horizontal_grid_size * ratio))


def _predict_ball_y(ball: Ball, paddle_x: int, surface_top: int, surface_bottom: int) -> int:
    """Project the ball's row at the right paddle, reflecting off top and bottom."""
    return _project_ball_y(
        ball, paddle_x - ball.x, surface_top, surface_bottom
    )


def _move_computer_paddle(
    computer_top: int,
    predicted_y: int,
    surface_top: int,
    surface_bottom: int,
    height: int,
    max_step: int = 1,
) -> int:
    if predicted_y < computer_top:
        return _move_paddle(
            computer_top, -max_step, surface_top, surface_bottom, height
        )
    if predicted_y >= computer_top + height:
        return _move_paddle(computer_top, max_step, surface_top, surface_bottom, height)
    return computer_top


def _computer_target_y(
    behavior: str,
    ball: Ball,
    paddle_x: int,
    surface_top: int,
    surface_bottom: int,
    horizontal_grid_size: int,
    hybrid_horizon_ticks: Optional[int] = None,
) -> int:
    if behavior == COMPUTER_BEHAVIOR_TRACK_CURRENT_ROW:
        return ball.y
    if behavior == COMPUTER_BEHAVIOR_SHORT_HORIZON:
        return _project_ball_y(
            ball,
            min(
                paddle_x - ball.x,
                hybrid_horizon_ticks
                if hybrid_horizon_ticks is not None
                else _hybrid_horizon_ticks(horizontal_grid_size),
            ),
            surface_top,
            surface_bottom,
        )
    if behavior == COMPUTER_BEHAVIOR_PREDICT_INTERCEPT:
        return _predict_ball_y(ball, paddle_x, surface_top, surface_bottom)
    raise ValueError("Unknown computer behavior: {}".format(behavior))


def _simulate_computer_loss_turn(
    logical_columns: int,
    surface_top: int,
    surface_bottom: int,
    horizon_ticks: int,
    direction: tuple[int, int],
) -> Optional[int]:
    """Return the computer's loss turn, or None if the rally enters a cycle."""
    left_paddle_x = 2
    right_paddle_x = logical_columns - 3
    horizontal_grid_size = right_paddle_x - left_paddle_x
    surface_height = surface_bottom - surface_top + 1
    paddle_height = _paddle_height(surface_height)
    center_top = surface_top + (surface_height - paddle_height) // 2
    ball = Ball(
        logical_columns // 2,
        surface_top + (surface_height - 1) // 2,
        direction[0],
        direction[1],
    )
    computer_top = center_top
    computer_move_ticks = 0
    turns = 0
    seen_states = set()

    while not ball.game_over:
        state = (
            ball.x,
            ball.y,
            ball.dx,
            ball.dy,
            computer_top,
            computer_move_ticks,
        )
        if state in seen_states:
            return None
        seen_states.add(state)

        if ball.dx > 0:
            if ball.x + ball.dx == right_paddle_x:
                turns += 1
            computer_move_ticks += 1
            if computer_move_ticks >= COMPUTER_MOVE_INTERVAL_TICKS:
                target_y = _computer_target_y(
                    COMPUTER_BEHAVIOR_SHORT_HORIZON,
                    ball,
                    right_paddle_x,
                    surface_top,
                    surface_bottom,
                    horizontal_grid_size,
                    horizon_ticks,
                )
                computer_top = _move_computer_paddle(
                    computer_top,
                    target_y,
                    surface_top,
                    surface_bottom,
                    paddle_height,
                    COMPUTER_PADDLE_STEP,
                )
                computer_move_ticks = 0
        else:
            computer_move_ticks = 0

        if ball.dx < 0:
            next_y = _project_ball_y(ball, 1, surface_top, surface_bottom)
            player_top = min(
                max(next_y, surface_top), surface_bottom - paddle_height + 1
            )
        else:
            player_top = center_top

        _advance_ball(
            ball,
            surface_top,
            surface_bottom,
            left_paddle_x,
            right_paddle_x,
            player_top,
            computer_top,
            paddle_height,
        )

    return turns if ball.winner == "Player" else None


def _calibrate_hybrid_horizon(
    logical_columns: int, surface_top: int, surface_bottom: int
) -> int:
    """Select a horizon that targets five computer turns on this playfield."""
    horizontal_grid_size = (logical_columns - 3) - 2
    if horizontal_grid_size <= 1:
        return 1

    directions = DIRECTIONS
    candidates = []
    for horizon_ticks in range(1, horizontal_grid_size + 1):
        loss_turns = [
            _simulate_computer_loss_turn(
                logical_columns,
                surface_top,
                surface_bottom,
                horizon_ticks,
                direction,
            )
            for direction in directions
        ]
        finite_turns = [turn for turn in loss_turns if turn is not None]
        non_loss_count = len(loss_turns) - len(finite_turns)
        average_turn = (
            sum(finite_turns) / len(finite_turns) if finite_turns else math.inf
        )
        candidates.append(
            (non_loss_count, abs(average_turn - COMPUTER_TARGET_LOSS_TURNS), horizon_ticks)
        )

    return min(candidates)[2]


def _advance_ball(
    ball: Ball,
    surface_top: int,
    surface_bottom: int,
    left_paddle_x: int,
    right_paddle_x: int,
    player_top: int,
    computer_top: int,
    paddle_height: int,
) -> None:
    if ball.game_over:
        return

    next_y = ball.y + ball.dy
    if next_y < surface_top or next_y > surface_bottom:
        ball.dy = -ball.dy
        next_y = ball.y + ball.dy

    next_x = ball.x + ball.dx
    if next_x < left_paddle_x or next_x > right_paddle_x:
        ball.game_over = True
        ball.winner = "Computer" if next_x < left_paddle_x else "Player"
        return

    if next_x == left_paddle_x and player_top <= next_y < player_top + paddle_height:
        ball.dx = -ball.dx
        _speed_up_ball(ball)
        next_x = ball.x + ball.dx
    elif (
        next_x == right_paddle_x
        and computer_top <= next_y < computer_top + paddle_height
    ):
        ball.dx = -ball.dx
        _speed_up_ball(ball)
        next_x = ball.x + ball.dx

    ball.x = next_x
    ball.y = next_y


def _speed_up_ball(ball: Ball) -> None:
    ball.tick_seconds = max(
        MIN_BALL_TICK_SECONDS, ball.tick_seconds * BALL_SPEEDUP_FACTOR
    )


def _draw_grid(
    stdscr: curses.window,
    rows: int,
    columns: int,
    white_pair: int,
    message_pair: int,
) -> None:
    logical_columns = columns // 2
    left = 1
    right = logical_columns - 2
    top = 2
    bottom = rows - 3
    middle = logical_columns // 2

    stdscr.erase()
    draw_rectangle(stdscr, left, top, right, bottom, curses.color_pair(white_pair))
    for row in range(top + 1, bottom):
        draw_cell(stdscr, row, middle, curses.color_pair(1))
    stdscr.addnstr(0, 0, CONTROL_MESSAGE, columns, curses.color_pair(message_pair))
    stdscr.refresh()


def _draw_players(
    stdscr: curses.window,
    columns: int,
    player_top: int,
    computer_top: int,
    height: int,
    blue_pair: int,
    red_pair: int,
) -> None:
    logical_columns = columns // 2
    left = 2
    right = logical_columns - 3
    for offset in range(height):
        draw_cell(stdscr, player_top + offset, left, curses.color_pair(blue_pair))
        draw_cell(stdscr, computer_top + offset, right, curses.color_pair(red_pair))
    stdscr.refresh()


def _draw_ball(
    stdscr: curses.window,
    ball: Ball,
    rows: int,
    columns: int,
    yellow_pair: int,
    message_pair: int,
) -> None:
    if ball.flash_visible:
        draw_cell(stdscr, ball.y, ball.x, curses.color_pair(yellow_pair))
    if ball.game_over:
        message = PLAYER_WIN_MESSAGE if ball.winner == "Player" else COMPUTER_WIN_MESSAGE
        stdscr.addnstr(
            rows - 1,
            0,
            message,
            columns,
            curses.color_pair(message_pair),
        )
        if ball.winner == "Player" and ball.flash_visible:
            stdscr.addnstr(
                rows - 1,
                len(PLAYER_WIN_MESSAGE),
                WIN_EMOJI,
                columns - len(PLAYER_WIN_MESSAGE),
                curses.color_pair(message_pair),
            )
    stdscr.refresh()


def _run(stdscr: curses.window) -> int:
    rows, columns = stdscr.getmaxyx()
    if rows < MIN_ROWS or columns < MIN_COLUMNS:
        return SIZE_EXIT

    try:
        cursor_visibility = curses.curs_set(0)
    except curses.error:
        cursor_visibility = None

    try:
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_BLUE)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        black_background = curses.color_pair(1)
        stdscr.bkgd(" ", black_background)
        stdscr.timeout(50)
        top = 2
        bottom = rows - 3
        surface_top = top + 1
        surface_bottom = bottom - 1
        surface_height = surface_bottom - surface_top + 1
        player_height = _paddle_height(surface_height)
        center_top = surface_top + (surface_height - player_height) // 2
        player_top = center_top
        computer_top = center_top
        logical_columns = columns // 2
        left_paddle_x = 2
        right_paddle_x = logical_columns - 3
        hybrid_horizon_ticks = _hybrid_horizon_ticks(
            right_paddle_x - left_paddle_x
        )
        if COMPUTER_BEHAVIOR == COMPUTER_BEHAVIOR_SHORT_HORIZON:
            stdscr.erase()
            stdscr.addnstr(
                0,
                0,
                "Calibrating computer...",
                columns,
                curses.color_pair(5),
            )
            stdscr.refresh()
            hybrid_horizon_ticks = _calibrate_hybrid_horizon(
                logical_columns, surface_top, surface_bottom
            )
        rng = random.Random()

        def new_ball() -> Ball:
            return _new_ball(logical_columns, surface_top, surface_bottom, rng)

        ball = new_ball()
        last_ball_tick = time.monotonic()
        last_flash_tick = last_ball_tick
        computer_move_ticks = 0

        def draw() -> None:
            _draw_grid(stdscr, rows, columns, 2, 5)
            _draw_players(
                stdscr, columns, player_top, computer_top, player_height, 3, 4
            )
            _draw_ball(stdscr, ball, rows, columns, 6, 5)

        draw()

        while True:
            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                return RESIZE_EXIT
            if key in (ord("e"), ord("E")):
                return 0
            if key in (ord("n"), ord("N")):
                player_top = center_top
                ball = new_ball()
                computer_top = center_top
                computer_move_ticks = 0
                last_ball_tick = time.monotonic()
                last_flash_tick = last_ball_tick
                draw()
                continue
            if not ball.game_over and key == curses.KEY_UP:
                next_top = _move_paddle(
                    player_top, -1, surface_top, surface_bottom, player_height
                )
                if next_top != player_top:
                    player_top = next_top
                    draw()
            elif not ball.game_over and key == curses.KEY_DOWN:
                next_top = _move_paddle(
                    player_top, 1, surface_top, surface_bottom, player_height
                )
                if next_top != player_top:
                    player_top = next_top
                    draw()

            now = time.monotonic()
            if ball.game_over:
                while now - last_flash_tick >= BALL_FLASH_INTERVAL_SECONDS:
                    ball.flash_visible = not ball.flash_visible
                    last_flash_tick += BALL_FLASH_INTERVAL_SECONDS
                    draw()
            else:
                while now - last_ball_tick >= ball.tick_seconds:
                    last_ball_tick += ball.tick_seconds
                    if ball.dx > 0:
                        computer_move_ticks += 1
                        if computer_move_ticks >= COMPUTER_MOVE_INTERVAL_TICKS:
                            target_y = _computer_target_y(
                                COMPUTER_BEHAVIOR,
                                ball,
                                right_paddle_x,
                                surface_top,
                                surface_bottom,
                                right_paddle_x - left_paddle_x,
                                hybrid_horizon_ticks,
                            )
                            computer_top = _move_computer_paddle(
                                computer_top,
                                target_y,
                                surface_top,
                                surface_bottom,
                                player_height,
                                COMPUTER_PADDLE_STEP,
                            )
                            computer_move_ticks = 0
                    else:
                        computer_move_ticks = 0
                    _advance_ball(
                        ball,
                        surface_top,
                        surface_bottom,
                        left_paddle_x,
                        right_paddle_x,
                        player_top,
                        computer_top,
                        player_height,
                    )
                    if ball.game_over:
                        last_flash_tick = now
                    draw()
    finally:
        if cursor_visibility is not None:
            curses.curs_set(cursor_visibility)


def main() -> int:
    return run_game(_run, SIZE_MESSAGE, SIZE_EXIT)


if __name__ == "__main__":
    raise SystemExit(main())
