# Scale

Modifier that resizes each spawned object by a **per-axis multiplier**.
Use to make objects smaller/larger, stretched, or randomly sized across
a dataset.

Wire between an object generator (`Toy`, `Fruit`) and a placement
node.

## Inputs

| Input | What it controls |
|---|---|
| **Scale X** | Multiplier along the X axis. `1.0` = original size, `2.0` = double, `0.5` = half. |
| **Scale Y** | Multiplier along the Y axis. |
| **Scale Z** | Multiplier along the Z axis. |
| **Generator** | The object generator to resize. |

## Output

| Output | Where it goes |
|---|---|
| **Generator** | The generator with scale applied. Wire into a placement node. |

## Examples

**Mini toys**: `Scale X=0.5, Y=0.5, Z=0.5` between `Toy` and
`Random Placement`.

**Stretched skateboards**: `Scale X=2, Y=1, Z=1` for elongated
boards.

**Random size variation**: wire a `Random Uniform` into all three
Scale inputs so each spawned object comes out at a random size.

## Notes

- The applied scale is recorded in each object's annotation, so
  downstream tools see the actual rendered size.
- If you're also using `Warp`, put Warp *after* Scale so the warp
  distorts the post-scaled shape.
