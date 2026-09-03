# Avatar Pose

Freezes a character in a **single static pose** for a still-image
render. Use for portrait-style frames — a person standing, sitting,
gesturing — where you want one moment captured, not motion over time.

For motion across a frame range, use `Avatar Animation` + `Animation
Render` instead.

## Inputs

| Input | What it controls |
|---|---|
| **Character Generator** | The character to pose. Wire from `Avatar Convert`. |
| **Pose File** | The pose to use. Wire one file for a fixed pose, or several — the node picks one per run for variety. Pose files live under `RocketboxAnimations/` on the assets volume (`Idle/…`, `Talk/…`, `Sit/…`, etc.). |
| **Skeleton** | How the pose file's bones are named. `Auto` (default) detects it from the file — leave on `Auto` unless you know you need to override. |
| **Frame** | Which moment of the pose file to capture. For most poses `1` is a safe default. For long clips (a 30-second `Talk` sequence has 800+ frames), pick a frame in the middle to see the character mid-gesture. Wire a `Random Integer` here to sample a different frame every run. |

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | The posed character. Wire into a placement node (`Manual Placement` typically), then into a `Procedural Scene` / `Blend File Scene`. |

## Notes

- **Feet always land at ground level.** The node measures the posed
  character's lowest point and adjusts, so placing at `Z=0` puts them
  on the ground regardless of whether the pose is standing, sitting,
  or crouching.
- **Root translation is stripped.** A pose from a walk cycle won't
  drift — the character stays exactly where placement puts them.
- **For pose variety across a dataset**: wire multiple `Pose File`s
  AND wire a `Random Integer` into `Frame`. Same random seed = same
  pick, so previews and datasets reproduce.
