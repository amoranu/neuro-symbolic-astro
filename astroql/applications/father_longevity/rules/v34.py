"""CF rules for father's longevity, v34 — sixth draft under HO+Train
methodology (2026-04-26).

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R7. ad_lord_combust_with_father_bhava_role
      Engine v2 introduced `is_combust` (planet within ~5° of Sun
      in transit). v15 has no rule using this field.

      When the AD-lord plays a father-bhava role AND is combust at
      the AD time, two effects classically combine:

        (a) The bhava-significator-of-period is conjunct natal Sun
            in transit (since combust = within Sun's burning zone).
            Sun is the father karaka, so an F-role AD-lord burning
            with Sun is a "merger" of the period-significator with
            the karaka — classically a stress event for the karaka.

        (b) The combust planet's natural force is burnt out
            (BPHS Ch. 30: combust planets lose their independent
            ability to act). An F-role AD-lord that is combust
            cannot defend the bhava it rules.

      Fires when:
        * AD lord plays a father-bhava role (lagna_lord, 9L, 8L,
          F-loss-lord) on this chart
        * AD lord is_combust at this epoch

      base_cf = -0.20
      primary_planet = <ad_lord>

      Modifiers:
        - PD lord ALSO combust (compound burnt-bhava-lord at PD
          level): -0.10
        - AD lord additionally retrograde (acutely afflicted
          combust-retrograde state): -0.10
        - Jupiter aspects natal Sun strength >= 0.5: +0.15

  Note: Sun-AD self-combusts in any sense vacuously, so we exclude
  AD == "Sun" from the gate (Sun cannot be combust by itself).
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v31 import RULES_V31


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


def _ad_lord_combust_with_father_bhava_role(ep: EpochState) -> bool:
    """v34 R7 fires_when:
        * AD lord plays a father-bhava role on this chart
        * AD lord is combust (within Sun's burning zone)
        * AD lord != "Sun" (Sun cannot combust itself)
    """
    ad = ep.dashas.antar
    if not ad or ad == "Sun":
        return False
    p = ep.planets.get(ad)
    if p is None or not p.is_combust:
        return False
    return _ad_plays_father_bhava_role(ep)


def _pd_lord_combust(ep: EpochState) -> bool:
    pd = ep.dashas.pratyantar
    if not pd or pd == "Sun":
        return False
    p = ep.planets.get(pd)
    return p is not None and p.is_combust


def _ad_lord_retrograde(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    if not ad:
        return False
    p = ep.planets.get(ad)
    return p is not None and p.is_retrograde


_BPHS_COMBUST_BHAVA_LORD_CITATION = Citation(
    source_id="BPHS Ch. 30 (Sun's combustion of planets) + bhava-"
              "lord-burnt-by-karaka doctrine",
    text_chunk="A planet within Sun's combustion zone (asta) loses "
               "its independent significatory ability for the period "
               "of combustion. When a bhava-lord is combust during "
               "its dasha activation, the bhava it rules cannot "
               "manifest its protective indications. For paternal "
               "longevity, an AD-lord that plays a father-bhava role "
               "and is simultaneously combust (= conjunct natal Sun "
               "in transit, the karaka itself) is a doubly "
               "afflicted activation: the karaka-merger amplifies "
               "the burnt-out lord's failure to protect father.",
)


_R_AD_COMBUST_FATHER_BHAVA = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ad_lord_combust_with_father_bhava_role.cf34",
        school=School.PARASHARI,
        source="BPHS combustion of bhava-lord during its dasha. "
               "Engine v2's is_combust field is now load-bearing for "
               "a generalizing rule. Distinct from sphuta-aspect "
               "rules: combustion is a conjunction-with-Sun event, "
               "not an aspect-formation event.",
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
            citations=[_BPHS_COMBUST_BHAVA_LORD_CITATION],
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
    fires_when=_ad_lord_combust_with_father_bhava_role,
)


_R_AD_COMBUST_FATHER_BHAVA.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="PD lord ALSO combust at this epoch: "
                           "compound burnt-bhava-lord at AD+PD."),
)
_R_AD_COMBUST_FATHER_BHAVA.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="AD lord additionally retrograde at this "
                           "epoch: combust-retrograde state, acutely "
                           "afflicted bhava-lord."),
)
_R_AD_COMBUST_FATHER_BHAVA.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _pd_lord_combust,
    _ad_lord_retrograde,
]


# ── v34 rule list (additive over v31 canonical) ───────────────────

RULES_V34: List[CFRuleSpec] = list(RULES_V31) + [
    _R_AD_COMBUST_FATHER_BHAVA,
]
