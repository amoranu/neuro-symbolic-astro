"""CF rules for father's longevity, v37 — ninth draft under HO+Train
methodology (2026-04-26).

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R10. malefic_AD_with_TIGHT_sphuta_aspect_on_natal_sun
       Refinement of v31's R3 with tighter orb requirement
       (>= 0.7 = within ~3° of exact, vs R3's >= 0.5 = ~5°).

       Rationale: if v31's R3 generalized cleanly with a 5° orb,
       a 3° orb might give a higher signal-to-noise ratio. Some
       transit aspects at 4-5° orb may be noise; the inner ~3°
       window is closer to the canonical "exact-orb" classical
       drishti.

       Companions v31's R3 — both fire if both gates are satisfied.
       Stack effect: a malefic AD-lord with very tight aspect on
       Sun gets v31's contribution PLUS v37's contribution = a
       compound -0.45 base before modifiers. The MYCIN combine
       caps it well within (-1, 1).

       Fires when:
         * AD lord is a natural malefic
         * AD lord's aspect_strengths_on_natal["Sun"] >= 0.7

       base_cf = -0.18 (incremental — sits on top of v31's -0.25
                        for the inner-orb subset; combined
                        effective magnitude ~ -0.40 at firing)
       primary_planet = <ad_lord>

       Modifiers:
         - AD-lord additionally retrograde (acutely afflicted
           tight-orb attacker): -0.08
         - Jupiter aspects natal Sun strength >= 0.5: +0.10
"""
from __future__ import annotations

from typing import List

from astroql.engine.cf_predict import CFRuleSpec
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v31 import RULES_V31


_MALEFIC_DASHA_LORDS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}


def _ad_lord_tight_sphuta_aspect_on_sun(ep: EpochState) -> bool:
    """v37 R10 fires_when:
        * AD lord is a natural malefic
        * AD lord's sphuta-aspect strength on natal Sun >= 0.7
    """
    ad = ep.dashas.antar
    if not ad or ad not in _MALEFIC_DASHA_LORDS:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.7


def _ad_lord_retrograde(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    if not ad:
        return False
    p = ep.planets.get(ad)
    return p is not None and p.is_retrograde


_BPHS_TIGHT_SPHUTA_CITATION = Citation(
    source_id="BPHS Aspects (Drishti) — exact-orb intensification",
    text_chunk="A drishti's effect peaks at the exact aspect-point. "
               "Within a 3° inner orb the malefic aspect's force is "
               "near-maximum classically; rules that gate on this "
               "tighter orb capture the precise transit moment of "
               "near-perfect aspect formation, refining the broader "
               "5° gate of v31's R3.",
)


_R_MALEFIC_AD_TIGHT_SPHUTA_ASPECT_SUN = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.malefic_ad_tight_sphuta_aspect_on_natal_sun.cf37",
        school=School.PARASHARI,
        source="Inner-orb (>=0.7 = ~3°) refinement of v31's R3. "
               "Stacks with R3 — when both fire, compound effective "
               "CF tightens at the precise aspect-formation moment.",
        is_veto=False,
        base_cf=-0.18,
        primary_planet="<ad_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_TIGHT_SPHUTA_CITATION],
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
    fires_when=_ad_lord_tight_sphuta_aspect_on_sun,
)


_R_MALEFIC_AD_TIGHT_SPHUTA_ASPECT_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.08,
               explanation="AD-lord additionally retrograde at this "
                           "tight-orb aspect: acutely afflicted "
                           "attacker on the karaka."),
)
_R_MALEFIC_AD_TIGHT_SPHUTA_ASPECT_SUN.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _ad_lord_retrograde,
]


# ── v37 rule list (additive over v31 canonical) ───────────────────

RULES_V37: List[CFRuleSpec] = list(RULES_V31) + [
    _R_MALEFIC_AD_TIGHT_SPHUTA_ASPECT_SUN,
]
