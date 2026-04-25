"""CF rules for father's longevity, v41 — REJECTED under HO+Train
methodology (2026-04-26).

Status: REJECTED. Train AD 8→7 (-1), train mean +14d. HO improves
slightly (-6d mean, -8d median) but train regression triggers
REJECT under the verdict logic. Suggests dusthana-from-Sun gate is
tighter than maraka-from-Sun (v30) but still pulls a training
prediction off-target.

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R14. ad_lord_transit_dusthana_from_natal_sun
       AD-lord transits 6th/8th/12th sign from natal Sun's sign.

       6/8/12 are the "dusthana" houses — universally afflicting
       to whichever house they're counted from. From the karaka's
       natal position (Sun for father), these mark transit
       positions from which the AD-lord's force corrupts the
       karaka's signification.

       Note v15 has `sun_dusthana_malefic_md` (Sun transit dusthana
       from native lagna) and `ashtama_from_natal_sun` (8th from
       Sun specifically). This rule covers ALL THREE dusthanas
       (6/8/12) from Sun for the AD-lord — broader than ashtama-
       from-Sun, distinct from Sun-in-dusthana-from-lagna.

       v30 (rejected) was AD-lord at 2nd/7th from Sun (maraka). This
       v41 is at 6/8/12 from Sun (dusthana) — different geometry.
       Whether either generalizes is empirical.

       Fires when:
         * AD lord transits 6th, 8th, or 12th sign from natal Sun
         * AD lord is a natural malefic OR plays a father-bhava role

       base_cf = -0.18
       primary_planet = <ad_lord>

       Modifiers:
         - AD lord transits 8th from Sun specifically (the
           strongest dusthana for longevity): -0.07
         - PD lord ALSO transits dusthana from natal Sun: -0.08
         - Jupiter aspects natal Sun strength >= 0.5: +0.10
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v39 import RULES_V39


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
    for n in (10, 3, 4, 8):
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


def _dusthana_signs_from_natal_sun(ep: EpochState) -> tuple:
    sun = ep.planets.get("Sun")
    if sun is None or not sun.natal_sign:
        return ()
    return tuple(_nth_sign_from(sun.natal_sign, n) for n in (6, 8, 12))


def _ad_lord_transit_dusthana_from_sun(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    if not ad:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    dusth = set(s for s in _dusthana_signs_from_natal_sun(ep) if s)
    if not dusth or p.transit_sign not in dusth:
        return False
    return ad in _MALEFIC_DASHA_LORDS or _is_father_bhava_role(ep, ad)


def _ad_in_8th_from_sun(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    if not ad:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    sun = ep.planets.get("Sun")
    if sun is None or not sun.natal_sign:
        return False
    eighth = _nth_sign_from(sun.natal_sign, 8)
    return p.transit_sign == eighth


def _pd_in_dusthana_from_sun(ep: EpochState) -> bool:
    pd = ep.dashas.pratyantar
    if not pd:
        return False
    p = ep.planets.get(pd)
    if p is None:
        return False
    dusth = set(s for s in _dusthana_signs_from_natal_sun(ep) if s)
    return p.transit_sign in dusth


_BPHS_DUSTHANA_FROM_KARAKA_CITATION = Citation(
    source_id="BPHS Bhava-pidā doctrine + dusthana-from-karaka "
              "geometry",
    text_chunk="The 6/8/12 from any house are its dusthanas — "
               "the upachaya/asubha-trika that corrupt the house's "
               "signification. Counted from the karaka's natal "
               "position, the dusthanas-from-Sun mark transit "
               "positions from which an active dasha-lord attacks "
               "the karaka. Distinct from dusthana-from-lagna "
               "(which targets the chart-self) and maraka-from-"
               "Sun (2/7, which targets death-houses for the "
               "karaka).",
)


_R_AD_DUSTHANA_FROM_NATAL_SUN = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ad_lord_transit_dusthana_from_natal_sun.cf41",
        school=School.PARASHARI,
        source="AD-lord at 6/8/12 from natal Sun's sign — dusthana "
               "from karaka, gated by malefic-AD or AD-F-role.",
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
            citations=[_BPHS_DUSTHANA_FROM_KARAKA_CITATION],
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
    fires_when=_ad_lord_transit_dusthana_from_sun,
)


_R_AD_DUSTHANA_FROM_NATAL_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.07,
               explanation="AD-lord specifically at 8th from Sun "
                           "(longevity-trika of the karaka)."),
)
_R_AD_DUSTHANA_FROM_NATAL_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.08,
               explanation="PD-lord ALSO transits a dusthana from "
                           "natal Sun: AD+PD compound dusthana-"
                           "from-karaka activation."),
)
_R_AD_DUSTHANA_FROM_NATAL_SUN.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _ad_in_8th_from_sun,
    _pd_in_dusthana_from_sun,
]


# ── v41 rule list (additive over v39 canonical) ───────────────────

RULES_V41: List[CFRuleSpec] = list(RULES_V39) + [
    _R_AD_DUSTHANA_FROM_NATAL_SUN,
]
