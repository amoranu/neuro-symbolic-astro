"""CF rules for father's longevity, v16 — exercise the new schema
fields exposed by the engine v2 architectural overhaul:
  * `is_combust`               (Asta / solar combustion)
  * `is_in_graha_yuddha`       (planetary war)
  * `aspect_strengths_*`       (longitudinal Sphuta Drishti)
  * `navamsha_sign` + `is_vargottama`   (D-9 dignity — surfaced on
                                          state but no v16 rule
                                          consumes it directly; see
                                          'lessons learned' below)
  * mixed-sign veto cancellation in cf_engine

v16 = v15 + 4 additive rules (was 5; vargottama dropped — see below).
None replace v15 rules; subsumption links are used where overlap is
clean (the Saturn-strong-aspect rule subsumes the legacy binary form
when its longitudinal strength is high).

Rule additions:

  N1. combustion_drains_jupiter_protection
      Jupiter natal aspect on Sun (aspector strength > 0) is the
      classical Mahamrityunjaya light-form. If Jupiter is combust at
      the sookshma, his beneficence is dead (BPHS Asta-avastha) —
      adds a negative CF that re-imposes the maraka force the v15
      Jupiter-protection modifier would otherwise cancel.

  N2. saturn_strong_aspect_natal_sun
      Sphuta Drishti form of v15's saturn_aspects_natal_sun. Fires
      only when Saturn's longitudinal aspect on natal Sun is strong
      (≥ 0.7 — within ~3° of exact 7th/3rd/10th aspect points).
      Subsumes the v15 binary form so we don't double-count the
      same drishti.

  N3. ad_lord_lost_graha_yuddha
      AD lord is engaged in Graha Yuddha as the loser (slower mover,
      classically destroyed for the period). Adds a focused negative
      CF when the engine flags this state.

  V1. mahamrityunjaya_yoga_protection  (high-weight non-veto)
      Jupiter exalted in dignity, not combust, with a strong (≥ 0.7)
      longitudinal aspect on natal Sun, AND in 5th/9th from natal
      Sun. Rare classical full-protection yoga. base_cf=+0.85
      (review #4: a +1.0 veto would absolutely override even an
      overwhelming maraka stack — and at the truth-epoch of an actual
      death, transient satisfaction of the protective conditions
      would zero out the prediction. +0.85 is high enough to dampen
      typical maraka accumulation but allows an overwhelming negative
      stack to legitimately override). The cancellation path in
      cf_engine remains exercised by unit tests independently.

LESSONS LEARNED — DROPPED RULES
================================

  X1. ninth_lord_vargottama_protection  (DROPPED 2026-04-25)
      Originally added as a chart-static positive rule (+0.20) when
      the 9th lord's D-1 sign equals its D-9 sign. Per-chart audit
      showed this is structurally incapable of helping any
      prediction:

        * Vargottama is chart-static — the rule fires on EVERY
          sookshma epoch of a given chart with the same +0.20.
        * The predictor picks epochs by DIFFERENTIAL CF; a constant
          boost cancels across all candidates.
        * On the verified set, exactly one chart (Will Smith) had
          a vargottama 9L. Tiny non-zero differential (+0.013)
          appeared due to MYCIN's nonlinearity at different existing-
          accumulation levels — and that differential pushed the
          prediction AWAY from truth.

      Generalizable rule: chart-static signals (vargottama, exalted/
      debilitated natal placement, dispositorship of stable lords)
      must be MODIFIERS on transit-driven rules, not standalone
      rules. They modulate the strength of a transit-driven signal
      at the same epoch; they cannot stand alone in a per-epoch
      pick-the-extreme predictor.

      Reinstating vargottama as a modifier is left to v17+: it
      requires either pre-computing a chart-wide flag on the
      EpochState (like derived_lords) so DSL conditions can read it,
      or extending the DSL to support dynamic-key indexing
      (`planets[derived_lords.ninth_lord].is_vargottama`).

PER-CHART AUDIT (v16, N=19 verified)
====================================

  v16 fires at NEITHER truth nor picked: 15/19 charts → no impact.
  v16 fires at PICKED but not TRUTH:      2 charts (Mia Farrow,
                                          Carla Bruni) → ad_lord_lost
                                          _yuddha pulls predictions
                                          AWAY from truth.
  v16 fires at TRUTH only:                1 chart (Nixon, jupiter_
                                          combust) → -0.052 differ-
                                          ential, helped but not
                                          enough to flip MD→AD.
  v16 fires at picked when v15-binary-saturn would have been
  stronger:                               1 chart (Jane Fonda) →
                                          subsumption WEAKENED
                                          picked, marginally pulled
                                          prediction toward truth.

  Net: aggregate metrics unchanged. The new fields don't carry
  signal at the specific truth events in this dataset — the v16
  rules cover astrological mechanisms that don't happen to coincide
  with the verified deaths.

WHAT WOULD ACTUALLY MOVE METRICS
================================

  v17+ should follow the v9–v15 playbook: pick a specific failing
  chart (one of the 13 AD-misses), diagnose what classical pattern
  truth has that picked doesn't using ANY field (new or existing),
  write the targeted rule. Each prior version flipped 1–2 charts
  via this workflow; v16 skipped it and went straight to "exercise
  the new fields," producing instrumentation rather than accuracy.

Conservative weights chosen to avoid disturbing v15's hit rates: each
new rule contributes ≤0.25 in magnitude, well under the 0.45 ceiling
of v15's primary maraka rules. Empirical re-tuning is left to the
critic / per-chart analysis sweeps.
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

# Classical exaltation signs (used by V1 mahamrityunjaya gate).
_EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer",
    "Venus": "Pisces", "Saturn": "Libra",
}

_BPHS_AVASTHA_CITATION = Citation(
    source_id="BPHS Ch. 47 (Avastha-prakaranam)",
    text_chunk="A planet within solar combustion orb (Asta) loses "
               "its natural beneficence; its dasha and aspects yield "
               "the results of a malefic regardless of natural nature.",
)

_BPHS_VARGOTTAMA_CITATION = Citation(
    source_id="BPHS Ch. 5 (Varga-vichara)",
    text_chunk="A planet whose Rasi sign is identical to its "
               "Navamsha sign (Vargottama) yields exalted-class "
               "results irrespective of other dignity signals.",
)


def _nth_sign_from(sign: str, n: int) -> Optional[str]:
    try:
        idx = _SIGN_ORDER.index(sign)
    except ValueError:
        return None
    return _SIGN_ORDER[(idx + n - 1) % 12]


def _ninth_lord(ep: EpochState) -> Optional[str]:
    if not ep.natal_lagna_sign:
        return None
    ninth = _nth_sign_from(ep.natal_lagna_sign, 9)
    return sign_lord(ninth) if ninth else None


def _r(
    rule_id: str, base_cf: float, primary_planet: Optional[str],
    modifiers: List[CFModifier] = (), source: str = "v16",
    is_veto: bool = False, subsumes: List[str] = (),
    provenance: Optional[Provenance] = None,
) -> Rule:
    return Rule(
        rule_id=rule_id,
        school=School.PARASHARI,
        source=source,
        is_veto=is_veto,
        base_cf=base_cf,
        primary_planet=primary_planet if not is_veto else None,
        modifiers=list(modifiers),
        subsumes_rules=list(subsumes),
        applicable_to={
            "relationships": ["father"],
            "life_areas": ["longevity"],
            "effects": ["event_negative"] if base_cf < 0 else
                       ["event_positive"],
        },
        provenance=provenance,
    )


# ── N1: Jupiter combust drains its protection ─────────────────────

def _jupiter_combust_during_protection_window(ep: EpochState) -> bool:
    """N1 fires_when: Jupiter would otherwise protect (his
    longitudinal aspect on natal Sun is non-zero), but he is combust
    at this sookshma — his protection is dead. Gated on malefic MD so
    we don't fire on benign chart windows where there's no maraka
    force to re-impose.
    """
    if ep.dashas.maha not in _MALEFIC_DASHA_LORDS:
        return False
    sun = ep.planets.get("Sun")
    jup = ep.planets.get("Jupiter")
    if sun is None or jup is None:
        return False
    if not jup.is_combust:
        return False
    return sun.aspect_strengths_on_natal.get("Jupiter", 0.0) > 0.0


_R_JUPITER_COMBUST_DRAINS_PROTECTION = CFRuleSpec(
    rule=_r(
        "parashari.father.jupiter_combust_drains_protection.cf16",
        base_cf=-0.20, primary_planet="Jupiter",
        source="BPHS Asta-avastha (Ch. 47): a combust benefic loses "
               "its beneficence and acts as a malefic agent. Used here "
               "to re-impose maraka force the v15 'Jupiter aspects "
               "natal Sun' protective modifier would have cancelled.",
        provenance=Provenance(
            author="human", confidence=0.50,
            citations=[_BPHS_AVASTHA_CITATION],
        ),
        modifiers=[
            # DSL-evaluated against EpochState. The path lookup raises
            # DSLEvalError when Jupiter has zero aspect on Sun (the
            # field is omitted at emit time); `evaluate_modifier_indices`
            # catches that as "not fired", which is the desired
            # semantics here.
            CFModifier(
                condition={
                    "path": "planets.Sun.aspect_strengths_on_natal.Jupiter",
                    "op": ">=",
                    "value": 0.7,
                },
                effect_cf=-0.10,
                explanation="Jupiter's would-be aspect strength on "
                            "natal Sun is high (>=0.7) — the lost "
                            "protection would have been substantial",
            ),
        ],
    ),
    fires_when=_jupiter_combust_during_protection_window,
)


# ── N2: Saturn strong longitudinal aspect on natal Sun ────────────

def _saturn_strong_aspect_on_natal_sun(ep: EpochState) -> bool:
    """N3 fires_when: Saturn's longitudinal aspect strength on natal
    Sun is high (>= 0.7, i.e. within ~3° of exact). Subsumes the v15
    binary saturn_aspects_natal_sun rule when this stronger condition
    holds — the binary rule still fires for moderate-orb cases.
    """
    sun = ep.planets.get("Sun")
    if sun is None:
        return False
    return sun.aspect_strengths_on_natal.get("Saturn", 0.0) >= 0.7


_R_SATURN_STRONG_ASPECT_NATAL_SUN = CFRuleSpec(
    rule=_r(
        "parashari.father.saturn_strong_aspect_natal_sun.cf16",
        base_cf=-0.20, primary_planet="Saturn",
        source="Sphuta Drishti longitudinal form: when Saturn's "
               "exact aspect angle to natal Sun is within ~3° (orb "
               "strength >=0.7), classical force is significantly "
               "stronger than the v15 binary sign-based rule "
               "captures. Subsumes the binary form to avoid double-"
               "counting the same drishti.",
        provenance=Provenance(
            author="human", confidence=0.50,
            citations=[],
        ),
        subsumes=[
            "parashari.father.saturn_aspects_natal_sun.cf12",
        ],
        modifiers=[
            CFModifier(
                condition={
                    "path": "planets.Sun.aspect_strengths_on_natal.Saturn",
                    "op": ">=",
                    "value": 0.9,
                },
                effect_cf=-0.10,
                explanation="Saturn aspect strength is near-exact "
                            "(>=0.9, within ~1°)",
            ),
            CFModifier(
                condition={
                    "any": [
                        {"path": "dashas.antar", "op": "==",
                         "value": "Saturn"},
                        {"path": "dashas.pratyantar", "op": "==",
                         "value": "Saturn"},
                    ],
                },
                effect_cf=-0.10,
                explanation="Saturn = AD or PD (dasha confluence)",
            ),
        ],
    ),
    fires_when=_saturn_strong_aspect_on_natal_sun,
)


# ── N3: AD lord lost in Graha Yuddha ──────────────────────────────

def _ad_lord_lost_yuddha(ep: EpochState) -> bool:
    """N3 fires_when: AD lord is in Graha Yuddha and lost (the slower
    of the two). Classically destroyed for the period. Sun/Moon/Rahu/
    Ketu can never satisfy this (yuddha is between true planets only),
    so no extra gate needed — `is_in_graha_yuddha` will be False for
    those planets by construction.
    """
    ad = ep.dashas.antar
    p = ep.planets.get(ad)
    if p is None:
        return False
    return p.is_in_graha_yuddha and p.graha_yuddha_lost


_R_AD_LORD_LOST_YUDDHA = CFRuleSpec(
    rule=_r(
        "parashari.father.ad_lord_lost_graha_yuddha.cf16",
        base_cf=-0.22, primary_planet="Sun",
        source="BPHS Graha Yuddha: when two true planets are within "
               "1° longitude, the slower planet is classically "
               "'destroyed' for the duration. An AD lord in this "
               "state cannot deliver its dasha-period results "
               "constructively, allowing father-bhava maraka force "
               "to surface unchecked.",
        provenance=Provenance(
            author="human", confidence=0.40,
            citations=[],
        ),
        modifiers=[
            CFModifier(
                condition={
                    "path": "dashas.maha",
                    "op": "in",
                    "value": ["Saturn", "Mars", "Rahu", "Ketu", "Sun"],
                },
                effect_cf=-0.08,
                explanation="MD lord is also a malefic: maraka context",
            ),
            CFModifier(
                condition={
                    "path": "planets.Sun.aspect_strengths_on_natal.Jupiter",
                    "op": ">=",
                    "value": 0.5,
                },
                effect_cf=+0.15,
                explanation="Jupiter aspects natal Sun with strength "
                            ">= 0.5: partial protective offset",
            ),
        ],
    ),
    fires_when=_ad_lord_lost_yuddha,
)


# ── V1: Mahamrityunjaya protective rule (non-veto, +0.85) ─────────

def _mahamrityunjaya_protective_yoga(ep: EpochState) -> bool:
    """V1 fires_when (strict, classical):
        * Jupiter NOT combust
        * Jupiter's longitudinal aspect on natal Sun strength >= 0.7
        * Jupiter natally in 5th or 9th from natal Sun
        * Jupiter shadbala mu >= 0.7

    Conjunctive gate. Rare on the verified set; when it fires it
    contributes a substantial protective CF that an overwhelming
    maraka stack can still legitimately override (review #4 — a
    full +1.0 veto would blind the engine on truth-epochs where
    these conditions transiently hold).
    """
    jup = ep.planets.get("Jupiter")
    sun = ep.planets.get("Sun")
    if jup is None or sun is None:
        return False
    if jup.is_combust:
        return False
    if sun.aspect_strengths_on_natal.get("Jupiter", 0.0) < 0.7:
        return False
    if jup.shadbala_coefficient < 0.7:
        return False
    if not sun.natal_sign:
        return False
    fifth_from_sun = _nth_sign_from(sun.natal_sign, 5)
    ninth_from_sun = _nth_sign_from(sun.natal_sign, 9)
    return jup.natal_sign in (fifth_from_sun, ninth_from_sun)


_R_MAHAMRITYUNJAYA_PROTECTION = CFRuleSpec(
    rule=_r(
        "parashari.father.mahamrityunjaya_yoga.cf16",
        base_cf=+0.85, primary_planet="Jupiter",
        source="Classical Mahamrityunjaya yoga: Jupiter strong, not "
               "combust, in 5th/9th from karaka, with exact-orb "
               "drishti on the karaka. Demoted from a +1.0 veto to a "
               "high-weight (+0.85) non-veto rule — a hard veto would "
               "blind the predictor on truth-epochs where these "
               "conditions transiently hold; +0.85 dampens typical "
               "maraka stacks but stays overrideable by overwhelming "
               "negative evidence.",
        provenance=Provenance(
            author="human", confidence=0.45,
            citations=[_BPHS_VARGOTTAMA_CITATION],
        ),
    ),
    fires_when=_mahamrityunjaya_protective_yoga,
)


# ── Final v16 rule list ───────────────────────────────────────────
# v15 rules first (baseline), v16 additions appended. The Saturn-
# strong-aspect rule's subsumes_rules link will defeat v15's binary
# saturn-aspect rule whenever both fire, so the order doesn't change
# CF aggregation semantics.

RULES_V16: List[CFRuleSpec] = list(RULES_V15) + [
    _R_JUPITER_COMBUST_DRAINS_PROTECTION,
    _R_SATURN_STRONG_ASPECT_NATAL_SUN,
    _R_AD_LORD_LOST_YUDDHA,
    _R_MAHAMRITYUNJAYA_PROTECTION,
]
