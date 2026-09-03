# Avatar Convert

Takes a rigged-character file (`.fbx`, `.blend`, `.glb`, `.gltf`) and
prepares it for the rest of the avatar pipeline. Every character in
your dataset goes through this node before it can be posed, animated,
or placed.

The node handles the internal bookkeeping — bone renaming, mesh
alignment, metadata tagging — so downstream nodes (`Avatar Pose`,
`Avatar Animation`, placement, camera) work the same way regardless of
whether the character came from Rocketbox, Mixamo, or somewhere else.

## Inputs

| Input | What it controls |
|---|---|
| **Avatar File** | The character file to use. Wire from a `VolumeFile` (fixed character) or from `Avatar Randomizer` (draws a different one each run). |
| **Source Rig** | Where the character came from. `Auto` (default) detects from the file — leave this on `Auto` unless you have a mixed-source pool and want to force a specific interpretation. |
| **Rest Pose** | The pose the character was authored in. `T-Pose` is the industry standard; `A-Pose` is accepted (tagged only — no correction applied). Leave at `T-Pose` unless you know the source uses A-Pose. |
| **Gender**, **Ethnicity** | Optional demographic labels stamped onto the character. Only matters if the input file's own metadata is incomplete and you want annotations to include these fields. Leave blank if the pool sidecars already carry them. |

## Output

| Output | Where it goes |
|---|---|
| **Object Generator** | The prepared character. Wire into `Avatar Pose` (still frame) or `Avatar Animation` (video), or straight into a placement node. |

## Notes

- **Same character, same result.** Conversion is cached — the same
  input file produces the same standardised character every time.
- **Errors are explicit.** If the input rig is missing bones the
  pipeline needs, you get a clear list of what's missing rather than a
  silent wrong render.
