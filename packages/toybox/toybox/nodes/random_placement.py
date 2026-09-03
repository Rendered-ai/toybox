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
import math
from anatools.lib.node import Node
from anatools.lib.generator import CreateBranchGenerator
from anatools.lib.ana_object import AnaObject
import anatools.lib.context as ctx
import numpy as np
import logging
from anatools.lib.file_handlers import file_to_objgen
from toybox.lib.parsers import parse_vec3
from toybox.nodes.object_generators import ToyboxChannelObject

logger = logging.getLogger(__name__)

class PlacementOverContainerClass(Node):
    """
    A class to represent the PlacementOverContainer node, a node that places objects in a scene.
    """

    def exec(self):
        """Execute node"""
        logger.info("Executing {}".format(self.name))

        object_number = min(200, int(self.inputs["Number of Objects"][0]))
        cx, cy, drop_z, radius = _scatter_params(
            self.inputs, default_radius=0.05, node="Place Over Container"
        )

        object_list = []
        objects_input = self.inputs["Object Generators"]
        if objects_input[0] not in ("", None):
            #Wrap any file objects in an object generator
            generators = file_to_objgen(self.inputs["Object Generators"], ToyboxChannelObject)

            #Set up a branch generator for multiple input objects
            branch_generator = CreateBranchGenerator(generators)

            for ii in np.arange(object_number):
                #Pick a new branch from the inputs and executes it
                this_object = branch_generator.exec()
                object_list.append(this_object)
                #.root is the actual blender object
                this_object.root.location = (
                    cx + 2.0 * radius * (ctx.random.random() - 0.5),
                    cy + 2.0 * radius * (ctx.random.random() - 0.5),
                    drop_z + 0.1 * ii,
                )
                this_object.root.rotation_euler = (
                    math.radians(ctx.random.uniform(0,360)),
                    math.radians(ctx.random.uniform(0,360)),
                    math.radians(ctx.random.uniform(0,360)))

        return {"Objects of Interest": object_list}


class RandomPlacementClass(Node):
    """Scatter objects in a single Z plane with non-overlapping XY footprints.

    Use this for flat layouts -- e.g. toys laid out on a table, or items
    spread out for individual annotation. The node rejection-samples XY
    positions inside a square of side ``2 * Scatter Radius`` centered on
    (Center X, Center Y) such that no two object footprints overlap.
    All objects are placed at the same Z (``Drop Height``).

    Footprint is the bounding-sphere radius of each object's mesh, so the
    non-overlap guarantee holds for any rotation. If the scatter region is
    too small to fit ``Number of Objects`` non-overlapping footprints,
    overflow objects are hidden (moved far below the scene) and a warning
    is logged with the placed/requested counts.

    For gravity-stacked piles inside a container, use Place Over Container
    instead -- it places objects in a tight Z column and lets physics resolve
    overlaps as they fall.
    """

    def exec(self):
        """Execute node"""
        logger.info("Executing {}".format(self.name))

        object_number = min(200, int(self.inputs["Number of Objects"][0]))
        cx, cy, drop_z, radius = _scatter_params(
            self.inputs, default_radius=0.25, node="Random Placement"
        )

        object_list = []
        placed = []  # list of (x, y, footprint_radius) for non-overlap test
        skipped = 0

        objects_input = self.inputs["Object Generators"]
        if objects_input[0] != "":
            generators = file_to_objgen(self.inputs["Object Generators"], ToyboxChannelObject)
            branch_generator = CreateBranchGenerator(generators)

            for ii in np.arange(object_number):
                this_object = branch_generator.exec()
                footprint = _bounding_sphere_radius(this_object.root)

                xy = _rejection_sample_xy(cx, cy, radius, footprint, placed)
                if xy is None:
                    # Could not find a non-overlapping spot; hide the object
                    # below the scene so it doesn't appear in renders, and
                    # do not add it to the object-of-interest list.
                    this_object.root.location = (0.0, 0.0, -1000.0 - skipped)
                    skipped += 1
                    continue

                x, y = xy
                this_object.root.location = (x, y, drop_z)
                this_object.root.rotation_euler = (
                    math.radians(ctx.random.uniform(0, 360)),
                    math.radians(ctx.random.uniform(0, 360)),
                    math.radians(ctx.random.uniform(0, 360)),
                )
                placed.append((x, y, footprint))
                object_list.append(this_object)

        if skipped:
            logger.warning(
                "RandomPlacement: placed %d/%d objects; %d skipped (no non-overlapping spot in Scatter Radius=%.3f m). Increase Scatter Radius or reduce Number of Objects.",
                len(object_list), object_number, skipped, radius,
            )

        return {"Objects of Interest": object_list}


