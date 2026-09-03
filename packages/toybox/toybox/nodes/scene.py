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
"""Scene aggregator nodes.

Toybox offers two flavors of scene aggregator, both under ``Scenes / Aggregators``:

- :class:`ProceduralSceneNode` -- build a scene procedurally from toybox
  parts (placed objects, lights, floor, container) and accept an optional
  wired Camera input (Procedural / Outdoor / Parameterized). When no
  Camera is wired the node falls back to a built-in Look Down camera
  driven by the legacy ``Lens (mm)`` / ``Camera Height (m)`` / ``Look At``
  scalar inputs. Either way the camera is linked and ``scn.camera`` is
  set here, conforming to the Blender API model where the active camera
  is a scene-space concern, not a render-time concern.
- :class:`BlendFileSceneNode` -- load a prebuilt .blend file as the scene
  environment, overlay placed objects and lights, and accept an explicit
  Camera input (Procedural / Outdoor / Parameterized). The camera is
  linked and activated here for the same reason.

Both set ``scn.camera`` before returning the :class:`AnaScene` token so
:class:`RenderNode` only needs to call ``bpy.ops.render.render()``.
"""
import logging
import math
import os

import bpy
import mathutils
import anatools.lib.context as ctx
from anatools.lib.node import Node
from anatools.lib.scene import AnaScene
from anatools.lib.file_object import FileObject
from anatools.lib.directory_object import DirectoryObject
from toybox.nodes.random_placement import assemble_bed, bake_gravity, settle_on_floor
from toybox.nodes.simulation import point_at

logger = logging.getLogger(__name__)


def _flatten(items):
    """Upstream input ports arrive as lists of values, possibly nested."""
    out = []
    for item in items or []:
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out


def _linked_lights(scn, lights_input):
    """Link every non-empty light in ``lights_input`` into ``scn`` (idempotent).

    Returns the count of lights actually linked.
    """
    count = 0
    for light in lights_input or []:
        if light == "" or light is None:
            continue
        try:
            scn.collection.objects.link(light)
        except RuntimeError:
            # Already linked (e.g. legacy graph wires lights to Render too).
            pass
        count += 1
    return count


