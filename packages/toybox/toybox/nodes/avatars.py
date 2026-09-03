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
"""Rigged-character + animation nodes for the toybox channel.

Public API: :class:`CharacterNode`, :class:`AvatarConvertNode`,
:class:`AvatarRandomizerNode`, :class:`AnimationNode`,
:class:`AvatarPoseNode`. See ``docs/`` for the drop-in conventions.
"""

import glob
import json
import logging
import os
import tempfile
from collections import defaultdict

import bpy
import numpy as np

import anatools.lib.context as ctx
from anatools.lib.node import Node
from anatools.lib.generator import ObjectGenerator, ObjectModifier
from anatools.lib.file_handlers import file_to_objgen
from anatools.lib.file_object import FileObject
from anatools.lib.directory_object import DirectoryObject
from anatools.lib.search_utils import find_root
from anatools.lib.ana_object import AnaObject

from toybox.nodes.object_generators import ToyboxChannelObject
from toybox.lib.fbx_to_blend import cache_key, fbx_to_blend
from toybox.lib.rig_convert import convert_rig_to_standard
from toybox.standards import vocab

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AvatarObject + custom loader
# ---------------------------------------------------------------------------


# Demographic vocabularies from the avatars-volume ASSET_STANDARDS.md §3.4.
_ETHNICITY_VOCAB = {
    "hispanic", "black", "asian", "caucasian", "middleeastern", "southasian",
}


def _norm_demo(value):
    """Lowercase + strip whitespace: 'Middle Eastern' -> 'middleeastern'."""
    return "".join(str(value).lower().split())


def _parse_avatar_demographics(blender_file, armature):
    """Demographics dict for an avatar (gender / ethnicity / age_group).

    Priority (ASSET_STANDARDS.md §3.4): (1) ``ana_gender`` / ``ana_ethnicity``
    / ``ana_age_group`` custom props on the Armature; (2) filename + path
    convention for the pre-standard baked rigs
    (``<Ethnicity>_<Name>_Rig_v2.blend`` under ``Females/`` or
    ``Male_Avatars/``). Only determinable fields are emitted -- ``age_group``
    is never guessed, so all-adult assumptions don't fabricate ground truth.
    """
    demo = {}
    for key, prop in (
        ("gender", "ana_gender"),
        ("ethnicity", "ana_ethnicity"),
        ("age_group", "ana_age_group"),
    ):
        val = armature.get(prop)
        if val:
            demo[key] = _norm_demo(val)

    if "ethnicity" not in demo:
        stem = os.path.splitext(os.path.basename(blender_file))[0]
        prefix = _norm_demo(stem.split("_", 1)[0])
        if prefix in _ETHNICITY_VOCAB:
            demo["ethnicity"] = prefix

    if "gender" not in demo:
        segs = [s.lower() for s in blender_file.replace("\\", "/").split("/")]
        if any(s.startswith("female") for s in segs):
            demo["gender"] = "female"
        elif any(s.startswith("male") for s in segs):
            demo["gender"] = "male"

    return demo


class AvatarObject(ToyboxChannelObject):
    """A rigged-character object whose ``.root`` is the Armature.

    Subclasses :class:`ToyboxChannelObject` so it interoperates with every
    existing toybox modifier (Scale, Color, Warp) and placement node. The
    ``color`` method is a no-op by default -- character colour variation is
    expected to live in PBR shader nodes per the standards doc, not in a
    single RGB constant.
    """

    def color(self, color_type=None):  # pragma: no cover - intentional no-op
        # Characters use PBR materials with multiple slots; per-character
        # tinting is out of scope for v1. Subclasses may override.
        pass

    def dump_metadata(self):
        """Add a ``demographics`` block to the per-object metadata.

        Calls :meth:`AnaObject.dump_metadata` directly rather than ``super()``
        because :func:`_avatar_class` builds the concrete instance class as a
        *sibling* of ``AvatarObject`` (cloned ``__dict__`` over
        ``AvatarObject.__bases__``), so ``self`` is not an ``AvatarObject``
        subtype and a zero-arg ``super()`` would raise.
        """
        meta = AnaObject.dump_metadata(self)
        demo = getattr(self, "demographics", None)
        if demo:
            meta["demographics"] = demo
        return meta


