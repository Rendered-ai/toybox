# Procedural Scene

Assembles a scene **from parts**: placed objects (or characters), a
floor, optional container, lights, an HDRI backdrop, and a camera.
The default choice for scenes you're building up procedurally.

Sibling to `Blend File Scene`, which loads a pre-authored environment
`.blend` instead. Choose Procedural Scene when the scene doesn't need
authored geometry — a tabletop scatter, a person against an HDRI, a
container full of toys.

## Inputs

| Input | What it controls |
|---|---|
| **Placed Objects** | The objects or characters that populate the scene. Required. From `Random Placement`, `Place Over Container`, `Manual Placement`, etc. |
| **Lights** | One or more `Light` / `Sun` nodes. Optional if you're using an HDRI as the light source. |
| **Floor Generator** | Optional floor beneath the objects. When wired, the scene automatically runs a physics settle so objects land on the floor. |
| **Container Generator** | Optional container (bin, basket) that sits on the floor. Only meaningful with a Floor Generator. |
| **HDRI** | An HDR sky/environment image that serves as backdrop AND primary light source. Wire multiple for per-run variety. |
| **HDRI Rotation (deg)** | Rotates the HDRI around the vertical axis — sweeps the sun position. Wire a `Random Uniform` for variation. |
| **Camera** | The view. Wire from `Procedural Camera`, `Outdoor Camera`, or `Parameterized Camera`. |

## Output

| Output | Where it goes |
|---|---|
| **Scene** | The assembled scene. Wire into `Render` (still image) or `Animation Render` (video). |

## Common configurations

**Tabletop toys in a container** — Placed Objects = toys via
`Place Over Container`, Floor Generator + Container Generator wired,
Lights = a POINT light overhead. Physics settles the toys.

**Person against a backdrop** — Placed Objects = an avatar via
`Manual Placement`, HDRI wired (indoor or outdoor image), Camera at
eye level pointed at the person. No Floor needed.

**Fruit scatter on grass** — Placed Objects = fruit via
`Random Placement`, HDRI = an outdoor grass image, no Floor (the HDRI
provides the ground look).

## Notes

- **When an HDRI is wired**, the scene switches to HDRI-friendly
  render settings automatically — more samples, denoising, softer
  film response. You don't need to configure anything.
- **When multiple HDRIs are wired**, one is picked at random each run.
