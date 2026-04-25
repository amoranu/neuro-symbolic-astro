"""Relationship → karaka planet resolver.

Classical Parashari karaka assignments per BPHS Ch. 32 + Phaladeepika
Ch. on Karaka theory. Most karakas are universal (gender-independent);
the spouse and a handful of intimate-relation karakas are gender-
asymmetric. This module is the single source of truth for the engine
when an LLM-emitted rule needs to resolve "what planet is the karaka
for relationship X under native gender Y?".

Universal karakas (gender-independent):
  Father              Sun
  Mother              Moon
  Self / Atma         Saturn  (also Atmakaraka per Jaimini)
  Children            Jupiter (with sub-distinctions per Saptamsha)
  Career              Saturn  (action / livelihood)
  Wealth / Finances   Jupiter
  Knowledge           Mercury
  Brothers            Mars
  Maternal uncle      Mercury

Gender-asymmetric karakas:
  Spouse:
    Male native      Venus     (significator of wife / female partner)
    Female native    Jupiter   (significator of husband / male partner)
  Sexual / sensual relations: Mars (male native) / Venus (female native)
    — secondary to spouse karaka, used by some traditions for non-
    marital relationship queries.

Reference:
  - BPHS Ch. 32 (Karaka-bheda)
  - Phaladeepika Ch. 12 (Karaka theory)
  - Sanjay Rath: "Karaka Vichara" lecture series (modern compilation)
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple


class KarakaResolutionError(ValueError):
    """Raised when a relationship + gender combination has no
    classical karaka assignment, or when gender is required but
    not supplied."""


# (relationship, gender) → karaka planet name. `None` for gender
# means the assignment is gender-independent. The resolver tries
# the gender-specific entry first, then falls back to the gender-
# independent one.
_KARAKA_TABLE: Dict[Tuple[str, Optional[str]], str] = {
    # Universal karakas (gender-independent) — listed under None;
    # the resolver falls back to None when M/F entry is absent.
    ("father",          None): "Sun",
    ("mother",          None): "Moon",
    ("self",            None): "Saturn",
    ("longevity",       None): "Saturn",
    ("children",        None): "Jupiter",
    ("career",          None): "Saturn",
    ("wealth",          None): "Jupiter",
    ("knowledge",       None): "Mercury",
    ("brothers",        None): "Mars",
    ("maternal_uncle",  None): "Mercury",
    # Gender-asymmetric karakas.
    ("spouse",          "M"): "Venus",
    ("spouse",          "F"): "Jupiter",
    # Sensual / non-marital relationships (secondary; some texts).
    ("relationship",    "M"): "Mars",
    ("relationship",    "F"): "Venus",
}

# Relationships whose karaka REQUIRES a known gender (no gender-
# independent fallback). Querying these without gender raises.
_GENDER_REQUIRED = frozenset(("spouse", "relationship"))


def target_karaka_planet(
    relationship: str,
    gender: Optional[str] = None,
) -> str:
    """Return the karaka planet for `(relationship, gender)`.

    Args:
        relationship: one of the keys in `_KARAKA_TABLE`. Case-
            insensitive at the boundary; canonicalized to lowercase.
        gender: "M" / "F" / None. None is allowed for universal
            karakas; queries for gender-asymmetric relationships
            (spouse, relationship) raise `KarakaResolutionError`
            when gender is None.

    Raises:
        KarakaResolutionError: unknown relationship, or gender-
            required relationship queried without gender.

    Examples:
        >>> target_karaka_planet("father")
        'Sun'
        >>> target_karaka_planet("spouse", "M")
        'Venus'
        >>> target_karaka_planet("spouse", "F")
        'Jupiter'
    """
    rel = (relationship or "").lower().strip()
    if not rel:
        raise KarakaResolutionError(
            "relationship must be a non-empty string"
        )
    if gender not in (None, "M", "F"):
        raise KarakaResolutionError(
            f"gender must be 'M', 'F', or None — got {gender!r}"
        )
    # Try gender-specific assignment first.
    if gender is not None:
        karaka = _KARAKA_TABLE.get((rel, gender))
        if karaka is not None:
            return karaka
    # Fall back to gender-independent.
    karaka = _KARAKA_TABLE.get((rel, None))
    if karaka is not None:
        return karaka
    # No assignment found.
    if rel in _GENDER_REQUIRED:
        raise KarakaResolutionError(
            f"relationship {rel!r} has gender-asymmetric karakas; "
            f"caller must supply gender='M' or 'F'"
        )
    known = sorted({r for (r, _) in _KARAKA_TABLE})
    raise KarakaResolutionError(
        f"unknown relationship {rel!r}. Known: {known}"
    )


def known_relationships() -> list:
    """Return the sorted list of relationships this resolver knows
    about. Useful for documentation and validation."""
    return sorted({r for (r, _) in _KARAKA_TABLE})
