"""CF rules for father's longevity, v35 — REJECTED under HO+Train
methodology (2026-04-26).

Status: REJECTED. Surprising finding: HO (AD+PD+SD) decreased 15→12
and HO mean +41d. The graha-yuddha-lost AD rule (also present in
v16) was previously assumed to be benign within v16's HO regression;
this isolated test shows it IS the source of v16's HO regression.
The rule fires on graha-yuddha events, which on at least one held-
out chart coincide with non-truth epochs and pull predictions away.

Lesson: chart-static or transient-state rules with no tight gate to
the bhava under question can fire spuriously. Preserved for
documentation; v16 HO regression is now traced to this rule.

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R8. ad_lord_lost_graha_yuddha
      Identical in structure to v16's R3 (lifted out of v16 because
      v16 also bundled vargottama and Mahamrityunjaya rules that
      caused HO regression). Tested standalone here over v31.

      BPHS Graha Yuddha doctrine: when two true planets are within
      1° longitude in the same sign, they are in planetary war; the
      slower of the two is classically "destroyed" for the period
      (Phaladeepika Ch. 2). An AD-lord in graha-yuddha-lost state
      cannot deliver constructive dasha-period results, leaving any
      maraka activations on the chart unmitigated for father.

      Fires when:
        * AD lord is_in_graha_yuddha AND graha_yuddha_lost
        (Sun/Moon/Rahu/Ketu cannot satisfy this — yuddha is between
        true non-luminary planets only — so no extra gate needed.)

      base_cf = -0.22
      primary_planet = "Sun"  (universal father karaka — gives the
                               rule consistent magnitude regardless
                               of which planet is in yuddha)

      Modifiers:
        - MD lord is a natural malefic (maraka context): -0.08
        - Jupiter aspects natal Sun strength >= 0.5: +0.15
"""
from __future__ import annotations

from typing import List

from astroql.engine.cf_predict import CFRuleSpec
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v31 import RULES_V31


def _ad_lord_lost_yuddha(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    p = ep.planets.get(ad) if ad else None
    if p is None:
        return False
    return p.is_in_graha_yuddha and p.graha_yuddha_lost


_BPHS_GRAHA_YUDDHA_CITATION = Citation(
    source_id="BPHS Graha Yuddha-prakaranam + Phaladeepika Ch. 2",
    text_chunk="When two true planets are within 1° of longitude "
               "in the same sign, they are in planetary war (graha "
               "yuddha). The slower of the two is classically "
               "destroyed for the duration; its dasha results cannot "
               "manifest constructively. An AD-lord in this state "
               "cannot defend the bhava-significations it rules.",
)


_R_AD_LOST_GRAHA_YUDDHA = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ad_lord_lost_graha_yuddha.cf35",
        school=School.PARASHARI,
        source="BPHS Graha Yuddha: AD-lord-as-loser cannot deliver "
               "dasha-period results constructively, leaving any "
               "maraka activations unmitigated. Lifted standalone "
               "from v16's bundled engine-v2 ruleset (which "
               "regressed HO due to vargottama and Mahamrityunjaya "
               "additions, not this rule).",
        is_veto=False,
        base_cf=-0.22,
        primary_planet="Sun",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.40,
            citations=[_BPHS_GRAHA_YUDDHA_CITATION],
        ),
        modifiers=[
            CFModifier(
                condition={
                    "path": "dashas.maha",
                    "op": "in",
                    "value": ["Saturn", "Mars", "Rahu", "Ketu", "Sun"],
                },
                effect_cf=-0.08,
                explanation="MD lord is a natural malefic: maraka "
                            "context for the burnt AD-lord",
            ),
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
    fires_when=_ad_lord_lost_yuddha,
)


# ── v35 rule list (additive over v31 canonical) ───────────────────

RULES_V35: List[CFRuleSpec] = list(RULES_V31) + [
    _R_AD_LOST_GRAHA_YUDDHA,
]