def avatar_load(self, **kwargs):
    """Loader bound to :class:`AvatarObject` instances.

    Loads collections from the character ``.blend`` and **explicitly skips
    actions** so any animation accidentally baked into the character file
    does not leak into the scene. The animation node is the sole owner of
    armature actions.

    After load the lone parentless object in the loaded collection is
    asserted to be an ``ARMATURE`` and assigned as ``self.root`` so every
    downstream placement / modifier sees the rig as the manipulable root.
    """
    if self.loaded:
        return

    blender_file = kwargs.pop("blender_file")

    # Pull collections only; deliberately leave actions/worlds/cameras alone.
    with bpy.data.libraries.load(filepath="//" + blender_file, link=False) as (df, dt):
        dt.collections = df.collections

    if not dt.collections:
        raise RuntimeError(
            f"AvatarObject: character blend '{blender_file}' has no collection. "
            "Wrap the rig + meshes in a single collection per the toybox "
            "character standard."
        )

    self.collection = dt.collections[0]
    bpy.context.scene.collection.children.link(self.collection)

    self.root = find_root(self.collection)
    if self.root is None or self.root.type != "ARMATURE":
        raise RuntimeError(
            f"AvatarObject: character blend '{blender_file}' root must be an "
            f"ARMATURE; got {getattr(self.root, 'type', None)!r}. Re-parent "
            "meshes under the armature and re-export."
        )

    # Stash skeleton + metadata custom props onto the AnaObject config so
    # the animation node can read them without re-touching bpy.
    skeleton = self.root.get("ana_skeleton") or "rigify"
    self.config = dict(self.config or {})
    self.config["ana_skeleton"] = str(skeleton).lower()
    self.config["ana_height"] = float(self.root.get("ana_height") or 1.78)

    # Stash the resolved source-blend path so AnimationNode can retarget a
    # raw source FBX against THIS avatar's own rig rest pose at apply time
    # (the rest-pose correction is rig-specific; see _fbx_to_action_blend).
    self.config["ana_source_blend"] = blender_file

    # Scrape demographic ground-truth (gender / ethnicity / age_group) so it
    # reaches the per-object metadata via AvatarObject.dump_metadata. Uses
    # custom props when present, else the baked-rig filename/path convention.
    self.demographics = _parse_avatar_demographics(blender_file, self.root)
    if self.demographics:
        self.config["ana_demographics"] = dict(self.demographics)

    # Rename collection + root to filename stem for metadata consistency,
    # mirroring anatools.lib.file_handlers.blender_load.
    name = os.path.splitext(os.path.basename(blender_file))[0]
    try:
        self.root.users_collection[0].name = name
    except (IndexError, AttributeError):
        pass
    self.root.name = name
    self.object_type = name

    self.loaded = True

    if "config" in kwargs:
        # Caller-provided config wins over scraped custom props.
        self.config.update(kwargs.pop("config"))


# ---------------------------------------------------------------------------
# Character node (object generator)
# ---------------------------------------------------------------------------


def _avatar_class():
    """Build a one-off ``AvatarObject`` subclass with ``avatar_load`` bound.

    Mirrors the trick :func:`anatools.lib.file_handlers.filename_to_generator`
    uses for generic blends: clone the class so we can override ``load``
    without mutating the shared :class:`AvatarObject`.
    """
    return type("AvatarObjectInstance", AvatarObject.__bases__, {
        **dict(AvatarObject.__dict__),
        "load": avatar_load,
    })


class CharacterNode(Node):
    """Wrap a rigged-character ``.blend`` (from a VolumeFile) into an
    object generator that placement nodes can scatter exactly like a yo-yo.
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        char_file = self.inputs["Character File"][0]
        if not isinstance(char_file, FileObject):
            raise RuntimeError(
                "Character: 'Character File' must be a FileObject (wire a "
                "VolumeFile pointing at a .blend)."
            )
        filename = char_file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext != ".blend":
            raise RuntimeError(
                f"Character: only .blend characters are supported (got {ext!r})."
            )

        generator = ObjectGenerator(
            _avatar_class(),
            None,
            blender_file=filename,
        )
        return {"Object Generator": generator}


def _expykit_target_rest_blend(obj, gender: str, dst_skel: str) -> str | None:
    """Rest-pose reference for FBX-clip retargeting: the avatar's own converted rig."""
    return obj.config.get("ana_source_blend")


# ---------------------------------------------------------------------------
# Avatar Convert node
# ---------------------------------------------------------------------------

