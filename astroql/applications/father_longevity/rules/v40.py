"""CF rules for father's longevity, v40 — REJECTED under HO+Train
methodology (2026-04-26).

Status: REJECTED. Fires zero times across the 39-subject dataset
(no chart's 3-year window has 2+ malefics simultaneously in
natal 9h). Multi-malefic 9h pile-up is a real classical
configuration but too rare to manifest in our window sizes.

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R13. multi_malefic_in_natal_9h_transit
       Distinct family from v31/v37/v38/v39 (sphuta-on-Sun rules):
       this targets the natal 9h (father bhava) directly via
       multi-malefic transit occupation.

       Classical: 9th house = father bhava. When two or more
       malefics (Sat/Mar/Rah/Ket; Sun excluded as ambiguous) are
       simultaneously transiting the native's 9th house from
       lagna, the bhava is multiply afflicted by transit
       occupation. Combined with malefic or bhava-related MD,
       this is a window of bhava-stress.

       v15 has `ninth_lord_transit_dusthana` (9L going to dusthana)
       and `ninth_lord_transit_afflicted` (9L being aspected). This
       rule is distinct: it concerns malefics OCCUPYING the natal
       9h directly.

       Fires when:
         * Two or more non-luminary malefics (Sat/Mar/Rah/Ket) have
           transit_house == 9 simultaneously
         * MD lord is malefic OR plays a father-bhava role

       base_cf = -0.20
       primary_planet = "Saturn"  (consistent maraka magnitude)

       Modifiers:
         - One of the occupants is also retrograde: -0.08
         - Three or more malefics simultaneously in 9h
           (extremely rare): -0.10
         - Jupiter aspects natal Sun strength >= 0.5: +0.10
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v39 import RULES_V39


_NON_LUMINARY_MALEFICS = ("Saturn", "Mars", "Rahu", "Ketu")
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


def _count_malefics_in_natal_9h(ep: EpochState) -> int:
    n = 0
    for malef in _NON_LUMINARY_MALEFICS:
        p = ep.planets.get(malef)
        if p is None:
            continue
        if p.transit_house == 9:
            n += 1
    return n


def _multi_malefic_in_natal_9h(ep: EpochState) -> bool:
    """v40 R13 fires_when:
        * Two or more non-luminary malefics in natal 9h transit
        * MD lord is malefic OR plays father-bhava role
    """
    if _count_malefics_in_natal_9h(ep) < 2:
        return False
    return _md_father_bhava_role_or_malefic(ep)


def _any_9h_malefic_retrograde(ep: EpochState) -> bool:
    for malef in _NON_LUMINARY_MALEFICS:
        p = ep.planets.get(malef)
        if p is None:
            continue
        if p.transit_house == 9 and p.is_retrograde:
            return True
    return False


def _three_or_more_in_9h(ep: EpochState) -> bool:
    return _count_malefics_in_natal_9h(ep) >= 3


_BPHS_MULTI_MALEFIC_BHAVA_CITATION = Citation(
    source_id="BPHS Bhava-pidā doctrine + Phaladeepika gochara",
    text_chunk="When two or more malefics simultaneously transit a "
               "bhava, the bhava's signification is multiply "
               "afflicted; classical 'paapa-kartari' or related "
               "multi-malefic configurations specifically target "
               "the bhava under occupation. For paternal longevity, "
               "the 9th from native lagna (father bhava) is the "
               "subject — multi-malefic transit there compounds "
               "father's affliction.",
)


_R_MULTI_MALEFIC_NATAL_9H = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.multi_malefic_in_natal_9h_transit.cf40",
        school=School.PARASHARI,
        source="Multi-malefic 9h transit gated by MD context. "
               "Distinct from v15's 9L-focused rules and v31-v39's "
               "Sun-focused rules — addresses the bhava itself "
               "under transit-occupation stress.",
        is_veto=False,
        base_cf=-0.20,
        primary_planet="Saturn",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_MULTI_MALEFIC_BHAVA_CITATION],
        ),
        modifiers=[
            CFModifier(
                condition={
                    "path": "planets.Sun.aspect_strengths_on_natal.Jupiter",
                    "op": ">=",
                    "value": 0.5,
                },
                effect_cf=+0.10,
                explanation="Jupiter aspects natal Sun (strength "
                            ">= 0.5): partial protective offset",
            ),
        ],
    ),
    fires_when=_multi_malefic_in_natal_9h,
)


_R_MULTI_MALEFIC_NATAL_9H.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.08,
               explanation="At least one of the 9h-transit malefics "
                           "is retrograde at this epoch."),
)
_R_MULTI_MALEFIC_NATAL_9H.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="Three or more malefics simultaneously in "
                           "natal 9h transit — extremely rare 9h "
                           "occupation pile-up."),
)
_R_MULTI_MALEFIC_NATAL_9H.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _any_9h_malefic_retrograde,
    _three_or_more_in_9h,
]


# ── v40 rule list (additive over v39 canonical) ───────────────────

RULES_V40: List[CFRuleSpec] = list(RULES_V39) + [
    _R_MULTI_MALEFIC_NATAL_9H,
]
