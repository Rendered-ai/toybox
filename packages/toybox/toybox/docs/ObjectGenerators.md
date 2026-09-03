# Object Generators

Object generators are the **factory nodes** that produce the objects
you place in a scene. Each wraps a family of related 3D models.

They all share the same shape: one dropdown for the specific model,
one output port that wires into a placement node.

## Nodes in this family

| Node | What it produces | Help |
|---|---|---|
| **Toy** | Bubbles, Yo-yo, Skateboard, Playdough, Rubik's Cube, Mix Cube. | [ToyNode.md](ToyNode.md) |
| **Fruit** | Apple, Orange. | [FruitNode.md](FruitNode.md) |
| **Container** | Boxes, tubs, bowls — receptacles that other objects land in. | [ContainerNode.md](ContainerNode.md) |
| **Floor** | Tile, hardwood, granite, metal, rocks, cobbles, plain. | [FloorNode.md](FloorNode.md) |

## Typical wiring

```
Toy (<random>)   ──┐
                   ├─► Color Variation ─► Random Placement ─► Render
Fruit (<random>) ─┘
                        ▲
          Container ────┤   (into Procedural Scene)
          Floor    ─────┘
```

Any object generator output can wire straight into a placement node,
or first go through a `Color Variation` / `Scale` / `Warp` modifier
for per-instance variety.
