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
"""Sun light node.

Blender's ``SunLight`` is fundamentally different from Spot / Point:

- The lamp is infinitely far away, so ``location`` is ignored. Only the
  *direction* of the parallel rays matters.
- ``angle`` (radians) controls the angular diameter of the sun disc, which
  in turn controls penumbra softness -- the real sun is ~0.5 deg, overcast
  diffuse light is effectively 20+ deg.
- Energy is in W/m^2; typical clear-noon values are 2-5, not 100+ like an
  indoor point light.

The node exposes elevation + azimuth instead of Euler rotations because
those are the natural sky-coordinate axes (matches Blender's Nishita sky
shader) and the most useful knobs for dataset variation (time-of-day,
compass direction).
"""
import logging
import math

import bpy

from anatools.lib.node import Node

from toybox.lib.parsers import parse_vec3

logger = logging.getLogger(__name__)


class SunNode(Node):
    """Directional sunlight controlled by elevation + azimuth.

    Maps to a Blender ``SUN`` light. Location is irrelevant for sun lights
    (parallel rays from infinity); only the rotation matters.
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        elevation_deg = float(self.inputs["Elevation (deg)"][0])
        azimuth_deg = float(self.inputs["Azimuth (deg)"][0])
        strength = float(self.inputs["Strength (W/m^2)"][0])
        color = parse_vec3(self.inputs["Color"][0], name="Color", node="Sun")
        angular_size_deg = float(self.inputs["Angular Size (deg)"][0])

        sun_data = bpy.data.lights.new(self.name, type="SUN")
        sun_data.energy = strength
        sun_data.color = tuple(max(0.0, c) for c in color)
        sun_data.angle = math.radians(max(0.0, angular_size_deg))

        sun_obj = bpy.data.objects.new(self.name, sun_data)
        # Blender sun shines along the lamp's local -Z axis. To aim it from
        # a given (elevation, azimuth):
        #   - Elevation 0 deg  -> sun at the horizon, rays horizontal.
        #   - Elevation 90 deg -> sun directly overhead, rays straight down.
        #   - Azimuth 0/90/180/270 -> N / E / S / W on a standard compass.
        # The default lamp orientation already points down (-Z), so:
        #   rotation_euler.x = (90 - elevation) tilts it toward the horizon.
        #   rotation_euler.z = azimuth spins it around the compass.
        elev_rad = math.radians(elevation_deg)
        azim_rad = math.radians(azimuth_deg)
        sun_obj.rotation_euler = (math.radians(90.0) - elev_rad, 0.0, azim_rad)

        logger.info(
            "Sun: elevation=%.1f deg, azimuth=%.1f deg, strength=%.2f W/m^2, "
            "angular_size=%.2f deg, color=%s",
            elevation_deg, azimuth_deg, strength, angular_size_deg, color,
        )

        return {"Light": sun_obj}
