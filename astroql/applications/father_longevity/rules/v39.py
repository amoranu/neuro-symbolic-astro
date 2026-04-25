"""CF rules for father's longevity, v39 — eleventh draft under
HO+Train methodology (2026-04-26).

Designed against training (ids 3-26) only; held-out (ids 27-46)
reserved for unbiased acceptance test via `eval_split`.

  R12. any_malefic_with_TIGHT_sphuta_aspect_on_natal_sun
       v31/v37/v38 require the malefic-aspector to be the AD-lord
       or PD-lord. This rule catches the case where a malefic
       (any) is in tight-orb aspect on natal Sun even when neither
       AD nor PD is that malefic, gated by MD context.

       The classical doctrine doesn't require the aspector to be a
       dasha-lord — it cares about the aspect itself. This rule
       captures Saturn-aspects-Sun, Mars-aspects-Sun, and so on
       at exact-orb moments regardless of which planet is currently
       activating its dasha period.

       v15 already has binary saturn_aspects_natal_sun and
       mars_afflicts_natal_sun (sign-based). This rule narrows to
       the tight-orb (~3°) sphuta moment AND adds Rahu/Ketu's
       analogous case.

       Fires when:
         * Some malefic planet (Sat/Mar/Rah/Ket — Sun excluded since
           Sun-aspecting-Sun is degenerate) has sphuta-aspect
           strength on natal Sun >= 0.7
         * MD lord is malefic OR plays a father-bhava role

       base_cf = -0.15
       primary_planet = "Saturn"  (the most consistent maraka
                                   planet for paternal longevity;
                                   gives stable magnitude regardless
                                   of which malefic is aspecting)

       Modifiers:
         - The aspecting malefic is also retrograde: -0.08
         - Two or more malefics simultaneously aspect Sun >= 0.5
           (compound multi-malefic transit drishti): -0.10
         - Jupiter aspects natal Sun strength >= 0.5: +0.10
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v38 import RULES_V38


_NON_LUMINARY_MALEFICS = ("Saturn", "Mars", "Rahu", "Ketu")
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


def _any_malefic_tight_aspect_on_sun(ep: EpochState) -> bool:
    """v39 R12 fires_when:
        * Some non-luminary malefic has sphuta-aspect strength on
          natal Sun >= 0.7
        * MD lord is malefic OR plays father-bhava role
    """
    if not _md_father_bhava_role_or_malefic(ep):
        return False
    for malef in _NON_LUMINARY_MALEFICS:
        p = ep.planets.get(malef)
        if p is None:
            continue
        if p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.7:
            return True
    return False


def _firing_aspector_retrograde(ep: EpochState) -> bool:
    for malef in _NON_LUMINARY_MALEFICS:
        p = ep.planets.get(malef)
        if p is None:
            continue
        if (p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.7
                and p.is_retrograde):
            return True
    return False


def _two_or_more_malefics_aspect_sun(ep: EpochState) -> bool:
    count = 0
    for malef in _NON_LUMINARY_MALEFICS:
        p = ep.planets.get(malef)
        if p is None:
            continue
        if p.aspect_strengths_on_natal.get("Sun", 0.0) >= 0.5:
            count += 1
            if count >= 2:
                return True
    return False


_BPHS_ANY_MALEFIC_KARAKA_CITATION = Citation(
    source_id="BPHS Aspects + Phaladeepika multi-malefic-on-karaka",
    text_chunk="Tight-orb special aspect by a malefic on a bhava-"
               "karaka is classically afflicting regardless of which "
               "planet currently holds the dasha — the aspect's force "
               "is intrinsic to the configuration. Multi-malefic "
               "transit drishti on a karaka compounds the affliction.",
)


_R_ANY_MALEFIC_TIGHT_SPHUTA_SUN = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.any_malefic_tight_sphuta_aspect_on_natal_sun.cf39",
        school=School.PARASHARI,
        source="Tight-orb (>=0.7) sphuta-aspect by ANY non-luminary "
               "malefic (Sat/Mar/Rah/Ket) on natal Sun, gated by "
               "MD context. Distinct from v31/v37 (which require "
               "the aspector to BE the AD-lord). Catches Saturn- or "
               "Mars-aspects-Sun moments when those planets are not "
               "the active dasha-lord.",
        is_veto=False,
        base_cf=-0.15,
        primary_planet="Saturn",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_ANY_MALEFIC_KARAKA_CITATION],
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
    fires_when=_any_malefic_tight_aspect_on_sun,
)


_R_ANY_MALEFIC_TIGHT_SPHUTA_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.08,
               explanation="The malefic at >= 0.7 aspect on Sun is "
                           "additionally retrograde."),
)
_R_ANY_MALEFIC_TIGHT_SPHUTA_SUN.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="Two or more malefics simultaneously "
                           "aspect natal Sun (each strength >= 0.5): "
                           "compound multi-malefic karaka drishti."),
)
_R_ANY_MALEFIC_TIGHT_SPHUTA_SUN.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _firing_aspector_retrograde,
    _two_or_more_malefics_aspect_sun,
]


# ── v39 rule list (additive over v38 canonical) ───────────────────

RULES_V39: List[CFRuleSpec] = list(RULES_V38) + [
    _R_ANY_MALEFIC_TIGHT_SPHUTA_SUN,
]
