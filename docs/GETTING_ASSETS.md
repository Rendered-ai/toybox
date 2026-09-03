# Getting the assets

The showcase graphs reference specific files on the Rendered.ai
public-share volume `708b0ca9-d81c-4679-b164-141418507830`. If you
have a Rendered.ai account with read access to that volume, the
paths in the graphs Just Work.

If you don't — you found this repo in the wild, or you're forking to
run standalone — this doc tells you where each asset came from and
how to reproduce or substitute it. Everything referenced by a hero
graph is CC0 (public domain) or MIT (permissive); nothing is
Rendered.ai-proprietary.

The four asset families are covered below, in the order they appear
across the showcase graphs.

---

## 1. Rocketbox avatars

**Source**: Microsoft Rocketbox library — a curated set of 115
professionally-rigged humanoids released as MIT in 2020.

- **Upstream**: <https://github.com/microsoft/Microsoft-Rocketbox>
- **License**: MIT (see the repo's `LICENSE`)
- **Volume path**: `/RocketboxAvatars/<Name>/<Name>.fbx`

### Used by the showcase graphs

| Avatar | Graph |
|---|---|
| `Business_Female_01` | `parking_lot_blend_scene` |
| `Female_Adult_01` | `avatar_animation_demo` |
| `Business_Female_01`, `Chef_Female_01`, `Female_Adult_01`, `Medical_Female_01` (Randomizer pool) | `avatar_hdri_indoor_test` |

### How to acquire

1. Clone the upstream repo:
   ```bash
   git clone https://github.com/microsoft/Microsoft-Rocketbox.git
   ```
2. Individual avatar `.fbx` files live under
   `Assets/Avatars/all_avatars_max_motextr_static/`.
3. Copy the eight `Business_*`, `Chef_*`, `Construction_*`,
   `Female_*`, `Male_*`, `Medical_*` avatars into your own volume or
   local filesystem, mirroring the `RocketboxAvatars/<Name>/<Name>.fbx`
   layout the graphs expect.

Each `<Name>.fbx` should sit next to a matching `<Name>.json` sidecar
carrying at minimum `ana_kind = "character"` + `ana_gender` +
`ana_clothing` + `ana_setting`. See
`scripts/stamp_rocketbox_sidecars.py` in this repo for the stamping
recipe used against the public-share volume.

---

## 2. Rocketbox animations

**Source**: Same Microsoft Rocketbox library — pro-mocap animations
sharing the Rocketbox skeleton.

- **Upstream**: <https://github.com/microsoft/Microsoft-Rocketbox>
  (subdirectory `Assets/Animations/`)
- **License**: MIT
- **Volume path**: `/RocketboxAnimations/<Category>/<clip>.fbx`

### Used by the showcase graphs

| Clip | Graph |
|---|---|
| `Idle/f_idle_breathe_01.fbx` | `avatar_hdri_indoor_test` |
| `Talk/f_gestic_talk_neutral_01.fbx` | `avatar_hdri_indoor_test` |
| `Run/f_run_neutral.fbx` | `avatar_animation_demo` |
| `Walk/f_walk_neutral.fbx` | `parking_lot_blend_scene` |

### How to acquire

Same repo as the avatars. Clips are under
`Assets/Animations/all_animations_max_motextr_static/`. Copy the four
files above (and any others you want) into your volume mirroring the
`RocketboxAnimations/<Category>/<clip>.fbx` layout the graphs expect.

Categories: `Idle` · `Talk` · `Walk` · `Run` · `Sit`. Male
equivalents (`m_*` prefix) live alongside the female clips.

---

## 3. Poly Haven HDRIs

**Source**: Poly Haven — a CC0 asset library for HDRIs, textures, and
models.

- **Upstream**: <https://polyhaven.com/hdris>
- **License**: CC0 1.0 Universal (public domain — no attribution
  required, though appreciated)
- **Volume path**: `/HDRIs/Poly Haven/<Condition>/<name>_<res>.hdr`
- **Companion inventory**: the volume's `HDRIs/HDRI LIBRARY.md`
  documents every included file with brightness metrics, time-of-day,
  and avatar-pairing suggestions.

### Used by the showcase graphs

| HDRI | Graph |
|---|---|
| `Clear/noon_grass_4k.hdr` | `fruit_hdri_test`, `avatar_animation_demo` |
| `Indoor/phone_shop_8k.hdr` | `avatar_hdri_indoor_test` |
| `Indoor/decor_shop_8k.hdr` | `avatar_hdri_indoor_test` |
| `Indoor/bush_restaurant_8k.hdr` | `avatar_hdri_indoor_test` |
| `Indoor/hospital_room_8k.hdr` | `avatar_hdri_indoor_test` |
| `Outdoor/mall_parking_lot_4k.exr` | `parking_lot_blend_scene` |

### How to acquire

Each HDRI has its own polyhaven.com page. The permalink pattern is
`https://polyhaven.com/a/<name>` — so
<https://polyhaven.com/a/noon_grass> for `noon_grass_4k.hdr`.

1. Download the `4K` (or `8K` where applicable) `.hdr` / `.exr` file
   from each page.
2. Place under `HDRIs/Poly Haven/<Condition>/` mirroring the volume
   layout above. Condition folders are `Clear` · `Cloudy` ·
   `Indoor` · `Night` · `Outdoor`.

If you want more variety without changing the graphs, download the
sibling files listed in the volume's `HDRIs/HDRI LIBRARY.md` — those
already appear on Poly Haven under the same URLs.

---

## 4. Rendered.ai-authored assets (CC0)

The remaining assets in the showcase graphs — fruit, toys, containers,
floors, and the parking-lot environment — were **created by
Rendered.ai and released as CC0**. That means: use them freely,
redistribute freely, no attribution required.

If you have volume access, the paths in the graphs Just Work. If you
don't, three options:

### Option A — Ask for the assets

`admin@rendered.ai` grants read access to volume
`708b0ca9-d81c-4679-b164-141418507830` for anyone with a Rendered.ai
account. The volume is called "public-share" precisely so it can be
shared broadly under CC0.

### Option B — Substitute with other CC0 sources

None of the Rendered.ai assets are irreplaceable — every one has
plentiful CC0 substitutes on the same public asset libraries. The
graphs read the paths from
`packages/toybox/toybox/package.yml` — swap the `filename:` entry
for any asset to point at your own copy.

| Category | Volume path | CC0 substitute sources |
|---|---|---|
| **Fruit** (`Apple.blend`, `Orange.blend`) | `/Fruit/*.blend` | Blender Studio, [Poly Haven models](https://polyhaven.com/models), Sketchfab CC0 filter |
| **Toys** (`YoYo`, `Skateboard`, `PlayDough`, `BubbleBottle`, `Cube`, `MixCube`) | `/Toys/*.blend` | Sketchfab CC0, Kenney.nl (game-asset packs) |
| **Containers** (wooden boxes, plastic tubs, bowls, baskets) | `/Containers/*.blend` | Poly Haven models, [Blender Studio props](https://studio.blender.org/tools/) |
| **Floors** (`Tile`, `Hardwood`, `Granite`, `Metal`, `Rock`, `Cobble`) | `/Floors/*.blend` | [Poly Haven textures](https://polyhaven.com/textures) applied to a simple plane |
| **Outdoor** (`ParkingLot.blend`) | `/Outdoor/*.blend` | Sketchfab CC0 filter — "parking lot" · "warehouse" · "city block"; or replace the whole `Blend File Scene` graph with a Procedural Scene composed from parts |

### Option C — Author your own

The channel doesn't care where the assets came from as long as they
match the drop-in contracts:

- **Toys / Fruit / Containers / Floors**: any Blender `.blend`
  containing a single collection whose root is the visible mesh.
  Naming: put the collection name in the matching
  `package.yml → objects → <Type Name> → filename` entry.
- **`Blend File Scene`**: any `.blend` whose meshes describe the
  environment. Cameras baked into the file are removed on load; light
  and world settings are preserved.

See `packages/toybox/toybox/nodes/object_generators.py` for the
`_TOY_REGISTRY` / `_FRUIT_REGISTRY` / etc. that map display names to
volume paths.

---

## Licensing recap

Everything referenced by the showcase graphs is redistributable and
usable for ML training:

- **Rocketbox** (MIT) — commercial and ML use both permitted, requires
  shipping the MIT license text. Handled by the volume's
  `RocketboxAvatars/LICENSE.md` and `RocketboxAnimations/LICENSE.md`.
- **Poly Haven** (CC0) — no attribution required (though appreciated).
- **Rendered.ai** (CC0) — same.

Full asset-licensing policy for contributions: [LICENSE-ASSETS.md](../LICENSE-ASSETS.md).

Excluded from the showcase (and the wider volume) on license grounds:
Adobe Mixamo (ML-training carve-out), HumGen3D content pack
(unresolved ML-training question), any GPL or CC-BY-SA/NC/ND asset.
See `LICENSE-ASSETS.md` for the decisions log.
