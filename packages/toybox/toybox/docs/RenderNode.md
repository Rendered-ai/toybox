# Render

The **final node** in every graph. Produces the RGB image, the
segmentation masks, and the annotation files that go into your
training dataset.

For multi-frame video output (a walk cycle, an animation), use
`Animation Render` instead.

## Inputs

| Input | What it controls |
|---|---|
| **Scene** | The scene to render. Wire from `Procedural Scene` or `Blend File Scene`. |
| **Resolution (px)** | Image size as `[width, height]`. Default `[1920, 1080]`. Lower resolutions render faster — use `[640, 360]` for iteration, then bump for the final dataset. |
| **Collect Depth and Normal Masks** | `Enabled` = also save per-pixel depth and surface-normal images alongside the RGB. Useful for depth-supervised training. |
| **Calculate Obstruction** | `Enabled` = compute how much of each object is occluded by others (populates occlusion percentages in the annotations). Slower — leave off unless you need it. |

## Output

Render has no output port — it's the terminal node. Files land in the
run's output directory:

- `images/<frame>.png` — the RGB render
- `masks/<frame>.png` — instance segmentation (one colour per object)
- `masks/<frame>-depth.png` — depth map (if Collect Depth and Normal Masks is enabled)
- `masks/<frame>-normal.png` — surface normals (same condition)
- `annotations/<frame>.json` — bounding boxes, class labels, occlusion values
- `preview.png` — a low-res thumbnail in `--preview` runs

## Notes

- Fast iteration: drop resolution to `[640, 360]`, run with `--preview`.
- The objects surfaced in the segmentation mask are the ones wired
  into the scene's `Placed Objects` port — they're the "objects of
  interest".
