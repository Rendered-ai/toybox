"""Convert a Rocketbox FBX animation into an AnimationNode-ready .blend.

`AnimationNode` (alias ``Avatar Animation``) and `AvatarPoseNode`
(``Avatar Pose``) call :func:`fbx_to_blend` at graph-execution time.

The retarget path is worldspace matrix copy when the caller passes a
``target_rest_blend``, and text-only bone-name rename otherwise.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

_BONE_RE = re.compile(r'pose\.bones\["([^"]+)"\]')

_ROCKETBOX_SIGNATURE = (
    "Bip01 Pelvis", "Bip01 Spine", "Bip01 Head",
    "Bip01 L UpperArm", "Bip01 R UpperArm",
    "Bip01 L Thigh", "Bip01 R Thigh",
)


def _detect_source_skeleton(arm_obj) -> str:
    """Return ``rocketbox`` for Bip01-namespaced armatures, ``unknown`` otherwise."""
    if arm_obj is None or getattr(arm_obj, "type", None) != "ARMATURE":
        return "unknown"
    names = {b.name for b in arm_obj.data.bones}
    if all(sig in names for sig in _ROCKETBOX_SIGNATURE):
        return "rocketbox"
    return "unknown"


_RETARGET_ALGO_VERSION = "v9-rocketbox-only"


def cache_key(
    fbx_path: str,
    *,
    skeleton: str,
    fps: int,
    loop: bool,
    name: Optional[str] = None,
    target_rest_blend: Optional[str] = None,
) -> str:
    """Stable hash of the FBX + filter knobs used to name the cached output.

    Re-running with the same .fbx (same path, mtime and size) and the same
    knobs returns the same key, so the AnimationNode can skip conversion
    on repeat graph executions.
    """
    stat = os.stat(fbx_path)
    h = hashlib.sha1()
    h.update(os.path.abspath(fbx_path).encode())
    h.update(str(stat.st_mtime_ns).encode())
    h.update(str(stat.st_size).encode())
    h.update(skeleton.encode())
    h.update(str(int(fps)).encode())
    h.update(str(bool(loop)).encode())
    h.update((name or "").encode())
    h.update(_RETARGET_ALGO_VERSION.encode())
    if target_rest_blend and os.path.isfile(target_rest_blend):
        tstat = os.stat(target_rest_blend)
        h.update(os.path.abspath(target_rest_blend).encode())
        h.update(str(tstat.st_mtime_ns).encode())
        h.update(str(tstat.st_size).encode())
    return h.hexdigest()[:16]


def fbx_to_blend(
    fbx_path: str,
    out_path: str,
    *,
    name: Optional[str] = None,
    skeleton: str = "rocketbox",
    fps: int = 30,
    loop: bool = True,
    root_motion: bool = False,
    target_rest_blend: Optional[str] = None,
) -> str:
    """Import ``fbx_path``, retarget its action, and write an Action-only .blend.

    When ``target_rest_blend`` is provided, uses a worldspace matrix-copy
    retarget onto that rig; otherwise falls back to text-only bone-name
    rename via the Rocketbox map. ``root_motion=False`` strips every
    location F-curve so the avatar stays anchored at its placement.
    """
    import bpy

    if not os.path.isfile(fbx_path):
        raise FileNotFoundError(f"FBX not found: {fbx_path!r}")
    if os.path.splitext(fbx_path)[1].lower() != ".fbx":
        raise ValueError(f"fbx_to_blend expects an .fbx file, got {fbx_path!r}")

    anim_name = name or os.path.splitext(os.path.basename(fbx_path))[0]

    from toybox.lib.rig_convert import ROCKETBOX_BONE_MAP

    # Snapshot current scene data so we can clean up everything the FBX
    # import drops in (armature, mesh, materials, objects, ...).
    pre_actions = set(bpy.data.actions.keys())
    pre_objects = set(bpy.data.objects.keys())
    pre_armatures = set(bpy.data.armatures.keys())
    pre_meshes = set(bpy.data.meshes.keys())
    pre_materials = set(bpy.data.materials.keys())
    pre_images = set(bpy.data.images.keys())

    logger.info("fbx_to_blend: importing %s", fbx_path)
    bpy.ops.import_scene.fbx(filepath=fbx_path)

    new_actions = [a for a in bpy.data.actions if a.name not in pre_actions]
    if not new_actions:
        raise RuntimeError(
            f"fbx_to_blend: no Action data-block found after importing {fbx_path!r}; "
            f"is this an FBX with baked animation?"
        )

    new_armatures = [
        o for o in bpy.data.objects
        if o.type == "ARMATURE" and o.name not in pre_objects
    ]
    src_arm_obj = new_armatures[0] if new_armatures else None

    # Rocketbox .fbx files ship multiple sibling actions; prefer the one
    # bound to the source armature, fall back to the largest.
    action = None
    if src_arm_obj and src_arm_obj.animation_data and src_arm_obj.animation_data.action \
       and src_arm_obj.animation_data.action.name not in pre_actions:
        action = src_arm_obj.animation_data.action
    if action is None:
        action = max(new_actions, key=lambda a: len(a.fcurves))
    if len(new_actions) > 1:
        logger.info(
            "fbx_to_blend: %d new actions found, using %r (%d fcurves)",
            len(new_actions), action.name, len(action.fcurves),
        )

    src_skel = _detect_source_skeleton(src_arm_obj) if src_arm_obj else "unknown"
    logger.info("fbx_to_blend: detected source skeleton = %s", src_skel)

    if target_rest_blend and src_arm_obj is not None:
        action = _worldspace_retarget_action(
            src_arm_obj, target_rest_blend, anim_name, ROCKETBOX_BONE_MAP,
        )
    else:
        action = _textonly_remap_action(action, ROCKETBOX_BONE_MAP)

    if not root_motion:
        loc_curves = [
            fc for fc in list(action.fcurves) if fc.data_path.endswith("location")
        ]
        for fc in loc_curves:
            action.fcurves.remove(fc)
        logger.info(
            "fbx_to_blend: root_motion=False -> stripped %d location F-curves",
            len(loc_curves),
        )

    # Tag the Action and stamp metadata.
    action.name = anim_name
    action.use_fake_user = True
    action["ana_kind"] = "animation"
    action["ana_skeleton"] = skeleton
    action["ana_fps"] = int(fps)
    action["ana_loop"] = bool(loop)
    action["ana_root_motion"] = bool(root_motion)

    start_f = int(action.frame_range[0])
    end_f = int(action.frame_range[1])
    n_frames = end_f - start_f + 1
    logger.info(
        "fbx_to_blend: action %r frames %d-%d (%d frames)",
        action.name, start_f, end_f, n_frames,
    )

    # Write JUST the Action to the output file. fake_user=True keeps the
    # data-block alive on the consumer side without an owner referencing
    # it directly (AnimationNode does its own owner-assignment later).
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    bpy.data.libraries.write(out_path, {action}, fake_user=True)
    logger.info("fbx_to_blend: wrote %s", out_path)

    # Clean up the imported junk so we don't leak armature/mesh/object/etc
    # data-blocks into whatever scene the caller is building.
    _purge_new(pre_objects, bpy.data.objects)
    _purge_new(pre_armatures, bpy.data.armatures)
    _purge_new(pre_meshes, bpy.data.meshes)
    _purge_new(pre_materials, bpy.data.materials)
    _purge_new(pre_images, bpy.data.images)
    # The Action itself stays in bpy.data.actions until orphan purge --
    # harmless, and avoids breaking anyone holding a reference.

    return out_path


def _purge_new(pre_keys: Iterable[str], data_collection) -> None:
    """Remove every datablock in ``data_collection`` whose name is not in ``pre_keys``."""
    pre = set(pre_keys)
    for name in [k for k in data_collection.keys() if k not in pre]:
        try:
            data_collection.remove(data_collection[name], do_unlink=True)
        except Exception as e:  # pragma: no cover - best-effort cleanup
            logger.debug("fbx_to_blend cleanup: could not remove %s: %s", name, e)


def _textonly_remap_action(action, bone_map: dict):
    """Rewrite F-curve ``data_path`` entries via ``bone_map`` (source ->
    rendered_humanoid). Fallback when no ``target_rest_blend`` is supplied."""
    remapped = 0
    unmapped: set[str] = set()
    for fc in action.fcurves:
        m = _BONE_RE.search(fc.data_path)
        if not m:
            continue
        src = m.group(1)
        dst = bone_map.get(src)
        if dst is None:
            unmapped.add(src)
            continue
        fc.data_path = fc.data_path.replace(
            f'pose.bones["{src}"]', f'pose.bones["{dst}"]'
        )
        remapped += 1
    logger.info(
        "fbx_to_blend: text-only remap rewrote %d F-curve bone references",
        remapped,
    )
    if unmapped:
        logger.warning(
            "fbx_to_blend: %d bone(s) had no entry in the bone map: %s",
            len(unmapped), sorted(unmapped),
        )
    return action




def _worldspace_retarget_action(src_arm_obj, target_rest_blend: str, new_action_name: str, bone_map: dict):
    """Retarget by copying each mapped bone's WORLD-space matrix, frame by
    frame, from ``src_arm_obj`` onto a fresh instance of the target rig
    loaded from ``target_rest_blend``.

    Source and target share bone-for-bone topology (only the name
    differs, via ``bone_map``), so setting ``pose_bone.matrix`` directly
    to the source bone's world matrix reproduces the same spatial
    orientation regardless of rest-pose differences. Bones are processed
    parent-before-child each frame so a child's ``matrix_basis`` is
    always solved against its parent's already-updated pose.
    """
    import bpy  # noqa: F401

    # Load the OBJECT to preserve its residual transform (see
    # rig_convert._floor_clamp_rest_pose / convert_rig_to_standard).
    pre_obj_names = {o.name for o in bpy.data.objects}
    with bpy.data.libraries.load(target_rest_blend, link=False) as (df, dt):
        dt.objects = list(df.objects)
    new_objs = [o for o in bpy.data.objects if o.name not in pre_obj_names]
    tgt_arm_obj = next((o for o in new_objs if o.type == "ARMATURE"), None)
    if tgt_arm_obj is None:
        raise RuntimeError(
            f"fbx_to_blend: [worldspace] no armature object found in {target_rest_blend!r}"
        )
    bpy.context.scene.collection.objects.link(tgt_arm_obj)
    bpy.context.view_layer.update()
    logger.info(
        "fbx_to_blend: [worldspace] appended target armature %r (%d bones, matrix_world=%s) from %s",
        tgt_arm_obj.data.name, len(tgt_arm_obj.data.bones),
        [round(c, 4) for row in tgt_arm_obj.matrix_world for c in row],
        os.path.basename(target_rest_blend),
    )

    src_bones = src_arm_obj.pose.bones
    tgt_bones = tgt_arm_obj.pose.bones
    pairs = [(s, t) for s, t in bone_map.items() if s in src_bones and t in tgt_bones]
    if not pairs:
        bpy.data.objects.remove(tgt_arm_obj, do_unlink=True)
        raise RuntimeError("fbx_to_blend: [worldspace] no bones matched between source and target")

    def _depth(tgt_name: str) -> int:
        b = tgt_arm_obj.data.bones[tgt_name]
        d = 0
        while b.parent is not None:
            d += 1
            b = b.parent
        return d

    pairs.sort(key=lambda p: _depth(p[1]))

    src_action = src_arm_obj.animation_data.action if src_arm_obj.animation_data else None
    if src_action is None:
        bpy.data.objects.remove(tgt_arm_obj, do_unlink=True)
        raise RuntimeError("fbx_to_blend: [worldspace] source armature has no action")
    f_start, f_end = int(src_action.frame_range[0]), int(src_action.frame_range[1])

    new_action = bpy.data.actions.new(new_action_name)
    if tgt_arm_obj.animation_data is None:
        tgt_arm_obj.animation_data_create()
    tgt_arm_obj.animation_data.action = new_action

    tgt_world_inv = tgt_arm_obj.matrix_world.inverted()
    scene = bpy.context.scene
    orig_frame = scene.frame_current

    for f in range(f_start, f_end + 1):
        scene.frame_set(f)
        for src_name, tgt_name in pairs:
            world_m = src_arm_obj.matrix_world @ src_bones[src_name].matrix
            tgt_bones[tgt_name].matrix = tgt_world_inv @ world_m
            # PoseBone.matrix setter derives matrix_basis from the parent's
            # currently-evaluated pose. Without an intervening depsgraph tick,
            # the parent's just-assigned basis has not propagated -- pose.bones
            # reads still return rest -- so any child bone's basis gets solved
            # against a stale parent and cascades wrong down the chain. Tick
            # after each assignment so every subsequent child sees the fresh
            # parent pose. Pairs are sorted parent-first above.
            bpy.context.view_layer.update()
        for _, tgt_name in pairs:
            tpb = tgt_bones[tgt_name]
            prop = "rotation_quaternion" if tpb.rotation_mode == "QUATERNION" else "rotation_euler"
            tpb.keyframe_insert(prop, frame=f)
            tpb.keyframe_insert("location", frame=f)

    scene.frame_set(orig_frame)
    logger.info(
        "fbx_to_blend: [worldspace] baked %d frames x %d bones -> action %r (%d fcurves)",
        f_end - f_start + 1, len(pairs), new_action.name, len(new_action.fcurves),
    )

    bpy.data.objects.remove(tgt_arm_obj, do_unlink=True)

    return new_action

