# Pong Computer Behavior

## Status

Implemented

## Goal

Give the computer a simple opponent paddle that can return an approaching ball, while keeping the player in control of the rally outcome. The computer only moves vertically and stays within the play surface.

## Options

The options are ranked from strongest recommendation to weakest; the active selection is marked. Green means the option meets the criterion well, yellow means it has a tradeoff, and red means it performs poorly.

| Criterion | Rank 1: Short-horizon hybrid (selected) | Rank 2: Full-intercept prediction | Rank 3: Track current row | Rank 4: Unbounded prediction | Rank 5: Stationary |
|---|---|---|---|---|---|
| Plays as a credible opponent | 🟢 Anticipates nearby path | 🟢 Tracks likely intercept | 🟡 Chases a moving target | 🟢 Reaches the intercept | 🔴 Never reacts |
| Leaves room for player success | 🟢 Limited movement rate | 🟢 Limited movement rate | 🟢 Can lag behind | 🔴 Can be nearly perfect | 🟢 Easy to beat |
| Handles wall bounces | 🟢 Predicts nearby reflections | 🟢 Projects reflections | 🔴 Reacts after the bounce | 🟢 Projects reflections | 🔴 No response |
| Implementation simplicity | 🟡 Short projection horizon | 🟡 Full projection logic | 🟢 Minimal logic | 🟡 Prediction logic | 🟢 No control logic |
| Tunable difficulty | 🟢 Tune horizon and movement pace | 🟢 Adjust movement interval | 🟡 Adjust tracking interval | 🔴 Needs artificial errors | 🔴 Fixed difficulty |

### Rank 1: Short-horizon hybrid (selected)

Project the ball ahead by a calibrated whole-tick horizon, capped at the remaining distance to the computer. Include top and bottom wall reflections, then move toward that row. This anticipates part of the upcoming path without committing to the full intercept.

### Rank 2: Full-intercept prediction

Predict the row where the ball will reach the computer paddle, including wall reflections, then move toward that row at a limited pace.

### Rank 3: Track the current ball row

Move toward the ball's current row at a limited rate. This is simple, but the paddle may chase a row the ball has already left after a wall bounce.

### Rank 4: Unbounded prediction

Predict the intercept and move directly to it, or move quickly enough to stay on it. This returns many balls reliably but makes the computer hard to beat and leaves difficulty tuning to extra randomness or intentional mistakes.

### Rank 5: Stationary paddle

Keep the computer paddle centered. This is useful as a placeholder or easiest mode, but does not behave like an opponent.

## Current Selection

Use **short-horizon hybrid** (Rank 1). Its lookahead is calibrated to target a five-turn average computer loss on the current playfield. Keep current-row tracking and full-intercept prediction available as alternatives.

The active strategy is selected by the `COMPUTER_BEHAVIOR` module constant in `pong/main.py`. Choose `short_horizon`, `predict_intercept`, or `track_current_row` to switch among the three implemented intelligence layers. When `short_horizon` is active, the game calibrates its lookahead horizon once at startup for the current playfield size. `COMPUTER_HYBRID_HORIZON_RATIO` remains the default used by the target helper when no calibrated horizon is supplied.

## Behavior

1. Only consider movement while the ball's horizontal direction points toward the right paddle.
2. Use the selected intelligence layer's target row: its current row for `track_current_row`, its row at the calibrated short horizon for `short_horizon`, or its projected intercept for `predict_intercept`. Projection reflects off top and bottom walls.
3. For all three strategies, move at most one logical cell every second approaching ball tick. Leave the paddle in place if the target row is already covered by its span.
4. Clamp movement so the paddle remains inside the playable surface.
5. Reset the movement interval when the ball travels away. Center the computer paddle and reset the interval when starting a new game.
6. Keep computer movement independent of wall bounce speed changes; the ball only accelerates after a paddle hit.
7. Size both paddles to at least 4 logical rows, or the full playable height when the surface is shorter than 4 rows. Otherwise use 10% of the playable height, rounded up.

## Horizon Calibration

At startup, the short-horizon strategy evaluates every whole-tick horizon from 1 through the horizontal distance between paddle columns. For each candidate it simulates the four possible diagonal serve directions against a perfect player that positions its paddle to cover the next ball row. One turn is counted each time the ball reaches the computer paddle. A repeated ball/paddle/movement-cadence state marks that run as a non-loss.

Calibration first prefers candidates with fewer non-loss runs, then the candidate whose mean finite computer-loss turn is closest to five. Ties resolve to the smaller horizon. If every run for a candidate cycles, its average turn is treated as infinitely far from the target. The selected horizon remains fixed for that game's playfield and is passed directly to the hybrid target calculation.

## Implementation Notes

The projection and one-cell paddle movement are pure helpers in `pong/main.py`. The game loop applies the movement before advancing the ball on the corresponding tick, so the updated paddle position is used for collision detection. Projection assumes the ball advances one logical column per ball tick, matching the current ball model.

## Verification

Tests should verify:

- Current-row, calibrated-horizon hybrid, and full-intercept targets, including top/bottom wall reflections.
- Movement by at most one logical cell toward the predicted row, staying clamped at both surface limits.
- No movement when the projected row is already within the paddle span.
- All three strategies move every second approaching ball tick and stop when the ball travels away.
- A new game centers the computer paddle and resets its movement interval.
- The full root `make test` target passes.

The existing suite covers prediction, bounded movement, interval behavior while approaching, and both game directories through `make test`. The new-game computer reset is part of the behavior contract and should have direct regression coverage if the restart logic changes.
