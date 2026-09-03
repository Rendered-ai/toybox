# Toybox architecture

How the pieces fit together end-to-end, so a new contributor can see
where their work lands. For the generic channel-authoring reference
(applies to any Rendered.ai channel, not just Toybox), see the
[Rendered.ai channel-development guide](https://support.rendered.ai/dg/Channel-Development.1576501252.html).

## The five layers

```
┌────────────────────────────────────────────────────────────────────┐
│  Graph            graphs/*.yml                                     │
│  Wires nodes together, sets per-run parameters                     │
├────────────────────────────────────────────────────────────────────┤
│  Node             packages/toybox/toybox/nodes/*.py + *.yml        │
│  Python class implementing exec(); YAML schema declaring ports     │
├────────────────────────────────────────────────────────────────────┤
│  Standards        packages/toybox/toybox/standards/vocab.py        │
│  Controlled vocabularies from Rendered.ai Asset Standards          │
├────────────────────────────────────────────────────────────────────┤
│  Package          packages/toybox/                                 │
│  Bundle of nodes + docs + package.yml asset registry               │
├────────────────────────────────────────────────────────────────────┤
│  Channel          toybox.yml + .devcontainer/Dockerfile            │
│  Docker image + platform registration + anatools built-in nodes    │
└────────────────────────────────────────────────────────────────────┘
```

Each layer is loosely coupled to the next: a graph doesn't care how a
node is implemented, a node doesn't care where the channel deploys, and
the channel doesn't care what graphs run against it.

## Graph → Render lifecycle

```
   toybox.yml
      │
      │ registers packages, anatools nodes, remote-channel config
      ▼
   Docker image (built via .devcontainer/Dockerfile)
      │
      │ ana wrapper mounts /workspace/ana → /ana, runs entrypoint
      ▼
   ana --graph <path>.yml
      │
      │ 1. parse graph YAML → node instances
      │ 2. resolve inputs from wired links and typed values
      │ 3. topologically sort nodes → execute exec() one at a time
      │ 4. terminal Render / Animation Render writes to /output
      ▼
   /output/{images, masks, annotations, metadata}/…
```

Each node's `exec()` runs once per graph interpretation. State flows
node-to-node through the return dictionary; there's no global scene
until the scene aggregator (`Procedural Scene` / `Blend File Scene`)
walks the collected `Placed Objects` and materializes them into
`bpy.context.scene`.

## Node internals

A node is:

- **YAML schema** — declares `alias`, `inputs`, `outputs`, `help`,
  UI category, and validation rules. Consumed at graph-load time to
  build the port list the graph editor shows.
- **Python class** — subclass of `anatools.lib.node.Node` with an
  `exec()` method. Reads `self.inputs`, returns a dict keyed by the
  YAML's output port names.

Ports on `self.inputs` are always **lists** — a port that receives one
link from upstream shows up as a one-element list; a `oneOrMany` port
shows up as a variable-length list. Always index with `[0]` for
single-value ports.

**Determinism** — every source of randomness must route through
`ctx.random` (a per-run seeded `numpy.RandomState`). Never call
`random.random()`, `np.random.uniform()`, or read `time.time()` from
inside a node — those break dataset reproducibility.

## The standards module

`packages/toybox/toybox/standards/vocab.py` is the canonical source
of controlled vocabularies from Rendered.ai Asset Standards. Both node
runtime code and node YAML schemas mirror the tuples defined there:

- **Character demographics** (§3.4) — `GENDERS`, `ETHNICITIES`,
  `AGE_GROUPS`, `BUILDS`, `CLOTHING`, `CLIMATES`, `SETTINGS`.
- **Animation** (§4.4) — `ANIMATION_CATEGORIES`, `TEMPOS`.
- **Skeleton** (§2) — `SKELETONS`, plus `SKELETON_ALIASES`
  (`humgen` ↔ `rendered_humanoid`) and a `normalize_skeleton()` helper.
- **Rest pose** (§3.3) — `REST_POSES`.
- **Sidecar** (§1.4) — `ORIGINS`, `FILE_FORMATS`.

Adding a new value to a controlled vocabulary is a one-line edit in
`vocab.py` plus the matching `select:` update in the node schema. The
`AvatarRandomizerNode` is the current reference for reading vocab from
Python + mirroring in YAML.

## Asset conventions

### Package-registered objects

Toys, Fruit, Containers, Floors — each is a `.blend` on the asset
volume, referenced from `packages/toybox/toybox/package.yml`:

```yaml
objects:
  Skateboard:
    filename: example:Toys/Skateboard_v2.blend
```

The `filename` uses a `<volume-alias>:<path>` scheme where the
volume alias is defined in the top of the same `package.yml`:

```yaml
volumes:
  example: 708b0ca9-d81c-4679-b164-141418507830
```

Node display names are decoupled from asset paths — that's what the
`_TOY_REGISTRY` / `_FRUIT_REGISTRY` dicts in `object_generators.py` do.
The graph author picks by display name; the runtime resolves through
the registry to a `package.yml` entry to a volume path to a file.

### Standards-conforming avatars

Rocketbox avatars aren't in `package.yml` — the `Avatar Convert`
node reads them straight from a `FileObject` supplied by
`VolumeFile` or `Avatar Randomizer`. Each avatar has a sibling
`<name>.json` sidecar carrying `ana_*` metadata per ASSET_STANDARDS
§3.4 (demographics, rest pose, skeleton, height, licence). See
[`docs/GETTING_ASSETS.md`](GETTING_ASSETS.md) for what the sidecar
schema needs to look like.

## Two scene-composition flows

Every graph ends at either `Procedural Scene` or `Blend File Scene`,
and the choice determines how the environment gets assembled:

| Flow | When to use |
|---|---|
| **Procedural Scene** | Compose the environment from parts (Floor + Container + Lights + HDRI). Right for tabletop scenes, HDRI backdrops, and any case where you want per-run randomization to sweep across everything. |
| **Blend File Scene** | Load a pre-authored `.blend` as the whole environment; overlay placed objects on top. Right when an artist has built the space, or when you need real ground geometry for cast shadows. |

Both aggregators end at `Render` (single frame) or `Animation Render`
(multi-frame video). Both require an upstream camera node; Blend File
Scene additionally purges any cameras baked into the loaded blend.

## Deploy lifecycle

Local iteration:

- Code changes in `packages/toybox/toybox/**/*.py` and
  `graphs/**/*.yml` are picked up **live** via the bind mount —
  no rebuild needed.
- Dockerfile / requirements changes trigger an image rebuild
  automatically the next time `ana` runs (fingerprint-keyed cache).

Platform deploy:

```bash
anadeploy
```

Reads `.devcontainer/Dockerfile` (**not** the top-level `Dockerfile`,
which is a stale copy) plus `toybox.yml`. Pushes the image, updates
platform-side channel metadata, and — if `docs/channel.md` changed —
uploads the channel documentation page.

Graphs are separately synced to a QA workspace via
`scripts/sync_platform_to_repo.py`, which uploads each hero graph and
optionally kicks off a smoke dataset per graph.

## Key files, at a glance

| Path | Role |
|---|---|
| `toybox.yml` | Channel config — registers packages, anatools built-in nodes, platform metadata. |
| `.devcontainer/Dockerfile` | The image that gets built and deployed. |
| `packages/toybox/toybox/nodes/*.py` + `.yml` | Node implementations + schemas. |
| `packages/toybox/toybox/standards/vocab.py` | Controlled vocabularies. |
| `packages/toybox/toybox/docs/*.md` | Per-node help pages surfaced from the graph editor's `i` icon. |
| `packages/toybox/toybox/package.yml` | Registered asset objects (Toys, Fruit, Containers, Floors). |
| `graphs/*.yml` | Showcase graphs. |
| `graphs/TEST_GRAPHS.md` | Showcase-graph reference + node-coverage table. |
| `docs/channel.md` | Platform-published channel documentation. |
| `docs/GETTING_ASSETS.md` | Per-asset provenance and substitution guide. |
| `mappings/*.yml` | Annotation class mappings. |
| `scripts/sync_platform_to_repo.py` | Sync showcase graphs to the QA workspace. |
| `scripts/stamp_rocketbox_sidecars.py` | Asset-side script that stamps `ana_*` metadata on the Rocketbox sidecars. |
