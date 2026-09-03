# Animation Render

Renders a **range of frames** with per-frame masks and annotations —
one image per frame. Use for video datasets: a person walking across a
scene, an animation cycle, or any sequence where motion matters.

For a single still image, use `Render` instead.

## Inputs

| Input | What it controls |
|---|---|
| **Scene** | The scene to render. Wire from `Procedural Scene` or `Blend File Scene`. |
| **Start Frame** | First frame to render. Default `1`. |
| **End Frame** | Last frame to render. A 30 fps walk cycle is typically 30–60 frames. |
| **Frame Step** | `1` = render every frame, `2` = every other frame, etc. Use `3`–`5` for quick previews; `1` for final datasets. |
| **Resolution (px)** | Image size as `[width, height]`. Default `[1024, 1024]`. Lower renders faster. |
| **Collect Depth and Normal Masks** | `Enabled` = also save per-pixel depth and surface normals alongside the RGB. Useful for depth-supervised training. |
| **Save Blend File** | `Enabled` = save a debug scene file so you can inspect the setup afterwards. |

## Output

Animation Render is a terminal node — no output port. Files land in
the run's output directory:

- `images/<run>-<frame>-RGBCamera.png` — the RGB render per frame
- `masks/<run>-<frame>-RGBCamera.png` — instance segmentation per frame
- `annotations/<run>-<frame>-RGBCamera-ana.json` — bounding boxes, labels, per-frame
- `metadata/<run>-<frame>-RGBCamera-metadata.json` — per-frame scene metadata

## Common configurations

**Preview a 24-frame walk cycle** — Start Frame `1`, End Frame `24`,
Frame Step `1`, Resolution `[640, 640]`.

**Final training run** — same frame range, Frame Step `1`, full
resolution.

**Every-other-frame preview** — Frame Step `2` cuts render time in
half at the cost of temporal resolution.

## Notes

- Use `Random Choice` on the character's heading (via
  `Manual Placement`) to vary direction across runs so the walking
  character isn't identical every time.
