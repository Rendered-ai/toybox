# Manual Placement

Places **one specific object at an exact position** and orientation.
Use when you know exactly where a character or object should be — a
person standing at a marked spot, a hero object centered in a shot.

For a random scatter of many objects, use `Random Placement` or
`Place Over Container` instead.

## Inputs

| Input | What it controls |
|---|---|
| **Object Generators** | What to place. Usually one — a character, a toy, a piece of furniture. If more than one is wired, one is picked. |
| **Location (m)** | Where in the scene to place it, in metres. `[0, 0, 0]` is the scene centre on the ground. Wire a `Vector3D` (fed by `Random Uniform`) to jitter position per run. |
| **Rotation (deg)** | Which way the object faces, as XYZ Euler angles in degrees. Only the Z (yaw) usually matters for characters — it's the direction they face. Wire a `Vector3D` to randomize heading. |

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | The placed object. Wire into `Procedural Scene` or `Blend File Scene` as one of the `Placed Objects`. |

## Common configurations

**A person facing the camera** — Location `[0, 0, 0]`, Rotation
`[0, 0, -90]` (or whatever faces the camera in your setup).

**A person walking in a random direction** — Rotation Z fed by
`Random Uniform` `[0, 360]`.

**A person at a slightly-jittered spot** — Location fed by a `Vector3D`
whose X and Y come from `Random Uniform` `[-0.5, 0.5]` — realistic
frame-to-frame variation instead of pixel-locked positioning.

## Notes

- No physics runs by default — the object appears exactly where you
  put it.
- The object's feet land at the given Z; a character posed sitting or
  standing sits on the ground plane at Z=0.
