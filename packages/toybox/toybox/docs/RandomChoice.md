# Random Choice

Picks one element at random from a **list of options** — a colour
name, a container type, an XYZ triple, any discrete value.

## Inputs

| Input | What it controls |
|---|---|
| **Options** | A list of choices as a JSON string. Example: `["Red","Green","Blue","Yellow"]` or `["[0,0,-90]","[0,0,90]"]`. Type directly or wire from another node. |

## Output

| Output | Where it goes |
|---|---|
| **Selection** | One element from the list. Wire into whatever downstream input needs the picked value. |

## Examples

**Random colour name** — Options `["Red","Green","Blue","Yellow"]`,
wire into a `Color Variation` node's `Color` input.

**Random walking direction** — Options
`["[0,0,-90]", "[0,0,90]", "[0,0,-100]", "[0,0,100]"]`, wire into a
`Manual Placement` node's `Rotation (deg)` input. Each run picks one
heading.

**Random container** — Options
`["Dark Wooden Box","Blue Tub","Yellow Bowl"]`, wire into a
`Container` node's `Container Type`.

## Notes

- Same random seed produces the same pick — datasets reproduce.
