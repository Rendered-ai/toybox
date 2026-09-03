# Fruit

Selects a **fruit prop** for placement nodes to spawn. Same pattern as
`Toy` — one node, one Type dropdown.

## Inputs

| Input | What it controls |
|---|---|
| **Fruit Type** | Which fruit appears. `<random>` picks per instance. Available: `Apple` · `Orange`. |

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | Wire into a placement node (`Random Placement`, `Place Over Container`, `Manual Placement`, `Spatial Cluster`) or into a `Color Variation` / `Scale` / `Warp` modifier first. |

## Notes

- Fruit meshes don't support recolouring (the artwork is textured).
- Toys (Yo-yo, Skateboard, Playdough, Rubik's Cube, Mix Cube,
  Bubbles) live on the sibling `Toy` node.
