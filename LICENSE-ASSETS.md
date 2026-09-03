# Toybox — Asset Licensing Policy

**Applies to**: every third-party asset (mesh, rig, animation, texture,
HDRI, sound, shader library, addon zip, sidecar-referenced file) that is
shipped with the Toybox channel, referenced by a graph in
`graphs/`, or staged on a volume declared in `packages/toybox/toybox/package.yml`.

**Code license** for the channel itself is Apache-2.0 (`LICENSE`); this
document covers **assets only**.

---

## 1. Allowlist

An asset MAY be included in Toybox iff **both** of the following hold:

### 1a. License is on this list

| License | SPDX | Notes |
|---|---|---|
| **CC0 1.0 Universal** | `CC0-1.0` | Public-domain dedication. **Preferred**. Zero attribution obligation. |
| **MIT** | `MIT` | Requires shipping the license text; satisfied by an entry in `NOTICE.md`. |
| **Apache License 2.0** | `Apache-2.0` | Same attribution mechanism as MIT plus a patent grant. |
| **Creative Commons Attribution 4.0** | `CC-BY-4.0` | Requires attribution; satisfied by an entry in `NOTICE.md` naming author + source URL. |

### 1b. The specific asset's terms do NOT carve out any of:

- Machine-learning / AI training on the asset or on renders derived from it.
- Redistribution of the asset (raw or converted) on customer-shared
  volumes / registries.
- Commercial use of derivative outputs (renders, models trained on
  renders, dataset packages).

Predicate (1b) is what disqualifies otherwise-"free" sources:

| Source | Nominal license | Why excluded |
|---|---|---|
| **Adobe Mixamo** | "Free for personal and commercial use" | FAQ explicitly excludes ML-training and prohibits standalone redistribution of raw assets. |
| **HumGen3D (Blender Market)** | Blender Market Royalty Free | EULA predates the AI-training question; vendor has not confirmed training-data use in writing. |
| **Adobe Stock free tier** | Adobe Stock license | Carves out ML training. |
| **Sketchfab "Free download" (non-CC)** | Case-by-case | Most non-CC free downloads prohibit AI/ML use. |
| **"Free for personal use only"** | Various | Not commercial-safe. |

## 2. Excluded license families

Even if permissive in every other respect, these are **not** accepted:

| License | SPDX | Reason |
|---|---|---|
| CC BY-SA 4.0 | `CC-BY-SA-4.0` | Share-alike is viral onto downstream datasets and models. |
| CC BY-NC (any) | `CC-BY-NC-*` | Non-commercial forbids the channel's primary use. |
| CC BY-ND (any) | `CC-BY-ND-*` | No-derivatives forbids rendering, which is a derivative. |
| GPL / AGPL / LGPL | `GPL-*`, `*-GPL-*` | Copyleft; not designed for asset distribution and viral onto downstream. |
| Proprietary / EULA-encumbered | — | Includes anything requiring per-project sign-off. |

## 3. Original-author work

Assets authored in-house by Rendered.ai contributors are equivalent to
CC0 **iff** they are explicitly relicensed CC0 (or one of the other
allowlisted licenses) at contribution time. An unqualified "Proprietary,
Rendered.ai-authored" tag is **not** sufficient for a channel intended
to be open-sourced — the org must pick a license for each original
asset before it ships.

## 4. Verification

Every asset carries a sidecar `<name>.json` per `ASSET_STANDARDS.md` §1.4
with a `license` field. Two consistency rules:

1. The `license` field MUST be one of the SPDX identifiers in the §1a
   table, or `original-author-<spdx>` where `<spdx>` names the elected
   license (e.g. `original-author-CC0-1.0`).
2. The `NOTICE.md` that lives at the root of the volume hosting the
   asset MUST contain a corresponding entry for every non-CC0 asset
   (including original-author-CC0 assets when the author asks to be
   credited). For the Toybox public-share volume this file is
   `708b0ca9-…/NOTICE.md`.

A CI check (`scripts/validate_licenses.py`) fails contribution when
either rule is violated. Run it on any volume root:

```bash
python3 scripts/validate_licenses.py /path/to/volume
# add --strict to also require a sidecar next to every .blend / .fbx /
# .glb / .gltf / .obj / .usd asset.
```

## 5. Adding a new source

Before staging an asset from a new source:

1. Identify the license (SPDX where possible; verbatim text otherwise).
2. Confirm predicate (1b) — read the vendor's FAQ / terms specifically
   for AI-training and redistribution language.
3. Add a row to the `NOTICE.md` on the volume the asset will be
   staged on.
4. If the license is not already in the §1a table, open a decision
   entry in `ASSET_STANDARDS.md` before merging.

## 6. Attribution mechanism

Attribution for MIT / Apache-2.0 / CC-BY-4.0 assets is satisfied by:

1. An entry in the volume-side `NOTICE.md` at the root of the volume
   hosting the asset (`708b0ca9-…/NOTICE.md` for the Toybox
   public-share volume). The NOTICE travels with the volume so it is
   present wherever the assets are consumed.
2. Retention of the upstream `LICENSE` file next to the asset on the
   volume (already done for Rocketbox at
   `708b0ca9-…/RocketboxAvatars/LICENSE.md` and
   `708b0ca9-…/RocketboxAnimations/LICENSE.md`).

Renders / datasets produced by Toybox do **not** need to individually
attribute each asset — the volume-level `NOTICE.md` covers the pipeline
that produced them.
