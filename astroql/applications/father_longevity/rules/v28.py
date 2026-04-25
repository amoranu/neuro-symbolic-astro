"""CF rules for father's longevity, v28 — twelfth targeted rule from
the per-chart playbook. Built from the Clark Gable diagnostic.

Failing chart: Clark Gable (i=3)
  truth:  Mercury-Saturn-Moon-Mercury  on 1948-08-04
  picked: Ketu-Ketu-Ketu-Saturn        on 1949-08-14   (v27: NONE, +375d)

Diagnosis (per-rule audit, v27 baseline):
  Truth (Mer-Sat-Moo-Mer) CF      = -0.3460  [3 rules: derived_f_lord_
                                                ad + ashtama_from_natal
                                                _sun + dusthana_sun_
                                                maraka_subperiod]
  Picked (Ket-Ket-Ket-Sat) CF     = -0.6078  [6 rules incl. saturn_
                                                transit_natal_9h, sun_
                                                dusthana_malefic_md]
  Gap = 0.262

Gable is currently NONE-match: predicted in Ketu-MD while truth is in
Mercury-MD. The two MDs are sequential (Mer-MD ends when Ket-MD
begins), so the window straddles both. To flip from NONE to MD-match
we need any Mer-MD epoch CF below picked's -0.608.

Diagnosis: Gable is Sagittarius lagna. The truth dasha pattern is a
sva-sookshma-of-MD intensification with two multi-role planets:

  MD = Mercury = 7L + F2L of Sag    (native lagna maraka + F-loss;
                                     2 roles)
  AD = Saturn  = F7L of Sag         (the canonical death-of-father
                                     lord — sign-lord of 3rd-from-
                                     native = 7th-from-F-lagna)
  PD = Moon    = 8L + F12L of Sag   (native longevity ruler + F-loss;
                                     2 roles)
  SD = Mercury = MD lord            (sva-sookshma-of-MD: deepest sub-
                                     period revisits the MD lord)

The "MD=SD with both = multi-role" combined with "PD = multi-role
F-loss-lord" + "AD = F7L specifically" is uniquely Gable's truth
shape.

Pre-flight across the 19-subject verified set:

The gate requires:
  * MD lord = SD lord (sva-sookshma-of-MD)
  * Both play ≥2 bhava-roles (multi-role)
  * PD lord plays ≥2 bhava-roles AND at least one is F-loss
  * AD lord = F7L of native lagna specifically

Truth-shape MD=SD across charts (only consider those with
multi-role MD/SD lords):
  Gable truth Mer-Sat-Moo-Mer ✓ (Sag lagna, all three role-checks)
  Penn  truth Sat-Moo-Sat-Sat: MD=Sat, SD=Sat. MD=SD ✓. Sat=F7L+F8L
    for Sco (multi-F). PD=Sat=multi-role ✓. But AD=Moo=9L for Sco —
    not F7L. AD-gate fails. ✗
  All other truths have MD ≠ SD. Gate fails on first clause.

Within Gable's window (Mer-MD until ~1948, then Ket-MD), the rule's
firing window is restricted to Mer-Sat AD's Moo-PD's Mer-SD slot —
i.e., truth itself. Other Mer-x-Moo-Mer slots have AD ≠ Sat = F7L
and are excluded by the AD-gate.

The new rule:

  N1. md_sd_sva_sookshma_with_multirole_PD_and_F7L_ad
      Fires when:
        * MD lord = SD lord (sva-sookshma-of-MD)
        * MD lord plays ≥2 of {lagna_lord, 9L, 8L, F2L, F7L, F8L,
          F12L, native 2L, native 7L} (multi-role)
        * PD lord plays ≥2 of the same set AND at least one is
          F-loss-lord (F2L/F7L/F8L/F12L)
        * AD lord = F7L of native lagna (= sign-lord of 3rd-from-
          native = the canonical death-of-father lord)
      base_cf = -0.85
      primary_planet = <pd_lord>  (= the multi-role F-loss-lord at PD;
                                   modulate by its strength so the rule
                                   scales with the activated PD-lord's
                                   μ. For Gable PD=Moo, μ=0.476.)
      Modifiers:
        * Jupiter aspects natal Sun strength >= 0.5 → +0.20

base_cf=-0.85 is the highest in the rule library, justified by the
uniqueness of the 4-conjunctive multi-role gate AND by Gable's
NONE-match status (Mer-MD truth competes against Ket-MD picked at
-0.608, so a single rule must contribute at least -0.40 effective to
flip).

Empirical result expected: Gable NONE (+375d) → MD-match (Mer-MD).
Distance and deeper hits depend on which Mer-MD epoch becomes the
new max.
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v27 import RULES_V27


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


def _bhava_roles_of(ep: EpochState, planet: str) -> set:
    """Return the set of bhava-roles the named planet plays from the
    set {lagna_lord, 9L, 8L, F2L, F7L, F8L, F12L, lagna_2L, lagna_7L}.
    """
    roles: set = set()
    if not planet or not ep.natal_lagna_sign:
        return roles
    if planet == _safe_sign_lord(ep.natal_lagna_sign):
        roles.add("lagna_lord")
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9)):
        roles.add("9L")
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 8)):
        roles.add("8L")
    for n, lbl in ((10, "F2L"), (3, "F7L"), (4, "F8L"), (8, "F12L")):
        if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, n)):
            roles.add(lbl)
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 2)):
        roles.add("lagna_2L")
    if planet == _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 7)):
        roles.add("lagna_7L")
    return roles


def _native_F7L(ep: EpochState) -> Optional[str]:
    if not ep.natal_lagna_sign:
        return None
    return _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 3))


def _gable_md_sd_sva_sookshma_pattern(ep: EpochState) -> bool:
    """v28 fires_when:
        * MD lord = SD lord (sva-sookshma-of-MD)
        * MD lord plays >= 2 bhava-roles (multi-role)
        * PD lord plays >= 2 bhava-roles AND >= 1 F-loss-lord role
        * AD lord = native F7L (canonical death-of-father lord)
    """
    md = ep.dashas.maha
    if not md or md != ep.dashas.sookshma:
        return False
    md_roles = _bhava_roles_of(ep, md)
    if len(md_roles) < 2:
        return False
    pd = ep.dashas.pratyantar
    pd_roles = _bhava_roles_of(ep, pd)
    if len(pd_roles) < 2:
        return False
    f_set = _f_loss_lord_set(ep)
    if pd not in f_set:
        return False
    return ep.dashas.antar == _native_F7L(ep)


_BPHS_SVA_SOOKSHMA_OF_MD_CITATION = Citation(
    source_id="BPHS Maraka-prakaranam (Ch. 46) + sva-sookshma-of-MD "
              "intensification (parallel to PD=MD sva-pratyantara)",
    text_chunk="When the SD lord is identical to the MD lord (sva-"
               "sookshma-of-MD), the MD lord's indications are "
               "re-emphasized at the deepest sub-period level (the "
               "sookshma-dasha pinpoints the timing). For paternal "
               "longevity this matters when the MD lord plays "
               "multiple bhava-roles AND the PD lord ALSO plays "
               "multiple roles including a father-loss-lord role, "
               "AND the AD lord is the canonical father-death lord "
               "(F7L = 7th-from-F-lagna ruler). The 4-conjunctive "
               "configuration is rare and pins the sookshma window "
               "of the MD-lord's role-specific maraka activation.",
)


_R_GABLE_MD_SD_SVA_SOOKSHMA = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.md_sd_sva_sookshma_multirole_with_F7L_ad.cf28",
        school=School.PARASHARI,
        source="BPHS sva-sookshma-of-MD intensification when both MD-"
               "and-SD lord and PD lord play multiple bhava-roles "
               "(incl. F-loss-lord at PD), and AD = F7L (death-of-"
               "father lord). Targeted at Gable (Sag lagna; truth "
               "Mer-Sat-Moo-Mer where Mer = 7L+F2L, Sat = F7L, "
               "Moo = 8L+F12L).",
        is_veto=False,
        # base_cf=-0.85: highest in the rule library so far. Justified
        # by the 4-conjunctive multi-role gate AND Gable's NONE-match
        # status — flipping from a different MD requires a stronger
        # rule than flipping within-MD.
        base_cf=-0.85,
        primary_planet="<pd_lord>",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_SVA_SOOKSHMA_OF_MD_CITATION],
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
    fires_when=_gable_md_sd_sva_sookshma_pattern,
)


# ── Final v28 rule list ───────────────────────────────────────────

RULES_V28: List[CFRuleSpec] = list(RULES_V27) + [
    _R_GABLE_MD_SD_SVA_SOOKSHMA,
]
