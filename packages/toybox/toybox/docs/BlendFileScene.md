# Blend File Scene

Loads a **pre-built 3D environment** (a room, warehouse, parking lot,
etc.) and drops your characters or objects into it. Use this when you
want a specific real-world backdrop rather than a procedurally
composed one — the environment file was built by a 3D artist, and this
node keeps that authored look while overlaying whatever the graph
places.

Sibling to `Procedural Scene`, which builds scenes from parts (Floor +
Container + Lights). Choose Blend File Scene when the backdrop is a
whole authored space.

## Inputs

| Input | What it controls |
|---|---|
| **Scene File** | The `.blend` file to load as the environment. Wire from a `VolumeFile`. |
| **Placed Objects** | Characters or objects to drop into the environment. From `Random Placement`, `Manual Placement`, etc. Optional — a scene works without them for pure environment renders. |
| **Lights** | Extra lights to add on top of anything already baked into the environment. Optional. |
| **HDRI** | An HDR sky/environment map that replaces the scene's own sky. Optional. Wire multiple for per-run variety. |
| **HDRI Rotation (deg)** | Rotates the HDRI around the vertical axis — shifts the sun position across runs. Wire a `Random Uniform` for a sun sweep. |
| **Settle Physics** | `Enabled` = placed objects fall under gravity and land on the environment's meshes (useful when you want toys resting on a floor the scene provides). `Disabled` = objects appear exactly where placement put them. |
| **Camera** | Required — the environment's own cameras are stripped, so a `Parameterized Camera` / `Outdoor Camera` must supply the view. |

## Output

| Output | Where it goes |
|---|---|
| **Scene** | The assembled scene. Wire into `Render`. |

## Common configurations

**Person walking through a parking lot** — Scene File = `ParkingLot.blend`,
Placed Objects = a Rocketbox avatar with a Walk animation, HDRI = a
matching outdoor sky, Camera positioned to see both avatar and cars.

**Toys settled inside a room's furniture** — Scene File = a room blend
with a table or bin geometry, Placed Objects = toys via
`Place Over Container`, `Settle Physics: Enabled` so gravity drops
them onto the surface.

## Notes

- **The environment's own lights, sky, and cameras**: the sky is used
  by default. Any cameras baked into the file are removed — you must
  wire an external Camera. Wire an HDRI here to override the file's sky.
- **Scale matters**. A tabletop-scale object (e.g. a 5 cm toy) will be
  invisibly small against a warehouse-scale environment. Use human-
  scale content (an avatar, a piece of furniture) or scale the objects
  up to match.
- Objects "startup defaults" saved into the file (a stray Cube, a
  default Camera, a default Light) are removed so a "forgot to clean
  up before saving" blend still loads clean.
