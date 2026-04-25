"""CF rules for father's longevity, v31 — third draft under HO+Train
methodology (2026-04-26).

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R3. malefic_AD_with_sphuta_aspect_on_natal_sun
      Combines two v15 angles into one tight time-gate using engine
      v2's longitudinal Sphuta Drishti:

      v15 has `mars_afflicts_natal_sun.cf12` and `saturn_aspects_
      natal_sun.cf12` — both binary (sign-based) aspect rules. They
      fire whenever Mars/Saturn occupies a 4/7/8/3/10-from-Sun sign
      in transit, without orb constraint, so they fire for ~30-day
      stretches per year per planet.

      This rule narrows to the moments when the AD-lord (any malefic)
      forms an EXACT-orb sphuta aspect on natal Sun (strength >= 0.5,
      i.e. within ~5° of an aspect's exact longitude). The AD-lord
      restriction also ties the affliction to the active period:
      it's the dasha-lord ATTACKING the karaka via tight aspect.

      For Sat/Mars/Rah/Ket the aspect set is well-defined (special
      aspects). Sun-AD has only the 7th aspect; this rule still
      fires when Sun's transit is opposing natal Sun within orb.

      Fires when:
        * AD lord is a natural malefic (Sat/Mar/Rah/Ket/Sun)
        * AD lord's `aspect_strengths_on_natal["Sun"]` >= 0.5

      base_cf = -0.25 (slightly stronger than v29/v30 since the gate
                        is tighter — fires only at exact-orb aspect
                        moments, not throughout the AD)
      primary_planet = <ad_lord>

      Modifiers:
        - PD lord ALSO has sphuta-aspect on natal Sun >= 0.5 (compound
          aspect activation across two dasha levels): -0.10
        - AD-lord aspect strength on natal Sun >= 0.7 (very tight
          orb, ~3° of exact): additional -0.10
        - Jupiter aspects natal Sun strength >= 0.5: +0.15
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v15 import RULES_V15


_MALEFIC_DASHA_LORDS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}


def _ad_lord_sphuta_aspect_on_sun(ep: EpochState) -> bool:
    """v31 R3 fires_when:
        * AD lord is a natural malefic
        * AD lord's sphuta-aspect strength on natal Sun >= 0.5
    """
    ad = ep.dashas.antar
    if not ad or ad not in _MALEFIC_DASHA_LORDS:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.5


def _pd_lord_sphuta_aspect_on_sun(ep: EpochState) -> bool:
    pd = ep.dashas.pratyantar
    if not pd:
        return False
    p = ep.planets.get(pd)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.5


def _ad_lord_tight_sphuta_aspect_on_sun(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    if not ad:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.7


_BPHS_SPHUTA_DRISHTI_KARAKA_CITATION = Citation(
    source_id="BPHS Aspects (Drishti) chapter + Phaladeepika gocharā",
    text_chunk="A drishti's effect intensifies as the longitudinal "
               "distance from the exact aspect-point shrinks (sphuta "
               "drishti). When a malefic dasha-lord is within tight "
               "orb of casting an exact-orb special aspect on a "
               "bhava-karaka, that period's affliction is acute. "
               "This refines the binary classical drishti rules to "
               "the precise time-window of exact-orb formation.",
)


_R_MALEFIC_AD_SPHUTA_ASPECT_SUN = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.malefic_ad_sphuta_aspect_on_natal_sun.cf31",
        school=School.PARASHARI,
        source="Sphuta-drishti refinement of v15's binary aspect "
               "rules: any malefic AD-lord casting a tight-orb (>=0.5 "
               "= within ~5°) aspect on natal Sun amplifies the "
               "father-karaka affliction at that specific transit "
               "moment, vs the broad sign-based v15 rules that fire "
               "for the whole aspect-formation arc.",
        is_veto=False,
        base_cf=-0.25,
        primary_planet="<ad_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_SPHUTA_DRISHTI_KARAKA_CITATION],
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
    fires_when=_ad_lord_sphuta_aspect_on_sun,
)


_R_MALEFIC_AD_SPHUTA_ASPECT_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="PD lord ALSO casts sphuta aspect on natal "
                           "Sun (strength >= 0.5): two-level compound "
                           "exact-orb karaka affliction."),
)
_R_MALEFIC_AD_SPHUTA_ASPECT_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="AD-lord aspect strength on natal Sun "
                           ">= 0.7 (within ~3° of exact): very tight "
                           "orb intensification."),
)
_R_MALEFIC_AD_SPHUTA_ASPECT_SUN.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _pd_lord_sphuta_aspect_on_sun,
    _ad_lord_tight_sphuta_aspect_on_sun,
]


# ── v31 rule list (additive over v15 baseline) ────────────────────

RULES_V31: List[CFRuleSpec] = list(RULES_V15) + [
    _R_MALEFIC_AD_SPHUTA_ASPECT_SUN,
]
