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
"""Camera nodes for toybox.

Three cameras covering the common placement strategies:

- **Procedural Camera** -- procedurally-placed camera for scenes with
  objects near the world origin. Randomly places the camera on a
  quarter-circle hemisphere at the requested height (elevation always
  >= 45 degrees); user picks the height, roll, and look-at point. Works
  with both Procedural Scene and origin-centered Blend File Scene.
  (Previously named "Indoor Camera".)
- **Outdoor Camera** -- procedural placement around a large scene using
  named view angles (Overhead, Side, Corner, Entrance). User sets a
  distance, a focal length, and picks an angle.
- **Parameterized Camera** -- full manual control. User provides the exact
  camera position, the exact look-at point, and the focal length. The
  escape hatch for BYO-blend scenes or any case where the other two don't
  fit.

All three build a fresh Blender camera object unlinked from any scene
collection. Linking and activating the camera (``scn.camera``) is handled
by the downstream scene aggregator node -- Blend File Scene always, and
Procedural Scene when a Camera is wired (else it falls back to its own
embedded Look Down camera).
"""
import logging
import math

import bpy

import anatools.lib.context as ctx
from anatools.lib.node import Node

# Reuse the toybox point_at helper so camera orientation is consistent
# across all camera nodes (Procedural Camera uses it too).
from toybox.nodes.simulation import point_at

logger = logging.getLogger(__name__)


def _new_camera(name, focal_length_mm):
    """Create a fresh unlinked Blender camera object.

    The object is NOT linked into any scene collection and ``scene.camera``
    is NOT set -- ``RenderNode`` owns both of those steps. This mirrors the
    existing contract used by the Indoor camera in ``simulation.py`` so all
    camera nodes behave identically from Render's point of view.
    """
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = focal_length_mm
    cam_obj = bpy.data.objects.new(name, cam_data)
    return cam_obj