_AVATAR_CONVERT_REST = {"t-pose": "t_pose", "a-pose": "a_pose"}


class AvatarConvertNode(Node):
    """Convert a user-uploaded rigged avatar to the rendered_humanoid standard.

    Emits an ``Object Generator`` drop-in compatible with every Object
    Generators consumer and the Avatar Pose / Avatar Animation decorators --
    identical to :class:`CharacterNode`, but the input is an arbitrary
    user-supplied rig instead of a pre-conforming ``.blend``.
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        avatar_file = (self.inputs.get("Avatar File") or [None])[0]
        if not isinstance(avatar_file, FileObject):
            raise RuntimeError(
                "Avatar Convert: 'Avatar File' must be a FileObject (wire a "
                "VolumeFile pointing at a .blend/.fbx/.glb)."
            )
        src_path = avatar_file.filename
        ext = os.path.splitext(src_path)[1].lower()
        if ext not in (".blend", ".fbx", ".glb", ".gltf"):
            raise RuntimeError(
                f"Avatar Convert: unsupported upload extension {ext!r}; use "
                ".blend, .fbx, or .glb/.gltf."
            )

        source = str((self.inputs.get("Source Rig") or ["Auto"])[0]).strip().lower()
        rest_in = str((self.inputs.get("Rest Pose") or ["T-Pose"])[0]).strip().lower()
        rest_pose = _AVATAR_CONVERT_REST.get(rest_in, "t_pose")

        demographics = {}
        for key, field in (("gender", "Gender"), ("ethnicity", "Ethnicity")):
            val = (self.inputs.get(field) or [""])[0]
            if isinstance(val, str) and val.strip():
                demographics[key] = _norm_demo(val)

        out_blend = convert_rig_to_standard(
            src_path,
            source=source,
            rest_pose=rest_pose,
            demographics=demographics,
        )

        generator = ObjectGenerator(
            _avatar_class(),
            None,
            blender_file=out_blend,
        )
        return {"Object Generator": generator}


# ---------------------------------------------------------------------------
# Animation node (object modifier)
# ---------------------------------------------------------------------------


def _retarget_action(action, src_skeleton, dst_skeleton):
    """Stub retargeter.

    v1 only supports same-namespace assignment. When source and destination
    skeleton namespaces differ we log a clear warning and return the action
    unmodified. A future commit will load a JSON bone-name map from
    ``packages/toybox/toybox/retarget/<src>_to_<dst>.json`` and rewrite each
    F-curve ``data_path`` accordingly.
    """
    if src_skeleton == dst_skeleton:
        return action
    logger.warning(
        "Animation: skeleton mismatch src=%s dst=%s -- retargeting not yet "
        "implemented; assigning action verbatim. Bone-name remapping JSON "
        "will land in toybox/retarget/.",
        src_skeleton, dst_skeleton,
    )
    return action


def _anim_cache_dir():
    """On-disk cache for FBX→Action retarget output."""
    base = os.environ.get("ANA_FBX_CACHE_DIR") or os.path.join(
        tempfile.gettempdir(), "ana_fbx_cache"
    )
    os.makedirs(base, exist_ok=True)
    return base


def _fbx_to_action_blend(fbx_path, rig_blend, *, name, skeleton, fps, loop, root_motion):
    """Retarget a source FBX onto ``rig_blend``'s rest pose; return a cached
    Action-only ``.blend`` path.

    ``rig_blend`` is normally the canonical reference rig for the avatar's gender
    (see :func:`_canonical_rig_blend`), so every source clip is baked once and
    the resulting action is shared across all characters of that gender — no
    per-character calibration variance.  Falls back to the character's own
    ``ana_source_blend`` when the canonical rig is unavailable.

    Cache-backed (keyed on FBX mtime/size + knobs + rig file) so repeated
    avatars and graph runs sharing a ``(clip, rig)`` pair convert only once.
    """
    if not rig_blend or not os.path.isfile(rig_blend):
        raise RuntimeError(
            "Avatar Animation: cannot retarget FBX %r -- the upstream avatar "
            "has no resolvable source rig (ana_source_blend). Wire a Character "
            "or Avatar Convert node (not a raw VolumeFile) so the rig rest pose "
            "is known." % os.path.basename(fbx_path)
        )
    key = cache_key(
        fbx_path,
        skeleton=skeleton,
        fps=fps,
        loop=loop,
        name=name,
        target_rest_blend=rig_blend,
    )
    out_path = os.path.join(_anim_cache_dir(), f"{name}_{key}.blend")
    if os.path.isfile(out_path):
        logger.info("Avatar Animation: FBX retarget cache hit %s", out_path)
    else:
        logger.info(
            "Avatar Animation: retargeting %s onto %s (fps=%d loop=%s root_motion=%s)",
            os.path.basename(fbx_path), os.path.basename(rig_blend),
            fps, loop, root_motion,
        )
        fbx_to_blend(
            fbx_path,
            out_path,
            name=name,
            skeleton=skeleton,
            fps=fps,
            loop=loop,
            root_motion=root_motion,
            target_rest_blend=rig_blend,
        )
    return out_path


def apply_animation(obj, *, anim_sources, skeleton, loop, frame_offset, fps, root_motion):
    """Modifier function bound by :class:`AnimationNode`.

    Randomly picks one source from ``anim_sources`` (using ``ctx.random`` so
    selection is reproducible). A ``.fbx`` source is retargeted on the fly
    against this avatar's own rig rest pose (see :func:`_fbx_to_action_blend`);
    a pre-baked ``.blend`` source is used verbatim. The resulting first Action
    is pushed onto the armature via an NLA strip. Each scattered avatar draws
    independently, so a crowd naturally mixes clips -- and FBX clips are
    retargeted per-identity, so mixed-rig crowds stay anatomically correct.
    """
    arm = obj.root
    if arm is None or arm.type != "ARMATURE":
        raise RuntimeError(
            "Avatar Animation: upstream Generator did not produce an Armature "
            "root. Wire a Character node (not a raw VolumeFile) into Avatar "
            "Animation."
        )

    source = ctx.random.choice(anim_sources) if len(anim_sources) > 1 else anim_sources[0]
    ext = os.path.splitext(source)[1].lower()

    dst_skel = str(obj.config.get("ana_skeleton") or "rigify").lower()
    requested = skeleton.lower() if skeleton and skeleton != "Auto" else dst_skel

    is_fbx = ext == ".fbx"
    if is_fbx:
        gender = obj.config.get("ana_demographics", {}).get("gender", "female")
        rig_blend = _expykit_target_rest_blend(obj, gender, dst_skel)
        anim_path = _fbx_to_action_blend(
            source,
            rig_blend,
            name=os.path.splitext(os.path.basename(source))[0],
            skeleton=requested,
            fps=fps,
            loop=loop,
            root_motion=root_motion,
        )
    else:
        anim_path = source

    with bpy.data.libraries.load(filepath="//" + anim_path, link=False) as (df, dt):
        dt.actions = df.actions

    if not dt.actions:
        logger.warning("Avatar Animation: no Actions found in '%s'; skipping", anim_path)
        return
    action = dt.actions[0]
    action.use_fake_user = True

    # FBX sources are already retargeted onto the canonical rig above. Only the
    # legacy pre-baked .blend path needs the (stub) skeleton-name remap.
    if not is_fbx:
        src_skel = str(action.get("ana_skeleton") or "rigify").lower()
        if requested != src_skel:
            action = _retarget_action(action, src_skel, requested)

    ad = arm.animation_data_create()
    track = ad.nla_tracks.new()
    track.name = f"ana_anim_{action.name}"
    start = max(1, 1 + int(frame_offset))
    strip = track.strips.new(name=action.name, start=start, action=action)
    if loop:
        # Tile the strip over the rest of the timeline. Render frame range
        # decides how much of the loop is actually evaluated.
        strip.repeat = 100.0
    strip.use_auto_blend = False

    obj.modifiers.append({
        "Avatar Animation": {
            "action": action.name,
            "skeleton": requested,
            "loop": bool(loop),
            "frame_offset": int(frame_offset),
            "source": os.path.basename(source),
            "retargeted_from_fbx": is_fbx,
        }
    })


class AnimationNode(Node):
    """Animate upstream avatars: retarget + attach an Action via an NLA strip.

    Acts as an :class:`ObjectModifier`: chain
    ``Character → Avatar Animation → Spatial Cluster`` and every scattered
    avatar receives an NLA strip of the chosen clip.

    ``Animation File`` accepts either a **Rocketbox ``.fbx``** -- retargeted on
    the fly against each avatar's own rig rest pose, so the target rest pose
    can't be mis-wired -- or a pre-baked Action-only ``.blend``. When multiple
    links are wired, each avatar draws
    one clip independently via :func:`ctx.random.choice`, naturally mixing
    actions (and retargeting FBX per-identity) across a crowd from one node.
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        raw_files = self.inputs["Animation File"]
        anim_sources = []
        for f in raw_files:
            path = f.filename if isinstance(f, FileObject) else str(f)
            if os.path.splitext(path)[1].lower() not in (".blend", ".fbx"):
                raise RuntimeError(
                    f"Avatar Animation: Animation File must be a .fbx "
                    f"(auto-retargeted onto the avatar's rig) or a pre-baked "
                    f".blend (got {path!r})."
                )
            anim_sources.append(path)

        if not anim_sources:
            raise RuntimeError(
                "Avatar Animation: at least one Animation File must be wired."
            )

        skeleton = (self.inputs.get("Skeleton") or ["Auto"])[0]
        loop = (self.inputs.get("Loop") or ["Enabled"])[0] == "Enabled"
        frame_offset = int(float((self.inputs.get("Frame Offset") or [0])[0]))
        fps = int(float((self.inputs.get("FPS") or [30])[0]))
        root_motion = (self.inputs.get("Root Motion") or ["Disabled"])[0] == "Enabled"

        # Pass-through if upstream is already an ObjectGenerator (Character
        # node); wrap if it's a raw FileObject (lets users skip the Character
        # node for quick prototyping at the cost of no armature validation).
        children = file_to_objgen(self.inputs["Character Generator"], AvatarObject)

        generator = ObjectModifier(
            method="apply_animation",
            children=children,
            anim_sources=anim_sources,
            skeleton=skeleton,
            loop=loop,
            frame_offset=frame_offset,
            fps=fps,
            root_motion=root_motion,
        )
        generator.function = apply_animation
        return {"Object Generator": generator}


