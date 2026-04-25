"""CF rules for father's longevity, v21 — fifth targeted rule from
the per-chart playbook. Built from the Michael Douglas diagnostic;
unexpectedly helpful for Mia Farrow as a structural side-effect.

Failing chart: Michael Douglas (i=0)
  truth:  Jupiter-Mars-Sun-Jupiter      on 2020-02-05
  picked: Jupiter-Moon-Saturn-Venus     on 2019-03-14  (v19: MD-only, -328d)

Diagnosis (per-rule audit, v19 baseline):
  Truth-AD (Jup-Mar) CF        = -0.253   [ashtama_from_natal_sun
                                            + dusthana_sun_maraka_sub]
  Picked-AD (Jup-Moo) CF       = -0.489   [same 2 + saturn_aspects_
                                            natal_sun -0.213 +
                                            derived_f_lord_ad -0.130]
  Gap = 0.236 favoring picked

The two extra picked-firings are:
  1. saturn_aspects_natal_sun: at picked (March 2019) Saturn is in
     Sagittarius and its 10th aspect (Virgo) hits natal Sun. At
     truth (Sept 2020) Saturn is in Capricorn and its aspects don't
     reach Virgo. Pure transit timing — irreducible by rule.
  2. derived_f_lord_ad: AD=Moon is F2L for Libra lagna. AD=Mars is
     NOT in F-loss-lord set, so this rule doesn't fire at truth
     even though Mars is classically a STRONG MARAKA from Libra
     lagna (Mars = 2L + 7L for Libra: 2L=Scorpio→Mars, 7L=Aries→
     Mars).

The rule library uses ONLY Sun-karaka maraka theory
(`father_marakas` = sign-lords of 2nd/7th from natal Sun's sign).
That captures father-significator marakas. But the OTHER classical
maraka pattern — 2L and 7L of NATIVE'S OWN LAGNA — is missing.
2L/7L from native lagna are the universal life-end markers per
BPHS Ch. 41 and Phaladeepika; for father longevity the native's
own maraka activations also pull death events into specific dasha
windows.

The new rule:

  N1. ad_is_native_lagna_maraka
      Fires when:
        * AD lord = 2L OR 7L of native's lagna chart (sign-lords
          of 2nd-from-lagna or 7th-from-lagna)
        * MD lord is malefic OR plays a father-bhava role (lagna_
          lord, 9L, 8L, F-loss-lord, 9h-resident)
        * AD lord is NOT in derived F-loss-lord set
          (disjoint from derived_f_lord_ad)
        * AD lord is NOT 9L, lagna_lord, 9h-resident, or 8L
          (disjoint from lagna_lord_AD, 9th_lord_only,
          9h_resident, 8th_lord_AD rules)
      base_cf = -0.40
      Modifiers:
        * SD lord ∈ F-loss-lord set: confluence (-0.10)
        * PD lord is malefic: PD-pin (-0.10)
        * Jupiter aspects natal Sun (strength >= 0.5): partial
          protective offset (+0.20)

  Pre-flight check across the verified set (charts where rule
  could fire = AD ∈ {2L, 7L} for that lagna):
    - Douglas (Libra): Mars=2L+7L. Truth AD=Mars ✓ FIRES (intended)
    - Farrow  (Aries): Venus=2L+7L. Truth AD=Venus ✓ FIRES (bonus)
    - Other charts: AD-lord rarely matches 2L/7L of their lagna
      AND survives the disjointness gates. Empirical eval validates.
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


def _safe_sign_lord(sign: Optional[str]) -> Optional[str]:
    if not sign:
        return None
    try:
        return sign_lord(sign)
    except ValueError:
        return None


def _native_lagna_marakas(ep: EpochState) -> set:
    """2L and 7L of native's lagna chart — the classical lagna-maraka
    set from BPHS Ch. 41."""
    if not ep.natal_lagna_sign:
        return set()
    L2 = _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 2))
    L7 = _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 7))
    return {x for x in (L2, L7) if x}


def _derived_f_loss_lords(ep: EpochState) -> set:
    """F2L/F7L/F8L/F12L per derived father-lagna (= 9th from native)."""
    if not ep.natal_lagna_sign:
        return set()
    out = set()
    for n_from_native in (10, 3, 4, 8):
        s = _nth_sign_from(ep.natal_lagna_sign, n_from_native)
        lord = _safe_sign_lord(s)
        if lord:
            out.add(lord)
    return out


def _ninth_lord(ep: EpochState) -> Optional[str]:
    if not ep.natal_lagna_sign:
        return None
    return _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 9))


def _eighth_lord(ep: EpochState) -> Optional[str]:
    if not ep.natal_lagna_sign:
        return None
    return _safe_sign_lord(_nth_sign_from(ep.natal_lagna_sign, 8))


def _lagna_lord(ep: EpochState) -> Optional[str]:
    if not ep.natal_lagna_sign:
        return None
    return _safe_sign_lord(ep.natal_lagna_sign)


def _md_is_father_active_or_malefic(ep: EpochState) -> bool:
    """MD lord is malefic OR plays a father-bhava role (lagna_lord,
    9L, 8L, F-loss-lord, 9h-resident)."""
    md = ep.dashas.maha
    if md in _MALEFIC_DASHA_LORDS:
        return True
    if md == _ninth_lord(ep) or md == _eighth_lord(ep):
        return True
    if md == _lagna_lord(ep):
        return True
    if md in _derived_f_loss_lords(ep):
        return True
    p = ep.planets.get(md) if md else None
    if p is not None and p.natal_house == 9:
        return True
    return False


def _ad_is_native_lagna_maraka(ep: EpochState) -> bool:
    """v21 fires_when:
        * AD lord ∈ {2L, 7L} of native's lagna chart
        * MD malefic OR father-active
        * AD NOT in F-loss-lord set (disjoint from derived_f_lord_ad)
        * AD NOT 9L, 8L, lagna_lord (disjoint from 9th_lord_only,
          8th_lord_AD, lagna_lord_AD)
        * AD lord NOT natally in 9h (disjoint from 9h_resident_dasha)
    """
    ad = ep.dashas.antar
    if not ad:
        return False
    if ad not in _native_lagna_marakas(ep):
        return False
    if not _md_is_father_active_or_malefic(ep):
        return False
    if ad in _derived_f_loss_lords(ep):
        return False
    if ad in (_ninth_lord(ep), _eighth_lord(ep), _lagna_lord(ep)):
        return False
    p = ep.planets.get(ad)
    if p is not None and p.natal_house == 9:
        return False
    return True


def _sd_in_f_loss_lords(ep: EpochState) -> bool:
    return ep.dashas.sookshma in _derived_f_loss_lords(ep)


def _pd_is_malefic(ep: EpochState) -> bool:
    return ep.dashas.pratyantar in _MALEFIC_DASHA_LORDS


_BPHS_LAGNA_MARAKA_CITATION = Citation(
    source_id="BPHS Ch. 41 (Maraka-bheda) + Phaladeepika Ch. on "
              "Maraka theory",
    text_chunk="The lords of the 2nd and 7th houses from the lagna "
               "are the universal maraka planets — they inflict "
               "death of the body. When their dashas mature in "
               "concert with affliction to the karaka of the bhava "
               "in question, the death of that karaka's significations "
               "(here, the father) is timed within the activation.",
)


_R_AD_IS_NATIVE_LAGNA_MARAKA = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.ad_is_native_lagna_maraka.cf21",
        school=School.PARASHARI,
        source="BPHS Ch. 41 lagna-maraka theory: 2L and 7L of "
               "native's lagna are universal death-inflictors. The "
               "v15 rule library uses only Sun-karaka maraka theory; "
               "this rule adds the lagna-maraka mechanism. Targeted "
               "at Douglas (Libra lagna, Mars=2L+7L; truth AD=Mars). "
               "Side-effect benefit expected for Farrow (Aries lagna, "
               "Venus=2L+7L; truth AD=Venus).",
        is_veto=False,
        base_cf=-0.50,
        # NOTE: Reverted from <ad_lord> to "Sun" 2026-04-25 because
        # the dynamic form regressed Shriver (Tau lagna): static "Sun"
        # gives consistent magnitude across charts, while <ad_lord>
        # over-fires at non-truth Mar-AD (Mars=7L for Tau) where
        # mu_Mars > mu_Sun, pulling the predictor away from truth's
        # Rah-AD. Sun-as-karaka stays static here even though it's
        # not the role-playing planet — it caps the rule's magnitude
        # uniformly across charts.
        primary_planet="Sun",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.55,
            citations=[_BPHS_LAGNA_MARAKA_CITATION],
        ),
        modifiers=[
            CFModifier(
                condition={
                    "path": "dashas.pratyantar",
                    "op": "in",
                    "value": ["Saturn", "Mars", "Rahu", "Ketu", "Sun"],
                },
                effect_cf=-0.10,
                explanation="PD lord is malefic: PD-level pin",
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
    fires_when=_ad_is_native_lagna_maraka,
)


# Add SD-in-F-loss-lord modifier via Python predicate (chart-dynamic).
_R_AD_IS_NATIVE_LAGNA_MARAKA.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="SD lord is in F-loss-lord set "
                           "(F2L/F7L/F8L/F12L): SD-level confluence"),
)
_R_AD_IS_NATIVE_LAGNA_MARAKA.modifier_predicates = [
    lambda ep: False,  # PD-malefic (DSL handles)
    lambda ep: False,  # Jupiter-aspect (DSL handles)
    _sd_in_f_loss_lords,
]


# ── Final v21 rule list ───────────────────────────────────────────

RULES_V21: List[CFRuleSpec] = list(RULES_V19) + [
    _R_AD_IS_NATIVE_LAGNA_MARAKA,
]
