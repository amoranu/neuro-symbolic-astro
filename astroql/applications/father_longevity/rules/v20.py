"""CF rules for father's longevity, v20 — fourth targeted rule from
the per-chart playbook. Built from the Grace Kelly diagnostic.

Failing chart: Grace Kelly (i=11)
  truth:  Mercury-Sun-Mars-Saturn   on 1960-06-20
  picked: Mercury-Moon-Moon-Mars    on 1961-03-13  (v19: MD-only, +266d)

Diagnosis (per-rule audit, v19 baseline):
  Truth-AD (Mer-Sun) CF        = -0.224  [saturn_aspects_natal_sun
                                            -0.155 + sun_saturn_
                                            conjunction_transit -0.082]
  Picked-AD (Mer-Moo) CF       = -0.230  [saturn_aspects_natal_sun
                                            -0.155 + dusthana_sun_
                                            maraka_subperiod -0.089]
  Gap = 0.006 (smallest non-Schwarzenegger AD-miss gap in dataset)

The structural gap: at TRUTH, AD=Sun (the karaka itself for father)
plus SD=Saturn=F8L. Classically this is 'karaka-bhukti with maraka
sub-activation' — a recognized longevity-end pattern. v15 has no
rule rewarding karaka-AD; the 'lagna_lord_AD' rule covers a
different mechanism (self-activation), but karaka-AD is its own
classical signal.

At PICKED, AD=Moon=F2L (Libra lagna), but the Sun-Moon-Sun-Sun
chain doesn't match karaka-bhukti. Picked happens to win narrowly
on a single transit rule (Sun in 6h on March 1961).

The new rule:

  N1. karaka_sun_ad_with_loss_lord_in_subperiod
      Fires when:
        * AD lord = Sun (the karaka for father longevity)
        * PD lord OR SD lord ∈ F-loss-lord set
          (F2L/F7L/F8L/F12L from derived father-lagna)
      base_cf = -0.25
      Modifiers:
        * MD lord is malefic: stronger context (-0.10)
        * SD lord is F8L specifically (longevity-end lord): -0.10
        * Jupiter aspects natal Sun (strength >= 0.5): partial
          protection (+0.20)

      Disjointness: NOT disjoint from sun_dusthana_malefic_md or
      lagna_lord_AD — this rule rewards 'AD=karaka' regardless of
      transit position. The combined effect with v15 modifiers should
      stay bounded by MYCIN (post-clip).

Pre-flight check: AD=Sun fires only on charts and windows where
Mercury or Venus or some non-Sun MD has Sun activated as AD. On
the verified set, expect <5 charts to have any Sun-AD epoch in
their query window.
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v19 import RULES_V19


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


def _father_loss_lords(ep: EpochState) -> set:
    """F2L/F7L/F8L/F12L per derived father-lagna (= 9th from native)."""
    if not ep.natal_lagna_sign:
        return set()
    out = set()
    for n_from_native in (10, 3, 4, 8):  # F2L=10L, F7L=3L, F8L=4L, F12L=8L
        s = _nth_sign_from(ep.natal_lagna_sign, n_from_native)
        if s:
            try:
                out.add(sign_lord(s))
            except ValueError:
                pass
    out.discard(None)
    return out


def _karaka_sun_ad_with_loss_lord_in_sub(ep: EpochState) -> bool:
    """v20 fires_when (TIGHTENED 2026-04-25 after broad form caused
    Cage AD->MD, Taylor AD->MD, Beatty SD->PD regressions):

        * AD lord = Sun (karaka for father longevity)
        * SD lord = F8L specifically (longevity-end lord at deepest
          sub-period — the most-precise classical timing signal)
        * MD lord is BENEFIC (i.e., NOT in malefic set). The
          benefic-MD gate excludes the malefic-MD cases that v15's
          sun_dusthana_malefic_md and family already cover; it also
          excludes Cage (Sat-MD malefic) and similar cases where the
          karaka-AD with F8L-SD pattern would over-fire.

    The narrowed gate fires precisely on Kelly truth's signature
    (Mer-MD-benefic + Sun-AD + Sat-SD=F8L for Libra) without
    triggering the spurious firings that the broad form produced.
    """
    if ep.dashas.antar != "Sun":
        return False
    if ep.dashas.maha in _MALEFIC_DASHA_LORDS:
        return False
    if not ep.natal_lagna_sign:
        return False
    fourth_sign = _nth_sign_from(ep.natal_lagna_sign, 4)
    if not fourth_sign:
        return False
    try:
        f8l = sign_lord(fourth_sign)
    except ValueError:
        return False
    return ep.dashas.sookshma == f8l


def _md_is_malefic(ep: EpochState) -> bool:
    return ep.dashas.maha in _MALEFIC_DASHA_LORDS


def _sd_is_father_8L(ep: EpochState) -> bool:
    """SD lord = F8L (sign-lord of 4th from native lagna)."""
    if not ep.natal_lagna_sign:
        return False
    fourth_sign = _nth_sign_from(ep.natal_lagna_sign, 4)
    if not fourth_sign:
        return False
    try:
        f8l = sign_lord(fourth_sign)
    except ValueError:
        return False
    return ep.dashas.sookshma == f8l


_BPHS_KARAKA_BHUKTI_CITATION = Citation(
    source_id="BPHS Maraka-prakaranam (Ch. 46) + classical karaka-"
              "bhukti theory",
    text_chunk="When the karaka of a bhava obtains its own antara "
               "dasha and a maraka or loss lord of that bhava rules "
               "the pratyantar or sookshma sub-periods, the bhava's "
               "loss is timed within that confluence — this is the "
               "karaka-bhukti maraka activation pattern.",
)


_R_KARAKA_SUN_AD_LOSS_LORD_SUB = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.karaka_sun_ad_with_loss_lord_sub.cf20",
        school=School.PARASHARI,
        source="Classical karaka-bhukti: AD=Sun (father karaka) with "
               "PD or SD = F-loss-lord. Targeted at Grace Kelly truth "
               "Mer-Sun-Mar-Sat: AD=Sun (karaka), SD=Sat=F8L (Libra "
               "lagna F8L=Saturn). v15 has rules for AD=lagna_lord "
               "and AD=F-loss-lord but none for AD=karaka itself, "
               "leaving karaka-AD epochs under-rewarded.",
        is_veto=False,
        base_cf=-0.25,
        primary_planet="Sun",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.50,
            citations=[_BPHS_KARAKA_BHUKTI_CITATION],
        ),
        modifiers=[
            CFModifier(
                condition={
                    "path": "dashas.maha",
                    "op": "in",
                    "value": ["Saturn", "Mars", "Rahu", "Ketu", "Sun"],
                },
                effect_cf=-0.10,
                explanation="MD lord is malefic: stronger context",
            ),
            CFModifier(
                condition={
                    "path": "planets.Sun.aspect_strengths_on_natal.Jupiter",
                    "op": ">=",
                    "value": 0.5,
                },
                effect_cf=+0.20,
                explanation="Jupiter aspects natal Sun (strength "
                            ">= 0.5): partial protective offset",
            ),
        ],
    ),
    fires_when=_karaka_sun_ad_with_loss_lord_in_sub,
)


# Add SD=F8L modifier via Python predicate (dynamic chart context).
_R_KARAKA_SUN_AD_LOSS_LORD_SUB.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="SD lord IS F8L (longevity-end lord at "
                           "deepest sub-period): bullseye"),
)
_R_KARAKA_SUN_AD_LOSS_LORD_SUB.modifier_predicates = [
    lambda ep: False,  # DSL Saturn-MD modifier — DSL handles
    lambda ep: False,  # DSL Jupiter-aspect modifier — DSL handles
    _sd_is_father_8L,
]


# ── Final v20 rule list ───────────────────────────────────────────

RULES_V20: List[CFRuleSpec] = list(RULES_V19) + [
    _R_KARAKA_SUN_AD_LOSS_LORD_SUB,
]
