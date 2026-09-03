# Outdoor Camera

A camera you position by **named viewpoint** — Overhead, Side, Corner,
or Entrance — around a point you specify. Use for scenes where you
want repeatable framing across a dataset (a training set that shows
every scene from these four canonical angles), or for
`<random>` to sample one viewpoint per run.

For exact XYZ positioning, use `Parameterized Camera`.
For toys-at-origin tabletop scenes, `Procedural Camera` is simpler.

## Inputs

| Input | What it controls |
|---|---|
| **Camera Angle** | `Overhead` = straight down, `Side` = profile view, `Corner` = 3/4 isometric-style, `Entrance` = low front-facing. `<random>` = pick one per run for dataset variety. |
| **Distance to Center (m)** | How far the camera sits from the look-at point. Scale to the scene: tabletop = 1 m, room = 5 m, parking lot = 15–30 m. |
| **Focal Length (mm)** | Lens character. `35 mm` = wide, `50 mm` = normal, `85 mm` = tight portrait. |
| **Look At** | Where the camera aims, as `[X, Y, Z]` in metres. Default `[0, 0, 0]` (world origin). For a large environment whose action isn't at origin, set this to the scene's actual centre. |

## Output

| Output | Where it goes |
|---|---|
| **Camera** | Wire into a scene's `Camera` input. |

## The four angles

- **Overhead** — camera at `(0, 0, distance)` pointing straight down.
  Top-down / satellite feel.
- **Side** — profile view, camera off to the +X side at ~22° elevation.
- **Corner** — 3/4 diagonal, camera at 27° elevation from the (-X, +Y)
  quadrant. Isometric-style.
- **Entrance** — front-facing, camera at low elevation coming from -Y.
  Approach angle.

## Common configurations

**Dataset variety across canonical angles** — Camera Angle `<random>`,
Distance sized to the scene, Look At at the action's centre. Every
run picks a different vantage.

**Consistent framing across the whole dataset** — Camera Angle set to
one specific value (e.g. `Corner`) for reproducible framing.

## Notes

- Roll (horizon tilt) is fixed at zero — the horizon stays level.
- If the action isn't near world origin, remember to set Look At —
  the camera aims there, not at origin.