# ---------------------------------------------------------------------------
# Avatar Pose node (object modifier)
# ---------------------------------------------------------------------------


def _bake_action_frame_to_pose(arm, action, frame):
    """Freeze a single frame of ``action`` onto ``arm``'s pose bones.

    Evaluates each F-curve at ``frame`` and writes the value straight onto the
    corresponding pose-bone property, so the armature holds the pose as a
    *static* configuration -- no ``animation_data``, no NLA strip, nothing to
    evaluate per render frame. This is what lets :class:`AvatarPoseNode` pair
    with the plain ``Render`` node (a single still) instead of requiring the
    frame-stepping ``Animation Render``.

    Pose-bone ``rotation_mode`` is aligned to whichever rotation channel the
    action drives (quaternion / euler / axis-angle) so the written values
    actually take effect. Returns the number of channels applied.
    """
    pose = arm.pose

    # Align each posed bone's rotation_mode to the action's rotation channel.
    rot_mode = {}
    for fc in action.fcurves:
        dp = fc.data_path
        if '"' not in dp:
            continue
        bone = dp.split('"')[1]
        if dp.endswith("rotation_quaternion"):
            rot_mode[bone] = "QUATERNION"
        elif dp.endswith("rotation_axis_angle"):
            rot_mode[bone] = "AXIS_ANGLE"
        elif dp.endswith("rotation_euler"):
            rot_mode.setdefault(bone, "XYZ")
    for bone, mode in rot_mode.items():
        pb = pose.bones.get(bone)
        if pb is not None:
            pb.rotation_mode = mode

    applied = 0
    for fc in action.fcurves:
        dp = fc.data_path
        try:
            owner_path, prop = dp.rsplit(".", 1)
            owner = arm.path_resolve(owner_path)
            arr = getattr(owner, prop)
        except (ValueError, AttributeError):
            continue
        try:
            arr[fc.array_index] = fc.evaluate(frame)
            setattr(owner, prop, arr)
            applied += 1
        except (TypeError, IndexError):
            continue
    return applied


