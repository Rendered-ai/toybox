# Toy

Selects a **toy model** for placement nodes to spawn.

## Inputs

| Input | What it controls |
|---|---|
| **Toy Type** | Which toy appears. `<random>` picks per instance for a mixed pile. |

Available types:

| Type | Recolour support |
|---|---|
| Bubbles | Yes — bottle body colour. |
| Yo-yo | Yes — full body colour. |
| Skateboard | Yes — board deck colour. |
| Playdough | Yes — lid colour. |
| Rubik's Cube | No (fixed sticker layout). |
| Mix Cube | No (per-spawn random scramble). |

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | Wire into a placement node (`Random Placement`, `Place Over Container`, `Manual Placement`, `Spatial Cluster`) or into a `Color Variation` / `Scale` / `Warp` modifier first. |

## Notes

- Recolour support = works with a `Color Variation` upstream. Toys
  without recolour keep their default artwork.
- Fruit props (Apple, Orange) live on the sibling `Fruit` node.
