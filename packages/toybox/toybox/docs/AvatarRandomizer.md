# Avatar Randomizer

Every time the graph runs, pick a **different avatar** from a folder of
available characters — filtered by demographic and outfit. Use this to
build datasets where each frame shows a different person instead of the
same one repeated.

Wires straight into `Avatar Convert` in place of a specific character
file. The `Height (m)` output lets a Camera frame the picked person at
their actual height instead of a fixed value.

## Inputs

| Input | What it controls |
|---|---|
| **Avatar Pool** | Folder to draw characters from. Point at the whole avatar library for maximum variety, or a subfolder to narrow the pool (e.g. only medical staff, only casual outfits). Wired from a `VolumeDirectory` node. |
| **Gender** | `any` = draw from both, `female` = only women, `male` = only men. |
| **Clothing** | Outfit category — `casual`, `business`, `medical`, `workwear`, `uniform`, etc. `any` picks across all outfit types in the pool. Use this to match the scene (e.g. `medical` for a hospital scene, `workwear` for a construction site). |
| **Setting** | `indoor` or `outdoor`. Filters to characters whose outfit fits that environment. Businesswear reads as `indoor`; construction workwear reads as `outdoor`. `any` disables the filter. |

## Outputs

| Output | Where it goes |
|---|---|
| **Avatar File** | The picked character file. Wire into `Avatar Convert`'s **Avatar File** input. |
| **Height (m)** | The picked character's real height. Wire into a Camera's **Look At Z** input so the camera frames the head level for whichever character came up. |

## Example configurations

**Diverse crowd** — Gender `any`, Clothing `any`, Setting `indoor`.
Every run picks a different indoor-appropriate character.

**Hospital dataset** — Gender `any`, Clothing `medical`, Setting `indoor`.
Only medical staff (scrubs, coats) show up.

**Same person every run** — point the Avatar Pool at a folder
containing exactly one character. The filters don't matter; you get
that one person every time.

## Notes

- **A filter is respected only when the character's metadata carries
  that field.** If a character file is missing a gender tag, it won't
  match a `female` or `male` filter — set the filter to `any` or ask
  whoever curates the volume to add the tag.
- **The pool is scanned recursively.** A folder at
  `RocketboxAvatars/` catches every character sitting in any
  subfolder underneath it.
- **Determinism**: same random seed + same pool contents → same pick,
  so previews and datasets reproduce.