class ProceduralSceneNode(Node):
    """Build a scene procedurally from toybox parts.

    Aggregates placed objects, lights, and optionally a Floor and Container
    into an ``AnaScene`` for Render.

    When a ``Floor Generator`` is wired, the node spawns the floor (and an
    optional container), attaches rigid bodies to every placed object, and
    bakes a gravity simulation so the placed objects settle onto the floor.
    This moves responsibility for the procedural scene-bed out of the
    placement nodes and onto the Scene aggregator (Phase 2a).

    When ``Floor Generator`` is not wired, the node simply aggregates the
    upstream state and returns the AnaScene (Phase 1 passthrough behavior,
    used by legacy graphs that still settle physics inside Random Placement /
    Place Over Container, and by non-physics graphs like Spatial Cluster).
    """

    def exec(self):
        logger.info("Executing %s", self.name)
        scn = bpy.context.scene

        # Placed Objects: flatten and strip empty-string sentinels.
        objects = [o for o in _flatten(self.inputs.get("Placed Objects", [])) if o and o != ""]

        # Floor / Container: if a floor is wired, we own the scene-bed and
        # gravity bake here. Otherwise the upstream placement node already did
        # this (legacy path).
        floor_input = self.inputs.get("Floor Generator", [""]) or [""]
        container_input = self.inputs.get("Container Generator", [""]) or [""]

        # TODO(public-channel): make the gravity bake OPT-IN, not an implicit
        # side effect of wiring a Floor Generator. Hand-composed graphs (e.g.
        # Manual Placement + Avatar Pose, already floor-clamped to z=0) want the
        # floor as static geometry WITHOUT a physics settle. Add an explicit
        # "Settle Physics" Enabled/Disabled input (default Disabled) and gate
        # settle_on_floor on it; wiring a Floor alone should only spawn geometry.
        if floor_input and floor_input[0] != "":
            logger.info("Procedural Scene: spawning floor + container and settling physics")
            settle_on_floor(objects, floor_input, container_input)

        # Mark each object as object-of-interest for annotation.
        for obj in objects:
            if hasattr(obj, "ooi"):
                obj.ooi = True

        linked = _linked_lights(scn, self.inputs.get("Lights", [""]) or [""])

        hdri_inputs = [h for h in (self.inputs.get("HDRI", []) or []) if h and h != ""]
        hdri_rotation = float((self.inputs.get("HDRI Rotation (deg)") or [0.0])[0])
        if hdri_inputs:
            hdri_input = ctx.random.choice(hdri_inputs)
            applied = False
            if isinstance(hdri_input, DirectoryObject):
                exts = ('.hdr', '.exr')
                candidates = sorted(f for f in hdri_input.get_files() if f.lower().endswith(exts))
                if candidates:
                    chosen = ctx.random.choice(candidates)
                    logger.info("Procedural Scene: random HDRI from directory -> '%s'", chosen)
                    _apply_hdri(FileObject(chosen), hdri_rotation)
                    applied = True
                else:
                    logger.warning("Procedural Scene: HDRI directory has no .hdr/.exr files, skipping")
            elif isinstance(hdri_input, FileObject):
                _apply_hdri(hdri_input, hdri_rotation)
                applied = True
            if applied:
                _apply_hdri_render_tweaks(scn)

        # Camera: prefer a wired upstream Camera (Procedural / Outdoor /
        # Parameterized) so this node's contract matches Blend File Scene.
        # Fall back to the legacy embedded Look Down camera when no Camera is
        # wired -- keeps pre-Commit-2 graphs working.
        camera_input = self.inputs.get("Camera", []) or []
        wired_camera = camera_input[0] if camera_input and camera_input[0] not in ("", None) else None
        if wired_camera is not None:
            try:
                scn.collection.objects.link(wired_camera)
            except RuntimeError:
                pass
            scn.camera = wired_camera
            logger.info("Procedural Scene: wired camera '%s' activated", wired_camera.name)
        else:
            # Legacy Look Down placement -- constrained quarter-circle guarantees
            # elevation >= 45 degrees. Conforms to Blender API: camera is a scene
            # object; scn.camera is set here, not in RenderNode.
            height = float((self.inputs.get("Camera Height (m)") or [0.5])[0])
            focal_length = float((self.inputs.get("Lens (mm)") or [50.0])[0])
            look_at = (self.inputs.get("Look At") or ["[0, 0, 0]"])[0]
            if isinstance(look_at, str):
                look_at = [float(v) for v in look_at.replace("[", "").replace("]", "").split(",")]
            look_at = tuple(look_at)
            x = ctx.random.uniform(0, height)
            y_limit = math.sqrt(height ** 2 - x ** 2)
            y = ctx.random.uniform(-y_limit, y_limit)
            cam_data = bpy.data.cameras.new(self.name + "_cam")
            cam_data.lens = focal_length
            cam_obj = bpy.data.objects.new(self.name + "_cam", cam_data)
            cam_obj.location = (x, y, height)
            point_at(cam_obj, look_at)
            scn.collection.objects.link(cam_obj)
            scn.camera = cam_obj
            logger.info(
                "Procedural Scene: built-in Look Down camera loc=(%.2f, %.2f, %.2f) lens=%.1fmm look_at=%s",
                x, y, height, focal_length, look_at,
            )

        ana_scene = AnaScene(
            blender_scene=scn,
            annotation_view_layer=bpy.context.view_layer,
            objects=objects,
            sensor_name="RGBCamera",
        )
        logger.info("Procedural Scene: %d placed objects, %d light(s)",
                    len(objects), linked)
        return {"Scene": ana_scene}


# Back-compat alias: old graphs referencing SceneNode (by class key) resolve.
SceneNode = ProceduralSceneNode


