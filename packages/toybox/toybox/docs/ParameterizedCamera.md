# Parameterized Camera

A camera you position **by exact coordinates**. Use when you know
where the camera should sit and what it should look at — a
documented framing you can reproduce, or when you need to jitter
position programmatically across a dataset.

For automatic framing around origin, use `Procedural Camera` or
`Outdoor Camera` instead.

## Inputs

| Input | What it controls |
|---|---|
| **Camera X / Y / Z** | Where the camera sits in the scene, in metres. Y is usually negative to look at the origin from "in front"; Z is height. |
| **Look At X / Y / Z** | Where the camera aims, in metres. Adjust Look At Z to point at a subject's head level, not their feet. |
| **Focal Length (mm)** | Lens character. Lower = wider angle (see more), higher = more zoom / telephoto compression. `35 mm` is scene-friendly, `50 mm` is a normal lens, `85 mm` is portrait-tight. |

## Output

| Output | Where it goes |
|---|---|
| **Camera** | Wire into a scene's `Camera` input. |

## Common configurations

**Eye-level portrait of a person at origin** — Camera `[0, -2, 1.5]`,
Look At `[0, 0, 1.6]`, Focal 50 mm.

**Low three-quarter view** — Camera `[2, -3, 1.0]`, Look At
`[0, 0, 1.0]`, Focal 35 mm.

**Framing tracks the subject's height** — wire the `Height (m)` output
from `Avatar Randomizer` into `Look At Z` so the camera aims at head
level whichever character the randomizer picked.

**Jittered position for augmentation** — feed Camera X and Camera Y
from `Random Uniform` nodes so each render sees the subject from a
slightly different angle.

## Notes

- The camera's roll (rotation around its own view direction) is fixed
  at zero — horizon stays level.
- To see what you'll get, drop reasonable values and preview at low
  resolution first.