def _bounding_sphere_radius(blender_obj):
    """Conservative XY bounding-circle radius of a Blender object.

    Returns the maximum distance from the object's local origin to any of
    its mesh ``bound_box`` corners. This is the radius of a sphere centered
    on the object that contains the entire mesh, so it is also the largest
    XY footprint the object can have under any 3D rotation. Used by
    Random Placement's rejection sampler to keep objects from overlapping
    in XY regardless of how they are rotated.
    """
    bb = blender_obj.bound_box
    if not bb:
        return 0.0
    return max(
        math.sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]) for c in bb
    )


def _rejection_sample_xy(cx, cy, scatter_radius, footprint, placed, max_attempts=50):
    """Sample a random XY position inside the scatter region that does not
    overlap any previously-placed object footprint.

    Args:
        cx, cy: Center of the scatter region in world-space metres.
        scatter_radius: Half-extent of the square scatter region.
        footprint: Bounding-circle radius of the object being placed.
        placed: Iterable of ``(x, y, radius)`` tuples for already-placed
            objects.
        max_attempts: Maximum random samples to try before giving up.

    Returns:
        ``(x, y)`` if a non-overlapping spot was found, else ``None``.
    """
    for _ in range(max_attempts):
        x = cx + 2.0 * scatter_radius * (ctx.random.random() - 0.5)
        y = cy + 2.0 * scatter_radius * (ctx.random.random() - 0.5)
        ok = True
        for (ex, ey, er) in placed:
            min_d = footprint + er
            if (x - ex) * (x - ex) + (y - ey) * (y - ey) < min_d * min_d:
                ok = False
                break
        if ok:
            return x, y
    return None


def _scatter_params(inputs, default_radius, *, node):
    """Read the Center (m) Vector3D + Scatter Radius inputs.

    The Z component of ``Center (m)`` is used as the drop / spawn elevation;
    it replaces the former separate ``Drop Height`` scalar so the port
    pairs cleanly with a single ``Vector3D`` math node.

    Args:
        inputs: ``self.inputs`` dict from a placement node.
        default_radius: Scatter radius used when ``Scatter Radius`` is not
            wired -- ``0.25`` for Random Placement, ``0.05`` for Place Over
            Container, matching their pre-refactor magic numbers.
        node: Node alias used in the parser error message.

    Returns:
        Tuple ``(center_x, center_y, drop_z, scatter_radius)``.
    """
    cx, cy, drop_z = parse_vec3(
        inputs["Center (m)"][0], name="Center (m)", node=node
    )
    radius_in = inputs.get("Scatter Radius", [None])[0]
    radius = float(radius_in) if radius_in not in (None, "") else float(default_radius)
    return cx, cy, drop_z, radius


def settle_on_floor(object_list, floor_input, container_input, frames=50):
    """Spawn floor + container into the active scene and bake a gravity
    simulation so ``object_list`` settles on them.

    Thin composition of :func:`assemble_bed` (geometry) and
    :func:`bake_gravity` (physics). Kept as a single entry point for
    callers that want "floor + bake" in one step (legacy placement nodes,
    Phase 2a SceneNode).

    Args:
        object_list: List of :class:`AnaObject` instances already scattered in
            the scene; will be linked as ACTIVE rigid bodies.
        floor_input: Raw ``self.inputs["Floor Generator"]`` value (required).
        container_input: Raw ``self.inputs["Container Generator"]`` value, or
            ``[""]`` if no container. Optional.
        frames: How many simulation frames to bake (default 50).
    """
    floor, container = assemble_bed(floor_input, container_input)
    passive = [floor] + ([container] if container is not None else [])
    bake_gravity(active_objects=object_list, passive_objects=passive, frames=frames)


