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
from anatools.lib.node import Node
from anatools.lib.generator import ObjectModifier
from toybox.nodes.object_generators import ToyboxChannelObject
from anatools.lib.file_handlers import file_to_objgen
import logging

logger = logging.getLogger(__name__)

class ColorVariationModifier(Node):
    """
    A class to represent the ColorVariationModifier node, a node that can modify the color of an object.
    """

    def exec(self):
        logger.info("Executing {}".format(self.name))

        # wrap any file objects in an object generator
        generators = file_to_objgen(self.inputs["Generators"], ToyboxChannelObject)
 
        # add modifier to the generator tree
        try:
            generator = ObjectModifier(
                method="color",  # the object method to use
                children=generators,  # the set of objects to choose from
                color_type=self.inputs["Color"][0])
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise

        return {"Generator": generator}
