# Color Variation

Modifier that **recolours** each spawned object. Use to add per-object
colour diversity so a placement of 20 toys shows a range of colours
instead of 20 identical ones.

Wire between an object generator (`Toy`, `Fruit`) and a placement
node.

## Inputs

| Input | What it controls |
|---|---|
| **Color** | Target colour. `<random>` picks a different colour per spawned object (rainbow + black/white palette). Or pick a specific one: `Red`, `Orange`, `Yellow`, `Green`, `Blue`, `Indigo`, `Violet`, `White`, `Black`. |
| **Generators** | The object generator(s) to recolour. |

## Output

| Output | Where it goes |
|---|---|
| **Generator** | The generator with colours applied. Wire into a placement node. |

## Notes

- `<random>` re-rolls per object, not per graph — a single
  `Color Variation → Random Placement` chain produces a colourful mix
  in one scene.
- Only the base tint changes. Objects with painted logos or decals
  keep their artwork; the colour underneath shifts.
- Combine with `Scale` or `Warp` upstream/downstream for compound
  variation (colour + size, colour + shape).
