# Toybox graph reference

Feature-showcase graphs. Five graphs; together they exercise every node the
channel is meant to demonstrate. All run against the `example` volume
(`708b0ca9-…`), which ships MIT Rocketbox avatars, Poly Haven CC0 HDRIs, and
Rendered.ai CC0 props. HDRI content and pairing suggestions are documented
in `HDRIs/HDRI LIBRARY.md` on the volume (brightness metrics, time-of-day,
avatar-pairing hints, weighted-selection wiring pattern).

```bash
ana --graph /ana/graphs/<file>.yml --output /output/<name> \
    --loglevel INFO --preview
```

---

## Two scene-composition flows

The set demonstrates the channel's two ways to assemble a scene, and
users typically pick one or the other:

- **Procedural Scene flow** (default / fruit_hdri / avatar_animation /
  avatar_hdri_indoor) — build a scene from parts: placement nodes,
  optional Floor, optional Lights, optional HDRI, camera. Best when you
  want per-run randomization variety, node-driven composition, or
  rigid-body physics.
- **Blend File Scene flow** (parking_lot) — adopt a pre-built `.blend`
  file as the entire environment (geometry, lights, world), and overlay
  placed objects / avatars on top. Best when an artist has authored the
  scene, when you need real ground geometry for cast shadows, or when
  the environment is a one-off you don't want to re-model as nodes.

## Set

| Graph | Flow | Showcases |
|---|---|---|
| `default.yml` | Procedural | `Toy` / `Container` / `Floor`, `Place Over Container`, gravity settle, `Color Variation`, `Warp`, `Weight`, overhead `Light` (POINT), `Procedural Scene`, `Procedural Camera` |
| `fruit_hdri_test.yml` | Procedural | `Fruit` (Apple + Orange), `Random Placement` non-overlapping scatter, `Procedural Scene` with noon_grass HDRI (no Floor — HDRI ground reads through), `Outdoor Camera` (Overhead angle hides the missing cast-shadow) |
| `avatar_animation_demo.yml` | Procedural | `Avatar Animation` NLA strip + `Animation Render` (24-frame Rocketbox run cycle on Female_Adult_01, root motion enabled), `Random Choice` heading (E/W with ±10° jitter) keeps the runner laterally near origin, noon_grass HDRI |
| `avatar_hdri_indoor_test.yml` | Procedural | `Avatar Pose` (Idle + Talk, `Random Integer` frame per run) in `Procedural Scene` with 4× indoor `VolumeFile` HDRIs (aggregator's `oneOrMany` picks one per run), HDRI-mode auto-tweaks (Filmic, samples 64, OIDN, 0.5 px pixel-blur), `Random Uniform` azimuth |
| `parking_lot_blend_scene.yml` | Blend File Scene | `Blend File Scene` loading `Outdoor/ParkingLot.blend` as the whole environment, Rocketbox avatar `Manual Placement`-d in front of the parked-car cluster, `mall_parking_lot` HDRI supplies sky + sun, `Parameterized Camera` for exact framing |

Outputs land in `/output/<name>/images/` and `/output/<name>/masks/`. The
`Error: Not freed memory blocks` line at the end of every run is harmless
Blender teardown.

---

## Node coverage

Every live channel node maps to at least one graph, or is deliberately left
uncovered (last column). "Uncovered" nodes are either pure math/plumbing
(exercised transitively) or currently blocked on a fix.

| Category | Node | Covered by |
|---|---|---|
| Objects / Basic | `Toy` | default |
| Objects / Basic | `Fruit` | fruit_hdri |
| Objects / Scene Props | `Container` | default |
| Objects / Scene Props | `Floor` | default |
| Objects / Modifiers | `Color Variation` | default |
| Objects / Modifiers | `Warp` | default |
| Objects / Modifiers | `Scale` | — *(uncovered; retired with spatial_cluster demo)* |
| Objects / Avatars | `Avatar Convert` | avatar_animation, avatar_hdri_indoor, parking_lot |
| Objects / Avatars | `Avatar Pose` | avatar_hdri_indoor, parking_lot |
| Objects / Avatars | `Avatar Animation` | avatar_animation |
| Objects / Avatars | `Avatar Randomizer` | avatar_hdri_indoor *(replaces retired Appearance Modifier — picks one asset-standard avatar per run from a demographic-filtered pool per ASSET_STANDARDS §3.4)* |
| Scenes / Placement | `Manual Placement` | avatar_animation, avatar_hdri_indoor, parking_lot |
| Scenes / Placement | `Place Over Container` | default |
| Scenes / Placement | `Random Placement` | fruit_hdri |
| Scenes / Placement | `Spatial Cluster` | — *(uncovered; retired with spatial_cluster demo)* |
| Scenes / Aggregators | `Procedural Scene` | default, fruit_hdri, avatar_animation, avatar_hdri_indoor |
| Scenes / Aggregators | `Blend File Scene` | parking_lot |
| Scenes / Lights | `Light` | default |
| Scenes / Lights | `Sun` | — *(uncovered; retired with avatar_static — Sun-only lighting with no HDRI produced ugly gray-void hero images; POINT `Light` and HDRI cover the interesting cases)* |
| Simulation / Cameras | `Parameterized Camera` | avatar_animation, avatar_hdri_indoor, parking_lot |
| Simulation / Cameras | `Procedural Camera` | default |
| Simulation / Cameras | `Outdoor Camera` | fruit_hdri |
| Simulation / Cameras | `Indoor Camera` | — *(uncovered; `Parameterized Camera` preferred for exact framing)* |
| Simulation / Render | `Render` | default, fruit_hdri, avatar_hdri_indoor, parking_lot |
| Simulation / Render | `Animation Render` | avatar_animation |
| Simulation / Render | `Generic Render` | — *(uncovered; specialised)* |
| Graph Control | `Random Uniform` | avatar_hdri_indoor |
| Graph Control | `Random Choice` | avatar_animation |
| Graph Control | `Random Integer` | avatar_hdri_indoor |
| Graph Control | `Weight` | default |
| Math | `Vector3D` / `Vector2D` / `Addition` / `Multiply` / `Value` | — *(uncovered plumbing)* |
| Graph Control | `Random Normal` / `String` / `Select Generator` | — *(uncovered plumbing)* |
| Anatools | `VolumeFile` | everywhere that reads volume assets |
