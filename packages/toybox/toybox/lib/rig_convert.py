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
"""Convert a user-uploaded rigged avatar to the ``rendered_humanoid`` standard.

This is the runtime embodiment of the contribution workflow in the avatars
volume ``ASSET_STANDARDS.md`` §1.8: take an arbitrary rigged-character file
(``.blend`` / ``.fbx`` / ``.glb``) and normalise it to the canonical
``rendered_humanoid`` skeleton namespace (§2.2/§2.3) so the existing
``Character`` / ``Avatar Pose`` / ``Avatar Animation`` nodes consume it
unchanged.

**Happy-path scope (deliberate).** v1 performs **bone-name remapping only**,
assuming the upload is authored in (or trivially close to) ``rendered_humanoid``
+ T-pose. It does NOT apply a rest-pose correction offset -- the parent-aware
rest-pose retarget math in ``lib/fbx_to_blend.py`` is flagged WIP/broken
(``ASSET_STANDARDS_OPEN_QUESTIONS.md`` C1), so cross-rest-pose sources (e.g.
A-pose rigs receiving T-pose clips) are intentionally out of scope until that
core is proven. Uploads must therefore be T-pose; an A-pose upload is accepted
but only *tagged* ``ana_rest_pose = "a_pose"`` for downstream handling, never
silently corrected.

Pipeline:

  1. Import the upload into the current Blender session (importer by extension).
  2. Find the single Armature root and the meshes parented to it.
  3. Detect/resolve the source skeleton namespace.
  4. If the source is not ``rendered_humanoid``, rename **edit bones** AND the
     matching **vertex groups** on every child mesh (the Armature modifier binds
     by name, so both must move together) using the source name map.
  5. Validate that all 20 required ``rendered_humanoid`` roles (§2.3) exist;
     raise a clear, enumerated error otherwise.
  6. Stamp the §3.4 character ``ana_*`` custom properties on the Armature.
  7. Wrap rig + meshes in one collection and write a temp ``.blend`` that the
     standard ``avatar_load`` loader then consumes.

Deterministic: no RNG is used here.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile

import bpy


logger = logging.getLogger(__name__)

#: Bump when the conversion logic changes meaningfully so the on-disk cache
#: invalidates stale outputs automatically.
_CONVERT_ALGO_VERSION = "v6-rocketbox-floor-clamp"

def _cache_dir() -> str:
    base = os.environ.get("ANA_RIG_CONVERT_CACHE_DIR") or os.path.join(
        tempfile.gettempdir(), "ana_rig_convert_cache"
    )
    os.makedirs(base, exist_ok=True)
    return base


def cache_key(src_path: str, *, source: str, rest_pose: str, demographics: dict) -> str:
    """Stable hash of the upload + conversion knobs used to name the output."""
    stat = os.stat(src_path)
    h = hashlib.sha1()
    h.update(os.path.abspath(src_path).encode())
    h.update(str(stat.st_mtime_ns).encode())
    h.update(str(stat.st_size).encode())
    h.update(source.encode())
    h.update(rest_pose.encode())
    for k in sorted(demographics or {}):
        h.update(f"{k}={demographics[k]}".encode())
    h.update(_CONVERT_ALGO_VERSION.encode())
    return h.hexdigest()[:16]

#: Canonical skeleton namespace every converted rig is normalised to
#: (ASSET_STANDARDS.md §2.2, resolved 2026-06-04).
CANONICAL_SKELETON = "rendered_humanoid"

#: The 20 required semantic roles of ``rendered_humanoid`` (ASSET_STANDARDS.md
#: §2.3): 1 pelvis role (HumGen's hip-height ``spine``) + 3 spine + 2 head/neck
#: + 8 arm + 6 leg. Fingers/toes/palms are optional and not validated here.
REQUIRED_BONES = (
    "spine", "spine.001", "spine.002", "spine.003",
    "neck", "head",
    "shoulder.L", "shoulder.R",
    "upper_arm.L", "upper_arm.R",
    "forearm.L", "forearm.R",
    "hand.L", "hand.R",
    "thigh.L", "thigh.R",
    "shin.L", "shin.R",
    "foot.L", "foot.R",
)

_ROCKETBOX_SIGNATURE = (
    "Bip01 Pelvis", "Bip01 Spine", "Bip01 Head",
    "Bip01 L UpperArm", "Bip01 R UpperArm",
    "Bip01 L Thigh", "Bip01 R Thigh",
)


def detect_source_skeleton(armature) -> str:
    """Return ``rendered_humanoid``, ``rocketbox``, or ``unknown``."""
    names = {b.name for b in armature.data.bones}
    if set(REQUIRED_BONES).issubset(names):
        return CANONICAL_SKELETON
    if all(sig in names for sig in _ROCKETBOX_SIGNATURE):
        return "rocketbox"
    return "unknown"


#: Microsoft Rocketbox NVIDIA-biped ``Bip01 <bone>`` → ``rendered_humanoid``
#: bone map. Mirrors the JSON asset at
#: ``708b0ca9-…/BoneMappings/rocketbox.json`` (MIT, Microsoft skeleton +
#: Rendered.ai-authored map). Covers the 20 required §2.3 roles plus the 32
#: optional finger/toe roles. Palm metacarpals are not authored on Rocketbox
#: and are omitted here per §2.3 which permits their absence.
ROCKETBOX_BONE_MAP = {
    "Bip01 Pelvis":     "spine",
    "Bip01 Spine":      "spine.001",
    "Bip01 Spine1":     "spine.002",
    "Bip01 Spine2":     "spine.003",
    "Bip01 Neck":       "neck",
    "Bip01 Head":       "head",

    "Bip01 L Clavicle": "shoulder.L",
    "Bip01 R Clavicle": "shoulder.R",
    "Bip01 L UpperArm": "upper_arm.L",
    "Bip01 R UpperArm": "upper_arm.R",
    "Bip01 L Forearm":  "forearm.L",
    "Bip01 R Forearm":  "forearm.R",
    "Bip01 L Hand":     "hand.L",
    "Bip01 R Hand":     "hand.R",

    "Bip01 L Thigh":    "thigh.L",
    "Bip01 R Thigh":    "thigh.R",
    "Bip01 L Calf":     "shin.L",
    "Bip01 R Calf":     "shin.R",
    "Bip01 L Foot":     "foot.L",
    "Bip01 R Foot":     "foot.R",

    "Bip01 L Toe0":     "toe.L",
    "Bip01 R Toe0":     "toe.R",

    "Bip01 L Finger0":  "thumb.01.L",
    "Bip01 L Finger01": "thumb.02.L",
    "Bip01 L Finger02": "thumb.03.L",
    "Bip01 R Finger0":  "thumb.01.R",
    "Bip01 R Finger01": "thumb.02.R",
    "Bip01 R Finger02": "thumb.03.R",

    "Bip01 L Finger1":  "f_index.01.L",
    "Bip01 L Finger11": "f_index.02.L",
    "Bip01 L Finger12": "f_index.03.L",
    "Bip01 R Finger1":  "f_index.01.R",
    "Bip01 R Finger11": "f_index.02.R",
    "Bip01 R Finger12": "f_index.03.R",

    "Bip01 L Finger2":  "f_middle.01.L",
    "Bip01 L Finger21": "f_middle.02.L",
    "Bip01 L Finger22": "f_middle.03.L",
    "Bip01 R Finger2":  "f_middle.01.R",
    "Bip01 R Finger21": "f_middle.02.R",
    "Bip01 R Finger22": "f_middle.03.R",

    "Bip01 L Finger3":  "f_ring.01.L",
    "Bip01 L Finger31": "f_ring.02.L",
    "Bip01 L Finger32": "f_ring.03.L",
    "Bip01 R Finger3":  "f_ring.01.R",
    "Bip01 R Finger31": "f_ring.02.R",
    "Bip01 R Finger32": "f_ring.03.R",

    "Bip01 L Finger4":  "f_pinky.01.L",
    "Bip01 L Finger41": "f_pinky.02.L",
    "Bip01 L Finger42": "f_pinky.03.L",
    "Bip01 R Finger4":  "f_pinky.01.R",
    "Bip01 R Finger41": "f_pinky.02.R",
    "Bip01 R Finger42": "f_pinky.03.R",
}


def _source_bone_map(source: str) -> dict:
    """``source-name -> rendered_humanoid-name`` map for a supported source."""
    if source == "rocketbox":
        return dict(ROCKETBOX_BONE_MAP)
    raise RuntimeError(
        f"Avatar Convert: no bone-name map for source skeleton {source!r}. "
        "Supported sources: 'rendered_humanoid' (no remap), 'rocketbox'."
    )


def _find_armature(objects):
    arms = [o for o in objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise RuntimeError(
            f"Avatar Convert: expected exactly one ARMATURE in the upload, "
            f"found {len(arms)}. The standard requires a single armature root "
            "with all meshes parented to it (ASSET_STANDARDS.md §3.5)."
        )
    return arms[0]


def _import_upload(src_path: str):
    """Import the upload and return the list of objects it added to the scene."""
    ext = os.path.splitext(src_path)[1].lower()
    before = set(bpy.data.objects)

    if ext == ".blend":
        # Load objects only (not the source collections) so cleanup afterwards
        # is a bounded set of objects we own -- no stray source collections to
        # track. Parenting + armature-modifier refs are carried on the object
        # data-blocks themselves, so the rig stays intact.
        with bpy.data.libraries.load(src_path, link=False) as (df, dt):
            dt.objects = df.objects
        for obj in dt.objects:
            if obj is not None and not obj.users_collection:
                bpy.context.scene.collection.objects.link(obj)
    elif ext == ".fbx":
        # Default importer flags. The importer leaves the armature at
        # scale 0.01 (source cm -> m residual) plus a -90 deg Z rotation
        # (axis remap), but the world-space geometry is correct: character
        # standing upright at Z=0..1.74, arms along X, facing +Y. We accept
        # the object-level residual and do not transform_apply -- doing so
        # would bake the scale into the bone rest matrices and shrink the
        # deformed mesh 100x. The subsequent floor-clamp step brings the
        # object origin from the pelvis to the feet.
        bpy.ops.import_scene.fbx(filepath=src_path)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=src_path)
    else:
        raise RuntimeError(
            f"Avatar Convert: unsupported upload extension {ext!r}. "
            "Use .blend, .fbx, or .glb/.gltf."
        )

    added = [o for o in bpy.data.objects if o not in before]
    if not added:
        raise RuntimeError(
            f"Avatar Convert: importing {src_path!r} added no objects."
        )
    return added


def _floor_clamp_rest_pose(armature) -> float:
    """Move the armature-object origin down to the feet and bake it in.

    Enforces the rendered_humanoid contract of "rig origin at the feet".
    Rocketbox FBX files ship with the armature object's origin at the
    pelvis (Z ~= 0.92 m) while the mesh feet already sit at world Z=0.
    Left as-is, ``avatar_load``'s later ``rig.location = (x, y, z)`` would
    place the pelvis at ``z`` instead of the feet, dropping the character
    ~0.9 m below the ground.

    Measures the lowest world-Z vertex across the parented meshes and
    shifts the armature object down by that offset, then bakes ONLY the
    location into the armature data via ``transform_apply(location=True)``
    -- rotation and scale are left untouched so the FBX importer's
    axis-conversion residuals don't bleed into the bone rest matrices
    (baking those would shrink the deformed mesh 100x).

    Idempotent: re-runs are no-ops when the mesh already touches Z=0.
    Returns the shift applied (positive = moved down).
    """
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    min_z = None
    for child in armature.children_recursive:
        if child.type != "MESH":
            continue
        ev = child.evaluated_get(depsgraph)
        mw = ev.matrix_world
        for v in ev.data.vertices:
            z = (mw @ v.co).z
            if min_z is None or z < min_z:
                min_z = z
    if min_z is None or abs(min_z) < 1e-4:
        return 0.0

    # Move armature so its own origin sits at feet in world space.
    armature.location.z -= min_z

    # Bake ONLY the translation into the armature data so a downstream
    # `rig.location = (x, y, z)` places the FEET at (x, y, z). Rotation
    # and scale are deliberately left alone (see docstring).
    prev_active = bpy.context.view_layer.objects.active
    prev_selected = list(bpy.context.selected_objects)
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    bpy.context.view_layer.objects.active = prev_active
    bpy.ops.object.select_all(action="DESELECT")
    for o in prev_selected:
        try:
            o.select_set(True)
        except (ReferenceError, RuntimeError):
            pass

    logger.info(
        "Avatar Convert: floor-clamped rest pose (shifted armature by %.4f m so feet -> Z=0)",
        -min_z,
    )
    return -min_z


def _rename_bones_and_groups(armature, name_map: dict) -> int:
    """Rename edit bones and the matching child-mesh vertex groups in place.

    Returns the number of bones renamed. Renaming is done in edit mode so bone
    parenting is preserved; vertex groups are renamed in object mode afterwards
    because the Armature deform binds vertex-group name -> bone name.
    """
    meshes = [c for c in armature.children_recursive if c.type == "MESH"]

    rename = {}
    for bone in armature.data.bones:
        target = name_map.get(bone.name)
        if target and target != bone.name:
            rename[bone.name] = target

    if not rename:
        return 0

    prev_active = bpy.context.view_layer.objects.active
    prev_mode = armature.mode if armature == prev_active else None

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        ebones = armature.data.edit_bones
        for old, new in rename.items():
            eb = ebones.get(old)
            if eb is not None:
                eb.name = new
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
        if prev_active is not None:
            bpy.context.view_layer.objects.active = prev_active
            if prev_mode and prev_mode != "OBJECT":
                try:
                    bpy.ops.object.mode_set(mode=prev_mode)
                except RuntimeError:
                    pass

    # Move the vertex groups so the deform keeps binding.
    for mesh in meshes:
        for old, new in rename.items():
            vg = mesh.vertex_groups.get(old)
            if vg is not None and mesh.vertex_groups.get(new) is None:
                vg.name = new

    logger.info("Avatar Convert: renamed %d bones to %s", len(rename), CANONICAL_SKELETON)
    return len(rename)


def _validate_required_bones(armature) -> None:
    names = {b.name for b in armature.data.bones}
    missing = [b for b in REQUIRED_BONES if b not in names]
    if missing:
        raise RuntimeError(
            "Avatar Convert: rig is missing required rendered_humanoid bones "
            f"after remap: {missing}. The upload must provide all 20 required "
            "roles (ASSET_STANDARDS.md §2.3). Supply an explicit Source Rig or "
            "fix the source bone names."
        )


def _measure_height_m(armature) -> float:
    """Height in metres = max world-Z of any deformed mesh vertex (rest pose)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    top = 0.0
    found = False
    for child in armature.children_recursive:
        if child.type != "MESH":
            continue
        ev = child.evaluated_get(depsgraph)
        mw = ev.matrix_world
        for v in ev.data.vertices:
            z = (mw @ v.co).z
            if not found or z > top:
                top = z
                found = True
    return float(top) if found else 1.78


