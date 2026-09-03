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

import bpy
import numpy as np

import anatools.lib.context as ctx
from anatools.lib.node import Node
from anatools.lib.bbox import total_bound_box
from anatools.lib.generator import ObjectModifier
from anatools.lib.file_handlers import file_to_objgen

from toybox.nodes.object_generators import ToyboxChannelObject

logger = logging.getLogger(__name__)


def _find_meshes_recursive(root, meshes=None):
    """Return all MESH-type descendants of `root` (inclusive)."""
    if meshes is None:
        meshes = []
    if root.type == 'MESH':
        meshes.append(root)
    for child in root.children:
        _find_meshes_recursive(child, meshes)
    return meshes


def warp_modifier(obj, warp_strength):
    """Warp an object using a 3x3x3 lattice with random per-point deformation.

    `warp_strength` is on a 0-100 scale; 0 = no warping, 100 = heavy warping.
    """
    [xmin, xmax, ymin, ymax, zmin, zmax] = total_bound_box(obj.root)
    xpos = xmin + (xmax - xmin) / 2
    ypos = ymin + (ymax - ymin) / 2
    zpos = zmin + (zmax - zmin) / 2

    # Create the lattice and size it to the object's bounds.
    bpy.ops.object.add(radius=2, type='LATTICE', enter_editmode=False,
                       location=(xpos, ypos, zpos))
    warp_lattice = bpy.context.object
    warp_lattice.name = 'Warp_Lattice'
    warp_lattice.scale = (xmax - xmin, ymax - ymin, zmax - zmin)

    # Bind the lattice to the object's root.
    obj.root.modifiers.new(name='Lattice', type='LATTICE')
    obj.root.modifiers["Lattice"].object = warp_lattice

    deform_amplitude = warp_strength / 100.0
    warp_lattice.data.points_u = 3
    warp_lattice.data.points_v = 3
    warp_lattice.data.points_w = 3

    # Apply random, mean-zero deformation to each lattice point so the object
    # doesn't drift in size on average.
    for point in warp_lattice.data.points:
        deform_array = deform_amplitude * (ctx.random.rand(3) - 0.5)
        deform_array = deform_array - np.average(deform_array)
        for kk in range(3):
            point.co_deform[kk] = point.co_deform[kk] + deform_array[kk]

    # Bake the lattice into the mesh hierarchy.
    for blobj in _find_meshes_recursive(obj.root):
        bpy.context.view_layer.objects.active = blobj
        if blobj.type == 'MESH':
            bpy.ops.object.modifier_apply(modifier="Lattice")

    obj.modifiers.append({
        "Warp": {
            "warp_strength": warp_strength,
        }
    })


class Warp(Node):
    """Warp object geometry using lattice deformation."""

    def exec(self):
        logger.info("Executing %s", self.name)

        warp_strength = float(self.inputs["Warp Strength"][0])
        children = file_to_objgen(self.inputs["Generator"], ToyboxChannelObject)

        generator = ObjectModifier(
            method="warp_modifier",
            children=children,
            warp_strength=warp_strength,
        )
        generator.function = warp_modifier
        # Emit under both keys: `Object Generator` is the current unified name (2026-05 refactor);
        # `Generator` is the legacy alias kept so pre-refactor graphs still load.
        return {"Object Generator": generator, "Generator": generator}
