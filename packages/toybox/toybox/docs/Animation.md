# Avatar Animation

Attaches a **motion clip** to a character so they walk, run, wave, or
gesture across a frame range. Use for video datasets where you want
motion captured over time — pair with `Animation Render` (multi-frame)
instead of `Render` (single still).

For a static pose in a single image, use `Avatar Pose` instead.

## Inputs

| Input | What it controls |
|---|---|
| **Character Generator** | The character to animate. Wire from `Avatar Convert`. |
| **Animation File** | The motion clip. Wire one for a fixed motion, or several — each character in the scene draws a different one at random. Clips live under `RocketboxAnimations/` (`Walk/`, `Run/`, `Idle/`, `Talk/`, `Sit/`). |
| **Skeleton** | How the motion clip's bones are named. `Auto` (default) detects — leave unless you know you need to override. |
| **Loop** | `Enabled` tiles the motion so it plays through any render frame range. Turn off for one-shot actions (a wave, a jump). |
| **Frame Offset** | Shifts when the motion starts. Useful for crowds — set different offsets on each character so they don't all step in unison. |
| **FPS** | The motion clip's native frame rate. Rocketbox clips are 30. |
| **Root Motion** | `Enabled` = the character moves through space as they animate (a walk cycle covers distance). `Disabled` = they animate in place, wherever placement put them. |

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | The character with motion attached. Wire into a placement node. |

## Common configurations

**A person walking across the scene** — Wire a `Walk` clip.
`Loop: Enabled`, `Root Motion: Enabled`. Pair with `Animation Render`
covering 30–60 frames so the walk cycle plays out.

**A person waving in place** — Wire a gesture clip. `Loop: Disabled`,
`Root Motion: Disabled`. The character stays put and does the gesture
once.

**Mixed crowd** — Wire multiple `Animation File`s (Walk, Idle, Talk).
Every character in a scattered scene draws a different one.

## Notes

- Root translation, when enabled, is taken straight from the source
  clip — no re-inventing motion in code, no foot-sliding.
- If a source clip and character have different skeletons, the node
  logs a warning and applies the clip anyway.
