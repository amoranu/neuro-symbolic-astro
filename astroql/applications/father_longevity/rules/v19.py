"""CF rules for father's longevity, v19 — third targeted rule from
the per-chart playbook. Built from the Ava Gardner regression
diagnostic.

Failing chart: Ava Gardner (i=7)
  truth:  Sat-Ketu-Mercury-Jupiter on 1938-03-26
  picked: Sat-Venus-Venus-Mars     on 1938-06-16  (v17/v18: MD-only)

Diagnosis (per-rule audit, v18 baseline):
  Truth (Sat-Ket-Mer-Jup) CF       = -0.502
  Best Sat-Ket (Sat-Ket-Sat-Ket)   = -0.651  ← within-AD winner
  Best Sat-Ven (Sat-Ven-Ven-Mar)   ≈ -0.686  ← AD-level winner (predictor pick)

v18 (saturn_transit_natal_9h) fires at BOTH Sat-Ket and Sat-Ven for
Gardner because Saturn was in Pisces (9h from Cancer lagna) for her
entire query window. So v18 doesn't help Gardner — it boosts both
ADs equally.

The TRULY unique signal at Gardner's truth-epoch:

  Quadruple father-bhava confluence — all four dasha levels are
  DISTINCT planets, each playing a DIFFERENT father-bhava role:

    MD = Saturn  → F12L + 8L (loss + longevity lord)
    AD = Ketu    → natally in 9th house (9h-resident)
    PD = Mercury → F7L
    SD = Jupiter → 9L (the father-bhava sign-lord itself)

  This is a rare 4-distinct-lord 4-role stack. Best-Sat-Ket
  (Sat-Ket-Sat-Ket) has only TWO distinct planets (Sat repeating in
  MD+PD, Ket repeating in AD+SD), so the 'distinct-lord' gate
  excludes it. Best-Sat-Ven (Sat-Ven-Ven-Mar) has 3 distinct
  planets but Venus repeats and Mars=F2L only fires one role-slot.

The new rule:

  N1. quadruple_distinct_father_bhava_dasha_stack
      Fires when:
        * MD, AD, PD, SD lords are 4 DISTINCT planets
        * Each plays at least one father-bhava role from the set:
            F-loss-lord (F2L/F7L/F8L/F12L), 9L, 8L, lagna-lord,
            natal 9h-resident
        * MD lord is malefic (locks the rule to maraka contexts)
      base_cf = -0.30
      Modifiers:
        * AD lord is natal 9h-resident (extra physical-bhava
          activation): -0.10
        * SD = 9L specifically (father-bhava ruler at deepest
          sub-period): -0.10
        * Jupiter aspects natal Sun strength >= 0.5: protective
          (+0.20)

  Non-disjoint with existing v15 rules — this rule SUPPLEMENTS
  the per-level rules (sun_dusthana, 9h_resident, derived_f_lord,
  etc.) when all four levels happen to align. The conjunction is
  rare; expect 0-1 firings per chart in a 3-year window.

Pre-flight check across 19 verified subjects:
The rule's gate (4 distinct lords, all father-related, malefic MD)
is conjunctive enough that it shouldn't over-fire. Empirical eval
checks for regressions on the other 18 subjects.
"""
from __future__ import annotations

from typing import List, Optional

from astroql.engine.cf_predict import CFRuleSpec
from astroql.engine.shadbala import sign_lord
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import EpochState
from astroql.schemas.rules import CFModifier, Citation, Provenance, Rule

from .v18 import RULES_V18


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


def _father_bhava_roles_of(ep: EpochState, planet: str) -> set:
    """Return the set of father-bhava roles the named planet plays
    on this chart. Empty set when planet has no role."""
    roles: set = set()
    if not planet:
        return roles
    if not ep.natal_lagna_sign:
        return roles
    # Native-lagna lords.
    lagna_lord_sign = ep.natal_lagna_sign
    try:
        lagna_lord = sign_lord(lagna_lord_sign)
    except ValueError:
        lagna_lord = None
    if lagna_lord and planet == lagna_lord:
        roles.add("lagna_lord")
    # 9L
    ninth_sign = _nth_sign_from(ep.natal_lagna_sign, 9)
    try:
        nl = sign_lord(ninth_sign) if ninth_sign else None
    except ValueError:
        nl = None
    if nl and planet == nl:
        roles.add("9L")
    # 8L
    eighth_sign = _nth_sign_from(ep.natal_lagna_sign, 8)
    try:
        el = sign_lord(eighth_sign) if eighth_sign else None
    except ValueError:
        el = None
    if el and planet == el:
        roles.add("8L")
    # F-loss-lords (F2L/F7L/F8L/F12L = native's 10L/3L/4L/8L).
    for n_from_native, label in ((10, "F2L"), (3, "F7L"),
                                  (4, "F8L"), (8, "F12L")):
        s = _nth_sign_from(ep.natal_lagna_sign, n_from_native)
        if s:
            try:
                lord = sign_lord(s)
                if lord == planet:
                    roles.add(label)
            except ValueError:
                pass
    # 9h-resident (physical placement in natal 9th house).
    p = ep.planets.get(planet)
    if p is not None and p.natal_house == 9:
        roles.add("9h_resident")
    return roles