class BlendFileSceneNode(Node):
    """Load a prebuilt .blend file as the scene environment.

    Appends all objects from the selected blend into ``bpy.context.scene``
    (world/camera data-blocks are left alone so upstream Lights and the
    Camera node still drive the render). Upstream Placed Objects and Lights
    are then overlaid on top of the loaded environment.

    When ``Settle Physics`` is ``Enabled`` and placed objects are wired, the
    node collects every newly-linked mesh as a PASSIVE rigid-body collider
    and bakes gravity so the placed objects settle onto the blend
    environment -- effectively turning any artist-built scene into a
    physics-ready floor. When ``Disabled``, objects land exactly where their
    upstream placement put them (matches the Spatial Cluster workflow).

    Inputs:
        Scene Blend: required name from ``package.yml`` objects: map whose
            ``filename`` points at a full-scene .blend (for toybox:
            ``Room Scene`` or ``Parking Lot Scene``).
        Placed Objects: optional Object-of-Interest lists from upstream
            placement nodes.
        Lights: optional Light objects to overlay on the loaded environment.
        Settle Physics: ``Enabled`` / ``Disabled``. Default ``Disabled``
            because most artist-built scenes already provide a floor mesh
            that placement nodes drop objects onto; enable only when you
            want the loaded environment to collide with placed objects.
    """

    def exec(self):
        logger.info("Executing %s", self.name)
        scn = bpy.context.scene

        scene_file = self.inputs["Scene File"][0]
        blend_path = scene_file.filename if isinstance(scene_file, FileObject) else str(scene_file)
        settle = self.inputs.get("Settle Physics", ["Disabled"])[0] == "Enabled"

        logger.info("BlendFileScene: loading '%s'", blend_path)

        # Append every object from the blend into the current scene. We
        # deliberately do not pull scenes/worlds/cameras so the existing
        # toybox camera + render pipeline stays in control.
        loaded = []
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            data_to.objects = list(data_from.objects)
            data_to.worlds = list(data_from.worlds)
            _blend_collections = set(data_from.collections)
        for world in (data_to.worlds or []):
            if world is not None:
                scn.world = world
                logger.info("BlendFileScene: applied world '%s' from blend", world.name)
                break
        for obj in data_to.objects:
            if obj is None:
                continue
            try:
                scn.collection.objects.link(obj)
            except RuntimeError:
                pass
            loaded.append(obj)
        logger.info("BlendFileScene: linked %d objects from blend", len(loaded))

        # Post-load purge: remove objects that would corrupt the toybox pipeline.
        #
        # Two rules:
        #   1. Always remove every CAMERA-type object — toybox owns camera
        #      placement via its camera nodes; a stray blend camera would
        #      fight with the active camera set by RenderNode.
        #   2. Remove Blender's known startup-default objects by exact name.
        #      When a user opens Blender to build a room blend they often
        #      forget to delete the startup scene objects (Cube, Camera,
        #      Light) before saving.  Matching by name is precise and does
        #      not accidentally remove intentional room geometry.
        _DEFAULT_NAMES = {
            ("Cube",   "MESH"),
            ("Camera", "CAMERA"),
            ("Light",  "LIGHT"),
        }
        stray = []
        for obj in list(loaded):
            is_default = (obj.name, obj.type) in _DEFAULT_NAMES
            if obj.type == "CAMERA" or is_default:
                stray.append(f"{obj.name}({obj.type})")
                try:
                    scn.collection.objects.unlink(obj)
                except RuntimeError:
                    pass
                bpy.data.objects.remove(obj, do_unlink=True)
                loaded.remove(obj)
        if stray:
            logger.info(
                "BlendFileScene: purged %d default/camera objects from blend: %s",
                len(stray), stray,
            )

        # Optional HDRI: override the world environment for outdoor scenes.
        hdri_inputs = [h for h in (self.inputs.get("HDRI", []) or []) if h and h != ""]
        hdri_rotation = float((self.inputs.get("HDRI Rotation (deg)") or [0.0])[0])
        if hdri_inputs:
            hdri_input = ctx.random.choice(hdri_inputs)
            if isinstance(hdri_input, DirectoryObject):
                exts = ('.hdr', '.exr')
                candidates = sorted(f for f in hdri_input.get_files() if f.lower().endswith(exts))
                if candidates:
                    chosen = ctx.random.choice(candidates)
                    logger.info("BlendFileScene: random HDRI from directory -> '%s'", chosen)
                    _apply_hdri(FileObject(chosen), hdri_rotation)
                else:
                    logger.warning("BlendFileScene: HDRI directory has no .hdr/.exr files, skipping")
            elif isinstance(hdri_input, FileObject):
                _apply_hdri(hdri_input, hdri_rotation)

        # Upstream placed objects (toys) and lights.
        # Filter out the empty-string sentinel the platform writes when a link is removed.
        placed = [o for o in _flatten(self.inputs.get("Placed Objects", [])) if o and o != ""]
        for obj in placed:
            if hasattr(obj, "ooi"):
                obj.ooi = True
        linked_lights = _linked_lights(scn, self.inputs.get("Lights", [""]) or [""])

        # Optional physics: treat selected loaded-blend meshes as PASSIVE
        # colliders and drop the placed objects onto them.
        if settle and placed:
            big_meshes = _passive_colliders(
                [o for o in loaded if o.type == "MESH"], min_xy_area=0.25
            )
            passive = [_AsAnaRoot(o) for o in big_meshes]
            logger.info(
                "BlendFileScene: settling %d placed objects against %d passive colliders"
                " (filtered from %d total meshes)",
                len(placed), len(passive),
                sum(1 for o in loaded if o.type == "MESH"),
            )
            # Set CONVEX_HULL on active toys before baking for faster
            # collision detection on small rounded objects.
            _bake_gravity_blend(
                active_objects=placed,
                passive_objects=passive,
                frames=100,
            )

        # Camera: link and activate. Conforms to Blender API -- scn.camera is
        # a scene-space concern set before RenderNode fires.
        camera_input = self.inputs.get("Camera", []) or []
        camera = camera_input[0] if camera_input and camera_input[0] not in ("", None) else None
        if camera is None:
            raise RuntimeError(
                "Blend File Scene requires a wired Camera input "
                "(Outdoor Camera or Parameterized Camera)."
            )
        try:
            scn.collection.objects.link(camera)
        except RuntimeError:
            pass
        scn.camera = camera
        logger.info("BlendFileScene: camera '%s' activated", camera.name)

        ana_scene = AnaScene(
            blender_scene=scn,
            annotation_view_layer=bpy.context.view_layer,
            objects=placed,
            sensor_name="RGBCamera",
        )
        logger.info(
            "Blend File Scene: blend='%s' meshes=%d placed=%d lights=%d settle=%s",
            blend_path, sum(1 for o in loaded if o.type == "MESH"),
            len(placed), linked_lights, settle,
        )
        return {"Scene": ana_scene}


