"""CF rules for father's longevity, v29 — REJECTED under HO+Train
validation methodology (2026-04-26).

Status: REJECTED. Preserved here for documentation of the failed
attempt. Not included in any canonical RULES set.

  eval_split --candidate v29 --baseline v15:
    Train Δ(AD+PD+SD) = -3   Δmean = +33d  ← regresses training
    HO    Δ(AD+PD+SD) = +0   Δmean = +6d   ← no held-out gain

  Why it failed: the rule's gate ("AD lord at 8h-from-lagna under
  malefic/F-role MD") is too broadly satisfied — fires on ~10-20%
  of epochs across the dataset. Many of those firings are at non-
  truth epochs where the AD-lord happens to be transiting the 8h
  position with stronger CF than at the actual truth window.
  Result: rule pulls predictions away from truth without finding
  it on any held-out chart either. Pure noise.

  Lesson: a "broad single-gate" rule needs a SECONDARY CONSTRAINT
  to localize the firing to the death-window specifically — e.g.
  combine ashtama-transit with simultaneous karaka stress, or with
  a narrower SD-level pin. v30 attempts this.

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

Rule philosophy: BROAD signals that fire across many charts, not
chart-specific lord-identity lookups. Each rule must accept under
the held-out criteria (HO Hit@MD non-decreasing, HO (AD+PD+SD) total
non-decreasing, HO mean within +5%) before being merged into RULES.

  R1. ad_lord_transit_8th_from_lagna
      Classical: ashtama (8th) transit of any dasha lord activates
      the longevity-trika of native's lagna. The 8th house from
      lagna is the classical "death-trika": its lord, occupants, and
      transits there govern life-end events for self AND for
      relations whose karakas are afflicted via this house.

      For paternal longevity specifically, the AD-lord transiting
      the 8h-from-lagna ties the active period planet to the
      death-trika. v15 covers "Sun in dusthana" (sun_dusthana_*)
      and "F-loss-lord at AD" (derived_f_lord_ad), but NO rule
      captures "AD-lord transit 8h-from-lagna" specifically.

      Fires when:
        * AD lord transits 8th sign from native lagna
        * MD lord is malefic OR plays a father-bhava role
          (lagna_lord, 9L, 8L, or any F-loss-lord)

      base_cf = -0.20  (modest — the rule fires in ~10-20% of
                        epochs across the dataset, so its signal
                        magnitude must be bounded to avoid swamping
                        per-chart variation)
      primary_planet = <ad_lord>  (modulate by AD lord's natal
                                   shadbala — strong AD lord with
                                   bad transit position attacks
                                   harder than weak)

      Modifiers:
        - AD lord plays a father-bhava role on the chart (any of
          lagna_lord/9L/8L/F-loss-lord): -0.10
        - SD lord ALSO transits 8h-from-lagna (compound transit
          activation): -0.05
        - Jupiter aspects natal Sun strength >= 0.5: +0.15
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v15 import RULES_V15


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
    for n in (10, 3, 4, 8):  # F2L=10L, F7L=3L, F8L=4L, F12L=8L
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


def _ad_lord_at_8h_from_lagna(ep: EpochState) -> bool:
    """v29 R1 fires_when:
        * AD lord transits 8th sign from native lagna
        * MD lord is malefic OR plays a father-bhava role
    """
    if not ep.natal_lagna_sign:
        return False
    eighth = _nth_sign_from(ep.natal_lagna_sign, 8)
    if not eighth:
        return False
    ad = ep.dashas.antar
    if not ad:
        return False
    p = ep.planets.get(ad)
    if p is None or p.transit_sign != eighth:
        return False
    return _md_father_bhava_role_or_malefic(ep)


def _ad_plays_father_bhava_role(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    if not ad or not ep.natal_lagna_sign:
        return False
    if ad == _safe_sign_lord(ep.natal_lagna_sign):
        return True
    if ad == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9)):
        return True
    if ad == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 8)):
        return True
    return ad in _f_loss_lord_set(ep)


def _sd_lord_also_at_8h_from_lagna(ep: EpochState) -> bool:
    if not ep.natal_lagna_sign:
        return False
    eighth = _nth_sign_from(ep.natal_lagna_sign, 8)
    sd = ep.dashas.sookshma
    if not sd or not eighth:
        return False
    p = ep.planets.get(sd)
    return p is not None and p.transit_sign == eighth


_BPHS_ASHTAMA_TRANSIT_CITATION = Citation(
    source_id="BPHS Gochara-prakaranam (Ch. 65) + Ayurdaya Adhyaya",
    text_chunk="When the antar-dasha lord transits the 8th house "
               "from native's lagna, the active period planet enters "
               "the longevity-trika and amplifies maraka effects "
               "for the period in question. Combined with a malefic "
               "or bhava-related maha-dasha, this places the "
               "dasha-bhukti force in direct conflict with the "
               "longevity of the bhava-karaka under stress.",
)


_R_AD_LORD_TRANSIT_8TH_FROM_LAGNA = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ad_lord_transit_8h_from_lagna.cf29",
        school=School.PARASHARI,
        source="BPHS gochara: AD-lord transiting 8th-from-lagna "
               "(longevity-trika of native) under a malefic or "
               "bhava-related MD activates death-period for stress-"
               "tested karakas. Generic transit-of-dasha-lord rule "
               "applicable to all charts (no chart-specific lord-"
               "identity narrowing).",
        is_veto=False,
        base_cf=-0.20,
        primary_planet="<ad_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_ASHTAMA_TRANSIT_CITATION],
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
    fires_when=_ad_lord_at_8h_from_lagna,
)


_R_AD_LORD_TRANSIT_8TH_FROM_LAGNA.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="AD lord plays a father-bhava role on the "
                           "chart (lagna_lord/9L/8L/F-loss-lord): "
                           "compound activation of bhava-significator "
                           "in transit-stress."),
)
_R_AD_LORD_TRANSIT_8TH_FROM_LAGNA.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.05,
               explanation="SD lord ALSO transits 8h-from-lagna at the "
                           "same epoch: deepest sub-period repeats the "
                           "ashtama-transit affliction."),
)
_R_AD_LORD_TRANSIT_8TH_FROM_LAGNA.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _ad_plays_father_bhava_role,
    _sd_lord_also_at_8h_from_lagna,
]


# ── v29 rule list (additive over v15 baseline) ────────────────────

RULES_V29: List[CFRuleSpec] = list(RULES_V15) + [
    _R_AD_LORD_TRANSIT_8TH_FROM_LAGNA,
]
