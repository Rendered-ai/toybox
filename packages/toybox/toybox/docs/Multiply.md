# Multiply

Multiplies two numbers and outputs the product. Companion to
`Addition`. Useful for scaling a sampled value (e.g. multiplying a
`Random Uniform` output by a per-graph factor to convert its range).

## Inputs

| Input | What it controls |
|---|---|
| **Input A** | First number. Type a literal or wire from another node. |
| **Input B** | Second number. |

## Output

| Output | Where it goes |
|---|---|
| **Product** | `Input A × Input B`. Wire into any numeric input downstream. |

## Notes

- Default `1.0` on each input means Multiply is a pass-through if you
  only wire one side.
