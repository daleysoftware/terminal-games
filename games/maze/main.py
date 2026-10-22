import curses
import random
import time
from dataclasses import dataclass, field
from terminal_games.controls import draw_control_message, wrap_control_message
from terminal_games.runtime import RESIZE_EXIT, run_game
from terminal_games.rendering import draw_cell


Coordinate = tuple[int, int]
BLINK_INTERVAL = 0.5
CONTROL_MESSAGE = "↑↓←→ move; H hint; N new; E exit"
WIN_MESSAGE = "Maze complete! Woot! "
WIN_EMOJI = "🎉"
DIRECTIONS = {
    curses.KEY_UP: (-1, 0),
    curses.KEY_DOWN: (1, 0),
    curses.KEY_LEFT: (0, -1),
    curses.KEY_RIGHT: (0, 1),
}


def generate_maze(
    height: int, width: int, rng: random.Random
) -> tuple[list[str], tuple[int, int], tuple[int, int]]:
    if height < 3 or width < 3:
        raise ValueError("Maze must be at least 3 rows and 3 columns")

    maze = [["#"] * width for _ in range(height)]
    maze[1][1] = " "
    stack = [(1, 1)]
    while stack:
        row, column = stack[-1]
        neighbors = []
        for row_step, column_step in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            next_row = row + row_step
            next_column = column + column_step
            if (
                1 <= next_row < height - 1
                and 1 <= next_column < width - 1
                and maze[next_row][next_column] == "#"
            ):
                neighbors.append((next_row, next_column))

        if not neighbors:
            stack.pop()
            continue

        next_row, next_column = rng.choice(neighbors)
        maze[(row + next_row) // 2][(column + next_column) // 2] = " "
        maze[next_row][next_column] = " "
        stack.append((next_row, next_column))

    columns = list(range(1, width - 1, 2))
    start_column = rng.choice(columns)
    end_column = rng.choice(columns)
    last_cell_row = max(range(1, height - 1, 2))
    for row in range(last_cell_row, height):
        maze[row][start_column] = " "
    maze[0][end_column] = " "

    return ["".join(row) for row in maze], (height - 1, start_column), (0, end_column)


@dataclass
class GameState:
    maze: list[str]
    start: Coordinate
    end: Coordinate
    position: Coordinate
    last_blink: float
    visited: set[Coordinate] = field(default_factory=set)
    blue_phase: bool = False
    won: bool = False
    visit_counts: dict[Coordinate, int] = field(default_factory=dict)
    hint_visible: bool = False

    @property
    def height(self) -> int:
        return len(self.maze)

    @property
    def width(self) -> int:
        return len(self.maze[0])

    def move(self, direction: Coordinate) -> bool:
        if self.won:
            return False

        destination = (
            self.position[0] + direction[0],
            self.position[1] + direction[1],
        )
        if destination == self.start:
            pass
        elif destination == self.end:
            pass
        elif (
            not 0 <= destination[0] < self.height
            or not 0 <= destination[1] < self.width
            or self.maze[destination[0]][destination[1]] == "#"
        ):
            return False

        self.position = destination
        if destination == self.end:
            self.won = True
        elif destination != self.start:
            self.visited.add(destination)
            if (
                0 <= destination[0] < self.height
                and 0 <= destination[1] < self.width
            ):
                self.visit_counts[destination] = self.visit_counts.get(destination, 0) + 1
        return True

    def update_blink(self, now: float) -> bool:
        if self.position not in (self.start, self.end):
            self.blue_phase = False
            self.last_blink = now
            return False

        elapsed = now - self.last_blink
        if elapsed < BLINK_INTERVAL:
            return False

        steps = int(elapsed / BLINK_INTERVAL)
        if steps % 2:
            self.blue_phase = not self.blue_phase
        self.last_blink += steps * BLINK_INTERVAL
        return True


def _draw_game(
    stdscr: curses.window,
    state: GameState,
    color_pairs: dict[str, int],
    maze_top: int = 3,
) -> None:
    stdscr.erase()
    solution_path = _solution_path(state) if state.hint_visible else set()
    for row, line in enumerate(state.maze, start=maze_top):
        for column, tile in enumerate(line):
            logical_cell = (row - maze_top, column)
            if tile == "#":
                pair = color_pairs["wall"]
            elif logical_cell in state.visited:
                pair = color_pairs[
                    "yellow" if state.visit_counts.get(logical_cell, 1) >= 2 else "orange"
                ]
            elif logical_cell in solution_path:
                pair = color_pairs["light_blue"]
            else:
                continue
            draw_cell(stdscr, row, column + 1, curses.color_pair(pair))

    start_row, start_column = state.start
    end_row, end_column = state.end
    draw_cell(
        stdscr,
        start_row + maze_top,
        start_column + 1,
        curses.color_pair(color_pairs["green"]),
    )
    draw_cell(
        stdscr,
        end_row + maze_top,
        end_column + 1,
        curses.color_pair(color_pairs["red"]),
    )

    player_pair = _player_color(state, color_pairs)
    player_row, player_column = state.position
    draw_cell(
        stdscr,
        player_row + maze_top,
        player_column + 1,
        curses.color_pair(player_pair),
    )
    rows, columns = stdscr.getmaxyx()
    draw_control_message(
        stdscr, CONTROL_MESSAGE, columns, curses.color_pair(color_pairs["message"])
    )
    if state.won:
        stdscr.addnstr(rows - 1, 0, WIN_MESSAGE, columns, curses.color_pair(color_pairs["message"]))
        if not state.blue_phase:
            stdscr.addnstr(rows - 1, len(WIN_MESSAGE), WIN_EMOJI, columns - len(WIN_MESSAGE), curses.color_pair(color_pairs["message"]))
    stdscr.refresh()


def _underlying_color(state: GameState, color_pairs: dict[str, int]) -> int:
    if state.position == state.start:
        return color_pairs["green"]
    if state.position == state.end:
        return color_pairs["red"]
    if state.position in state.visited:
        if state.visit_counts.get(state.position, 1) >= 2:
            return color_pairs["yellow"]
        return color_pairs["orange"]
    return color_pairs["passage"]


def _player_color(state: GameState, color_pairs: dict[str, int]) -> int:
    if state.position in (state.start, state.end) and not state.blue_phase:
        return _underlying_color(state, color_pairs)
    return color_pairs["blue"]


def _initialize_colors() -> dict[str, int]:
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_RED)
    has_256_colors = getattr(curses, "COLORS", 0) >= 256
    orange = 208 if has_256_colors else curses.COLOR_YELLOW
    blue = 21 if has_256_colors else curses.COLOR_BLUE
    yellow = 226 if has_256_colors else curses.COLOR_YELLOW
    curses.init_pair(5, curses.COLOR_BLACK, orange)
    curses.init_pair(6, curses.COLOR_BLACK, blue)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(8, curses.COLOR_BLACK, yellow)
    light_blue = 117 if has_256_colors else curses.COLOR_CYAN
    curses.init_pair(9, curses.COLOR_BLACK, light_blue)
    return {
        "passage": 1,
        "wall": 2,
        "green": 3,
        "red": 4,
        "orange": 5,
        "blue": 6,
        "message": 7,
        "yellow": 8,
        "light_blue": 9,
    }