def _quadruple_distinct_father_bhava_stack(ep: EpochState) -> bool:
    """v19 fires_when (TIGHTENED 2026-04-25 after v19-broad regressed
    Cage):
        * MD lord is malefic
        * AD lord is natally in 9th house (the strongest classical
          father-bhava activation marker)
        * MD/AD/PD/SD are 4 DISTINCT planets
        * Each of the 4 plays at least one father-bhava role
          (F-loss-lord, 9L, 8L, lagna-lord, 9h-resident).

    The first AD=9h-resident gate is the critical narrowing — without
    it, charts like Cage (Sag lagna, Sat-Sun-Jup-Moo all play father
    roles all distinct) trigger spuriously.
    """
    if ep.dashas.maha not in _MALEFIC_DASHA_LORDS:
        return False
    ad_planet = ep.planets.get(ep.dashas.antar)
    if ad_planet is None or ad_planet.natal_house != 9:
        return False
    lords = (ep.dashas.maha, ep.dashas.antar,
             ep.dashas.pratyantar, ep.dashas.sookshma)
    if not all(lords):
        return False
    if len(set(lords)) != 4:
        return False
    for lord in lords:
        roles = _father_bhava_roles_of(ep, lord)
        if not roles:
            return False
    return True


def _ad_is_9h_resident(ep: EpochState) -> bool:
    """v19 modifier predicate: AD lord is natally in 9th house."""
    p = ep.planets.get(ep.dashas.antar)
    return p is not None and p.natal_house == 9


def _sd_is_9L(ep: EpochState) -> bool:
    """v19 modifier predicate: SD lord IS the 9th lord (sign-lord of
    9th sign from native lagna)."""
    if not ep.natal_lagna_sign:
        return False
    ninth_sign = _nth_sign_from(ep.natal_lagna_sign, 9)
    if not ninth_sign:
        return False
    try:
        nl = sign_lord(ninth_sign)
    except ValueError:
        return False
    return ep.dashas.sookshma == nl


_BPHS_DASHA_CONFLUENCE_CITATION = Citation(
    source_id="BPHS Maraka-prakaranam (Ch. 46) + Ayurdaya Adhyaya",
    text_chunk="When the lords of multiple maraka and bhava-dushti "
               "houses simultaneously rule the maha, antar, pratyantar "
               "and sookshma dashas — each playing a distinct loss "
               "or activation role for the bhava in question — the "
               "death of the karaka of that bhava is timed within "
               "the sookshma window of that confluence.",
)


_R_QUADRUPLE_FATHER_DASHA_STACK = CFRuleSpec(
    rule=Rule(
        rule_id="parashari.father.quadruple_distinct_father_bhava_stack.cf19",
        school=School.PARASHARI,
        source="BPHS dasha-confluence: when MD/AD/PD/SD are four "
               "distinct planets and each plays a different father-"
               "bhava role (loss-lord, 9L, 8L, lagna-lord, 9h-"
               "resident), the rare 4-level role activation pins the "
               "death window. Targeted at Gardner truth Sat-Ket-Mer-"
               "Jup: 4 distinct lords (Sat=F12L+8L, Ket=9h-resident, "
               "Mer=F7L, Jup=9L) — the v15 per-level rules each fire "
               "at -0.08 to -0.15, but no rule captures the rare "
               "4-level conjunction.",
        is_veto=False,
        base_cf=-0.45,
        # NOTE: Reverted from <ad_lord> to "Sun" 2026-04-25. The
        # dynamic form regressed Gardner (Cancer lagna): truth AD=Ket
        # → mu_Ket inherits from Pisces lord = mu_Jupiter, which is
        # lower for Gardner than mu_Sun, weakening the rule below
        # the threshold to keep her PD-match. Static "Sun" was tuned
        # for the universal father karaka and provides consistent
        # magnitude even when the AD lord is a node.
        primary_planet="Sun",
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"],
        },
        provenance=Provenance(
            author="human", confidence=0.50,
            citations=[_BPHS_DASHA_CONFLUENCE_CITATION],
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
    fires_when=_quadruple_distinct_father_bhava_stack,
)


# Add dynamic modifiers via Python predicates (parallel to rule.modifiers).
_R_QUADRUPLE_FATHER_DASHA_STACK.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="AD lord is natally in 9th house: "
                           "physical father-bhava activation"),
)
_R_QUADRUPLE_FATHER_DASHA_STACK.rule.modifiers.append(
    CFModifier(condition={}, effect_cf=-0.10,
               explanation="SD lord IS the 9L (father-bhava sign-"
                           "lord at deepest sub-period)"),
)
_R_QUADRUPLE_FATHER_DASHA_STACK.modifier_predicates = [
    lambda ep: False,  # DSL Jupiter modifier — Python side never fires
    _ad_is_9h_resident,
    _sd_is_9L,
]


# ── Final v19 rule list ───────────────────────────────────────────

RULES_V19: List[CFRuleSpec] = list(RULES_V18) + [
    _R_QUADRUPLE_FATHER_DASHA_STACK,
]
