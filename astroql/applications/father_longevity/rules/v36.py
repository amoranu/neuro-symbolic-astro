"""CF rules for father's longevity, v36 — REJECTED under HO+Train
methodology (2026-04-26).

Status: REJECTED. HO PD 4→3 (-1), HO mean +31d. The 9L-as-aspector
variant fires on at least one held-out chart at a non-truth epoch
that also pulls a PD-match away. Preserved for documentation.

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R9. 9L_transit_aspect_on_natal_sun
      Companion to v31's R3, but with the aspector being 9L
      (father-bhava ruler) rather than a malefic AD-lord. Targets
      the same victim (natal Sun) but the aspector is the chart's
      own father-bhava ruler in transit.

      Classical interpretation: when the 9L (father bhava ruler)
      aspects natal Sun (father karaka) in transit at exact orb,
      the bhava-ruler signals a "live" interaction with the karaka.
      In the context of malefic dasha or maraka period, this
      interaction marks a stress-event for father.

      Note 9L can be Sun itself (Sag lagna). For those charts, the
      rule is trivially satisfied whenever Sun aspects itself —
      which never happens in practice (Sun's only 7th aspect
      doesn't fall on its own natal position unless natal Sun is
      exactly opposite transit Sun's position, possible but
      narrow). The rule excludes 9L=Sun case to avoid degeneracy.

      Fires when:
        * 9L (sign-lord of 9th from native lagna) is not Sun
        * 9L's aspect_strengths_on_natal["Sun"] >= 0.5
        * MD lord is malefic OR plays a father-bhava role

      base_cf = -0.18 (modest — 9L-aspect-on-Sun is a slower-
                       moving signal than dasha-lord-aspect)
      primary_planet = "Sun"  (universal karaka, gives consistent
                               magnitude regardless of which planet
                               IS 9L on a given chart)

      Modifiers:
        - 9L additionally retrograde at this transit (afflicted
          bhava-ruler aspecting karaka): -0.10
        - 9L is also in dusthana (6/8/12) from native lagna in
          transit (twice-afflicted: spatial dusthana + sphuta
          aspect on Sun): -0.05
        - Jupiter aspects natal Sun strength >= 0.5: +0.15
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v31 import RULES_V31


_MALEFIC_DASHA_LORDS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}

_SIGN_ORDER = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)


def _nth_sign_from(sign: str, n: int) -> Optional[str]:
    try:
        idx = _SIGN_ORDER.index(sign)
    except ValueError:
        return None
    return _SIGN_ORDER[(idx + n - 1) % 12]


def _safe_sign_lord(sign: Optional[str]) -> Optional[str]:
    if not sign:
        return None
    try:
        return sign_lord(sign)
    except ValueError:
        return None


def _ninth_lord(ep: EpochState) -> Optional[str]:
    if not ep.natal_lagna_sign:
        return None
    return _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9))


def _f_loss_lord_set(ep: EpochState) -> set:
    if not ep.natal_lagna_sign:
        return set()
    out: set = set()
    for n in (10, 3, 4, 8):
        lord = _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, n))
        if lord:
            out.add(lord)
    return out


def _md_father_bhava_role_or_malefic(ep: EpochState) -> bool:
    md = ep.dashas.maha
    if not md or not ep.natal_lagna_sign:
        return False
    if md in _MALEFIC_DASHA_LORDS:
        return True
    if md == _safe_sign_lord(ep.natal_lagna_sign):
        return True
    if md == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9)):
        return True
    if md == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 8)):
        return True
    return md in _f_loss_lord_set(ep)


def _9L_aspects_natal_sun(ep: EpochState) -> bool:
    """v36 R9 fires_when:
        * 9L is not Sun (avoid degenerate 9L=Sun case)
        * 9L's sphuta-aspect strength on natal Sun >= 0.5
        * MD lord is malefic OR plays father-bhava role
    """
    nl = _ninth_lord(ep)
    if nl is None or nl == "Sun":
        return False
    p = ep.planets.get(nl)
    if p is None:
        return False
    if p.aspect_strengths_on_natal.get("Sun", 0.0) < 0.5:
        return False
    return _md_father_bhava_role_or_malefic(ep)


def _9L_retrograde(ep: EpochState) -> bool:
    nl = _ninth_lord(ep)
    if nl is None:
        return False
    p = ep.planets.get(nl)
    return p is not None and p.is_retrograde


def _9L_in_dusthana_transit(ep: EpochState) -> bool:
    nl = _ninth_lord(ep)
    if nl is None:
        return False
    p = ep.planets.get(nl)
    return p is not None and p.transit_house in (6, 8, 12)


_BPHS_9L_KARAKA_INTERACTION_CITATION = Citation(
    source_id="BPHS Bhava-prakaranam (9th house) + sphuta drishti",
    text_chunk="When the 9th lord (father bhava ruler) forms a "
               "tight-orb special aspect on the natal position of the "
               "father karaka (Sun), the bhava-ruler is signaling an "
               "active interaction with the karaka. In the context "
               "of a malefic or bhava-related maha-dasha, this "
               "interaction is classically stressful — bhava-ruler "
               "and karaka both implicated in the same period.",
)


_R_9L_TRANSIT_ASPECT_ON_SUN = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ninth_lord_transit_sphuta_aspect_on_sun.cf36",
        school=School.PARASHARI,
        source="Sphuta refinement: 9L (father bhava ruler) casting "
               "tight-orb aspect on natal Sun (father karaka) under "
               "a malefic or bhava-related MD. Distinct from v31's "
               "R3 (where the aspector is a malefic dasha-lord); "
               "here the aspector is specifically the father-bhava "
               "ruler, capturing bhava-self-affliction at the karaka.",
        is_veto=False,
        base_cf=-0.18,
        primary_planet="Sun",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_9L_KARAKA_INTERACTION_CITATION],
        ),
        modifiers=[
            CFModifier(
                condition={
                    "path": "planets.Sun.aspect_strengths_on_natal.Jupiter",
                    "op": ">=",
                    "value": 0.5,
                },
                effect_cf=+0.15,
                explanation="Jupiter aspects natal Sun (strength "
                            ">= 0.5): partial protective offset",
            ),
        ],
    ),
    fires_when=_9L_aspects_natal_sun,
)


_R_9L_TRANSIT_ASPECT_ON_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="9L additionally retrograde at this "
                           "transit: afflicted bhava-ruler in tight "
                           "aspect formation on karaka."),
)
_R_9L_TRANSIT_ASPECT_ON_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.05,
               explanation="9L in dusthana (6/8/12) from native "
                           "lagna in transit: spatial-bhava "
                           "weakness compounds the aspect."),
)
_R_9L_TRANSIT_ASPECT_ON_SUN.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _9L_retrograde,
    _9L_in_dusthana_transit,
]


# ── v36 rule list (additive over v31 canonical) ───────────────────

RULES_V36: List[CFRuleSpec] = list(RULES_V31) + [
    _R_9L_TRANSIT_ASPECT_ON_SUN,
]
