"""CF rules for father's longevity, v38 — tenth draft under HO+Train
methodology (2026-04-26).

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R11. malefic_PD_with_TIGHT_sphuta_aspect_on_natal_sun
       v32 (PD-level at 0.5 orb) was REJECTED for noise. Tightening
       to >= 0.7 (~3° orb) might give a higher signal-to-noise ratio
       at PD level, parallel to v37's relationship to v31.

       PD slots are 1/9th of an AD, so a tight-orb sphuta event at
       PD level pins to a window of ~weeks instead of months.

       Fires when:
         * PD lord is a natural malefic
         * PD lord's aspect_strengths_on_natal["Sun"] >= 0.7

       base_cf = -0.18
       primary_planet = <pd_lord>

       Modifiers:
         - PD-lord additionally retrograde: -0.08
         - Jupiter aspects natal Sun strength >= 0.5: +0.10
"""
from __future__ import annotations

from typing import List

from astroql.engine.cf_predict import CFRuleSpec
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v37 import RULES_V37


_MALEFIC_DASHA_LORDS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}


def _pd_lord_tight_sphuta_aspect_on_sun(ep: EpochState) -> bool:
    pd = ep.dashas.pratyantar
    if not pd or pd not in _MALEFIC_DASHA_LORDS:
        return False
    p = ep.planets.get(pd)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.7


def _pd_lord_retrograde(ep: EpochState) -> bool:
    pd = ep.dashas.pratyantar
    if not pd:
        return False
    p = ep.planets.get(pd)
    return p is not None and p.is_retrograde


_BPHS_TIGHT_PD_SPHUTA_CITATION = Citation(
    source_id="BPHS Aspects + pratyantar-dasha doctrine",
    text_chunk="A pratyantar-dasha lord forming a near-exact aspect "
               "on a bhava-karaka pins the affliction to a narrow "
               "sub-period window. The inner-orb refinement (>=0.7 "
               "= ~3°) selects the precise transit moment within "
               "the PD when the aspect is fully formed.",
)


_R_MALEFIC_PD_TIGHT_SPHUTA_SUN = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.malefic_pd_tight_sphuta_aspect_on_natal_sun.cf38",
        school=School.PARASHARI,
        source="Inner-orb (>=0.7) PD-level companion to v31/v37's "
               "AD-level sphuta rules. Fires only when malefic PD "
               "lord casts a near-exact aspect on natal Sun within "
               "the brief pratyantar window.",
        is_veto=False,
        base_cf=-0.18,
        primary_planet="<pd_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_TIGHT_PD_SPHUTA_CITATION],
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
    fires_when=_pd_lord_tight_sphuta_aspect_on_sun,
)


_R_MALEFIC_PD_TIGHT_SPHUTA_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.08,
               explanation="PD-lord additionally retrograde at this "
                           "tight-orb aspect on natal Sun."),
)
_R_MALEFIC_PD_TIGHT_SPHUTA_SUN.modifier_predicates = [
    lambda ep: False,
    _pd_lord_retrograde,
]


# ── v38 rule list (additive over v37 canonical) ───────────────────

RULES_V38: List[CFRuleSpec] = list(RULES_V37) + [
    _R_MALEFIC_PD_TIGHT_SPHUTA_SUN,
]