def _avatar_min_world_z(arm):
    """Lowest world-space vertex Z across the armature's posed meshes.

    Evaluates the dependency graph so the *posed* (deformed) mesh is measured,
    not the rest mesh. Returns ``None`` when no mesh descendants exist.
    """
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    min_z = None
    stack = list(arm.children)
    seen = set()
    while stack:
        o = stack.pop()
        if o.name in seen:
            continue
        seen.add(o.name)
        stack.extend(o.children)
        if o.type != "MESH":
            continue
        eo = o.evaluated_get(deps)
        me = eo.to_mesh()
        mw = eo.matrix_world
        for v in me.vertices:
            z = (mw @ v.co).z
            if min_z is None or z < min_z:
                min_z = z
        eo.to_mesh_clear()
    return min_z


def _floor_clamp(arm):
    """Shift ``arm`` so its lowest posed vertex sits at z=0.

    Conforms to the channel's placement convention -- every object's lowest
    point is at z=0, so a placement node's Z value is the ground-contact
    height. A seated/posed avatar breaks this because the armature origin is
    the rest-pose feet, not the posed mesh's lowest point. The correction is
    written to ``delta_location`` (NOT ``location``) so it composes with the
    ``location`` a downstream Manual Placement node assigns rather than being
    overwritten. Z-only placement rotations preserve the clamp (rotating about
    Z does not change vertex Z); non-Z placement rotations would not.

    Returns the applied offset (``-min_z``), or ``None`` if unmeasurable.
    """
    min_z = _avatar_min_world_z(arm)
    if min_z is None:
        logger.warning("Avatar Pose: no mesh found under %s; skipping floor-clamp", arm.name)
        return None
    arm.delta_location.z -= min_z
    logger.info(
        "Avatar Pose: floor-clamped %s (lowest vertex was z=%.4f) to z=0 via delta_location",
        arm.name, min_z,
    )
    return -min_z




