"""Stamp `ana_*` metadata on the Rocketbox avatar sidecars to bring them
into conformance with Rendered.ai Asset Standards §3.4 controlled-vocab.

Two classes of change per sidecar:

1. Additions: `ana_kind = "character"` and `ana_skeleton = "humgen"` on
   every avatar (the standard's identification group; humgen is the
   §2.2-aliased canonical form for pre-normalisation Rocketbox rigs).
   Business_Female_01 and Business_Male_01 also gain `ana_gender`,
   `ana_clothing`, `ana_setting` derived from their tag arrays.

2. Normalisations of free-text values to §3.4 controlled vocab:
   * "chef whites" -> "uniform"
   * "scrubs"      -> "medical"

Skipped intentionally: ana_ethnicity / ana_age_group / ana_build /
ana_climate. §1.5 forbids invented values and none of these are
derivable from the tag arrays or filenames -- they need a human pass.

Dry-run by default. Pass --apply to write the sidecars.

Usage:
    python3 stamp_rocketbox_sidecars.py           # dry-run: report planned changes
    python3 stamp_rocketbox_sidecars.py --apply   # write files
"""
import argparse
import json
import os
import sys
from pathlib import Path

VOLUME_ROOT = Path(
    "/home/ubuntu/.renderedai/volumes/708b0ca9-d81c-4679-b164-141418507830/RocketboxAvatars"
)

# One entry per avatar. `additions` is merged in (only keys not already
# present are added). `normalisations` replaces the current value at the
# key with the new value (only if the current value matches the expected
# old value -- idempotent).
PLAN = {
    "Business_Female_01": {
        "additions": {
            "ana_kind": "character",
            "ana_skeleton": "humgen",
            "ana_gender": "female",
            "ana_clothing": "business",
            "ana_setting": "indoor",
        },
        "normalisations": {},
    },
    "Business_Male_01": {
        "additions": {
            "ana_kind": "character",
            "ana_skeleton": "humgen",
            "ana_gender": "male",
            "ana_clothing": "business",
            "ana_setting": "indoor",
        },
        "normalisations": {},
    },
    "Chef_Female_01": {
        "additions": {"ana_kind": "character", "ana_skeleton": "humgen"},
        "normalisations": {"ana_clothing": ("chef whites", "uniform")},
    },
    "Construction_Male_01": {
        "additions": {"ana_kind": "character", "ana_skeleton": "humgen"},
        "normalisations": {},
    },
    "Female_Adult_01": {
        "additions": {"ana_kind": "character", "ana_skeleton": "humgen"},
        "normalisations": {},
    },
    "Male_Adult_01": {
        "additions": {"ana_kind": "character", "ana_skeleton": "humgen"},
        "normalisations": {},
    },
    "Medical_Female_01": {
        "additions": {"ana_kind": "character", "ana_skeleton": "humgen"},
        "normalisations": {"ana_clothing": ("scrubs", "medical")},
    },
    "Medical_Male_01": {
        "additions": {"ana_kind": "character", "ana_skeleton": "humgen"},
        "normalisations": {"ana_clothing": ("scrubs", "medical")},
    },
}


def _reinsert_ana_block(sidecar):
    """Move all ana_* keys into a contiguous block just before
    `created_at`, matching the existing convention across sidecars.
    """
    if "created_at" not in sidecar:
        return sidecar
    ana_keys = {k: v for k, v in sidecar.items() if k.startswith("ana_")}
    if not ana_keys:
        return sidecar
    rebuilt = {}
    for k, v in sidecar.items():
        if k.startswith("ana_"):
            continue  # skip, will insert before created_at
        if k == "created_at":
            rebuilt.update(ana_keys)
        rebuilt[k] = v
    return rebuilt


def plan_changes(current, additions, normalisations):
    """Return (adds, norms, unchanged, errors) for a single sidecar."""
    adds, norms, unchanged, errors = [], [], [], []
    for k, v in additions.items():
        if k in current:
            if current[k] == v:
                unchanged.append((k, v))
            else:
                # Present but different -- treat as normalisation opportunity,
                # not automatic overwrite.
                errors.append(
                    f"key {k!r} already set to {current[k]!r}; refusing to overwrite with {v!r}"
                )
        else:
            adds.append((k, v))
    for k, (old, new) in normalisations.items():
        cur = current.get(k)
        if cur == new:
            unchanged.append((k, new))
        elif cur == old:
            norms.append((k, old, new))
        elif cur is None:
            errors.append(f"key {k!r} missing; expected {old!r} to normalise to {new!r}")
        else:
            errors.append(
                f"key {k!r} carries unexpected value {cur!r}; expected {old!r} to normalise to {new!r}"
            )
    return adds, norms, unchanged, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes.")
    args = parser.parse_args()

    total_adds, total_norms, total_errors = 0, 0, 0

    for avatar, spec in PLAN.items():
        sidecar_path = VOLUME_ROOT / avatar / f"{avatar}.json"
        if not sidecar_path.is_file():
            print(f"[{avatar}] MISSING sidecar at {sidecar_path}")
            total_errors += 1
            continue

        with sidecar_path.open() as f:
            current = json.load(f)

        adds, norms, unchanged, errors = plan_changes(
            current, spec["additions"], spec["normalisations"]
        )

        print(f"\n[{avatar}]")
        for k, v in adds:
            print(f"  + {k} = {v!r}")
        for k, old, new in norms:
            print(f"  ~ {k}: {old!r} -> {new!r}")
        for k, v in unchanged:
            print(f"  = {k} = {v!r}  (already correct)")
        for err in errors:
            print(f"  ! {err}")

        total_adds += len(adds)
        total_norms += len(norms)
        total_errors += len(errors)

        if not (adds or norms) or not args.apply:
            continue

        # Apply
        updated = dict(current)
        for k, v in adds:
            updated[k] = v
        for k, _old, new in norms:
            updated[k] = new
        updated = _reinsert_ana_block(updated)

        with sidecar_path.open("w") as f:
            json.dump(updated, f, indent=2)
            f.write("\n")
        print(f"  wrote {sidecar_path}")

    print(
        f"\nSummary: {total_adds} addition(s), {total_norms} normalisation(s), "
        f"{total_errors} error(s). "
        f"{'APPLIED.' if args.apply else 'Dry run -- pass --apply to write.'}"
    )
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
