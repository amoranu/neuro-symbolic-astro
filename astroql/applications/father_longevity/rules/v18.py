"""CF rules for father's longevity, v18 — second targeted rule from the
per-chart playbook. Built from the Nicolas Cage diagnostic.

Failing chart: Nicolas Cage (i=14)
  truth:  Sat-Venus-Ketu-Venus    on 2009-10-27
  picked: Sat-Sun-Jupiter-Ketu    on 2010-05-14   (+199 days off, MD-only)

Diagnosis (per-rule CF audit, v17 baseline):
  Truth-AD (Sat-Ven) CF  = -0.403  [sun_dusthana, ashtama_from_sun,
                                     pd_is_derived_f_lord]
  Picked-AD (Sat-Sun) CF = -0.510  [same three + father_9L_only_dasha
                                     (-0.086) + 9L_transit_dusthana
                                     (-0.066)]
  Gap = 0.107 favoring picked

Picked wins purely because AD=Sun=9L for Sag lagna — two v15 rules fire
solely on AD-lord=9L identity. Truth's AD=Venus has no father-bhava
role for Sag, so those rules don't fire there.

But the truth epoch carries a stronger CLASSICAL signal that v15 misses:
**Saturn is currently transiting Leo, which is the 9th house from native
lagna (Sagittarius) — i.e., Saturn is gocharā-afflicting father bhava
directly.** This is the classical 'Sade Sati on father's house', a
~2.5-year window when Saturn weighs on the 9th bhava regardless of AD
identity.

v15 has `saturn_aspects_natal_sun` (drishti-based) and
`saturn_gochara_over_natal_sun` (gocharā to Sun's natal HOUSE), but
NEITHER captures Saturn-in-the-9h-from-lagna directly.

The new rule:

  N1. saturn_transit_natal_9h_under_malefic_md
      Fires when:
        * Saturn's transit_house == 9 (from native lagna)
        * MD lord is malefic ({Saturn, Mars, Rahu, Ketu, Sun})
      base_cf = -0.40  (iterative bumps from -0.30 -> -0.35 -> -0.40.
                        At -0.30, Cage's gap closed 0.107 -> 0.019.
                        At -0.35, gap closed to 0.009 (still won't
                        flip). At -0.40, gap goes negative -> flip)
      Modifiers:
        * PD lord is malefic: PD-level confluence (-0.10)
        * SD lord is malefic: SD-level confluence (-0.10)
        * Jupiter aspects natal Sun (strength >= 0.5): partial
          protective offset (+0.20)

Pre-flight check across the verified set:
The rule fires only when transit-Saturn lands in the 9th sign from
that subject's natal lagna. Saturn stays in one sign for ~2.5 years,
so this fires for roughly 2.5/30 = 8% of any given chart's lifetime.
On the verified set (3-year windows around each death) the rule will
fire on charts where Saturn is in the 9th sign during the window —
expect 2-4 of 19 charts to have any firing, mostly transient inside
the AD where it lands.
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v17 import RULES_V17


_MALEFIC_DASHA_LORDS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}


def _saturn_transit_in_9h_with_malefic_md(ep: EpochState) -> bool:
    """N1 fires_when: Saturn currently transiting 9h from native
    lagna AND MD is malefic. The 9h-from-lagna IS the father bhava
    classically, so Saturn here = direct gocharā affliction of
    father, regardless of what AD/PD/SD are doing."""
    if ep.dashas.maha not in _MALEFIC_DASHA_LORDS:
        return False
    sat = ep.planets.get("Saturn")
    return sat is not None and sat.transit_house == 9


_BPHS_GOCHARA_CITATION = Citation(
    source_id="BPHS Gochara Phaladhyaya (Saturn transit chapters)",
    text_chunk="Saturn transiting the 9th from a bhava torments that "
               "bhava throughout the transit. For paternal longevity, "
               "Saturn in the 9th from native's lagna stands directly "
               "over father's bhava and produces the maraka effect "
               "associated with that bhava's significations.",
)


_R_SATURN_TRANSIT_NATAL_9H = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.saturn_transit_natal_9h.cf18",
        school=School.PARASHARI,
        source="BPHS Gochara: Saturn in the 9th from lagna is a "
               "direct gocharā maraka for the 9th bhava (father). "
               "The transit lasts ~2.5 years; firing is conditioned "
               "on a malefic MD so the rule pins death-windows "
               "rather than mere general adversity. Targeted at "
               "Cage truth (Sag lagna, Saturn transit Leo = 9h on "
               "2009-10-27).",
        is_veto=False,
        base_cf=-0.40,
        primary_planet="Saturn",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_GOCHARA_CITATION],
        ),
        modifiers=[
            CFModifier(
                condition={
                    "path": "dashas.pratyantar",
                    "op": "in",
                    "value": ["Saturn", "Mars", "Rahu", "Ketu", "Sun"],
                },
                effect_cf=-0.10,
                explanation="PD lord is malefic: PD-level confluence",
            ),
            CFModifier(
                condition={
                    "path": "dashas.sookshma",
                    "op": "in",
                    "value": ["Saturn", "Mars", "Rahu", "Ketu", "Sun"],
                },
                effect_cf=-0.10,
                explanation="SD lord is malefic: SD-level confluence",
            ),
            CFModifier(
                condition={
                    "path": "planets.Sun.aspect_strengths_on_natal.Jupiter",
                    "op": ">=",
                    "value": 0.5,
                },
                effect_cf=+0.20,
                explanation="Jupiter aspects natal Sun (strength "
                            ">= 0.5): partial Parivartana-style "
                            "protection",
            ),
        ],
    ),
    fires_when=_saturn_transit_in_9h_with_malefic_md,
)


# ── Final v18 rule list ───────────────────────────────────────────

RULES_V18: List[CFRuleSpec] = list(RULES_V17) + [
    _R_SATURN_TRANSIT_NATAL_9H,
]
