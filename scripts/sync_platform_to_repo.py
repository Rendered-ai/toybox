"""Re-sync the showcase graphs from `graphs/` to the Toybox_0.3QA
platform workspace.

Default: delete every showcase_* graph in the workspace, re-upload
each yaml as staged + unstaged, kick off a smoke dataset on each
staged copy.

--review: unstaged only. Delete showcase_* (both variants) so the
review pane isn't cluttered with old versions, re-upload each yaml
staged=False, no datasets kicked off. Reviewer stages what they
want from the platform UI.

--runs N: override the default runs per smoke dataset (5).

Run:
    python3 scripts/sync_platform_to_repo.py                 # default (stage + kick 5 runs)
    python3 scripts/sync_platform_to_repo.py --review        # unstaged only
    python3 scripts/sync_platform_to_repo.py --runs 3        # stage + kick 3 runs
"""
import argparse
import os

import anatools

WS = "d714278c-7c8d-4482-a7b8-9cc7d54b4bf0"
CHANNEL = "8bd3c9b7-77da-4b9b-afca-2ddcd7dcbf93"  # toybox_blender4.2
GRAPHS_DIR = "/workspace/ana/graphs"
RUNS = 5

# (filename, platform label, platform description).
# Description is what surfaces on the platform's Graphs listing page --
# make it name the workflow patterns the graph demonstrates so a
# reviewer can pick the right graph without opening it.
GRAPHS = [
    (
        "default.yml",
        "showcase_Toys_Container_Physics",
        "Rigid-body physics scene. Toys drop into a random container "
        "and gravity settles them into a pile. Showcases Procedural "
        "Scene composition, Place Over Container physics settle, "
        "Color Variation + Warp + Weight modifier chain, per-run POINT "
        "light jitter, and Outdoor Camera Random-angle orbit.",
    ),
    (
        "fruit_hdri_test.yml",
        "showcase_Fruit_HDRI",
        "HDRI-only outdoor scene. Apples and Oranges scattered on a "
        "grassy HDRI backdrop with no Floor node. Showcases Random "
        "Placement non-overlapping scatter, Procedural Scene HDRI + "
        "HDRI Rotation, and multi-generator Object Generators input.",
    ),
    (
        "avatar_animation_demo.yml",
        "showcase_Avatar_Animation",
        "Video-frame pipeline. Rocketbox run cycle on Female_Adult_01. "
        "Showcases Avatar Convert normalisation (Bip01 -> "
        "rendered_humanoid), Avatar Animation NLA strip with root "
        "motion extraction, Animation Render (24 per-frame masks + "
        "annotations), and Random Choice heading constraint.",
    ),
    (
        "avatar_hdri_indoor_test.yml",
        "showcase_Avatar_HDRI_Indoor",
        "Avatar diversity + HDRI backdrop. Random female avatar per "
        "run in a random indoor scene. Showcases Avatar Randomizer "
        "demographic-filtered pool (ASSET_STANDARDS §3.4), Height "
        "output driving Camera Look At Z, Avatar Pose oneOrMany + "
        "Random Integer frame, and Random Uniform XY + heading jitter.",
    ),
    (
        "parking_lot_blend_scene.yml",
        "showcase_ParkingLot_BlendFile",
        "Blend File Scene (BYO artist-authored blend). Rocketbox "
        "avatar walking through Outdoor/ParkingLot.blend. Showcases "
        "Blend File Scene as the aggregator, HDRI + HDRI Rotation "
        "override, Camera XY jitter around a fixed Look At for "
        "background variety, and Random Integer walk-cycle frame.",
    ),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review",
        action="store_true",
        help="Unstaged only, no dataset kickoff -- for platform-side review.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=RUNS,
        help=f"Runs per smoke dataset (default {RUNS}).",
    )
    args = parser.parse_args()

    c = anatools.client()

    # 1. Delete stale showcase_* graphs (both variants).
    for staged in (True, False):
        existing = c.get_graphs(workspaceId=WS, staged=staged)
        stale = [g for g in existing if str(g.get("name", "")).startswith("showcase_")]
        label = "staged" if staged else "unstaged"
        print(f"Deleting {len(stale)} stale {label} showcase_* graphs...")
        for g in stale:
            c.delete_graph(graphId=g["graphId"], workspaceId=WS)

    # 2. Upload each yaml.
    variants = (False,) if args.review else (True, False)
    staged_ids = {}
    for fname, label, description in GRAPHS:
        fpath = os.path.join(GRAPHS_DIR, fname)
        if not os.path.isfile(fpath):
            print(f"MISSING: {fpath} -- skipping")
            continue
        for staged in variants:
            variant = "staged" if staged else "unstaged"
            gid = c.upload_graph(
                graph=fpath,
                channelId=CHANNEL,
                name=label,
                description=description,
                staged=staged,
                workspaceId=WS,
            )
            print(f"  uploaded {label:<40s} {variant:<8s} -> {gid}")
            if staged:
                staged_ids[label] = gid

    # 3. Kick off a RUNS-run dataset on each staged copy (skip in review mode).
    if args.review:
        print("\nReview mode: stage from the platform to run datasets.")
        return

    runs = args.runs
    print(f"\nKicking off {runs}-run datasets on {len(staged_ids)} staged graphs...")
    for label, gid in staged_ids.items():
        ds_name = label.replace("showcase_", "smoke_")
        ds_id = c.create_dataset(
            name=ds_name,
            graphId=gid,
            description=f"{runs}-run smoke of {label}",
            runs=runs,
            workspaceId=WS,
        )
        print(f"  dataset {ds_name:<40s} runs={runs} -> {ds_id}")

    print("\nDone.")


if __name__ == "__main__":
    main()