def assemble_bed(floor_input, container_input):
    """Spawn the floor (and optional container) into ``bpy.context.scene``.

    Pure geometry: loads the .blend(s), links the resulting objects into the
    active scene, and returns them. Does **not** touch the rigid-body system;
    see :func:`bake_gravity` for that. This separation lets a scene
    aggregator assemble geometry without committing to physics.

    Args:
        floor_input: Raw ``self.inputs["Floor Generator"]`` value (required).
        container_input: Raw ``self.inputs["Container Generator"]`` value, or
            ``[""]`` if no container. Optional.

    Returns:
        (floor, container) AnaObjects. ``container`` is ``None`` when no
        container input was wired.
    """
    floor_generator = CreateBranchGenerator(file_to_objgen(floor_input, AnaObject))
    floor = floor_generator.exec()

    container = None
    if container_input and container_input[0] != "":
        container_generator = CreateBranchGenerator(file_to_objgen(container_input, AnaObject))
        container = container_generator.exec()

    return floor, container


def bake_gravity(active_objects, passive_objects, frames=50):
    """Add a rigid-body world to the active scene, attach bodies, bake.

    ``active_objects`` are linked into the rigid-body collection with Blender's
    default type (ACTIVE) -- they will fall under gravity.
    ``passive_objects`` are linked and explicitly typed PASSIVE with a MESH
    collision shape and a small collision margin -- they are stationary
    obstacles (floor, container walls, etc).

    After setup, advances ``scene.frame_current`` to ``frames`` and bakes the
    point cache so subsequent renders capture the settled state.

    Args:
        active_objects: List of :class:`AnaObject` instances to fall.
        passive_objects: List of :class:`AnaObject` instances to be stationary
            colliders. May be empty.
        frames: Number of simulation frames to cache (default 50).
    """
    #Let's make sure we have a rigid body world going.
    bpy.ops.rigidbody.world_add()
    sc = bpy.context.scene
    sc.rigidbody_world.enabled = True
    collection = bpy.data.collections.new("CollisionCollection")

    sc.rigidbody_world.collection = collection
    #sc.rigidbody_world.substeps_per_frame = 150 # default 10
    #sc.rigidbody_world.solver_iterations  = 150 # default 10

    # TODO(user-exposed): expose `frames` as a node input ("Physics Frames", default 50).
    # Currently hardcoded via the `frames` arg (settle_on_floor passes 50, _bake_gravity_blend
    # passes 100). Heavy/crowded scenes may need more frames to fully settle. The value should
    # also be forwarded through AnaScene so RenderNode can seek to the correct post-settle frame
    # rather than relying on this side-effect assignment of scn.frame_current.
    sc.rigidbody_world.point_cache.frame_end = frames
    sc.frame_current = frames

    for obj in active_objects:
        sc.rigidbody_world.collection.objects.link(obj.root)
        # Normalize the rigid body to ACTIVE so gravity applies. Defensive
        # against assets loaded from blends that ship with type=PASSIVE
        # (e.g. /Containers/*.blend) and were wired here as Object Generators.
        rb = obj.root.rigid_body
        if rb is None:
            # Non-mesh roots (e.g. a posed avatar whose root is an ARMATURE)
            # cannot be rigid bodies, so linking creates no rigid_body. Such
            # objects are already positioned by their placement/floor-clamp;
            # skip gravity for them rather than crashing the whole bake.
            logger.warning(
                "bake_gravity: '%s' root '%s' (type %s) cannot be a rigid body; "
                "leaving it in place and skipping gravity.",
                getattr(obj, "object_type", obj.root.name), obj.root.name, obj.root.type,
            )
            sc.rigidbody_world.collection.objects.unlink(obj.root)
            continue
        rb.type = 'ACTIVE'
        rb.enabled = True
        rb.kinematic = False

    for obj in passive_objects:
        sc.rigidbody_world.collection.objects.link(obj.root)
        rb = obj.root.rigid_body
        if rb is None:
            logger.warning(
                "bake_gravity: passive '%s' root '%s' (type %s) cannot be a rigid "
                "body; skipping.",
                getattr(obj, "object_type", obj.root.name), obj.root.name, obj.root.type,
            )
            sc.rigidbody_world.collection.objects.unlink(obj.root)
            continue
        rb.type = 'PASSIVE'
        rb.collision_shape = 'MESH'
        rb.use_margin = True
        rb.collision_margin = 0.001

    #Before we go, let's bake the physics
    #bpy.ops.wm.save_as_mainfile(filepath="scene4baked.blend")
    bpy.ops.ptcache.bake_all()

