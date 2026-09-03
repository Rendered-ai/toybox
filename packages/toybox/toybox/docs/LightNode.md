# Light

Adds a **spot** or **point** light to the scene. Use for interior
scenes, tabletop lighting, or supplemental fill on top of an HDRI.
For outdoor sunlight, use `Sun` instead.

## Inputs

| Input | What it controls |
|---|---|
| **Type** | `SPOT` = directional cone (like a hero light on the subject). `POINT` = omnidirectional bulb (like a bare lamp). |
| **Radiant Power (W)** | Brightness. Tabletop scenes usually want 50–500 W. Higher = brighter and more contrast. |
| **Location (m)** | Where the light sits in the scene, in metres. `[0, 0, 2]` is 2 m above the origin — a typical overhead light. Wire a `Vector3D` (fed by `Random Uniform`) to jitter position across runs. |
| **Color** | Tint as RGB (each 0–1). `[1, 1, 1]` is neutral. Warmer values (`[1, 0.4, 0.4]`) simulate tungsten; cooler (`[0.6, 0.8, 1]`) simulates daylight. Wire from a `Random Choice` to sweep across a palette. |
| **Target (m)** | For SPOT only — where the light points. Ignored for POINT. |

## Output

| Output | Where it goes |
|---|---|
| **Light** | Wire into a scene's `Lights` input. Multiple lights can be wired to the same scene. |

## Common configurations

**Overhead POINT for a tabletop scene** — Type POINT, Location
`[0, 0, 2]`, Power 400 W, neutral color.

**Randomized studio look** — POINT light, Location fed by random
`Vector3D`, Power fed by `Random Uniform` `[200, 500]`. Each run
gets a slightly different lighting mood.

**Warm-vs-cool split for augmentation** — Wire the Color input from a
`Random Choice` between a warm palette and a cool one.

## Notes

- POINT lights ignore rotation entirely, so the Target input has no
  effect on them.
- For pure environment lighting, no Light node is needed — the scene's
  HDRI (if wired) handles it.
