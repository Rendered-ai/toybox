# Procedural Camera

A camera that **automatically points down at the scene** from a random
elevated position. Use for tabletop / bin scenes where objects sit near
the origin and you want each render to see the scene from a slightly
different angle without manual positioning.

For exact XYZ positioning, use `Parameterized Camera`. For named
outdoor viewpoints (Overhead / Side / Corner / Entrance), use
`Outdoor Camera`.

## Inputs

| Input | What it controls |
|---|---|
| **Location Height (m)** | Camera altitude in metres. The camera lands at a random spot at this altitude and always looks down at the scene. Tabletop scenes: `0.5–1.0`. |
| **Roll (degrees)** | Rotation around the camera's own view direction (horizon tilt). Leave at `0` for a level horizon. |
| **Look At** | Point the camera aims at, `[X, Y, Z]` in metres. Default `[0, 0, 0]` (scene origin). Set higher (e.g. `[0, 0, 0.5]`) to frame taller objects. |

## Output

| Output | Where it goes |
|---|---|
| **Camera** | Wire into a scene's `Camera` input. |

## Common configurations

**Tabletop toys** — Location Height `0.5`, Look At `[0, 0, 0]`. Camera
lands 0.5 m up, always looks down at the origin, position varies per
run.

**Taller subject** — bump Location Height to `1.0`+ and set
Look At Z to the subject's mid-height so the camera frames it
consistently.

## Notes

- The lens is fixed at 50 mm — a typical product-photography lens.
- Position varies per run within the constraint that the camera
  always looks down at the scene (never sideways or upward).
