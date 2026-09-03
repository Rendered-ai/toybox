"""Rendered.ai Asset Standards -- controlled vocabularies.

Single source of truth for the enumerated string values defined in
`ASSET_STANDARDS.md` on volume `a7ad75f2-…` (the character / animation
standards volume). Both node schemas (`avatars.yml` `select:` blocks)
and runtime filter code import from here so a change to the standard
propagates in one place.

When ASSET_STANDARDS.md gains or renames a value, edit the tuple below.
Runtime code that rejects unknown values will start rejecting on the
next graph run; schema `select:` blocks in `avatars.yml` should be
updated in the same commit so the graph-editor UI stays in sync.

Section references throughout point to `ASSET_STANDARDS.md` (2026-05-22
draft, last amended 2026-07-15).
"""

# ---------------------------------------------------------------------------
# §3.4 -- Character demographic vocabularies
# ---------------------------------------------------------------------------

GENDERS = ("female", "male")

ETHNICITIES = (
    "hispanic",
    "black",
    "asian",
    "caucasian",
    "middleeastern",
    "southasian",
)

AGE_GROUPS = ("child", "teen", "adult", "senior")

BUILDS = ("slim", "average", "heavy", "athletic")

CLOTHING = (
    "casual",
    "business",
    "formal",
    "athletic",
    "swimwear",
    "uniform",
    "outerwear",
    "medical",
    "patient_gown",
    "traditional",
    "workwear",
    "sleepwear",
    "military",
)

CLIMATES = ("tropical", "arid", "temperate", "continental", "polar")

SETTINGS = ("indoor", "outdoor")


# ---------------------------------------------------------------------------
# §4.4 -- Animation vocabularies
# ---------------------------------------------------------------------------

ANIMATION_CATEGORIES = (
    "locomotion",
    "turn",
    "gesture",
    "reaction",
    "idle",
    "emote",
    "jump",
    "fall",
    "sitting",
    "interaction",
    "medical",
    "interact_prop",
    "combat",
    "dance",
    "crouch_crawl",
)

TEMPOS = ("slow", "moderate", "fast")


# ---------------------------------------------------------------------------
# §2 -- Skeleton namespaces (rigs the channel understands)
# ---------------------------------------------------------------------------

#: The canonical namespace per §2.2. Rocketbox / Mixamo / Rigify are accepted
#: source namespaces that Avatar Convert normalises to rendered_humanoid.
SKELETONS = (
    "rendered_humanoid",
    "rocketbox",
    "mixamo",
    "rigify",
    "ue_mannequin",
)

#: Case-insensitive aliases per §2.2. "humgen" is treated as
#: "rendered_humanoid" at runtime because HumGen's native bone convention
#: satisfies the rendered_humanoid contract as-is.
SKELETON_ALIASES = {"humgen": "rendered_humanoid"}


# ---------------------------------------------------------------------------
# §3.3 -- Rest poses
# ---------------------------------------------------------------------------

REST_POSES = ("t_pose", "a_pose")


# ---------------------------------------------------------------------------
# §1.4 -- Sidecar controlled values
# ---------------------------------------------------------------------------

ORIGINS = ("center-bottom", "centroid", "pivot")

FILE_FORMATS = ("blend", "fbx", "glb", "gltf", "obj")


# ---------------------------------------------------------------------------
# Helpers -- called from node exec() paths for tag reading
# ---------------------------------------------------------------------------


def normalize_skeleton(value):
    """Apply the §2.2 skeleton alias rule.

    Returns the canonical lowercase skeleton name after resolving aliases
    (currently ``humgen`` -> ``rendered_humanoid``). Case-insensitive.
    Returns ``None`` for None / empty input so callers can use
    ``normalize_skeleton(sidecar.get("ana_skeleton"))`` uniformly.
    """
    if not value:
        return None
    key = str(value).strip().lower()
    if not key:
        return None
    return SKELETON_ALIASES.get(key, key)


def normalize_multivalue(raw):
    """Parse a comma-separated `ana_*` value into a list of trimmed tokens.

    Per §3.4, multi-value tag strings are comma-separated (e.g.
    ``"business,formal"`` or ``"indoor,outdoor"``). Empty / None / non-
    string inputs yield an empty list so a missing tag never matches a
    filter that requires a specific value.
    """
    if not raw:
        return []
    return [tok.strip() for tok in str(raw).split(",") if tok.strip()]
