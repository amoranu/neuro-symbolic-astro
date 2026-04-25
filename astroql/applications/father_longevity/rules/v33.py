"""CF rules for father's longevity, v33 — REJECTED under HO+Train
methodology (2026-04-26).

Status: REJECTED. Train AD 7 → 6 (-1), HO unchanged. The 9L-target
variant of R3's sphuta-aspect pattern fired at non-truth epochs on
some training charts, swapping out one AD-match. Preserved for
documentation.

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R5. malefic_AD_with_sphuta_aspect_on_natal_9L
      Companion to v31's R3, targeting native's 9L (sign-lord of
      9th from native lagna = father-bhava ruler) instead of Sun.

      Rationale: father karaka is Sun, but father BHAVA RULER is
      9L. Affliction of 9L by transit aspect = direct attack on
      father-bhava significator. Combined with malefic AD = active
      period attacking father-bhava ruler.

      For Sagittarius lagna 9L = Sun, so this rule is redundant with
      R3 on those charts. For other lagnas it targets a distinct
      natal position. Across the dataset, 9L diversity covers most
      of the planetary set.

      v15 has `ninth_lord_transit_dusthana.cf13` and `ninth_lord_
      transit_afflicted.cf13` covering 9L's transit position and 9L
      being aspected. This rule is the inverse: someone aspecting
      9L (specifically a malefic dasha-lord with tight orb).

      Fires when:
        * AD lord is a natural malefic (Sat/Mar/Rah/Ket/Sun)
        * AD lord's aspect_strengths_on_natal[<9L_planet>] >= 0.5

      base_cf = -0.20
      primary_planet = <ad_lord>

      Modifiers:
        - 9L planet itself in dusthana (6/8/12) from native lagna
          natally (chart-static — 9L weakened intrinsically): -0.05
        - AD-lord aspect strength on 9L >= 0.7 (tight orb): -0.10
        - Jupiter aspects natal Sun strength >= 0.5: +0.15
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v31 import RULES_V31


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


def _ninth_lord(ep: EpochState) -> Optional[str]:
    if not ep.natal_lagna_sign:
        return None
    return _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9))


def _ad_lord_sphuta_aspect_on_9L(ep: EpochState) -> bool:
    """v33 R5 fires_when:
        * AD lord is a natural malefic
        * AD lord's sphuta-aspect strength on natal 9L position >= 0.5
    """
    ad = ep.dashas.antar
    if not ad or ad not in _MALEFIC_DASHA_LORDS:
        return False
    nl = _ninth_lord(ep)
    if nl is None or nl not in ep.planets:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get(nl, 0.0) >= 0.5


def _9L_natal_in_dusthana(ep: EpochState) -> bool:
    nl = _ninth_lord(ep)
    if nl is None:
        return False
    p = ep.planets.get(nl)
    return p is not None and p.natal_house in (6, 8, 12)


def _ad_lord_tight_sphuta_aspect_on_9L(ep: EpochState) -> bool:
    ad = ep.dashas.antar
    if not ad:
        return False
    nl = _ninth_lord(ep)
    if nl is None:
        return False
    p = ep.planets.get(ad)
    if p is None:
        return False
    return p.aspect_strengths_on_natal.get(nl, 0.0) >= 0.7


_BPHS_9L_AFFLICTION_CITATION = Citation(
    source_id="BPHS Bhava-prakaranam (9th house) + sphuta drishti",
    text_chunk="The 9th lord (father-bhava ruler) under tight-orb "
               "aspect from a malefic dasha-lord is a direct "
               "affliction of the father-bhava significator. Where "
               "v15's binary ninth-lord-transit-afflicted rule fires "
               "for the whole sign-aspect arc, the sphuta refinement "
               "narrows to the precise transit moment of exact-orb "
               "formation.",
)


_R_MALEFIC_AD_SPHUTA_ASPECT_9L = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.malefic_ad_sphuta_aspect_on_natal_9L.cf33",
        school=School.PARASHARI,
        source="Sphuta-drishti refinement: malefic AD-lord casting "
               "tight-orb (>=0.5 = within ~5°) aspect on native's "
               "9L (sign-lord of 9th from native = father bhava "
               "ruler) at the AD epoch. Companion to v31's R3 "
               "targeting Sun.",
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
            citations=[_BPHS_9L_AFFLICTION_CITATION],
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
    fires_when=_ad_lord_sphuta_aspect_on_9L,
)


_R_MALEFIC_AD_SPHUTA_ASPECT_9L.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.05,
               explanation="9L planet in natal dusthana (6/8/12 from "
                           "lagna): father-bhava ruler intrinsically "
                           "weakened, transit affliction compounds."),
)
_R_MALEFIC_AD_SPHUTA_ASPECT_9L.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="AD-lord aspect strength on 9L >= 0.7 "
                           "(within ~3° of exact)."),
)
_R_MALEFIC_AD_SPHUTA_ASPECT_9L.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _9L_natal_in_dusthana,
    _ad_lord_tight_sphuta_aspect_on_9L,
]


# ── v33 rule list (additive over v31 canonical) ───────────────────

RULES_V33: List[CFRuleSpec] = list(RULES_V31) + [
    _R_MALEFIC_AD_SPHUTA_ASPECT_9L,
]
