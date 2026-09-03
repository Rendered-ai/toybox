# Warp

Modifier that gives each spawned object a **randomly distorted shape**
— every instance is subtly (or dramatically) different from the source
model. Use to add non-rigid, per-object variation so a scattered pile
of yo-yos doesn't look like 20 identical copies of the same mesh.

Wire between an object generator (`Toy`, `Fruit`) and a placement
node.

## Inputs

| Input | What it controls |
|---|---|
| **Warp Strength** | How distorted the shapes get, on a `0–100` scale. `0` = no warp (source mesh untouched), `50` = noticeable but plausible variation, `100` = heavily deformed. |
| **Generator** | The object generator to distort. |

## Output

| Output | Where it goes |
|---|---|
| **Generator** | The generator with warp applied. Wire into a placement node. |

## Notes

- The average size of each object is preserved — warp adds shape
  variation without making some instances larger than others.
- At very high strengths thin objects (a yo-yo disc, a skateboard
  deck) can self-intersect. If physics becomes unstable, lower the
  strength.
- If you're also using `Scale`, put Warp *after* it so the warp
  distorts the post-scaled shape.
- Same random seed produces the same warp — datasets reproduce.
