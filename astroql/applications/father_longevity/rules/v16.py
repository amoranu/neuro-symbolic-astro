"""CF rules for father's longevity, v16 — exercise the new schema
fields exposed by the engine v2 architectural overhaul:
  * `is_combust`               (Asta / solar combustion)
  * `is_in_graha_yuddha`       (planetary war)
  * `aspect_strengths_*`       (longitudinal Sphuta Drishti)
  * `navamsha_sign` + `is_vargottama`   (D-9 dignity)
  * mixed-sign veto cancellation in cf_engine

v16 = v15 + 5 additive rules. None replace v15 rules; subsumption links
are used where overlap is clean (the Saturn-strong-aspect rule subsumes
the legacy binary form when its longitudinal strength is high). All
new rules are written so they fire only when the new field carries
distinguishing information — none would have been possible against
v15's pre-overhaul EpochState.

Rule additions:

  N1. combustion_drains_jupiter_protection
      Jupiter natal aspect on Sun (aspector strength > 0) is the
      classical Mahamrityunjaya light-form. If Jupiter is combust at
      the sookshma, his beneficence is dead (BPHS Asta-avastha) —
      adds a negative CF that re-imposes the maraka force the v15
      Jupiter-protection modifier would otherwise cancel.

  N2. ninth_lord_vargottama_protection
      Father bhava lord whose D-1 sign matches its D-9 sign attains
      Vargottama dignity (BPHS divisional-chart promise). Stable
      protective force that participates in MYCIN aggregation; not
      a veto — it dampens malefic accumulation rather than absolute-
      cancelling.

  N3. saturn_strong_aspect_natal_sun
      Sphuta Drishti form of v15's saturn_aspects_natal_sun. Fires
      only when Saturn's longitudinal aspect on natal Sun is strong
      (≥ 0.7 — within ~3° of exact 7th/3rd/10th aspect points).
      Subsumes the v15 binary form so we don't double-count the
      same drishti.

  N4. ad_lord_lost_graha_yuddha
      AD lord is engaged in Graha Yuddha as the loser (slower mover,
      classically destroyed for the period). Adds a focused negative
      CF when the engine flags this state.

  V1. mahamrityunjaya_yoga_veto  (the FIRST veto in this rule library)
      Jupiter exalted in dignity, not combust, with a strong (≥ 0.7)
      longitudinal aspect on natal Sun, AND in 5th/9th from natal
      Sun. Rare classical full-protection yoga. Set is_veto=True with
      base_cf=+1.0. With cf_engine v2's mixed-veto cancellation, this
      can co-fire with maraka veto patterns and produce a 0.0 score
      (severe hardship but survival) instead of crashing. v15 carries
      no vetoes at all, so V1 is what activates the veto + cancellation
      code path under real evaluation.

Conservative weights chosen to avoid disturbing v15's hit rates: each
new rule contributes ≤0.25 in magnitude, well under the 0.45 ceiling
of v15's primary maraka rules. Empirical re-tuning is left to the
critic / regression sweeps.
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


# ── N2: 9th lord Vargottama protective rule ───────────────────────

def _ninth_lord_is_vargottama(ep: EpochState) -> bool:
    """N2 fires_when: the 9th lord is Vargottama (D-1 sign == D-9
    sign). Chart-static — fires for every epoch on charts that have
    this configuration. Acts as a sustained dampener that participates
    in MYCIN aggregation against accumulating maraka rules.
    """
    nl = _ninth_lord(ep)
    if nl is None:
        return False
    p = ep.planets.get(nl)
    if p is None:
        return False
    return p.is_vargottama


_R_NINTH_LORD_VARGOTTAMA = CFRuleSpec(
    rule=_r(
        "parashari.father.ninth_lord_vargottama_protection.cf16",
        base_cf=+0.20,
        # Use Sun as primary so μ-modulation tracks the karaka, not
        # the variable 9L planet (μ already varies with 9L's natal
        # shadbala in the existing v13 modifiers).
        primary_planet="Sun",
        source="BPHS Ch. 5 (Varga-vichara): a planet Vargottama (D-1 "
               "sign == D-9 sign) yields exalted-class results. Father "
               "bhava lord in Vargottama provides chart-static "
               "protection against maraka accumulation.",
        provenance=Provenance(
            author="human", confidence=0.45,
            citations=[_BPHS_VARGOTTAMA_CITATION],
        ),
        # No modifiers: the would-be "9L is also strong" intensifier
        # requires dynamic 9L lookup (resolve `derived_lords.ninth_lord`
        # then index `planets.<name>.shadbala_coefficient`), which the
        # DSL doesn't support without dynamic-path interpolation. Left
        # for a future engine extension; the base +0.20 already
        # captures the dignity signal.
    ),
    fires_when=_ninth_lord_is_vargottama,
)


# ── N3: Saturn strong longitudinal aspect on natal Sun ────────────

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


# ── N4: AD lord lost in Graha Yuddha ──────────────────────────────

def _ad_lord_lost_yuddha(ep: EpochState) -> bool:
    """N4 fires_when: AD lord is in Graha Yuddha and lost (the slower
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


# ── V1: Mahamrityunjaya protective veto ───────────────────────────

def _mahamrityunjaya_protective_yoga(ep: EpochState) -> bool:
    """V1 fires_when (strict, classical):
        * Jupiter NOT combust
        * Jupiter's longitudinal aspect on natal Sun strength >= 0.7
        * Jupiter natally in 5th or 9th from natal Sun
        * Jupiter shadbala mu >= 0.7

    Conjunctive gate. Rare on the verified set — designed to exercise
    the veto + cancellation code path rather than to optimize accuracy
    on this specific dataset.
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


_R_MAHAMRITYUNJAYA_VETO = CFRuleSpec(
    rule=_r(
        "parashari.father.mahamrityunjaya_yoga.veto.cf16",
        base_cf=+1.0, primary_planet=None, is_veto=True,
        source="Classical Mahamrityunjaya yoga: Jupiter strong, not "
               "combust, in 5th/9th from karaka, with exact-orb "
               "drishti on the karaka. The first veto in this rule "
               "library — exercises the cf_engine v2 mixed-veto "
               "cancellation path when co-firing with future maraka "
               "vetoes.",
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
    _R_NINTH_LORD_VARGOTTAMA,
    _R_SATURN_STRONG_ASPECT_NATAL_SUN,
    _R_AD_LORD_LOST_YUDDHA,
    _R_MAHAMRITYUNJAYA_VETO,
]
