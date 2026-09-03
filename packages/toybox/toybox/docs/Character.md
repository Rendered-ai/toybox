# Character

Uses a **pre-conforming character `.blend` file** as a source in the
avatar pipeline. If the file was authored to the channel's standard
already, this node loads it directly.

For arbitrary character uploads (`.fbx`, `.blend`, `.glb`) that need
skeleton normalisation first, use `Avatar Convert` instead — it does
the standardisation step for you.

## Input

| Input | What it controls |
|---|---|
| **Character File** | The character `.blend` to load. Wire from a `VolumeFile`. Must be a rigged character already conforming to the channel standard. |

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | The character. Wire into `Avatar Pose` (still), `Avatar Animation` (video), or straight into a placement node. |

## What "pre-conforming" means

The source `.blend` needs to be authored so:

- One character = one collection in the file
- One Armature is the root; all meshes parented to it
- Bone names follow the channel's `rendered_humanoid` standard
- Rest pose = T-pose, +Z up, 1 Blender unit = 1 metre
- Transforms applied (scale = 1)

If any of these don't hold, the file won't load cleanly — go through
`Avatar Convert` instead.
