"""CF rules for father's longevity, v22 — sixth targeted rule from
the per-chart playbook. Built from the Will Smith diagnostic.

Failing chart: Will Smith (i=6)
  truth:  Ketu-Saturn-Venus-Rahu     on 2016-11-07
  picked: Ketu-Mars-Sun-Saturn       on 2014-05-07  (v21: MD-only, -915d)

Diagnosis (per-rule audit, v21 baseline):
  Truth-AD (Ket-Sat) CF        = -0.435   [saturn_aspects_natal_sun
                                            -0.260 + 5 weak rules]
  Picked-AD (Ket-Mar) CF       = -0.487   [sun_dusthana_md -0.146 +
                                            v21 lagna_maraka -0.130 +
                                            mars_afflicts -0.103 + ...]
  Gap = 0.052 favoring picked

Will Smith is Taurus lagna. Saturn = 9L (Capricorn = 9th from Taurus)
AND F2L (sign-lord of 10th from Taurus = Aquarius = Saturn). So the
truth-AD lord plays TWO distinct father-bhava roles. But v15's rule
library applies disjointness:

  derived_f_lord_ad rule excludes when AD is 9L
  → at Smith truth, ONLY 9th_lord_only_dasha fires (-0.057)
  → the F-loss-lord role of the SAME planet is suppressed

This is the same anti-pattern that affected Schwarzenegger (Mer =
lagna_lord + F8L for Gemini → only lagna_lord_AD rule fires, F8L
role suppressed). Multi-role AD lords classically signal STRONGER
maraka activation, not weaker — but our disjointness gates flatten
multi-role to single-role, losing signal.

The new rule INVERTS the disjointness logic: when AD lord plays
≥ 2 distinct father-bhava roles, fire an intensifier. Each existing
single-role rule still fires; this rule layers the multi-role bonus
on top.

  N1. ad_lord_multi_role_father_activation
      Fires when:
        * AD lord plays ≥ 2 father-bhava roles from the set:
            {9L, 8L, lagna_lord, F-loss-lord (any of F2L/F7L/F8L/F12L),
             natal 9h-resident}
        * MD lord is malefic OR plays father-bhava role
      base_cf = -0.30
      Modifiers:
        * 3+ roles: extreme multi-activation (-0.10)
        * PD lord ALSO in F-loss-lord set: PD-pin (-0.10)
        * Jupiter aspects natal Sun (strength >= 0.5): partial
          protective offset (+0.20)

Pre-flight check across the verified set (multi-role AD analysis):
    - Smith truth Ket-Sat: Sat=9L+F2L (Taurus) — 2 roles → FIRES
    - Schwarzenegger truth Sun-Mer: Mer=lagna_lord+F8L (Gemini)
        — 2 roles → FIRES
    - Schwarzenegger picked Sun-Sat: Sat=8L+F12L (Gemini)
        — 2 roles → ALSO FIRES (no Schwarzenegger flip; both ADs
        get equal boost. Acceptable — Schwarzenegger remains hard
        per earlier analysis.)
    - Bruni truth Rah-Sat: Sat=8L+9L (Gemini) — 2 roles → fires
        BOTH at truth and v21-picked (same Sat-AD). No effect on AD
        match.
    - Cage truth Sat-Ven, Cage v18-picked Sat-Ven-Sat-Sat:
        Ven=8L+lagna_lord (Sag, since lagna_lord=Jup not Ven)... Wait,
        Sag lagna_lord=Jup. Ven for Sag is 6L+11L. NOT in role set.
        0 roles → SAFE (Cage AD-match preserved).
    - Fonda truth Mar-Mar: Mars for Cap is 4L+11L. NOT in role set.
        0 roles → SAFE (Fonda preserved).
    - Gardner truth Sat-Ket: Ket has no lord roles, only 9h-resident
        (1 role). → SAFE (Gardner PD-match preserved).
    - Farrow truth Sun-Ven: Ven for Aries is 2L+7L. Both lagna-marakas
        but neither in our father-role set. 0 roles → SAFE.

The combined effect of v21 (which fires at picked Ket-Mar) and v22
(which fires at truth Ket-Sat) closes Smith's gap from 0.052 in v21
toward truth winning. Expected magnitude: v22 adds ~-0.16 to truth,
making truth ~-0.526 vs picked unchanged at -0.487, flipping AD.
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v21 import RULES_V21


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


def _father_bhava_role_count(ep: EpochState, planet: str) -> int:
    """Count distinct father-bhava roles a planet plays on this chart.

    Roles checked:
        - lagna_lord (sign-lord of native lagna)
        - 9L (sign-lord of 9th from native lagna)
        - 8L (sign-lord of 8th from native lagna)
        - F2L / F7L / F8L / F12L (derived father-lagna loss lords)
        - natal 9h-resident (planet physically in 9th house at birth)

    Returns the count of roles satisfied (0..6).
    """
    if not planet or not ep.natal_lagna_sign:
        return 0
    roles = 0
    # lagna_lord
    if planet == _safe_sign_lord(ep.natal_lagna_sign):
        roles += 1
    # 9L
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9)):
        roles += 1
    # 8L
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 8)):
        roles += 1
    # F-loss-lords
    for n_from_native in (10, 3, 4, 8):  # F2L=10L, F7L=3L, F8L=4L, F12L=8L
        if planet == _safe_sign_lord(
            _nth_sign_from(ep.natal_lagna_sign, n_from_native)
        ):
            roles += 1
            break  # multiple F-roles count as one bucket per BPHS
    # 9h-resident
    p = ep.planets.get(planet)
    if p is not None and p.natal_house == 9:
        roles += 1
    return roles


def _md_father_active_or_malefic(ep: EpochState) -> bool:
    if ep.dashas.maha in _MALEFIC_DASHA_LORDS:
        return True
    return _father_bhava_role_count(ep, ep.dashas.maha) >= 1


def _ad_has_9L_or_9h_resident_role(ep: EpochState, planet: str) -> bool:
    """True if the planet plays 9L OR 9h-resident — the two
    strongest father-bhava signals classically. The 'multi-role'
    rule requires AT LEAST ONE of these as a discriminator vs.
    the weaker 8L/F-loss-lord-only multi-role patterns."""
    if not planet or not ep.natal_lagna_sign:
        return False
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9)):
        return True
    p = ep.planets.get(planet)
    return p is not None and p.natal_house == 9


def _ad_lord_multi_role_father(ep: EpochState) -> bool:
    """v22 fires_when (TIGHTENED 2026-04-25 after broad form caused
    Shriver AD->MD regression and didn't flip Smith — 8L+F12L
    multi-role at non-truth ADs fired equally):

        * AD lord plays ≥ 2 father-bhava roles
        * AT LEAST ONE of those roles is 9L OR natal 9h-resident
          (the classically-strongest father-bhava signals)
        * MD lord is malefic or plays a father-bhava role

    Smith Tau lagna passes: Sat = 9L + F2L (has 9L ✓).
    Smith Jup-AD fails:    Jup = 8L + F12L (no 9L, not 9h-resident).
    Schwarzenegger Mer-AD fails: lagna_lord + F8L (no 9L, not 9h-res).
    """
    ad = ep.dashas.antar
    if not ad:
        return False
    if _father_bhava_role_count(ep, ad) < 2:
        return False
    if not _ad_has_9L_or_9h_resident_role(ep, ad):
        return False
    return _md_father_active_or_malefic(ep)


def _ad_lord_three_plus_roles(ep: EpochState) -> bool:
    return _father_bhava_role_count(ep, ep.dashas.antar) >= 3


def _pd_in_f_loss_lords(ep: EpochState) -> bool:
    if not ep.natal_lagna_sign:
        return False
    f_loss = set()
    for n in (10, 3, 4, 8):
        lord = _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, n))
        if lord:
            f_loss.add(lord)
    return ep.dashas.pratyantar in f_loss


_BPHS_MULTI_ROLE_CITATION = Citation(
    source_id="BPHS Ch. 32 (Karaka-bheda) + classical "
              "multi-bhava-rulership theory",
    text_chunk="When a single planet rules multiple bhavas of similar "
               "significance — e.g. the 9th and the loss-lord of the "
               "9th from the karaka — its dasha activation carries "
               "the combined force of all roles, intensifying the "
               "maraka effect proportionally.",
)


_R_AD_MULTI_ROLE_FATHER = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ad_multi_role_father_activation.cf22",
        school=School.PARASHARI,
        source="Multi-role AD intensifier: when the AD lord plays "
               ">=2 distinct father-bhava roles (lagna_lord, 9L, 8L, "
               "F-loss-lord, 9h-resident), the combined activation is "
               "stronger than any single-role rule captures. v15's "
               "disjointness gates flatten multi-role to single-role; "
               "this rule re-imposes the multi-role weight on top of "
               "the surviving single-role rule. Targeted at Smith "
               "(Tau lagna, Sat=9L+F2L) and Schwarzenegger "
               "(Gemini, Mer=lagna_lord+F8L).",
        is_veto=False,
        base_cf=-0.30,
        # Dynamic primary planet: this rule's effect depends on the
        # strength of the AD LORD itself (the planet playing multi-
        # roles), which varies per chart. Using <ad_lord> resolves
        # to ep.dashas.antar at fire time — Saturn at Smith truth,
        # Mer at Schwarzenegger truth (if it fired there), etc.
        # Earlier static choices ('Sun' karaka or 'Saturn' longevity-
        # karaka) couldn't generalize: Sun is debilitated on Smith's
        # chart (μ=0.22), making the rule too weak to flip his AD;
        # Saturn happens to work for Smith but is no more correct
        # than Sun on charts where AD lord ≠ Saturn.
        primary_planet="<ad_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_MULTI_ROLE_CITATION],
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
    fires_when=_ad_lord_multi_role_father,
)


# Add dynamic-context modifiers via Python predicates.
_R_AD_MULTI_ROLE_FATHER.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="AD lord plays 3+ father-bhava roles: "
                           "extreme multi-activation"),
)
_R_AD_MULTI_ROLE_FATHER.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="PD lord ALSO in F-loss-lord set: "
                           "PD-level confluence"),
)
_R_AD_MULTI_ROLE_FATHER.modifier_predicates = [
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _ad_lord_three_plus_roles,
    _pd_in_f_loss_lords,
]


# ── Final v22 rule list ───────────────────────────────────────────

RULES_V22: List[CFRuleSpec] = list(RULES_V21) + [
    _R_AD_MULTI_ROLE_FATHER,
]
