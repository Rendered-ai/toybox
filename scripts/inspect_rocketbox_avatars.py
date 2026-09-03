"""Headless Blender pass: populate bounding_box + polygon_count on the
Rocketbox avatar sidecars staged by the 2026-08-29 avatar-adding pass.

Loads each FBX into a clean empty scene, measures the combined
world-space bounding box across every MESH object, sums polygon counts,
and updates the sibling `<Name>.json` sidecar in place. Existing fields
are preserved; only `bounding_box` and `polygon_count` are overwritten.

Usage (via the ana channel container):
    docker run --rm \
        -v /workspace:/workspace \
        <ana-image> \
        blender --background --python /ana/scripts/inspect_rocketbox_avatars.py

Or via the wrapper script `scripts/inspect_rocketbox_avatars.sh`.
"""
from __future__ import annotations

import json
import os
import sys
from math import inf

import bpy  # type: ignore

# Six avatars staged in the 2026-08-29 pass. Business_Female_01 and
# Business_Male_01 already have Blender-inspected sidecars; skip them.
TARGETS = [
    "Chef_Female_01",
    "Construction_Male_01",
    "Medical_Female_01",
    "Medical_Male_01",
    "Female_Adult_01",
    "Male_Adult_01",
]

AVATAR_ROOT = "/workspace/volumes/708b0ca9-d81c-4679-b164-141418507830/RocketboxAvatars"


def measure_fbx(fbx_path):
    """Import the FBX into an empty scene, return (bbox, polygon_count)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_path)

    mn = [inf, inf, inf]
    mx = [-inf, -inf, -inf]
    poly_count = 0

    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.data is None:
            continue
        poly_count += len(obj.data.polygons)
        # World-space corner sweep -- honours FBX importer's residual
        # transform (0.01 scale + -90 Z remap) so the sidecar matches
        # what downstream code sees.
        for corner in obj.bound_box:
            wx = obj.matrix_world @ __import__("mathutils").Vector(corner)
            for i in range(3):
                if wx[i] < mn[i]:
                    mn[i] = wx[i]
                if wx[i] > mx[i]:
                    mx[i] = wx[i]

    bbox = {
        "min": [round(v, 3) for v in mn],
        "max": [round(v, 3) for v in mx],
    }
    return bbox, poly_count


def update_sidecar(sidecar_path, bbox, poly_count):
    with open(sidecar_path) as fh:
        data = json.load(fh)
    data["bounding_box"] = bbox
    data["polygon_count"] = poly_count
    if "notes" in data:
        data["notes"] = data["notes"].replace(
            "bounding_box and polygon_count omitted pending a Blender-inspect "
            "pass -- populate from bpy.context.scene.objects[<Armature>].dimensions "
            "and sum(o.data.polygons for o in mesh_objects).",
            "bounding_box and polygon_count filled by "
            "scripts/inspect_rocketbox_avatars.py (headless Blender pass)."
        )
    with open(sidecar_path, "w") as fh:
        json.dump(data, fh, indent=2)


def main() -> int:
    for name in TARGETS:
        fbx = os.path.join(AVATAR_ROOT, name, f"{name}.fbx")
        sidecar = os.path.join(AVATAR_ROOT, name, f"{name}.json")
        if not (os.path.isfile(fbx) and os.path.isfile(sidecar)):
            print(f"SKIP {name}: missing fbx or sidecar", file=sys.stderr)
            continue
        try:
            bbox, poly_count = measure_fbx(fbx)
        except Exception as e:
            print(f"FAIL {name}: {e}", file=sys.stderr)
            continue
        update_sidecar(sidecar, bbox, poly_count)
        print(f"OK   {name}: bbox={bbox['min']}..{bbox['max']} polys={poly_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
