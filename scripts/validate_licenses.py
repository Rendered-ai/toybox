#!/usr/bin/env python3
"""Validate asset-sidecar licenses against the channel allowlist.

Every asset staged on a Toybox-consumed volume MUST carry a sidecar JSON
per ``ASSET_STANDARDS.md`` §1.4, and that sidecar's ``license`` field
MUST be one of the SPDX identifiers listed in ``LICENSE-ASSETS.md`` §1a
(``CC0-1.0`` / ``MIT`` / ``Apache-2.0`` / ``CC-BY-4.0``), or the
``original-author-<spdx>`` form documented in ``LICENSE-ASSETS.md`` §4.

This script walks one or more directories, finds every asset sidecar
JSON, and enforces the rule. Intended to be run in CI on any volume
that hosts Toybox assets — typically the public-share volume, but
extensible to any other volume declared in ``package.yml``.

Usage
-----

Validate the current directory (e.g. a volume mount)::

    python scripts/validate_licenses.py .

Validate multiple volumes::

    python scripts/validate_licenses.py \\
        /mnt/volumes/708b0ca9-... \\
        /mnt/volumes/some-other-volume

Enforce presence of sidecars alongside every asset file, not just
sidecar correctness::

    python scripts/validate_licenses.py --strict .

Exit codes
----------

- ``0`` — every sidecar carries an allowlisted license (and, in
  ``--strict`` mode, every asset file has a sidecar).
- ``1`` — one or more violations were found. Details printed to stderr.
- ``2`` — invocation error (bad path, unreadable JSON, etc.).

The script has no external dependencies — Python 3.8+ stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Policy. Keep in sync with ``LICENSE-ASSETS.md`` §1a.
# ---------------------------------------------------------------------------

#: SPDX identifiers accepted as the ``license`` field of an asset sidecar.
ALLOWED_LICENSES: frozenset[str] = frozenset({
    "CC0-1.0",
    "MIT",
    "Apache-2.0",
    "CC-BY-4.0",
})

#: File extensions considered "asset files" for the ``--strict`` sidecar
#: presence check. Sidecars themselves are ``.json``; every asset file of
#: one of these extensions must have a same-stem ``.json`` next to it.
#:
#: HDR / EXR image collections are intentionally omitted — they are
#: conventionally batch-licensed via a directory-level index
#: (e.g. ``HDRIs/HDRI LIBRARY.md`` + a ``NOTICE.md`` section covering the
#: whole tree) rather than per-file sidecars. Add them to the allowlist
#: below if a channel elects to require per-HDR sidecars.
ASSET_EXTENSIONS: frozenset[str] = frozenset({
    ".blend", ".fbx", ".glb", ".gltf", ".obj", ".usd", ".usdc", ".usda",
})

#: Directories skipped during the walk. These typically contain scratch
#: caches, test outputs, or upstream ``LICENSE`` files that don't belong
#: to the sidecar convention.
SKIP_DIR_NAMES: frozenset[str] = frozenset({
    ".git", "__pycache__", ".ipynb_checkpoints", "node_modules",
    "unpacked", "test", "tests",
})

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Violation:
    """A single validation failure with a short human-readable message."""

    path: Path
    kind: str        # one of {"bad-license", "missing-license", "unreadable",
                     # "missing-sidecar"}
    detail: str

    def format(self, root: Path) -> str:
        try:
            rel = self.path.relative_to(root)
        except ValueError:
            rel = self.path
        return f"[{self.kind}] {rel}: {self.detail}"


@dataclass
class Report:
    root: Path
    sidecars_checked: int = 0
    assets_checked: int = 0
    violations: list[Violation] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.violations


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------


def _is_sidecar(payload: object) -> bool:
    """Heuristic: does this JSON look like an asset sidecar?

    We treat a JSON as a sidecar iff it is a top-level object AND contains
    any of the canonical sidecar keys defined in ``ASSET_STANDARDS.md``
    §1.4. This keeps unrelated JSON files (graph configs, node definitions,
    pose libraries, …) out of the license audit.
    """
    if not isinstance(payload, dict):
        return False
    canonical_keys = {
        "license", "names", "ana_kind", "file_format",
        "created_by", "bone_map",  # BoneMappings/*.json shape
    }
    return bool(canonical_keys & payload.keys())


def _license_is_allowed(value: str) -> bool:
    """Accept ``<spdx>`` verbatim or ``original-author-<spdx>`` forms."""
    if value in ALLOWED_LICENSES:
        return True
    prefix = "original-author-"
    if value.startswith(prefix) and value[len(prefix):] in ALLOWED_LICENSES:
        return True
    return False


def _iter_files(root: Path) -> Iterable[Path]:
    """Yield every file under ``root``, skipping SKIP_DIR_NAMES."""
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            continue
        for entry in entries:
            if entry.is_symlink():
                # Sidecars are always real files; ignore symlinks to avoid
                # loops and to keep the walk deterministic.
                continue
            if entry.is_dir():
                if entry.name in SKIP_DIR_NAMES:
                    continue
                stack.append(entry)
            elif entry.is_file():
                yield entry


def _check_sidecar(path: Path, report: Report) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        # A JSON in the tree that we can't parse is almost certainly not
        # a sidecar — skip it rather than fail, but log for visibility.
        report.violations.append(Violation(
            path=path, kind="unreadable",
            detail=f"could not parse as JSON: {exc.__class__.__name__}",
        ))
        return

    if not _is_sidecar(payload):
        return  # not an asset sidecar; ignore

    report.sidecars_checked += 1

    license_value = payload.get("license")
    if license_value is None:
        report.violations.append(Violation(
            path=path, kind="missing-license",
            detail="sidecar has no 'license' field",
        ))
        return

    if not isinstance(license_value, str):
        report.violations.append(Violation(
            path=path, kind="bad-license",
            detail=f"'license' is not a string: {license_value!r}",
        ))
        return

    if not _license_is_allowed(license_value):
        report.violations.append(Violation(
            path=path, kind="bad-license",
            detail=(
                f"'license' = {license_value!r} is not on the allowlist "
                f"{sorted(ALLOWED_LICENSES)} (or original-author-<spdx>)"
            ),
        ))


def _check_missing_sidecars(root: Path, report: Report) -> None:
    """In --strict mode, every asset file must have a same-stem sidecar."""
    for path in _iter_files(root):
        if path.suffix.lower() not in ASSET_EXTENSIONS:
            continue
        report.assets_checked += 1
        sidecar = path.with_suffix(".json")
        if not sidecar.exists():
            report.violations.append(Violation(
                path=path, kind="missing-sidecar",
                detail=(
                    "asset file has no accompanying .json sidecar "
                    "(ASSET_STANDARDS.md §1.4)"
                ),
            ))


def validate(root: Path, strict: bool = False) -> Report:
    """Walk ``root``, validate every sidecar, return a Report."""
    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)

    report = Report(root=root)
    for path in _iter_files(root):
        if path.suffix.lower() == ".json":
            _check_sidecar(path, report)

    if strict:
        _check_missing_sidecars(root, report)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate asset-sidecar licenses against the channel "
            "allowlist (LICENSE-ASSETS.md §1a)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help=(
            "One or more root directories to walk. Typically a mounted "
            "volume root (e.g. /mnt/volumes/708b0ca9-...)."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Also fail when an asset file (.blend / .fbx / .hdr / …) has "
            "no accompanying .json sidecar. Off by default so newly "
            "staged assets can be spotted separately from license drift."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-root summary line on success.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    reports: list[Report] = []
    for raw_path in args.paths:
        path = raw_path.resolve()
        try:
            reports.append(validate(path, strict=args.strict))
        except (FileNotFoundError, NotADirectoryError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    total_violations = 0
    for report in reports:
        for violation in report.violations:
            print(violation.format(report.root), file=sys.stderr)
        total_violations += len(report.violations)
        if not args.quiet:
            status = "OK" if report.ok() else f"FAIL ({len(report.violations)})"
            summary = (
                f"{report.root}: {status} "
                f"[sidecars={report.sidecars_checked}"
            )
            if args.strict:
                summary += f", assets={report.assets_checked}"
            summary += "]"
            print(summary)

    return 0 if total_violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