def _solution_path(state: GameState) -> set[Coordinate]:
    start = (state.height - 1, state.start[1])
    end = (0, state.end[1])
    pending = [start]
    previous: dict[Coordinate, Coordinate | None] = {start: None}

    while pending:
        cell = pending.pop(0)
        if cell == end:
            break
        for direction in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            neighbor = (cell[0] + direction[0], cell[1] + direction[1])
            if (
                0 <= neighbor[0] < state.height
                and 0 <= neighbor[1] < state.width
                and state.maze[neighbor[0]][neighbor[1]] == " "
                and neighbor not in previous
            ):
                previous[neighbor] = cell
                pending.append(neighbor)

    if end not in previous:
        return set()

    path = set()
    cell: Coordinate | None = end
    while cell is not None:
        path.add(cell)
        cell = previous[cell]
    return path


def _run(stdscr: curses.window) -> int:
    rows, columns = stdscr.getmaxyx()
    control_rows = len(wrap_control_message(CONTROL_MESSAGE, columns))
    maze_top = max(3, control_rows + 1)
    if rows < maze_top + 6 or columns < 10:
        return 1

    try:
        cursor_visibility = curses.curs_set(0)
    except curses.error:
        cursor_visibility = None

    try:
        color_pairs = _initialize_colors()
        stdscr.bkgd(" ", curses.color_pair(1))
        maze_width = (columns - 4) // 2
        maze_height = rows - maze_top - 3

        def new_game() -> GameState:
            maze, start, end = generate_maze(maze_height, maze_width, random.Random())
            start_position = (maze_height, start[1])
            return GameState(
                maze=maze,
                start=start_position,
                end=(-1, end[1]),
                position=start_position,
                last_blink=time.monotonic(),
            )

        state = new_game()
        stdscr.timeout(50)
        _draw_game(stdscr, state, color_pairs, maze_top)

        while True:
            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                return RESIZE_EXIT
            if key in (ord("e"), ord("E")):
                return 0
            if key in (ord("n"), ord("N")):
                state = new_game()
                should_draw = True
            elif key in (ord("h"), ord("H")):
                state.hint_visible = not state.hint_visible
                should_draw = True
            else:
                now = time.monotonic()
                should_draw = state.update_blink(now)
                direction = DIRECTIONS.get(key)
                if direction is not None and state.move(direction):
                    should_draw = True
            if should_draw:
                _draw_game(stdscr, state, color_pairs, maze_top)
    finally:
        if cursor_visibility is not None:
            curses.curs_set(cursor_visibility)


def main() -> int:
    return run_game(_run, "Terminal is too small for the maze and its controls.")


if __name__ == "__main__":
    raise SystemExit(main())
