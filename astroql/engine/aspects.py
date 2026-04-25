"""Parashari aspects (drishti) — sign-based binary form, plus
longitudinal (Sphuta Drishti) form with orbs.

Classical 7th-house aspect for all planets, plus special aspects:
  - Mars:    4th and 8th from self
  - Jupiter: 5th and 9th from self
  - Saturn:  3rd and 10th from self
  - Nodes (Rahu/Ketu): 5th, 7th, 9th — follow Jupiter convention.

Signs are 1..12 with Aries=1. The k-th sign from sign s is
  ((s - 1 + (k - 1)) % 12) + 1.

Sign-based vs longitudinal
--------------------------
The sign-based form (aspected_signs / aspects_receiving) is the
classical Parashari binary: planet X aspects sign Y or it does not.
The longitudinal form (aspect_strengths_*) replaces the binary with
an orb-graded float in [0, 1] where 1.0 = exact aspect (target
longitude equals the aspect's exact longitudinal target) and 0.0 =
beyond the orb. Both forms are surfaced on `PlanetEpochState` so
rules can choose either.
"""
from __future__ import annotations

from typing import Dict, List, Optional


_ASPECT_OFFSETS: Dict[str, tuple] = {
    # 7th = offset 6 (1-indexed "nth from": 7th from sign s means
    # (s - 1 + 6) mod 12 + 1 = s + 6 wrapping within 1..12).
    "Sun": (6,),
    "Moon": (6,),
    "Mercury": (6,),
    "Venus": (6,),
    "Mars": (3, 6, 7),       # 4th, 7th, 8th
    "Jupiter": (4, 6, 8),    # 5th, 7th, 9th
    "Saturn": (2, 6, 9),     # 3rd, 7th, 10th
    "Rahu": (4, 6, 8),       # Jupiter convention
    "Ketu": (4, 6, 8),       # Jupiter convention
}

# Aspect orb (degrees). Within ±this range, an aspect's strength
# decays linearly from 1.0 (exact) to 0.0 (at the orb edge). 10°
# matches the review's example and is conservative: outside this
# the aspect is considered not formed.
_ASPECT_ORB_DEG: float = 10.0


def _angular_diff(a: float, b: float) -> float:
    """Smallest absolute longitudinal separation in [0, 180]."""
    d = abs(a - b) % 360.0
    if d > 180.0:
        d = 360.0 - d
    return d


def aspect_strength_between(
    aspector: str,
    aspector_lon: float,
    target_lon: float,
    orb_deg: float = _ASPECT_ORB_DEG,
) -> float:
    """Strength of `aspector`'s aspect onto `target_lon`, in [0, 1].

    For each of the planet's classical aspect arcs (7th = 180° from
    self; special aspects = 90°/210°/240° etc. for Mars/Jupiter/Saturn)
    we compute the longitudinal distance from the target to the
    aspect's exact point and pick the closest. If that distance is
    within `orb_deg`, strength = 1 - distance / orb_deg; otherwise 0.

    Returns 0.0 for unknown planets.
    """
    offsets = _ASPECT_OFFSETS.get(aspector)
    if not offsets:
        return 0.0
    # Each "nth from" offset corresponds to (offset * 30°) of
    # longitudinal arc forward of the aspector. 7th aspect = 180°,
    # 4th = 90°, 8th = 210°, 5th = 120°, 9th = 240°, 3rd = 60°,
    # 10th = 270°. The exact point is `aspector_lon + offset * 30°`
    # mod 360.
    best = 360.0
    for off in offsets:
        exact = (aspector_lon + off * 30.0) % 360.0
        dist = _angular_diff(exact, target_lon)
        if dist < best:
            best = dist
    if best >= orb_deg:
        return 0.0
    return 1.0 - (best / orb_deg)


def aspect_strengths_receiving(
    target_lon: float,
    aspector_lons: Dict[str, float],
    skip_target: Optional[str] = None,
    orb_deg: float = _ASPECT_ORB_DEG,
) -> Dict[str, float]:
    """Per-aspector longitudinal aspect strengths onto `target_lon`.

    Returns `{aspector_name: strength}` for every planet whose strength
    is > 0 (planets outside the orb are omitted to keep the dict
    compact). `skip_target` excludes the target itself if it appears
    in `aspector_lons`.
    """
    out: Dict[str, float] = {}
    for name, lon in aspector_lons.items():
        if name == skip_target:
            continue
        s = aspect_strength_between(name, lon, target_lon, orb_deg)
        if s > 0.0:
            out[name] = s
    return out


def aspected_signs(planet: str, sign_num: int) -> List[int]:
    """Return the 1-indexed sign numbers that `planet` aspects from
    `sign_num` (1=Aries .. 12=Pisces).
    """
    if not (1 <= sign_num <= 12):
        raise ValueError(f"sign_num must be 1..12, got {sign_num}")
    offsets = _ASPECT_OFFSETS.get(planet)
    if offsets is None:
        return []
    return [((sign_num - 1 + off) % 12) + 1 for off in offsets]


def aspects_receiving(
    target_planet: str,
    target_sign_num: int,
    all_planet_signs: Dict[str, int],
) -> List[str]:
    """Return the list of *other* planets whose aspect reaches
    target_planet's sign.

    Target itself is excluded from its own aspects.
    """
    receivers: List[str] = []
    for other, other_sign in all_planet_signs.items():
        if other == target_planet:
            continue
        if target_sign_num in aspected_signs(other, other_sign):
            receivers.append(other)
    return receivers
