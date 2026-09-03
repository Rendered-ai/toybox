# Copyright 2019-2022 DADoES, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the root directory in the "LICENSE" file or at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Shared port-value parsers for toybox nodes.

These helpers coerce the various forms a port input can take (typed
``"[x, y, z]"`` strings, wired ``Vector3D`` arrays, raw lists/tuples) into
the concrete Python types node ``exec`` methods want to work with.

Centralised here so that any port using the standard ``oneOf`` validation
``string | numLinks:one | array[3]`` has exactly one parser implementation
and one error-message format. Add new parsers here when you add new port
shapes (Vector2D, RGBA, ranges, etc.) rather than open-coding them per node.
"""


def parse_vec3(value, *, name, node="node"):
    """Coerce a port input into a 3-element float tuple.

    Accepts the value shapes Anatools deserialises:
    - ``"[x, y, z]"`` (typed string default in the editor)
    - ``[x, y, z]`` list / tuple (wired from a ``Vector3D`` math node or
      passed through as an array literal)
    - ``""`` (empty string) is treated as ``(0.0, 0.0, 0.0)`` for
      convenience when a port's default got cleared in the UI.

    Args:
        value: The raw value pulled out of ``self.inputs[port][0]``.
        name: Port name, used in the error message.
        node: Node alias / class name, used to prefix the error message
            so the user knows which node rejected the input.

    Returns:
        Tuple of three ``float`` values.

    Raises:
        RuntimeError: If the value does not parse into exactly 3 numbers.
    """
    if value == "" or value is None:
        return (0.0, 0.0, 0.0)
    if isinstance(value, str):
        cleaned = value.replace("[", "").replace("]", "").strip()
        parts = [p for p in cleaned.split(",") if p.strip()] if cleaned else []
    else:
        parts = list(value)
    if len(parts) != 3:
        raise RuntimeError(
            f"{node}: '{name}' must be a 3-element vector, "
            f"got {len(parts)} value(s): {value!r}"
        )
    return tuple(float(p) for p in parts)
