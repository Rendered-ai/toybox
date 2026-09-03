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
"""Spatial Cluster placement node.

Places a set of objects at deterministic XY positions on a disc of a given
radius around a center point, using one of three patterns (Random / Circular /
Hexagonal) with optional collision avoidance based on a user-supplied spacing.

Unlike RandomPlacement / PlaceOverContainer this node does not run any
physics. Objects land where the geometry says they should. If you wire a
Floor into the downstream Scene node the gravity bake will move them --
typically you use Spatial Cluster without a floor, or prefer Random
Placement when you want a physics pile.

Cleanup-port of ``SingleBlenderFile/nodes/spatial_cluster.py``:
- Relies solely on ``ctx.random`` for determinism (no per-node hash advancement).
- Replaces the temp-load bounding-box probe with an explicit ``Object Spacing``
  input so students can tune collision avoidance directly.
- Uses toybox's ``file_to_objgen`` + ``ToyboxChannelObject`` and
  ``CreateBranchGenerator`` conventions, matching RandomPlacement.
- Output renamed ``Objects`` -> ``Objects of Interest`` for channel consistency.
"""
import logging
import math

from mathutils import Vector

import anatools.lib.context as ctx
from anatools.lib.file_handlers import file_to_objgen
from anatools.lib.generator import CreateBranchGenerator
from anatools.lib.node import Node

from toybox.lib.parsers import parse_vec3
from toybox.nodes.object_generators import ToyboxChannelObject

logger = logging.getLogger(__name__)


class SpatialClusterClass(Node):
    """Spatial cluster generator with configurable pattern and collision spacing."""

    def exec(self):
        logger.info("Executing %s", self.name)

        # Single Vector3D Center input (replaces former Center X/Y/Z scalars
        # so the port pairs cleanly with a Vector3D math node).
        center = Vector(parse_vec3(
            self.inputs["Center (m)"][0], name="Center (m)", node="Spatial Cluster"
        ))
        radius = float(self.inputs["Radius"][0])
        num_objects = min(1000, int(self.inputs["Number of Objects"][0]))
        spacing = float(self.inputs["Object Spacing (m)"][0])
        pattern = self.inputs["Pattern Type"][0]
        allow_overlap = self.inputs["Allow Overlap"][0] == "Enabled"

        logger.info(
            "SpatialCluster: center=%s radius=%.3f n=%d spacing=%.3f "
            "pattern=%s allow_overlap=%s",
            tuple(center), radius, num_objects, spacing, pattern, allow_overlap,
        )

        # Generators and round-robin / weighted selection (same pattern as
        # RandomPlacement for consistency).
        objects_input = self.inputs["Object Generators"]
        if not objects_input or objects_input[0] == "":
            logger.warning("SpatialCluster: no Object Generators provided")
            return {"Objects of Interest": []}

        generators = file_to_objgen(objects_input, ToyboxChannelObject)
        branch_generator = CreateBranchGenerator(generators)

        # Compute placement points (xy only; z is fixed to Center Z).
        if pattern == "Hexagonal":
            points = _generate_hexagonal_points(center, radius, num_objects, spacing)
        elif pattern == "Circular":
            points = _generate_circular_points(center, radius, num_objects, spacing, allow_overlap)
        else:  # Random (default)
            points = _generate_random_points(center, radius, num_objects, spacing, allow_overlap)

        if not points:
            # Fallback: a single object at the center keeps the graph valid.
            logger.warning("SpatialCluster: no points generated, placing single object at center")
            points = [center]

        # Spawn an object at each point.
        placed = []
        for i, p in enumerate(points):
            obj = branch_generator.exec()
            obj.root.location = p
            # Z-only random rotation so objects stay upright; matches original.
            obj.root.rotation_euler = (0.0, 0.0, ctx.random.uniform(0, 2 * math.pi))
            if hasattr(obj, "ooi"):
                obj.ooi = True
            placed.append(obj)

        logger.info("SpatialCluster: placed %d objects (requested %d)",
                    len(placed), num_objects)
        return {"Objects of Interest": placed}


