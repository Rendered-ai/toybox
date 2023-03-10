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
import bpy
from anatools.lib.node import Node
from anatools.lib.generator import CreateBranchGenerator
from anatools.lib.file_handlers import file_to_objgen
from anatools.lib.ana_object import AnaObject
import logging

logger = logging.getLogger(__name__)


class DropObjectsNode(Node):
    """
    A class to represent the DropObjects node, a node that applies gravity, "drop physics", to objects in a scene.
    """

    def exec(self):
        """Execute node"""
        logger.info("Executing {}".format(self.name))

        try:
            objects = self.inputs["Objects"][0]

            #Pick a link when more than one is provided
            container_generator = CreateBranchGenerator(file_to_objgen(self.inputs["Container Generator"], AnaObject))
            floor_generator = CreateBranchGenerator(file_to_objgen(self.inputs["Floor Generator"], AnaObject))

            #Create the container and floor
            container = container_generator.exec()
            floor = floor_generator.exec()

            #Let's make sure we have a rigid body world going.
            bpy.ops.rigidbody.world_add()
            sc = bpy.context.scene
            sc.rigidbody_world.enabled = True
            collection = bpy.data.collections.new("CollisionCollection")

            sc.rigidbody_world.collection = collection

            sc.rigidbody_world.collection.objects.link(container.root)
            container.root.rigid_body.type = 'PASSIVE'
            container.root.rigid_body.collision_shape = 'MESH'
            container.root.rigid_body.use_margin = True
            container.root.rigid_body.collision_margin = 0.001

            sc.rigidbody_world.collection.objects.link(floor.root)
            floor.root.rigid_body.type = 'PASSIVE'
            floor.root.rigid_body.collision_shape = 'MESH'
            floor.root.rigid_body.use_margin = True
            floor.root.rigid_body.collision_margin = 0.001
                
            #sc.rigidbody_world.substeps_per_frame = 150
            sc.rigidbody_world.solver_iterations = 150

            for obj in objects:
                sc.rigidbody_world.collection.objects.link(obj.root)

            #bpy.ops.wm.save_as_mainfile(filepath="scene4baked.blend")
            
            #Here's where you could do something interesting to determine what frame to use for the image.
            #You could expose this to the the user or choose it algorithmically.
            sc.frame_current = 250

            #Before we go, let's bake the physics
            bpy.ops.ptcache.bake_all()
        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise

        return {"Objects of Interest": objects}