class CameraNode(Node):
    """Procedural top-down-ish camera for scenes with objects near the origin.

    Randomly places the camera on a hemisphere at the given height
    (elevation always >= 45 degrees) and aims it at the look-at point.
    Suitable for both Procedural Scene and origin-centered Blend File
    Scene workflows. Exposed to graphs as ``Procedural Camera`` (formerly
    ``Indoor Camera``).
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        height = float(self.inputs["Location Height (m)"][0])
        x = ctx.random.uniform(0, height)
        y_limit = math.sqrt(height ** 2 - x ** 2)
        y = ctx.random.uniform(-y_limit, y_limit)

        roll = float(self.inputs["Roll (degrees)"][0])
        # Prefer the new [X, Y, Z] array port; fall back to legacy
        # Look At X / Look At Y / Look At Z scalars for graphs that predate
        # the unification.
        if "Look At" in self.inputs:
            raw = self.inputs["Look At"][0]
            if isinstance(raw, str):
                raw = [float(v) for v in raw.replace("[", "").replace("]", "").split(",")]
            look_at = tuple(float(v) for v in raw)
        else:
            look_at = (
                float(self.inputs["Look At X"][0]),
                float(self.inputs["Look At Y"][0]),
                float(self.inputs["Look At Z"][0]),
            )

        cam_obj = _new_camera(self.name, focal_length_mm=50.0)
        cam_obj.location = (x, y, height)
        point_at(cam_obj, look_at, roll=math.radians(roll))

        logger.info(
            "ProceduralCamera: loc=(%.2f, %.2f, %.2f) look_at=%s roll=%.1fdeg",
            x, y, height, look_at, roll,
        )
        return {"Camera": cam_obj}


class OutdoorCameraClass(Node):
    """Procedural camera for large outdoor / unbounded scenes.

    Places a camera at one of four named viewpoints around the world
    origin, at a user-specified distance and focal length, and aims it at
    ``(0, 0, 0)``. Works well with ``Blend File Scene`` when paired with a
    placement node whose center is at the origin; for BYO scenes whose
    geometry is far from origin, use ``Parameterized Camera`` instead.

    Camera angles:
        - Overhead: straight down from ``(0, 0, distance)``.
        - Side:     looking along +X from ``(distance, 0, distance * 0.4)``.
        - Corner:   diagonal from ``(-d, d, distance * 0.5)`` where
          ``d = distance / sqrt(2)`` (isometric-style).
        - Entrance: front-facing from ``(0, -distance, distance * 0.25)``.
        - <random>: picks one of the above uniformly.

    Inputs:
        Camera Angle (select): see above. Default ``<random>``.
        Distance to Center (m): how far from the origin to place the
            camera. Default ``8.0``.
        Focal Length (mm): camera lens focal length; lower is wider angle.
            Default ``50.0``.
    """

    _ANGLES = ("Overhead", "Side", "Corner", "Entrance")

    def exec(self):
        logger.info("Executing %s", self.name)

        angle = self.inputs["Camera Angle"][0]
        distance = float(self.inputs["Distance to Center (m)"][0])
        focal_length = float(self.inputs["Focal Length (mm)"][0])
        look_at = self.inputs.get("Look At", ["[0, 0, 0]"])[0]
        if isinstance(look_at, str):
            look_at = [float(v) for v in look_at.replace("[", "").replace("]", "").split(",")]
        look_at = tuple(look_at)

        if angle == "<random>":
            angle = ctx.random.choice(list(self._ANGLES))
            logger.info("OutdoorCamera: random angle selected -> %s", angle)

        cam_obj = _new_camera(self.name, focal_length)
        lx, ly, lz = look_at

        if angle == "Overhead":
            cam_obj.location = (lx, ly, lz + distance)
            point_at(cam_obj, look_at)
        elif angle == "Side":
            cam_obj.location = (lx + distance, ly, lz + distance * 0.4)
            point_at(cam_obj, look_at)
        elif angle == "Corner":
            diag = distance / math.sqrt(2.0)
            cam_obj.location = (lx - diag, ly + diag, lz + distance * 0.5)
            point_at(cam_obj, look_at)
        elif angle == "Entrance":
            cam_obj.location = (lx, ly - distance, lz + distance * 0.25)
            point_at(cam_obj, look_at)
        else:
            raise ValueError(
                "OutdoorCamera: unknown Camera Angle '%s'. Expected one of %s or '<random>'."
                % (angle, self._ANGLES)
            )

        logger.info(
            "OutdoorCamera: angle=%s distance=%.2fm focal=%.1fmm location=%s",
            angle, distance, focal_length, tuple(round(v, 3) for v in cam_obj.location),
        )
        return {"Camera": cam_obj}


class ParameterizedCameraClass(Node):
    """Full-manual camera with explicit position and look-at target.

    The escape-hatch camera for any scene the two procedural cameras can't
    frame. Common use case: a BYO blend scene whose geometry sits far from
    the world origin. The user opens the blend in Blender, reads a good
    camera position and target out of it, and types the numbers in.

    Inputs:
        Camera X / Y / Z (m): world-space camera position.
        Look At X / Y / Z (m): world-space target point the camera aims at.
        Focal Length (mm): camera lens focal length; default ``50.0``.
        Roll (degrees): rotation around the look-at (forward) axis; default 0.
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        cx = float(self.inputs["Camera X"][0])
        cy = float(self.inputs["Camera Y"][0])
        cz = float(self.inputs["Camera Z"][0])
        lx = float(self.inputs["Look At X"][0])
        ly = float(self.inputs["Look At Y"][0])
        lz = float(self.inputs["Look At Z"][0])
        focal_length = float(self.inputs["Focal Length (mm)"][0])
        roll = float((self.inputs.get("Roll (degrees)") or [0.0])[0])
        aperture = float((self.inputs.get("Aperture (f-stop)") or [0.0])[0])
        focus_distance = float((self.inputs.get("Focus Distance (m)") or [0.0])[0])

        cam_obj = _new_camera(self.name, focal_length)
        cam_obj.location = (cx, cy, cz)
        point_at(cam_obj, (lx, ly, lz), roll=math.radians(roll))

        if aperture > 0.0:
            cam_data = cam_obj.data
            cam_data.dof.use_dof = True
            cam_data.dof.aperture_fstop = aperture
            if focus_distance <= 0.0:
                focus_distance = math.sqrt(
                    (cx - lx) ** 2 + (cy - ly) ** 2 + (cz - lz) ** 2
                )
            cam_data.dof.focus_distance = focus_distance

        logger.info(
            "ParameterizedCamera: loc=(%.2f, %.2f, %.2f) look_at=(%.2f, %.2f, %.2f) focal=%.1fmm roll=%.1fdeg",
            cx, cy, cz, lx, ly, lz, focal_length, roll,
        )
        return {"Camera": cam_obj}
