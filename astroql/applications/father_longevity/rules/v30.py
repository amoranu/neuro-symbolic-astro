"""CF rules for father's longevity, v30 — REJECTED under HO+Train
methodology (2026-04-26).

Status: REJECTED. Train (AD+PD+SD) decreased 8→6 (lost 1 AD and
1 SD on training despite gaining 1 MD). HO unchanged. The rule's
gate ("AD-lord transits 2nd/7th from natal Sun") is broad enough
to fire at non-truth epochs more strongly than at truth on a
couple of training charts. Preserved for documentation; not in
canonical RULES.

Below is the original design notes preserved for reference.

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R2. ad_lord_transit_maraka_from_natal_sun
      Classical: maraka houses from any karaka are the 2nd and 7th
      from that karaka's natal position. They are the death-causing
      houses for the bhava the karaka represents (BPHS Maraka-
      prakaranam Ch. 46). For paternal longevity, 2nd and 7th from
      natal Sun are the maraka positions for father-as-karaka.

      An AD-lord transiting through one of these positions while
      being either a natural malefic or a chart-specific father-
      bhava-role player creates an "actively-killing" configuration
      — the active period planet is at the karaka-maraka position,
      tightening the death-window during the AD.

      Distinct from existing v15 rules:
        - sun_dusthana_malefic_md fires when SUN transits dusthana
          from native lagna; this rule fires when AD-LORD transits
          maraka from SUN (different geometry).
        - ashtama_from_natal_sun fires on 8th-from-Sun (longevity-
          trika); this fires on 2nd/7th-from-Sun (marakas).
        - karaka_hanana_over_natal_sun fires when 2+ malefics
          conjunct natal Sun's sign; this fires on the AD-lord
          specifically at maraka-from-Sun position.

      Fires when:
        * AD lord transits 2nd OR 7th sign from natal Sun's sign
        * AD lord is a natural malefic (Sat/Mar/Rah/Ket/Sun) OR
          plays a father-bhava role on the chart (lagna_lord, 9L,
          8L, F-loss-lord)

      base_cf = -0.20 (modest — fires on ~10-15% of epochs)
      primary_planet = <ad_lord>

      Modifiers:
        - PD lord ALSO transits maraka from natal Sun (compound
          maraka activation across two dasha levels): -0.10
        - AD lord is debilitated in this transit (rāshi-debilitated
          karaka attacker has compounded weakness): -0.05
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

# Classical debilitation signs by planet (1-indexed sign placeholders
# converted to names below). BPHS Ch. 3.
_DEBILITATION = {
    "Sun":     "Libra",
    "Moon":    "Scorpio",
    "Mars":    "Cancer",
    "Mercury": "Pisces",
    "Jupiter": "Capricorn",
    "Venus":   "Virgo",
    "Saturn":  "Aries",
    # Nodes don't have classical debilitation signs in BPHS — treat
    # as "no debilitation" for purposes of this modifier.
}


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


def _is_father_bhava_role(ep: EpochState, planet: str) -> bool:
    if not planet or not ep.natal_lagna_sign:
        return False
    if planet == _safe_sign_lord(ep.natal_lagna_sign):
        return True
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9)):
        return True
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 8)):
        return True
    return planet in _f_loss_lord_set(ep)


def _maraka_signs_from_natal_sun(ep: EpochState) -> set:
    sun = ep.planets.get("Sun")
    if sun is None or not sun.natal_sign:
        return set()
    second = _nth_sign_from(sun.natal_sign, 2)
    seventh = _nth_sign_from(sun.natal_sign, 7)
    return {s for s in (second, seventh) if s}


def _ad_lord_transit_maraka_from_sun(ep: EpochState) -> bool:
    """v30 R2 fires_when:
        * AD lord transits 2nd OR 7th sign from natal Sun's sign
        * AD lord is malefic OR plays father-bhava role
    """
    ad = ep.dashas.antar
    if not ad:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    maraka = _maraka_signs_from_natal_sun(ep)
    if not maraka or p.transit_sign not in maraka:
        return False
    if ad in _MALEFIC_DASHA_LORDS:
        return True
    return _is_father_bhava_role(ep, ad)


def _pd_also_transit_maraka_from_sun(ep: EpochState) -> bool:
    pd = ep.dashas.pratyantar
    if not pd:
        return False
    p = ep.planets.get(pd)
    if p is None:
        return False
    return p.transit_sign in _maraka_signs_from_natal_sun(ep)


def _ad_lord_debilitated_in_transit(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    if not ad:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    debil = _DEBILITATION.get(ad)
    return debil is not None and p.transit_sign == debil


_BPHS_MARAKA_FROM_KARAKA_CITATION = Citation(
    source_id="BPHS Maraka-prakaranam (Ch. 46) — maraka-from-karaka "
              "doctrine",
    text_chunk="The 2nd and 7th from any house are its maraka-sthana. "
               "Applied to a karaka's natal position, the 2nd and 7th "
               "from that karaka's sign mark the death-causing "
               "transit positions for the bhava the karaka represents. "
               "When a dasha-lord — especially a natural malefic or a "
               "bhava-role player on the chart — transits one of "
               "these positions during its own dasha period, the "
               "active period planet is in karaka-maraka, intensifying "
               "the death-window for that bhava.",
)


_R_AD_LORD_TRANSIT_MARAKA_FROM_SUN = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ad_lord_transit_maraka_from_natal_sun.cf30",
        school=School.PARASHARI,
        source="BPHS maraka-from-karaka: AD-lord transiting 2nd or "
               "7th from natal Sun's sign while malefic or bhava-"
               "role-playing creates an actively-killing position "
               "for the father karaka during the AD. Distinct from "
               "v15's Sun-dusthana (different geometry) and karaka-"
               "hanana (different gate).",
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
            citations=[_BPHS_MARAKA_FROM_KARAKA_CITATION],
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
    fires_when=_ad_lord_transit_maraka_from_sun,
)


_R_AD_LORD_TRANSIT_MARAKA_FROM_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="PD lord ALSO transits maraka (2nd/7th) "
                           "from natal Sun: compound karaka-maraka "
                           "activation across AD+PD."),
)
_R_AD_LORD_TRANSIT_MARAKA_FROM_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.05,
               explanation="AD lord is debilitated in this transit "
                           "sign: weakened karaka-attacker amplifies "
                           "the maraka effect classically."),
)
_R_AD_LORD_TRANSIT_MARAKA_FROM_SUN.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _pd_also_transit_maraka_from_sun,
    _ad_lord_debilitated_in_transit,
]


# ── v30 rule list (additive over v15 baseline) ────────────────────

RULES_V30: List[CFRuleSpec] = list(RULES_V15) + [
    _R_AD_LORD_TRANSIT_MARAKA_FROM_SUN,
]
