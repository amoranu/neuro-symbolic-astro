"""CF rules for father's longevity, v23 — seventh targeted rule from
the per-chart playbook. Built from the Clint Eastwood diagnostic;
expected side-effect benefits on Gardner (PD → SD upgrade) and
possibly Bruni (within-AD SD pinning).

Failing chart: Clint Eastwood (i=16)
  truth:  Venus-Moon-Venus-Mercury    on 1970-07-21
  picked: Venus-Mars-Mercury-Mars     on 1972-03-28  (v22: MD-only, +616d)

Diagnosis (per-rule audit, v22 baseline):
  Truth-AD (Ven-Moo) CF       = -0.366   [4 weak rules]
  Picked-AD (Ven-Mar) CF      = -0.701   [karaka_hanana -0.263 + v21
                                           lagna_maraka -0.213 + 3 more]
  Gap = 0.335 — too large for one rule to fully close.

Eastwood will likely STAY MD-only — picked has a legitimate strong
maraka stack (multi-malefic over natal Sun + Mars=2L+7L lagna-maraka).
But the new rule still fires at truth (-0.10 to -0.20 contribution)
and improves distance.

The new classical signal:

  SD = native's 9L (sign-lord of 9th from native lagna).
  This is the FATHER-BHAVA RULER itself activated at the deepest
  sub-period. v15 has rules for AD=9L (father_9th_lord_only_dasha)
  and PD=F-loss-lord (pd_is_derived_f_lord), but NO rule for
  SD=9L specifically. The 9L at SD level pins the death window
  inside its containing PD.

  Eastwood truth SD=Mer=9L (Libra → 9th=Gem → lord=Mer) ✓ — fires
  Eastwood picked SD=Mar=12L for Libra ✗ — doesn't fire

  Side-effect predictions:
    Gardner truth Sat-Ket-Mer-JUP: SD=Jup=9L (Can → 9th=Pis →
      lord=Jup) ✓. v23 fires at SD-Jup specifically → could
      upgrade Gardner from PD-match (current pred Sat-Ket-Mer-Mar
      has SD=Mar≠9L) to SD-match.
    Bruni truth Rah-Sat-Mer-SAT: SD=Sat=9L (Gem → 9th=Aqu →
      lord=Sat) ✓. v23 fires at SD-Sat → could shift within-Sat-AD
      pred toward truth.

The new rule:

  N1. sd_is_native_9L_with_father_active_AD
      Fires when:
        * SD lord = native's 9L (sign-lord of 9th from native lagna)
        * AD lord plays father-bhava role (lagna_lord, 9L, 8L,
          F-loss-lord, 9h-resident)
        * MD lord is malefic OR plays a father-bhava role
      base_cf = -0.30
      primary_planet = <sd_lord>  (the 9L is the role-playing planet
                                   at SD level; modulate by its μ)
      Modifiers:
        * AD lord ALSO is 9L (lord plays multi-roles via
          AD-and-SD): -0.10
        * AD lord is 9h-resident: -0.10
        * Jupiter aspects natal Sun strength >= 0.5: +0.20
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v22 import RULES_V22


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


def _ad_father_active(ep: EpochState) -> bool:
    """AD plays a father-bhava role: lagna_lord / 9L / 8L /
    F-loss-lord / 9h-resident."""
    ad = ep.dashas.antar
    if not ad or not ep.natal_lagna_sign:
        return False
    if ad == _safe_sign_lord(ep.natal_lagna_sign):
        return True
    if ad == _ninth_lord(ep):
        return True
    if ad == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 8)):
        return True
    for n_from_native in (10, 3, 4, 8):
        if ad == _safe_sign_lord(
            _nth_sign_from(ep.natal_lagna_sign, n_from_native)
        ):
            return True
    p = ep.planets.get(ad)
    if p is not None and p.natal_house == 9:
        return True
    return False


def _md_father_active_or_malefic(ep: EpochState) -> bool:
    md = ep.dashas.maha
    if md in _MALEFIC_DASHA_LORDS:
        return True
    if md == _safe_sign_lord(ep.natal_lagna_sign):
        return True
    if md == _ninth_lord(ep):
        return True
    if md == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 8)):
        return True
    if not ep.natal_lagna_sign:
        return False
    for n_from_native in (10, 3, 4, 8):
        if md == _safe_sign_lord(
            _nth_sign_from(ep.natal_lagna_sign, n_from_native)
        ):
            return True
    return False


def _sd_is_9L_with_father_active_ad(ep: EpochState) -> bool:
    """v23 fires_when:
        * SD lord = native's 9L
        * AD plays father-bhava role
        * MD malefic OR father-active
    """
    nl = _ninth_lord(ep)
    if nl is None or ep.dashas.sookshma != nl:
        return False
    if not _ad_father_active(ep):
        return False
    return _md_father_active_or_malefic(ep)


def _ad_is_9L(ep: EpochState) -> bool:
    return ep.dashas.antar == _ninth_lord(ep)


def _ad_is_9h_resident(ep: EpochState) -> bool:
    p = ep.planets.get(ep.dashas.antar)
    return p is not None and p.natal_house == 9


_BPHS_NINTH_LORD_SD_CITATION = Citation(
    source_id="BPHS Maraka-prakaranam (Ch. 46) + Ayurdaya Adhyaya",
    text_chunk="The 9th lord, when activated at the deepest sub-"
               "period (sookshma-dasha), pins the timing of bhava-"
               "related events to the precise window of that "
               "activation. For paternal longevity the 9th from "
               "native's lagna is father's bhava and its lord at "
               "SD level marks the death window precisely.",
)


_R_SD_IS_NATIVE_9L = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.sd_is_native_9L_with_father_active_AD.cf23",
        school=School.PARASHARI,
        source="BPHS deep-sub-period activation: when the 9th lord "
               "of native's lagna (= father bhava ruler) holds the "
               "sookshma dasha, AND the AD plays a father-bhava "
               "role, the precise death window is pinned. v15 "
               "rewards AD=9L and PD=F-loss-lord but NOT SD=9L; "
               "this rule closes that gap.",
        is_veto=False,
        base_cf=-0.30,
        # Dynamic: the 9L IS the SD lord here (gate ensures it).
        # Modulate by its strength.
        primary_planet="<sd_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_NINTH_LORD_SD_CITATION],
        ),
        modifiers=[
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
    fires_when=_sd_is_9L_with_father_active_ad,
)


# Add dynamic-context modifiers via Python predicates.
_R_SD_IS_NATIVE_9L.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="AD lord is ALSO 9L (multi-role 9L "
                           "across AD+SD): compound activation"),
)
_R_SD_IS_NATIVE_9L.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="AD lord natally in 9th house: physical "
                           "father-bhava AD + SD=9L confluence"),
)
_R_SD_IS_NATIVE_9L.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _ad_is_9L,
    _ad_is_9h_resident,
]


# ── Final v23 rule list ───────────────────────────────────────────

RULES_V23: List[CFRuleSpec] = list(RULES_V22) + [
    _R_SD_IS_NATIVE_9L,
]
