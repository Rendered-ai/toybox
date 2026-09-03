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
from anatools.lib.ana_object import AnaObject
from anatools.lib.generator import get_blendfile_generator
import anatools.lib.context as ctx
import logging

logger = logging.getLogger(__name__)

COLORS = {
    'Violet': (0.4196, 0.1412, 0.7020, 1),  # HSV: 270, 80, 70
    'Indigo': (0.1412, 0.1412, 0.7020, 1),  # HSV: 240, 80, 70
    'Blue':   (0.1412, 0.1412, 0.7020, 1),    # HSV: 210, 80, 70
    'Green':  (0.1412, 0.7020, 0.1412, 1),   # HSV: 120, 80, 70
    'Yellow': (0.7020, 0.7020, 0.1412, 1),  # HSV: 60, 80, 70
    'Orange': (0.7020, 0.4196, 0.1412, 1),  # HSV: 30, 80, 70
    'Red':    (0.7020, 0.1412, 0.1412, 1),     # HSV: 0, 80, 70
    'Black':  (0.0, 0.0, 0.0, 1),
    'White':  (1.0, 1.0, 1.0, 1),
}


class ToyboxChannelObject(AnaObject):
    """
    A class to represent the Toybox Channel AnaObjects.
    Add a 'color' method for the objects of interest.
    """

    def color(self, color_type=None):
        pass

    def setup_mask(self):
        pass


class BubblesObject(ToyboxChannelObject):
    """
    A class to represent the Bubbles AnaObject with a color method specific to the shader nodes of the blender file.
    """

    def color(self, color_type=None):
        # Change the bubbles bottle body color
        try:
            if color_type == '<random>':
                color_type = ctx.random.choice([c for c in COLORS.keys()])
                while color_type in ['White', 'Black']:
                    color_type = ctx.random.choice([c for c in COLORS.keys()])
            
            bottleBodyMatSlot = [ms for ms in self.root.material_slots if 'BubbleBottle' in ms.name][0]
            bottleBodyColor = bottleBodyMatSlot.material.node_tree.nodes['Principled BSDF'].inputs['Base Color']
            bottleBodyColor.default_value = COLORS[color_type]
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise


class YoyoObject(ToyboxChannelObject):
    """
    A class to represent the Yoyo AnaObject with a color method specific to the shader nodes of the blender file.
    """

    def color(self, color_type=None):
        # Change the YoYo specific RGB Node
        try:
            if color_type == '<random>':
                color_type = ctx.random.choice([c for c in COLORS.keys()])
                while color_type in ['White', 'Black']:
                    color_type = ctx.random.choice([c for c in COLORS.keys()])

            obj = self.root
            mat = obj.material_slots[0]  # there is only one material in the Yoyo
            rgb_node = mat.material.node_tree.nodes['RGB']
            rgb_node.outputs[0].default_value = COLORS[color_type]
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise


class SkateboardObject(ToyboxChannelObject):
    """
    A class to represent the Skateboard AnaObject with a color method specific to the shader nodes of the blender file.
    """

    def color(self, color_type=None):
        # Change the Skateboard specific RGB Node
        try:
            if color_type == '<random>':
                color_type = ctx.random.choice([c for c in COLORS.keys()])

            # Script in Blender: bpy.data.materials["Skateboard_Board"].node_tree.nodes["RGB"].outputs[0].default_value=...
            mat = [m for m in self.root.material_slots if 'Skateboard_Board' in m.name]
            if len(mat):
                rgb_node = mat[0].material.node_tree.nodes['RGB']
                rgb_node.outputs[0].default_value = COLORS[color_type]
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise


class PlayDohObject(ToyboxChannelObject):
    """
    A class to represent the PlayDoh AnaObject with a color method specific to the shader nodes of the blender file.
    """

    def color(self, color_type=None):
        # Change the RGB Node for the Play-Doh lid
        try:
            if color_type == '<random>':
                color_type = ctx.random.choice([c for c in COLORS.keys()])
                while color_type in ['Yellow', 'Orange']:
                    color_type = ctx.random.choice([c for c in COLORS.keys()])

            lidMatSlot = [ms for ms in self.root.material_slots if 'PlaydoughCover' in ms.name][0]
            lidColor = lidMatSlot.material.node_tree.nodes['Principled BSDF'].inputs['Base Color']
            lidColor.default_value = COLORS[color_type]
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise


