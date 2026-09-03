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
"""Manual Placement node.

The opposite of every other placement node in the channel: ``Random Placement``,
``Place Over Container`` and ``Spatial Cluster`` all sample positions
stochastically. ``Manual Placement`` puts ONE object at the exact
``Location`` and ``Rotation`` you specify -- nothing random about it.

Designed for hand-composed scenes, regression test graphs, and demos where
reproducibility matters more than crowd variety. Drop one Manual Placement
node per object you want to hand-place, then wire all of them into the
Scene aggregator's ``Placed Objects`` port (which already accepts
``oneOrMany``).

Both vector inputs accept either:
- A string default like ``"[0, 0, 0]"`` typed into the port, or
- A link from a ``Vector3D`` math node.
"""
import logging
import math

from mathutils import Vector

from anatools.lib.file_handlers import file_to_objgen
from anatools.lib.generator import CreateBranchGenerator
from anatools.lib.node import Node

from toybox.lib.parsers import parse_vec3
from toybox.nodes.object_generators import ToyboxChannelObject

logger = logging.getLogger(__name__)


class ManualPlacementClass(Node):
    """Deterministic single-object placement at a user-supplied transform."""

    def exec(self):
        logger.info("Executing %s", self.name)

        objects_input = self.inputs["Object Generators"]
        if not objects_input or objects_input[0] == "":
            logger.warning("ManualPlacement: no Object Generators provided")
            return {"Object Generator": []}

        location = parse_vec3(
            self.inputs["Location (m)"][0], name="Location (m)", node="Manual Placement"
        )
        rotation_deg = parse_vec3(
            self.inputs["Rotation (deg)"][0], name="Rotation (deg)", node="Manual Placement"
        )
        rotation_rad = tuple(math.radians(a) for a in rotation_deg)

        logger.info(
            "ManualPlacement: location=%s rotation_deg=%s",
            location, rotation_deg,
        )

        # When multiple generators are wired we still emit a single object;
        # CreateBranchGenerator picks one for us (matches Spatial Cluster /
        # Random Placement conventions).
        generators = file_to_objgen(objects_input, ToyboxChannelObject)
        branch_generator = CreateBranchGenerator(generators)

        obj = branch_generator.exec()
        obj.root.location = Vector(location)
        obj.root.rotation_euler = rotation_rad
        if hasattr(obj, "ooi"):
            obj.ooi = True

        return {"Object Generator": [obj]}
