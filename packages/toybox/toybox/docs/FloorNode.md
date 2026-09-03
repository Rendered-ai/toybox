# Floor

Selects the **ground surface** in a procedural scene. Objects placed
in the scene land on the floor (with a physics settle) and the floor
is visible in the render.

## Inputs

| Input | What it controls |
|---|---|
| **Floor Type** | Which floor material appears. `<random>` picks per run for dataset variety, or fix one for a consistent look. |

Available types: `Tile` · `Hardwood` · `Granite` · `Metal` · `Rocks`
· `Cobbles` · `Plane Floor` (plain grey).

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | Wire into a `Procedural Scene`'s `Floor Generator` input. |

## Notes

- Combine with `Container` for "objects in a tub on a wooden floor"
  scenes; combine without for "objects scattered on a stone floor"
  scenes.
- Floor models are sized to fully cover the camera view at the
  default 0.5 m tabletop camera height.
