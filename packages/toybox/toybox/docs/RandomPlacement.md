# Random Placement / Place Over Container

Two ways to scatter many objects into a scene.

- **Random Placement** — lay N objects **flat** on a plane with
  non-overlapping footprints. Every object visible individually. Use
  for tabletop layouts, evenly spread scenes.
- **Place Over Container** — drop N objects into a **tight column**
  above a container so gravity stacks them into a pile. Use when you
  want a heap of objects, not an even spread.

## Choosing

| You want... | Use | Pair with |
|---|---|---|
| Every object visible, flat spread | Random Placement | Any scene aggregator |
| A pile settled on the floor | Place Over Container | Scene with a Floor |
| Objects filling a container | Place Over Container | Scene with a Floor + Container |
| Precise layout (not random) | Manual Placement | — |

## Inputs

| Input | What it controls |
|---|---|
| **Object Generators** | What kind of objects to scatter. Wire one for a single type or several — the node picks one per placed object. Wire `Weight` nodes to bias the mix. |
| **Number of Objects** | How many to place total. |
| **Center (m)** | Where the scatter/pile happens, in metres. `[0, 0, 0.05]` puts the scatter at scene centre just above ground. For Place Over Container, Z is the drop height — gravity does the rest. |
| **Scatter Radius** | How wide the scatter is (Random Placement) or how tight the drop column is (Place Over Container). |

## Output

| Output | Where it goes |
|---|---|
| **Objects of Interest** | The list of placed objects. Wire into a scene's `Placed Objects`. |

## Notes

- **Random Placement**: if the scatter radius is too small for the
  number of objects (they'd have to overlap), a few objects will be
  hidden from the scene and a warning logged. Increase the radius or
  drop the count.
- **Place Over Container**: keep the count under ~50 in a small area
  — the physics simulation gets unstable with too many colliding
  objects.
- Use `Color Variation` or `Warp` upstream to make each placed object
  visually distinct.
