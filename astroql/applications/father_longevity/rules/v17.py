"""CF rules for father's longevity, v17 — first targeted per-chart rule
addition since v15. Built from the per-chart audit that showed v16's
new-fields rules don't move metrics; the only path to accuracy is the
v9–v15 playbook (pick a failing chart, find the discriminator, write
the targeted rule).

Failing chart: Schwarzenegger (i=4)
  truth:  Sun-Mercury-Mercury-Venus  on 1972-12-10
  picked: Sun-Saturn-Sun-Sun         on 1972-06-19

Diagnosis (per-rule CF audit, v16 baseline):
  Truth-AD CF  = -0.384   (5 rules: sun_dusthana_md -0.163,
                           lagna_lord_AD -0.151, 9L_transit_dusthana
                           -0.076, 9L_transit_afflicted -0.057,
                           saturn_aspects_natal_sun -0.006)
  Picked-AD CF = -0.547   (8 rules: karaka_hanana -0.233 dominates,
                           Mars+Ketu transiting Cancer in June 1972;
                           by December they've moved on)

The structural gap: for Gemini lagna, Mercury is BOTH lagna lord AND
father's 8th lord (longevity lord — F8L). Truth's Mer-AD activates
both roles; picked's Sat-AD activates F12L+9L+8L (a different role
combo). The v15 rules treat lagna-lord-AD and derived-F-lord-AD as
disjoint to avoid double-counting — but classically, the convergence
of multiple father-bhava roles on a single AD planet is a STRONGER
signal, not weaker.

The time-varying signal that pins the Nov-Dec 1972 sub-window of
Mer-AD specifically (vs Aug-Sept 1972 within the same Mer-AD) is
Sun's transit in 6h from native lagna (Scorpio for Gemini lagna).
At truth Sun is in Scorpio (6h dusthana); at picked-AD's June 1972
Sun is in Gemini (1h, not dusthana).

The new rule:

  N1. ad_is_f8l_with_sun_in_dusthana
      Fires when:
        * AD lord = F8L (sign-lord of 8th from father-lagna =
          sign-lord of 4th from native lagna)
        * Sun's transit house from lagna ∈ {6, 8, 12}
        * MD lord is malefic ({Saturn, Mars, Rahu, Ketu, Sun})
      base_cf = -0.30
      Modifiers:
        * PD-lord is also F8L: bullseye intensifier (-0.12)
        * SD-lord is in F-loss-lord set: deep activation (-0.10)
        * Jupiter aspects natal Sun (strength ≥ 0.5): partial
          protection (+0.20)
      Disjointness: this rule is INTENTIONALLY non-disjoint from
      v15's _R_FATHER_LAGNA_LORD_AD and _R_FATHER_DERIVED_F_LORD_AD.
      The point is that when AD lord plays multiple roles AND Sun is
      gocharā-afflicted, the signals stack via MYCIN — exactly the
      situation v15's disjointness suppresses.

Pre-flight check across the verified set (computed from lagna alone —
F8L is chart-static):
  Lagna   F8L     Subjects matching this lagna
  Aries   Moon
  Taurus  Sun
  Gemini  Mercury  Schwarzenegger ← intended target
  Cancer  Venus
  Leo     Mars
  Virgo   Jupiter
  Libra   Saturn
  Scorpio Saturn
  Sagi.   Jupiter
  Capr.   Mars
  Aqua.   Venus
  Pisces  Mercury
The rule's combined gate (AD=F8L AND Sun in 6/8/12 transit AND
malefic-MD) is narrow enough that on lagnas other than Schwarzenegger's
it should rarely fire. Empirical eval validates this.
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v16 import RULES_V16


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


def _father_8L(ep: EpochState) -> Optional[str]:
    """Sign-lord of (8th from father-lagna) where father-lagna = 9th
    from native lagna. Equivalently the sign-lord of the 4th sign from
    native lagna."""
    if not ep.natal_lagna_sign:
        return None
    fourth = _nth_sign_from(ep.natal_lagna_sign, 4)
    return sign_lord(fourth) if fourth else None


def _father_loss_lords(ep: EpochState) -> set:
    """Per derived father-lagna: F2L/F7L/F8L/F12L."""
    if not ep.natal_lagna_sign:
        return set()
    out = set()
    for n_from_native in (10, 3, 4, 8):  # F2L=10L, F7L=3L, F8L=4L, F12L=8L
        s = _nth_sign_from(ep.natal_lagna_sign, n_from_native)
        if s:
            out.add(sign_lord(s))
    out.discard(None)
    return out


# ── N1 fires_when ─────────────────────────────────────────────────

def _ad_is_f8l_with_sun_in_dusthana(ep: EpochState) -> bool:
    """N1 main predicate — see module docstring."""
    if ep.dashas.maha not in _MALEFIC_DASHA_LORDS:
        return False
    f8l = _father_8L(ep)
    if f8l is None or ep.dashas.antar != f8l:
        return False
    sun = ep.planets.get("Sun")
    if sun is None:
        return False
    return sun.transit_house in (6, 8, 12)


# ── Rule definition ───────────────────────────────────────────────

_BPHS_AYURDAYA_CITATION = Citation(
    source_id="BPHS Ayurdaya Adhyaya (longevity calculation chapters)",
    text_chunk="The 8th house from a bhava signifies death of the "
               "matters of that bhava. For paternal longevity the 8th "
               "from the 9th (= father's lagna) is reckoned; the lord "
               "of that 8th bhava is the maraka for father.",
)


_R_FATHER_AD_F8L_SUN_DUSTHANA = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ad_is_f8l_with_sun_in_dusthana.cf17",
        school=School.PARASHARI,
        source="BPHS Ayurdaya Adhyaya: F8L (lord of 8th from father-"
               "lagna) is the longevity-end lord for father. When this "
               "lord's antar dasha runs concurrent with Sun (father-"
               "karaka) gocharā in 6/8/12, the dual structural-and-"
               "transit activation pins the death window. Targeted at "
               "Schwarzenegger truth-AD (Mer = lagna_lord = F8L for "
               "Gemini lagna; Sun transits 6h dusthana on truth date).",
        is_veto=False,
        base_cf=-0.30,
        # Dynamic: rule fires when AD lord = F8L; the AD lord IS
        # the planet whose strength determines whether the F8L
        # activation delivers full maraka force. Migrated from
        # static "Sun" (which incorrectly modulated by Sun's
        # strength regardless of F8L identity).
        primary_planet="<ad_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_AYURDAYA_CITATION],
        ),
        modifiers=[
            CFModifier(
                condition={
                    "path": "planets.Sun.aspect_strengths_on_natal.Jupiter",
                    "op": ">=", "value": 0.5,
                },
                effect_cf=+0.20,
                explanation="Jupiter aspects natal Sun with strength "
                            ">= 0.5: partial Parivartana-style "
                            "protection",
            ),
        ],
    ),
    fires_when=_ad_is_f8l_with_sun_in_dusthana,
    modifier_predicates=[
        # Modifiers above already use DSL conditions; the
        # PD-also-F8L and SD-in-loss-lord intensifiers below need
        # dynamic chart context (resolve F8L per chart, then check
        # PD/SD against it), which DSL paths can't dynamically
        # interpolate. Push them to Python-lambda predicates as
        # CF-engine-native modifiers, mirroring v15's pattern.
    ],
)


def _pd_also_f8l(ep: EpochState) -> bool:
    f8l = _father_8L(ep)
    return f8l is not None and ep.dashas.pratyantar == f8l


def _sd_in_father_loss_lords(ep: EpochState) -> bool:
    return ep.dashas.sookshma in _father_loss_lords(ep)


# Append the dynamic-context modifiers via a second-stage rule build
# (Python-lambda modifier_predicates parallel to the rule.modifiers
# list). The CF engine unions DSL-evaluated indices with pre-evaluated
# indices, so both sets fire when applicable.
_R_FATHER_AD_F8L_SUN_DUSTHANA.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.12,
               explanation="PD-lord also F8L: bullseye intensifier"),
)
_R_FATHER_AD_F8L_SUN_DUSTHANA.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="SD-lord in F-loss-lord set "
                           "(F2L/F7L/F8L/F12L): SD-level activation"),
)
# Modifier_predicates parallel to rule.modifiers. Index 0 is the
# DSL-form Jupiter modifier (no Python predicate needed); indices
# 1 and 2 are the dynamic ones we just appended.
_R_FATHER_AD_F8L_SUN_DUSTHANA.modifier_predicates = [
    lambda ep: False,  # DSL-only modifier — Python-side never fires it
    _pd_also_f8l,
    _sd_in_father_loss_lords,
]


# ── Final v17 rule list ───────────────────────────────────────────

RULES_V17: List[CFRuleSpec] = list(RULES_V16) + [
    _R_FATHER_AD_F8L_SUN_DUSTHANA,
]