# ---------------------------------------------------------------------------
# Pattern generators (pure geometry; use ctx.random only for stochastic paths)
# ---------------------------------------------------------------------------

def _generate_random_points(center, radius, n, spacing, allow_overlap):
    """Rejection-sample points inside a disc of ``radius`` around ``center``.

    When ``allow_overlap`` is False, a candidate point is kept only if it lies
    at least ``spacing`` meters away from every previously accepted point.
    Gives up after ``n * 10`` attempts to avoid pathological loops on tight
    parameter combinations.
    """
    points = []
    max_attempts = max(1, n * 10)
    for _ in range(max_attempts):
        if len(points) >= n:
            break
        angle = ctx.random.uniform(0, 2 * math.pi)
        # sqrt() for uniform density on the disc (not the radius).
        dist = radius * math.sqrt(ctx.random.uniform(0, 1))
        candidate = Vector((
            center.x + dist * math.cos(angle),
            center.y + dist * math.sin(angle),
            center.z,
        ))
        if not allow_overlap and _collides(candidate, points, spacing):
            continue
        points.append(candidate)
    return points


def _generate_circular_points(center, radius, n, spacing, allow_overlap):
    """Even spacing around a single ring. Falls back to concentric rings if
    ``n`` objects don't fit at ``spacing`` on one ring."""
    if n <= 1:
        return [center]

    if allow_overlap:
        angle_step = 2 * math.pi / n
        return [
            Vector((
                center.x + 0.8 * radius * math.cos(i * angle_step),
                center.y + 0.8 * radius * math.sin(i * angle_step),
                center.z,
            ))
            for i in range(n)
        ]

    circumference = 2 * math.pi * radius
    max_on_ring = max(1, int(circumference / spacing))
    if n <= max_on_ring:
        angle_step = 2 * math.pi / n
        return [
            Vector((
                center.x + radius * math.cos(i * angle_step),
                center.y + radius * math.sin(i * angle_step),
                center.z,
            ))
            for i in range(n)
        ]
    return _generate_multi_ring_points(center, radius, n, spacing)


def _generate_multi_ring_points(center, radius, n, spacing):
    """Concentric rings, stepping outward by ``spacing`` until ``n`` points are
    placed or the outer radius is exceeded."""
    points = []
    ring_radius = spacing
    while len(points) < n and ring_radius <= radius:
        circumference = 2 * math.pi * ring_radius
        on_ring = min(max(1, int(circumference / spacing)), n - len(points))
        angle_step = 2 * math.pi / on_ring
        for i in range(on_ring):
            angle = i * angle_step
            points.append(Vector((
                center.x + ring_radius * math.cos(angle),
                center.y + ring_radius * math.sin(angle),
                center.z,
            )))
        ring_radius += spacing
    return points


def _generate_hexagonal_points(center, radius, n, spacing):
    """Hex-packed grid of points clipped to the disc."""
    if spacing <= 0:
        spacing = 0.01
    # Bound the grid generously; we'll clip by radius and take the first n.
    span = int(math.ceil(2 * radius / spacing)) + 1
    points = []
    for row in range(-span, span + 1):
        if len(points) >= n:
            break
        for col in range(-span, span + 1):
            if len(points) >= n:
                break
            offset_x = spacing * col
            offset_y = spacing * row * math.sqrt(3) / 2
            if row % 2:
                offset_x += spacing / 2
            p = Vector((center.x + offset_x, center.y + offset_y, center.z))
            if ((p - center).length) <= radius:
                points.append(p)
    return points


def _collides(candidate, existing, spacing):
    """Return True if ``candidate`` is closer than ``spacing`` to any point in ``existing``."""
    for p in existing:
        if (candidate - p).length < spacing:
            return True
    return False