# Display name (as it appears in the `Toy Type` / `Fruit Type` select) -> (AnaObject subclass,
# package.yml object name). The subclass supplies the `color()` override for materials-aware
# recolouring; entries that fall back to plain `ToyboxChannelObject` have no per-material hook.
# To add a new asset: add a row to `package.yml`, add an entry to the appropriate registry,
# and add the display name to the matching `select:` list in `object_generators.yml` -- no new
# node class required.
_TOY_REGISTRY = {
    "Bubbles":      (BubblesObject,       "BubbleBottle"),
    "Yo-yo":        (YoyoObject,          "YoYo"),
    "Skateboard":   (SkateboardObject,    "Skateboard"),
    "Playdough":    (PlayDohObject,       "PlayDough"),
    "Rubik's Cube": (ToyboxChannelObject, "Cube"),
    "Mix Cube":     (ToyboxChannelObject, "Mix Cube"),
}

_FRUIT_REGISTRY = {
    "Apple":  (ToyboxChannelObject, "Apple"),
    "Orange": (ToyboxChannelObject, "Orange"),
}


def _resolve_random(input_name, port_name, self):
    """Read a `<random>`-capable select input and return the concrete display name.

    Mirrors the Container / Floor pattern: reads the raw port value, and if it is `<random>`,
    samples uniformly from the port's `select:` list (excluding `<random>` itself).
    """
    value = self.inputs[input_name][0]
    if value == "<random>":
        select_list = [portdef["select"] for portdef in self.schema["inputs"] if
                       portdef.get('name') == port_name][0]
        choices = [t for t in select_list if t != "<random>"]
        value = ctx.random.choice(choices)
    return value


class ToyNode(Node):
    """
    A class to represent the Toy node, a single factory node for every toy declared in
    `_TOY_REGISTRY`. Replaces the previous per-toy nodes (Bubbles / Yo-yo / Skateboard /
    Playdough / Rubik's Cube / Mix Cube).
    """

    def exec(self):
        logger.info("Executing {}".format(self.name))

        try:
            toy_type = _resolve_random("Toy Type", "Toy Type", self)
            cls, obj_name = _TOY_REGISTRY[toy_type]
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise

        return {"Object Generator": get_blendfile_generator("toybox", cls, obj_name)}


class FruitNode(Node):
    """
    A class to represent the Fruit node, a single factory node for every fruit prop declared
    in `_FRUIT_REGISTRY`. Exposes the Apple / Orange fruit props (previously declared in
    `package.yml` but not reachable from any node).
    """

    def exec(self):
        logger.info("Executing {}".format(self.name))

        try:
            fruit_type = _resolve_random("Fruit Type", "Fruit Type", self)
            cls, obj_name = _FRUIT_REGISTRY[fruit_type]
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise

        return {"Object Generator": get_blendfile_generator("toybox", cls, obj_name)}


class ContainerNode(Node):
    """
    A class to represent the Container node, a node that instantiates a generator for the a container object.
    """

    def exec(self):
        logger.info("Executing {}".format(self.name))

        try:
            # get node inputs
            box_type = self.inputs["Container Type"][0]
            if box_type == "<random>":
                # select a random container
                select_list = [portdef["select"] for portdef in self.schema["inputs"] if
                               portdef.get('name') == "Container Type"][0]
                select_list.remove("<random>")
                box_type = ctx.random.choice(select_list)
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise

        generator = get_blendfile_generator("toybox", ToyboxChannelObject, box_type)
        # Emit under both keys: `Object Generator` is the current unified name (2026-05 refactor);
        # `Container Generator` is the legacy alias kept so pre-refactor graphs still load.
        return {"Object Generator": generator, "Container Generator": generator}


class FloorNode(Node):
    """
    A class to represent the Floor node, a node that instantiates a generator for the a floor object.
    """

    def exec(self):
        logger.info("Executing {}".format(self.name))

        try:
            floor_type = self.inputs["Floor Type"][0]
            if floor_type == "<random>":
                # select a random floor
                select_list = [portdef["select"] for portdef in self.schema["inputs"] if
                               portdef.get('name') == "Floor Type"][0]
                select_list.remove("<random>")
                floor_type = ctx.random.choice(select_list)
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise

        generator = get_blendfile_generator("toybox", ToyboxChannelObject, floor_type)
        # Emit under both keys: `Object Generator` is the current unified name (2026-05 refactor);
        # `Floor Generator` is the legacy alias kept so pre-refactor graphs still load.
        return {"Object Generator": generator, "Floor Generator": generator}