def _apply_hdri(file_object, rotation_deg=0.0):
    """Replace the active scene's world environment with an HDRI image.

    Builds a TexCoord → Mapping → EnvironmentTexture → Background → WorldOutput
    chain. The Mapping node's Z rotation is set from ``rotation_deg`` so the
    sky can be azimuth-rotated without editing the source image.

    Args:
        file_object: :class:`FileObject` whose ``.filename`` is the path
            to an ``.hdr`` or ``.exr`` equirectangular HDRI image.
        rotation_deg: Azimuth rotation in degrees (Z axis). Default 0.
    """
    scn = bpy.context.scene
    if scn.world is None:
        scn.world = bpy.data.worlds.new("World")
    scn.world.use_nodes = True
    tree = scn.world.node_tree
    tree.nodes.clear()

    hdri_path = os.path.abspath(file_object.filename)
    hdri_image = bpy.data.images.load(hdri_path)

    out        = tree.nodes.new('ShaderNodeOutputWorld')
    background = tree.nodes.new('ShaderNodeBackground')
    env        = tree.nodes.new('ShaderNodeTexEnvironment')
    mapping    = tree.nodes.new('ShaderNodeMapping')
    tex_coord  = tree.nodes.new('ShaderNodeTexCoord')

    env.image = hdri_image
    background.inputs['Strength'].default_value = 1.0
    mapping.inputs['Rotation'].default_value[2] = math.radians(rotation_deg)

    tree.links.new(tex_coord.outputs['Generated'],   mapping.inputs['Vector'])
    tree.links.new(mapping.outputs['Vector'],         env.inputs['Vector'])
    tree.links.new(env.outputs['Color'],              background.inputs['Color'])
    tree.links.new(background.outputs['Background'],  out.inputs['Surface'])

    logger.info("BlendFileScene: applied HDRI '%s' rotation=%.1f deg",
                file_object.filename, rotation_deg)


