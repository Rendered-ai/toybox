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

import logging

from anatools.lib.node import Node
from anatools.lib.generator import ObjectModifier
from anatools.lib.file_handlers import file_to_objgen

from toybox.nodes.object_generators import ToyboxChannelObject

logger = logging.getLogger(__name__)


def scale_modifier(obj, scale):
    """Scale an object's root."""
    obj.root.scale[0] = scale[0]
    obj.root.scale[1] = scale[1]
    obj.root.scale[2] = scale[2]

    # Update metadata
    obj.modifiers.append({
        "Scale": {
            "Scale": list(scale),
        }
    })


class Scale(Node):
    """Adjust the scale of an upstream object generator."""

    def exec(self):
        logger.info("Executing %s", self.name)

        scale_x = float(self.inputs["Scale X"][0])
        scale_y = float(self.inputs["Scale Y"][0])
        scale_z = float(self.inputs["Scale Z"][0])

        # Wrap any FileObjects coming in on the Generator input into ObjectGenerators,
        # matching the toybox ColorVariationModifier convention.
        children = file_to_objgen(self.inputs["Generator"], ToyboxChannelObject)

        generator = ObjectModifier(
            method="scale_modifier",
            children=children,
            scale=(scale_x, scale_y, scale_z),
        )
        generator.function = scale_modifier
        # Emit under both keys: `Object Generator` is the current unified name (2026-05 refactor);
        # `Generator` is the legacy alias kept so pre-refactor graphs still load.
        return {"Object Generator": generator, "Generator": generator}
