# Contributing to Toybox

Welcome. Toybox is open source under Apache-2.0 with a permissive
asset-licensing policy — we want it to be easy to extend and to run
against your own assets. This guide covers what you need to know to
contribute a node, an asset, or a graph.

## Table of contents

- [Prerequisites](#prerequisites)
- [Local development](#local-development)
- [Adding a node](#adding-a-node)
- [Adding an asset](#adding-an-asset)
- [Adding a showcase graph](#adding-a-showcase-graph)
- [Testing](#testing)
- [PR conventions](#pr-conventions)
- [Licensing rules for contributions](#licensing-rules-for-contributions)
- [Deeper docs](#deeper-docs)

## Prerequisites

- Docker + the [VSCode Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
- An **NVIDIA GPU** with current drivers and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Renders fall back to CPU without a working GPU passthrough and are much slower.
- A [Rendered.ai](https://rendered.ai) account with read access to volume `708b0ca9-d81c-4679-b164-141418507830` (contact `admin@rendered.ai` if it isn't visible on your account). Alternatively, [`docs/GETTING_ASSETS.md`](docs/GETTING_ASSETS.md) shows how to reproduce every asset from public sources so you can develop against your own volume.

The dev container ships Blender 4.2.3 LTS, Python 3.11, and the `anatools` SDK. The image builds automatically the first time you reopen the repo in a container.

## Local development

Toybox's local iteration loop is fast because the channel code is bind-mounted into the running container — edits to `.py` and `.yaml` files take effect immediately, no rebuild.

**Bring up the volume mount (Terminal 1):**

```bash
anamount --channel toybox.yml --email <your-rendered.ai-email>
```

Answer `y` to the "create an API key" prompt on first run. Leave this terminal running while you develop.

**Preview a graph (Terminal 2):**

```bash
ana --channel toybox.yml --graph graphs/default.yml \
    --data . --output ./out --preview --loglevel INFO
```

`--preview` renders a single low-res frame in a few seconds; drop it for a full-quality run. `--loglevel INFO` is essential — the default `ERROR` swallows most useful output.

**Reproducibility** — every run uses `ctx.random` (a per-run seeded `numpy.RandomState`). Same `--seed` + same graph = same output, bit-for-bit.

## Adding a node

Two files per node:

1. **Schema** — a YAML entry in `packages/toybox/toybox/nodes/<file>.yml` declaring inputs, outputs, defaults, and the docstring path.
2. **Implementation** — a Python class in `packages/toybox/toybox/nodes/<file>.py` with an `exec()` method that reads inputs, does work, returns outputs.

Ports on `self.inputs` are always **lists** — index with `[0]` for scalar values. Output keys returned from `exec()` must exactly match the schema's `outputs[].name` strings.

**Register a help page**:

Add a `<NodeName>.md` under `packages/toybox/toybox/docs/` and reference it from the schema:

```yaml
schemas:
  MyNodeClass:
    alias: My Node
    help: toybox/MyNode.md
    inputs: [...]
    outputs: [...]
```

Node help is surfaced from the graph editor's `i` icon at runtime. Keep the doc terse and CV-scientist-focused — describe *what each input controls* in practical terms, not implementation details. See [`packages/toybox/toybox/docs/AvatarRandomizer.md`](packages/toybox/toybox/docs/AvatarRandomizer.md) for the current voice standard.

**Controlled vocabularies** — if the node has a dropdown that maps to an `ana_*` sidecar field, source the values from `packages/toybox/toybox/standards/vocab.py`. That module is the single source of truth for the Rendered.ai Asset Standards §3.4 / §4.4 vocabularies. See `AvatarRandomizerNode` for the pattern.

## Adding an asset

The showcase graphs treat the asset volume as read-only. To add a new asset:

1. Add the `.blend` to the asset volume (or your own volume) in the appropriate subdirectory (`Toys/`, `Fruit/`, `Containers/`, etc.).
2. Author a sibling `<name>.json` sidecar with `ana_kind`, licensing metadata, and (for characters) the demographics fields defined in ASSET_STANDARDS §3.4.
3. Register the asset in `packages/toybox/toybox/package.yml` under `objects:`, mapping a display name to the volume path.
4. Append the display name to the matching registry (`_TOY_REGISTRY`, `_FRUIT_REGISTRY`, etc.) in `packages/toybox/toybox/nodes/object_generators.py`.
5. Add the display name to the matching `select:` list in `packages/toybox/toybox/nodes/object_generators.yml`.

No new node class is required per asset — this is the pattern for community-contributed content.

For characters specifically, see [`docs/GETTING_ASSETS.md`](docs/GETTING_ASSETS.md) for the sidecar conventions the `Avatar Randomizer` relies on.

## Adding a showcase graph

Showcase graphs live in `graphs/`. Convention:

- Filename lowercase-with-underscores: `my_showcase.yml`.
- Header comment names the workflow patterns the graph demonstrates — see [`graphs/avatar_hdri_indoor_test.yml`](graphs/avatar_hdri_indoor_test.yml) for the current template.
- Node `location: {x, y}` positions on a `500 × 400` grid for a clean graph-editor layout (columns 500 px apart, rows 400 px).
- Register the graph in `scripts/sync_platform_to_repo.py::GRAPHS` if it should sync to the QA workspace.
- Add a row to [`graphs/TEST_GRAPHS.md`](graphs/TEST_GRAPHS.md).

## Testing

Toybox has no formal test harness — the smoke test is: does every showcase graph preview clean?

```bash
for g in default fruit_hdri_test avatar_animation_demo avatar_hdri_indoor_test parking_lot_blend_scene; do
  ana --graph /ana/graphs/$g.yml --output /output/smoke_$g --preview --loglevel WARN
done
```

If all five write `preview.png` and no traceback appears in the logs, you're clear.

For a deeper check on a specific graph, run without `--preview` at full resolution and inspect `images/`, `masks/`, `annotations/`.

## PR conventions

- **One commit per conceptual change.** Small commits with clear messages read better than a single mega-commit.
- **Commit message style**: `<area>: <what changed>` — e.g. `graphs: fruit_hdri sink Center Z below origin`, `avatars: replace Appearance Modifier with Avatar Randomizer`.
- **Include a "why"** in the body when the change isn't self-explanatory from the diff.
- **Update docs in the same commit** as the code change, not in a follow-up. This includes per-node `.md` help pages and the `TEST_GRAPHS.md` coverage table.

## Licensing rules for contributions

Toybox is intended to be usable for ML training. Contributed assets must meet the [`LICENSE-ASSETS.md`](LICENSE-ASSETS.md) policy:

- **Allowed licenses** — CC0-1.0, MIT, Apache-2.0, CC-BY-4.0 (attribution satisfied by `NOTICE.md`).
- **Excluded** — any license that carves out ML training, dataset redistribution, or commercial derivative use. This rules out CC-BY-SA / NC / ND, GPL, and any EULA-encumbered content (Mixamo, HumGen3D asset packs).
- **Original-author contributions** must **elect** an allowed license explicitly — bare `"Proprietary"` sidecars are not accepted.
- Add each new asset to `NOTICE.md` on the asset volume with attribution and source URL.

Contribution PRs that ship non-conforming assets will be asked to resource or license-elect before merge.

## Deeper docs

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the channel is put together end to end.
- [`docs/channel.md`](docs/channel.md) — user-facing channel overview.
- [`docs/GETTING_ASSETS.md`](docs/GETTING_ASSETS.md) — per-asset provenance and substitution.
- [`graphs/TEST_GRAPHS.md`](graphs/TEST_GRAPHS.md) — showcase graph reference + node-coverage table.
- **[Rendered.ai channel-development guide](https://support.rendered.ai/dg/Channel-Development.1576501252.html)** — the generic (non-toybox-specific) channel-authoring reference.
- **Blender 4.2 API** — <https://docs.blender.org/api/4.2/> for the underlying render engine.

Thanks for contributing.
