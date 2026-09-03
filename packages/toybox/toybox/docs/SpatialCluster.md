# Spatial Cluster

Places objects in **predictable patterns** — a ring, a hex grid, or an
even scatter with a fixed minimum spacing. Use when the layout itself
matters (a grid of items being counted, a ring of characters around
a table).

For a stochastic scatter with physics, use `Random Placement`. For a
single hand-placed object, use `Manual Placement`.

## Inputs

| Input | What it controls |
|---|---|
| **Object Generators** | What to place. Wire one type or several — objects are drawn round-robin from all wired generators. |
| **Number of Objects** | How many to place. |
| **Center (m)** | Where the pattern is centred. |
| **Radius** | How wide the pattern spreads. |
| **Object Spacing (m)** | Minimum distance between adjacent objects (enforced when Allow Overlap is off). |
| **Pattern Type** | `Random` (uniform scatter, no overlap) · `Circular` (evenly spaced ring, falls back to concentric rings if crowded) · `Hexagonal` (hex-grid). |
| **Allow Overlap** | `Enabled` skips the spacing check — useful for very dense scenes. |

## Output

| Output | Where it goes |
|---|---|
| **Objects of Interest** | The list of placed objects. Wire into a scene's `Placed Objects`. |

## Notes

- Every placed object gets a random rotation around the vertical axis
  so it doesn't look mechanically identical.
- If you ask for too many objects in a tight radius, the node places
  what fits and logs a warning.
- Objects sit at the same fixed Z (from Center). If you want gravity
  to settle them onto a floor, wire the scene's `Floor Generator`
  input.