def convert_rig_to_standard(
    src_path: str,
    *,
    source: str = "auto",
    rest_pose: str = "t_pose",
    demographics: dict | None = None,
    out_dir: str | None = None,
) -> str:
    """Normalise ``src_path`` to ``rendered_humanoid`` and return a temp .blend.

    Args:
        src_path: absolute path to the uploaded ``.blend`` / ``.fbx`` / ``.glb``.
        source: ``auto`` | ``rendered_humanoid`` | ``rocketbox``. ``auto`` detects
            from bone names and errors if it can't decide.
        rest_pose: ``t_pose`` | ``a_pose`` -- tagged on the rig only (no offset).
        demographics: optional ``{gender, ethnicity, age_group}`` ground truth
            stamped as ``ana_*`` since uploads usually lack it.
        out_dir: directory for the temp blend (defaults to the system temp dir).

    Raises:
        RuntimeError on any contract violation, with an actionable message.
    """
    demographics = demographics or {}
    source = (source or "auto").strip().lower()
    rest_pose = (rest_pose or "t_pose").strip().lower()
    if rest_pose not in ("t_pose", "a_pose"):
        raise RuntimeError(f"Avatar Convert: rest_pose must be t_pose/a_pose, got {rest_pose!r}.")

    out_dir = out_dir or _cache_dir()
    os.makedirs(out_dir, exist_ok=True)
    key = cache_key(src_path, source=source, rest_pose=rest_pose, demographics=demographics)
    stem = os.path.splitext(os.path.basename(src_path))[0]
    out_blend = os.path.join(out_dir, f"converted_{stem}_{key}.blend")
    if os.path.isfile(out_blend):
        logger.info("Avatar Convert: cache hit %s", out_blend)
        return out_blend

    added = _import_upload(src_path)
    armature = _find_armature(added)

    if source == "auto":
        source = detect_source_skeleton(armature)
        if source == "unknown":
            raise RuntimeError(
                "Avatar Convert: could not auto-detect the source skeleton. "
                "Set Source Rig explicitly to 'rendered_humanoid' or 'rocketbox'."
            )
        logger.info("Avatar Convert: auto-detected source skeleton %s", source)

    if source != CANONICAL_SKELETON:
        _rename_bones_and_groups(armature, _source_bone_map(source))

    _validate_required_bones(armature)

    # Rocketbox (and some other sources) ship the rig with its origin at
    # the pelvis, not the feet. rendered_humanoid contract is "origin at
    # feet" so a placement node's Z lines up with ground-contact height.
    _floor_clamp_rest_pose(armature)

    # Drop any animation that rode along; Avatar Pose/Animation own actions.
    if armature.animation_data:
        armature.animation_data_clear()

    armature["ana_kind"] = "character"
    armature["ana_skeleton"] = CANONICAL_SKELETON
    armature["ana_rest_pose"] = rest_pose
    armature["ana_version"] = "1"
    armature["ana_height"] = _measure_height_m(armature)
    for dkey, prop in (("gender", "ana_gender"), ("ethnicity", "ana_ethnicity"),
                       ("age_group", "ana_age_group")):
        val = demographics.get(dkey)
        if val:
            armature[prop] = str(val)

    # Wrap rig + descendant meshes into one clean collection for export.
    members = [armature] + list(armature.children_recursive)
    col = bpy.data.collections.new(stem)
    for o in members:
        try:
            col.objects.link(o)
        except RuntimeError:
            pass
    bpy.context.scene.collection.children.link(col)

    try:
        bpy.ops.file.pack_all()
    except Exception as e:  # noqa: BLE001
        logger.warning("Avatar Convert: pack_all skipped: %s", e)
    bpy.data.libraries.write(out_blend, {col}, fake_user=True, compress=False)
    logger.info("Avatar Convert: wrote standardised rig -> %s", out_blend)

    # Clean the imported objects out of the current session so this exec-time
    # conversion never pollutes the render scene. Only the data-blocks WE
    # created/imported are removed -- never a global orphans_purge, which would
    # delete other nodes' not-yet-linked data (e.g. a Sun light created before
    # this node ran but not yet linked to a scene).
    _purge_session(col, set(added) | set(members))
    return out_blend


def _purge_session(collection, objects) -> None:
    """Remove the wrapper collection + imported objects + their data-blocks."""
    meshes, armatures = [], []
    for obj in objects:
        try:
            data = obj.data
        except ReferenceError:
            continue
        if obj.type == "MESH" and data is not None:
            meshes.append(data)
        elif obj.type == "ARMATURE" and data is not None:
            armatures.append(data)
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except (ReferenceError, RuntimeError):
            pass
    try:
        bpy.data.collections.remove(collection)
    except (ReferenceError, RuntimeError):
        pass
    # Remove the now-orphaned mesh/armature data-blocks we imported, targeted
    # by reference so nothing else in the session is touched.
    for data in meshes:
        if data.users == 0:
            try:
                bpy.data.meshes.remove(data)
            except (ReferenceError, RuntimeError):
                pass
    for data in armatures:
        if data.users == 0:
            try:
                bpy.data.armatures.remove(data)
            except (ReferenceError, RuntimeError):
                pass
