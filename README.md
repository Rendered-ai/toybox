# Toybox

**Open-source synthetic-data channel for [Rendered.ai](https://rendered.ai).** Generate annotated images and video of humans and objects in real environments — rendered by Blender Cycles, seeded per run, permissively licensed for ML training.

<p align="center">
  <img src="docs/output/avatar_hdri_indoor.png" alt="Medical avatar in a warm-toned interior" width="49%"/>
  <img src="docs/output/parking_lot.png" alt="Business avatar walking through a parking lot" width="49%"/>
</p>

## What Toybox produces

Every run writes to a standard directory layout that goes straight into most training pipelines:

- **`images/`** — the RGB render, one file per frame.
- **`masks/`** — instance segmentation (one colour per object). Add depth and surface-normal passes with one toggle on the Render node.
- **`annotations/`** — per-frame JSON: bounding boxes, class labels, per-object occlusion values.
- **`metadata/`** — per-frame scene metadata, seed, and every wired parameter value for reproducibility.

Same random seed + same graph = same output, bit-for-bit. Datasets reproduce.

## Showcase graphs

The `graphs/` directory ships five hero graphs. Each demonstrates a different channel workflow; together they exercise every node the channel offers. Full reference in [`graphs/TEST_GRAPHS.md`](graphs/TEST_GRAPHS.md).

### Rigid-body physics — `default.yml`

![Toys settled in a copper container](docs/output/default.png)

Toys drop into a random container and gravity resolves them into a pile. Container / Floor / Light and colour randomization sweep across runs; Outdoor Camera picks a fresh viewpoint each run so the same scene is captured from Overhead / Side / Corner / Entrance angles.

### HDRI outdoor scene — `fruit_hdri_test.yml`

![Apples and oranges on grass, top-down](docs/output/fruit_hdri.png)

Fruit scatter on a Poly Haven grass HDRI with no Floor node — the HDRI's own ground reads through. The sun angle rotates per run for lighting variety across a dataset.

### Video-frame pipeline — `avatar_animation_demo.yml`

![Rocketbox character mid-stride on grass](docs/output/avatar_animation.png)

Rocketbox `Bip01` rig converted to `rendered_humanoid`, animated with a run cycle whose baked root motion drives the character forward. Animation Render writes per-frame masks and annotations for 24 frames per run. Random Choice constrains heading to East/West with jitter.

### Avatar diversity + HDRI backdrop — `avatar_hdri_indoor_test.yml`

![Medical avatar in a warm-toned brick interior](docs/output/avatar_hdri_indoor.png)

Different female avatar per run, sampled from a demographic-filtered pool via `Avatar Randomizer`. Pose file, pose frame, HDRI, HDRI rotation, position jitter, and heading jitter all vary independently — five axes of per-run variation that compose combinatorially.

### Blend File Scene — `parking_lot_blend_scene.yml`

![Business avatar walking through a mall parking lot](docs/output/parking_lot.png)

BYO artist-authored `.blend`: the parking lot's asphalt geometry, cars, and world load wholesale, and a Rocketbox avatar walks through it. Camera XY jitters around a fixed look-at so different subsets of the parked-car cluster appear behind the avatar across runs.

## Open source, permissively licensed

- **Code** — Apache-2.0 ([`LICENSE`](LICENSE)).
- **Assets** — every asset the showcase graphs reference is CC0 (Rendered.ai fruit / toys / containers / floors / parking-lot scene, Poly Haven HDRIs) or MIT (Microsoft Rocketbox avatars and animations). Full policy: [`LICENSE-ASSETS.md`](LICENSE-ASSETS.md).
- **ML training** — explicitly permitted. Toybox deliberately does not depend on assets whose licenses ambiguously address ML-training use (Mixamo, HumGen3D content pack, or any GPL / CC-BY-SA / NC / ND asset).

Cloning without Rendered.ai account access? [`docs/GETTING_ASSETS.md`](docs/GETTING_ASSETS.md) tells you where every asset came from and how to reproduce or substitute it from public sources.

## Quick start

**Prerequisites:**

- Docker + VSCode's Dev Containers extension
- NVIDIA GPU with current drivers + NVIDIA Container Toolkit (renders fall back to CPU without, and are much slower)
- A Rendered.ai account with read access to volume `708b0ca9-d81c-4679-b164-141418507830` (contact `admin@rendered.ai` if the volume isn't visible)

**Bring it up:**

Open the repo in VSCode and choose **Reopen in Container**. The first build is slow (Blender 4.2 LTS + Miniconda are downloaded and extracted). Subsequent starts are instant.

Sanity check:

```bash
blender --version                 # 4.2.3 LTS
python -c "import anatools, bpy"  # both must import
```

**Render a hero:**

Two terminals. Terminal 1 holds the volume mounts open:

```bash
anamount --channel toybox.yml --email <your-rendered.ai-email>
```

Terminal 2 runs a graph:

```bash
ana --channel toybox.yml --graph graphs/avatar_hdri_indoor_test.yml \
    --data . --output ./out --preview --loglevel INFO
```

`--preview` renders one frame at low resolution — useful for iteration. Drop it for a full-quality run; add `--seed <N>` for reproducibility.

Output lands in `./out/`: `images/`, `masks/`, `annotations/`, `metadata/`, plus a top-level `preview.png` in `--preview` runs.

## Documentation

| Doc | Audience |
|---|---|
| [`docs/channel.md`](docs/channel.md) | Platform-published overview — a first look for anyone browsing the channel on rendered.ai. |
| [`docs/GETTING_ASSETS.md`](docs/GETTING_ASSETS.md) | How to acquire or substitute every asset the showcase graphs reference. |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How the channel is put together — nodes, packages, standards module, deploy lifecycle. |
| [`graphs/TEST_GRAPHS.md`](graphs/TEST_GRAPHS.md) | Showcase-graph reference + node-coverage table. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Adding a node, adding an asset, PR conventions, licensing rules for contributions. |
| Per-node help pages | Each node's `.md` under `packages/toybox/toybox/docs/`, surfaced by the graph editor's `i` icon at runtime. |

## Mappings

Ship three annotation mappings in `mappings/`:

| Mapping | Description |
|---|---|
| `default.yml` | Every object gets a unique class. |
| `rubikcube.yml` | Only Rubik's Cubes are annotated; everything else is a distractor. |
| `toy.yml` | All toys collapse to a single class. |