def _apply_hdri_render_tweaks(scn):
    """Filmic + exposure=0 for HDR tonemapping; flags read by
    ``simulation.render()`` to set samples, OIDN, and compositor blur."""
    try:
        scn.view_settings.view_transform = 'Filmic'
        scn.view_settings.exposure = 0.0
    except AttributeError:
        pass
    scn["hdri_scene_mode"] = True
    scn["hdri_blur_px"] = 0.5


def _bake_gravity_blend(active_objects, passive_objects, frames=100):
    """Rigid-body gravity bake tuned for the blend-file scene workflow.

    Same as :func:`bake_gravity` but explicitly sets ``CONVEX_HULL`` collision
    on the active objects (toys) for faster computation, and uses a higher
    default frame count to give objects time to fully settle.
    """
    bpy.ops.rigidbody.world_add()
    sc = bpy.context.scene
    sc.rigidbody_world.enabled = True
    collection = bpy.data.collections.new("BlendPhysicsCollection")
    sc.rigidbody_world.collection = collection
    # TODO(user-exposed): same as bake_gravity in random_placement.py — expose `frames`
    # as a "Physics Frames" input on the Blend File Scene / Procedural Scene node so
    # the user can control how many frames are baked. Needs to be threaded through
    # AnaScene so RenderNode seeks to the correct settled frame instead of relying on
    # this side-effect write to scn.frame_current.
    sc.rigidbody_world.point_cache.frame_end = frames
    sc.frame_current = frames

    for obj in active_objects:
        collection.objects.link(obj.root)
        # Linking adds a rigid_body component automatically, but it inherits
        # whatever was saved in the source blend. Assets loaded from container
        # blends (e.g. /Containers/DarkWoodenBox.blend) ship with type=PASSIVE
        # because they are usually wired as containers. When such an asset is
        # wired as an Object Generator (active toy), normalize it to ACTIVE so
        # gravity applies; otherwise the body sits frozen through the bake.
        rb = obj.root.rigid_body
        rb.type = 'ACTIVE'
        rb.enabled = True
        rb.kinematic = False
        rb.collision_shape = 'CONVEX_HULL'

    for obj in passive_objects:
        collection.objects.link(obj.root)
        obj.root.rigid_body.type = 'PASSIVE'
        obj.root.rigid_body.collision_shape = 'MESH'
        obj.root.rigid_body.use_margin = True
        obj.root.rigid_body.collision_margin = 0.001

    bpy.ops.ptcache.bake_all()


def _passive_colliders(loaded_meshes, min_xy_area=0.25):
    """Return loaded mesh objects whose horizontal (XY) bounding footprint
    exceeds ``min_xy_area`` square metres.  This selects floors, tables and
    other large surfaces as PASSIVE rigid-body colliders while skipping small
    decorative items that would bloat the physics solver.

    Uses world-space bound_box corners so objects whose pivot is at the origin
    (common in artist-built blends) are handled correctly.
    """
    colliders = []
    for obj in loaded_meshes:
        if not obj.data:
            continue
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        xs = [c.x for c in corners]
        ys = [c.y for c in corners]
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if area >= min_xy_area:
            colliders.append(obj)
    return colliders


class _AsAnaRoot:
    """Minimal shim exposing ``.root`` for :func:`bake_gravity`, which expects
    ``AnaObject``-shaped inputs. Wraps a raw Blender object so we can pass
    library-loaded meshes in as passive colliders without round-tripping
    through :class:`AnaObject`."""

    __slots__ = ("root",)

    def __init__(self, blender_object):
        self.root = blender_object
