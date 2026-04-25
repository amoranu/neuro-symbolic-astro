"""CF rules for father's longevity, v32 — REJECTED under HO+Train
methodology (2026-04-26).

Status: REJECTED. Train mean |days_off| 401d → 425d (+5.7%, just
over the 5% tolerance). HO mean improved -4d but no hit changes
on either cohort. The rule's stand-alone PD-level firing without
the AD-level gate is too broad; it perturbs predictions on training
charts in ways that cancel out for hits but worsen mean. Preserved
for documentation.

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R4. malefic_PD_with_sphuta_aspect_on_natal_sun
      Same pattern as v31's R3 but at the PD level instead of AD.
      A malefic PD-lord casting an exact-orb sphuta aspect on natal
      Sun pins the karaka-affliction to the deeper sub-period
      window (PDs are 1/9th of an AD).

      Distinct from v31's R3 PD-modifier: that modifier requires the
      AD-lord to ALSO be a malefic with aspect on Sun. This stand-
      alone rule fires whenever PD-lord satisfies the condition,
      regardless of AD-lord. Lets the rule pick up cases where the
      AD-lord is benefic (so R3 doesn't fire) but the PD-lord still
      attacks the karaka via tight aspect.

      Fires when:
        * PD lord is a natural malefic (Sat/Mar/Rah/Ket/Sun)
        * PD lord's aspect_strengths_on_natal["Sun"] >= 0.5

      base_cf = -0.20 (slightly weaker than R3's -0.25 since PD-only
                       activation is generally less forceful than
                       AD-level activation)
      primary_planet = <pd_lord>

      Modifiers:
        - SD lord ALSO casts sphuta-aspect on natal Sun >= 0.5
          (PD+SD compound exact-orb aspect): -0.10
        - PD-lord aspect strength on natal Sun >= 0.7 (very tight,
          ~3° of exact): -0.10
        - Jupiter aspects natal Sun strength >= 0.5: +0.15
"""
from __future__ import annotations

from typing import List

from astroql.engine.cf_predict import CFRuleSpec
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v31 import RULES_V31


_MALEFIC_DASHA_LORDS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}


def _pd_lord_sphuta_aspect_on_sun(ep: EpochState) -> bool:
    pd = ep.dashas.pratyantar
    if not pd or pd not in _MALEFIC_DASHA_LORDS:
        return False
    p = ep.planets.get(pd)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.5


def _sd_lord_sphuta_aspect_on_sun(ep: EpochState) -> bool:
    sd = ep.dashas.sookshma
    if not sd:
        return False
    p = ep.planets.get(sd)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.5


def _pd_lord_tight_sphuta_aspect_on_sun(ep: EpochState) -> bool:
    pd = ep.dashas.pratyantar
    if not pd:
        return False
    p = ep.planets.get(pd)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.7


_BPHS_SPHUTA_PD_LEVEL_CITATION = Citation(
    source_id="BPHS Aspects (Drishti) chapter + Pratyantar-dasha "
              "doctrine",
    text_chunk="When a malefic pratyantar-dasha lord forms an exact-"
               "orb special aspect on the bhava-karaka, the deeper "
               "sub-period activation pins the karaka-affliction to "
               "a window of weeks rather than months. This refines "
               "the broader AD-level sphuta-aspect rule to the "
               "deeper dasha level.",
)


_R_MALEFIC_PD_SPHUTA_ASPECT_SUN = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.malefic_pd_sphuta_aspect_on_natal_sun.cf32",
        school=School.PARASHARI,
        source="PD-level sphuta-drishti companion to v31's AD-level "
               "rule. Fires when the pratyantar-dasha lord is "
               "malefic and casts a tight-orb (>=0.5) aspect on "
               "natal Sun, pinning the karaka-affliction to the PD "
               "window. Stand-alone — fires regardless of AD-lord "
               "identity, complementing R3 which gates on AD.",
        is_veto=False,
        base_cf=-0.20,
        primary_planet="<pd_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_SPHUTA_PD_LEVEL_CITATION],
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
    fires_when=_pd_lord_sphuta_aspect_on_sun,
)


_R_MALEFIC_PD_SPHUTA_ASPECT_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="SD lord ALSO casts sphuta-aspect on natal "
                           "Sun >= 0.5: PD+SD compound exact-orb "
                           "aspect on karaka."),
)
_R_MALEFIC_PD_SPHUTA_ASPECT_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="PD-lord aspect strength on natal Sun "
                           ">= 0.7 (very tight ~3° orb)."),
)
_R_MALEFIC_PD_SPHUTA_ASPECT_SUN.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _sd_lord_sphuta_aspect_on_sun,
    _pd_lord_tight_sphuta_aspect_on_sun,
]


# ── v32 rule list (additive over v31) ─────────────────────────────

RULES_V32: List[CFRuleSpec] = list(RULES_V31) + [
    _R_MALEFIC_PD_SPHUTA_ASPECT_SUN,
]
