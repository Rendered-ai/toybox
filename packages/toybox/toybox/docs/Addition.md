# Addition

Adds two numbers and outputs the sum. A math helper for
parameterising other nodes — computing a derived sample count, an
offset from an upstream value, etc.

## Inputs

| Input | What it controls |
|---|---|
| **Input A** | First number. Type a literal or wire from another node. |
| **Input B** | Second number. |

## Output

| Output | Where it goes |
|---|---|
| **Sum** | `Input A + Input B`. Wire into any numeric input downstream. |

## Notes

- For more complex expressions, chain Addition and `Multiply` nodes.