def apply_pose(obj, *, pose_sources, skeleton, frame):
    """Modifier function bound by :class:`AvatarPoseNode`.

    Randomly picks one source from ``pose_sources`` (``ctx.random`` for
    determinism), retargets a ``.fbx`` onto this avatar's own rig (same path as
    :func:`apply_animation`) or uses a pre-baked ``.blend`` verbatim, then bakes
    the requested ``frame`` statically onto the pose bones via
    :func:`_bake_action_frame_to_pose`. The Action is discarded afterward --
    the pose lives on the bones, frameless, so any render node shows it.
    """
    arm = obj.root
    if arm is None or arm.type != "ARMATURE":
        raise RuntimeError(
            "Avatar Pose: upstream Generator did not produce an Armature root. "
            "Wire a Character node (not a raw VolumeFile) into Avatar Pose."
        )

    source = ctx.random.choice(pose_sources) if len(pose_sources) > 1 else pose_sources[0]
    ext = os.path.splitext(source)[1].lower()

    dst_skel = str(obj.config.get("ana_skeleton") or "rigify").lower()
    requested = skeleton.lower() if skeleton and skeleton != "Auto" else dst_skel

    is_fbx = ext == ".fbx"
    if is_fbx:
        gender = obj.config.get("ana_demographics", {}).get("gender", "female")
        rig_blend = _expykit_target_rest_blend(obj, gender, dst_skel)
        # Root motion stripped so the posed avatar stays anchored at its placement.
        pose_blend = _fbx_to_action_blend(
            source,
            rig_blend,
            name=os.path.splitext(os.path.basename(source))[0],
            skeleton=requested,
            fps=30,
            loop=False,
            root_motion=False,
        )
    else:
        pose_blend = source

    with bpy.data.libraries.load(filepath="//" + pose_blend, link=False) as (df, dt):
        dt.actions = df.actions

    if not dt.actions:
        logger.warning("Avatar Pose: no Actions found in '%s'; skipping", pose_blend)
        return
    action = dt.actions[0]

    # Clamp the requested frame to the action's range (a single-frame pose is 1-2
    # frames; pulling a pose out of a longer clip is allowed too).
    rng = action.frame_range
    f = max(int(rng[0]), min(int(frame), int(rng[1])))

    applied = _bake_action_frame_to_pose(arm, action, f)
    logger.info(
        "Avatar Pose: baked %d channels from '%s' frame %d onto %s",
        applied, action.name, f, arm.name,
    )

    # The pose is now frozen on the bones; drop the Action so no stray
    # animation data leaks into the scene or the output .blend.
    if action.users == 0 and action.name in bpy.data.actions:
        bpy.data.actions.remove(action)

    # Conform to the placement convention: the posed avatar's lowest point sits
    # at z=0 so a placement node's Z is the ground-contact height.
    clamp_offset = _floor_clamp(arm)

    obj.modifiers.append({
        "Avatar Pose": {
            "source": os.path.basename(source),
            "frame": f,
            "skeleton": requested,
            "retargeted_from_fbx": is_fbx,
            "floor_clamp_offset_m": clamp_offset,
        }
    })


