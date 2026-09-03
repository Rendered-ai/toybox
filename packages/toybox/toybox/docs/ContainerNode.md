# Container

Selects a **container** (box, tub, bowl, basket) that placement nodes
drop objects into. Rendered as a static prop in the final scene.

## Inputs

| Input | What it controls |
|---|---|
| **Container Type** | Which container appears. `<random>` picks per run; or fix one for a consistent look. |

Available types:

| Type | Look |
|---|---|
| Dark Wooden Box | Square, dark stained wood. |
| Light Wooden Box | Square, pale natural wood. |
| Clear Tub | Translucent plastic tub. |
| Orange Tub | Round opaque plastic tub. |
| Green Tub | Round opaque plastic tub. |
| Blue Tub | Round opaque plastic tub. |
| Gray Tub | Round opaque plastic tub. |
| Yellow Bowl | Wide shallow bowl. |
| Purple Bowl | Wide shallow bowl. |

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | Wire into a `Procedural Scene`'s `Container Generator` input. |

## Notes

- Container is optional in placement nodes — omit it for objects
  scattered loose on the floor.
- Wooden boxes suit dense piles; bowls suit sparse hero shots.