class AvatarPoseNode(Node):
    """Freeze a single static pose onto upstream avatars (pairs with Render).

    Acts as an :class:`ObjectModifier`: chain
    ``Character → Avatar Pose → Manual Placement`` and the avatar is posed
    once, statically -- no NLA strip, no frame range. Because the pose lives
    directly on the pose bones, the standard single-still ``Render`` node
    renders it correctly (no ``Animation Render`` / frame stepping needed).

    ``Pose File`` accepts a Rocketbox ``.fbx`` (single-frame pose or any frame of
    a longer clip, retargeted onto each avatar's own rig) or a pre-baked
    Action ``.blend``. Use ``Frame`` to pick which frame to sample. Multiple
    links scatter a random pose per avatar.
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        raw_files = self.inputs["Pose File"]
        pose_sources = []
        for f in raw_files:
            path = f.filename if isinstance(f, FileObject) else str(f)
            if os.path.splitext(path)[1].lower() not in (".blend", ".fbx"):
                raise RuntimeError(
                    f"Avatar Pose: Pose File must be a .fbx (auto-retargeted "
                    f"onto the avatar's rig) or a pre-baked .blend (got "
                    f"{path!r})."
                )
            pose_sources.append(path)

        if not pose_sources:
            raise RuntimeError("Avatar Pose: at least one Pose File must be wired.")

        skeleton = (self.inputs.get("Skeleton") or ["Auto"])[0]
        frame = int(float((self.inputs.get("Frame") or [1])[0]))

        children = file_to_objgen(self.inputs["Character Generator"], AvatarObject)

        generator = ObjectModifier(
            method="apply_pose",
            children=children,
            pose_sources=pose_sources,
            skeleton=skeleton,
            frame=frame,
        )
        generator.function = apply_pose
        return {"Object Generator": generator}


# ---------------------------------------------------------------------------
# Avatar Randomizer node
# ---------------------------------------------------------------------------

#: Avatar file extensions the randomizer will emit. Matches AvatarConvertNode's
#: accepted set (see AvatarConvertNode.exec).
_AVATAR_EXTS = (".fbx", ".blend", ".glb", ".gltf")


def _measure_height(meta):
    """Read the picked avatar's rest-pose height in metres from its sidecar.

    ASSET_STANDARDS §3.4 canonical property is ``ana_height`` (eyes Z);
    §1.4 requires the sidecar's ``bounding_box.max.z - bounding_box.min.z``
    to agree with it within ~1 cm. Prefer the stamped ``ana_height``, fall
    back to the bounding-box measurement so a sidecar that predates the
    §3.4 stamping pass still yields a usable value. Returns 0.0 when
    neither is available -- downstream consumers (a Camera's Look At Z,
    for example) should treat 0.0 as "unknown, use the graph default".
    """
    ana = meta.get("ana_height")
    if isinstance(ana, (int, float)) and ana > 0:
        return float(ana)
    bb = meta.get("bounding_box") or {}
    z_min = (bb.get("min") or [None, None, None])[2]
    z_max = (bb.get("max") or [None, None, None])[2]
    if isinstance(z_min, (int, float)) and isinstance(z_max, (int, float)):
        return max(0.0, float(z_max) - float(z_min))
    return 0.0


class AvatarRandomizerNode(Node):
    """Pick one asset-standard avatar per run from a demographic-filtered pool.

    Source-picker node -- reads sibling ``<name>.json`` sidecars in the
    supplied Avatar Pool directory, filters by ``ana_gender``,
    ``ana_clothing``, and ``ana_setting`` per Rendered.ai Asset Standards
    §3.4 controlled vocabulary, and emits a
    :class:`~anatools.lib.file_object.FileObject` for the picked avatar.
    Drop-in replacement for a :class:`~anatools.nodes.volume_file.VolumeFile`
    on :class:`AvatarConvertNode`'s ``Avatar File`` input.

    Filters are strictly the diversification axes (§3.4 demographics).
    Skeleton and rest-pose compatibility are pool-curation concerns --
    curate the ``Avatar Pool`` VolumeDirectory to a subtree whose rigs
    share a namespace and rest pose; ``Avatar Convert`` handles source
    detection from there.

    Missing-tag policy: when a filter is set, avatars whose sidecar omits
    the corresponding ``ana_*`` key are excluded. Follows §1.5 ("don't
    invent values") and §3.7 minimum-conformance (a sidecar may be
    identification-conformant without full demographics).

    Second output ``Height (m)`` emits ``ana_height`` (or bounding-box Z
    extent as a fallback) so downstream Camera / Placement nodes can
    track per-avatar geometry without a graph-side lookup.
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        pool_input = (self.inputs.get("Avatar Pool") or [None])[0]
        if not isinstance(pool_input, DirectoryObject):
            raise RuntimeError(
                "Avatar Randomizer: 'Avatar Pool' must be a DirectoryObject "
                "(wire a VolumeDirectory pointing at a folder of asset-standard "
                "avatars)."
            )
        pool_dir = pool_input.directory

        gender_filter = str((self.inputs.get("Gender") or ["any"])[0]).strip().lower()
        clothing_filter = str((self.inputs.get("Clothing") or ["any"])[0]).strip().lower()
        setting_filter = str((self.inputs.get("Setting") or ["any"])[0]).strip().lower()

        # Enumerate <name>.json sidecars anywhere under the pool. Sorted for
        # determinism (ctx.random.choice picks over an ordered list so the
        # same seed + same pool state = same avatar).
        sidecars = sorted(glob.glob(os.path.join(pool_dir, "**", "*.json"), recursive=True))
        if not sidecars:
            raise RuntimeError(
                f"Avatar Randomizer: no <name>.json sidecars found under "
                f"{pool_dir!r}. Sidecars are how the randomizer reads ana_* "
                f"demographics (ASSET_STANDARDS §1.4)."
            )

        candidates = []
        excluded = 0
        for sidecar_path in sidecars:
            try:
                with open(sidecar_path) as f:
                    meta = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            # Skip non-character sidecars. Empty ana_kind is accepted for
            # legacy sidecars predating the standard.
            kind = str(meta.get("ana_kind") or "").strip().lower()
            if kind and kind != "character":
                continue

            if gender_filter != "any":
                if str(meta.get("ana_gender") or "").strip().lower() != gender_filter:
                    excluded += 1
                    continue
            if clothing_filter != "any":
                sidecar_clothing = [c.lower() for c in vocab.normalize_multivalue(meta.get("ana_clothing"))]
                if clothing_filter not in sidecar_clothing:
                    excluded += 1
                    continue
            if setting_filter != "any":
                sidecar_setting = [s.lower() for s in vocab.normalize_multivalue(meta.get("ana_setting"))]
                if setting_filter not in sidecar_setting:
                    excluded += 1
                    continue

            # Locate the avatar file alongside the sidecar. Sidecar and asset
            # share a basename per ASSET_STANDARDS §1.4.
            stem, _ = os.path.splitext(sidecar_path)
            for ext in _AVATAR_EXTS:
                avatar_path = stem + ext
                if os.path.isfile(avatar_path):
                    name = (meta.get("names") or [os.path.basename(stem)])[0]
                    height = _measure_height(meta)
                    candidates.append((name, avatar_path, height))
                    break

        if not candidates:
            raise RuntimeError(
                f"Avatar Randomizer: no avatars in pool match filter "
                f"(gender={gender_filter}, clothing={clothing_filter}, "
                f"setting={setting_filter}); {excluded} candidate(s) "
                f"excluded by filter, {len(sidecars)} sidecar(s) scanned "
                f"in {pool_dir!r}."
            )

        # ctx.random is numpy.random.RandomState seeded per run so previews
        # and datasets reproduce (AGENT.md determinism). randint(low, high)
        # is [low, high) -- classic numpy pre-Generator API.
        pick_name, pick_path, pick_height = candidates[ctx.random.randint(0, len(candidates))]
        logger.info(
            "Avatar Randomizer: picked %r (height=%.3f m) from %d candidate(s) "
            "(filters: gender=%s clothing=%s setting=%s; %d excluded)",
            pick_name, pick_height, len(candidates),
            gender_filter, clothing_filter, setting_filter, excluded,
        )

        return {
            "Avatar File": FileObject(pick_path),
            "Height (m)": pick_height,
        }
