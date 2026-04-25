"""Epoch State schema (NEUROSYMBOLIC_ENGINE_DESIGN.md §2.1).

Pre-calculated astronomical snapshot for a discrete time window at
sookshma dasha granularity (MD → AD → PD → SD).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PlanetEpochState:
    transit_sign: str
    transit_house: int
    natal_house: int
    shadbala_coefficient: float
    is_retrograde: bool
    # Planets currently aspecting this planet's TRANSIT sign.
    aspects_receiving: List[str] = field(default_factory=list)
    # Planets currently aspecting this planet's NATAL sign — the
    # gochara form most classical Parashari rules actually mean when
    # they say "X afflicts/protects Y."
    aspects_on_natal: List[str] = field(default_factory=list)
    # Sidereal sign at birth (e.g., "Cancer"). Stable across all
    # epochs for a given chart; included on each epoch for self-
    # contained analysis.
    natal_sign: str = ""
    # Raw virupas retained for debugging / display; not used in CF math.
    shadbala_virupas: Optional[float] = None

    # ── Longitudinal aspect strengths (Sphuta Drishti, BPHS) ────────
    # `aspects_receiving` and `aspects_on_natal` are sign-based binary
    # flags; the dicts below carry the per-aspector orb-graded
    # strength in [0, 1]. A value of 1.0 = exact aspect (within ±1°);
    # 0.0 = aspect not formed (orb beyond limit). These let DSL rules
    # gate on aspect intensity (e.g. "Saturn aspect on natal Sun with
    # strength > 0.7"). Keys are aspector planet names; values are
    # floats. Missing planet ⇒ no aspect from that planet.
    aspect_strengths_receiving: Dict[str, float] = field(default_factory=dict)
    aspect_strengths_on_natal: Dict[str, float] = field(default_factory=dict)

    # ── Avasthas (qualitative states that override Shadbala) ────────
    # Asta (combustion): planet within solar combustion orb. Per
    # classical: a combust planet loses beneficence regardless of
    # Shadbala μ. Sun itself is never marked combust.
    is_combust: bool = False
    # Graha Yuddha: true planet within 1° longitude of another true
    # planet. Sun/Moon/Rahu/Ketu are excluded from yuddha by classical
    # convention. The "loser" carries the flag; rules can penalize.
    is_in_graha_yuddha: bool = False
    # Name of the opposing planet in graha yuddha (for trace/audit);
    # empty when not in yuddha.
    graha_yuddha_opponent: str = ""
    # Whether this planet "lost" the yuddha (slower daily speed).
    # When in_graha_yuddha=True and this is True, the planet is
    # classically destroyed for the duration; when False, this is
    # the winner. When not in yuddha, both flags are False.
    graha_yuddha_lost: bool = False

    # ── Navamsha (D-9) chart placement ──────────────────────────────
    # Sidereal sign in the D-9 chart. Classical Parashari (BPHS) holds
    # that a promise in the D-1 chart must be validated in the D-9 —
    # e.g. a debilitated D-1 planet exalted in D-9 attains Neecha
    # Bhanga (cancellation). Empty when emitter cannot derive D-9.
    navamsha_sign: str = ""
    # Vargottama: D-1 sign == D-9 sign. Strong dignity boost.
    is_vargottama: bool = False


@dataclass
class DashaStack:
    maha: str
    antar: str
    pratyantar: str
    sookshma: str


@dataclass
class EpochState:
    epoch_id: str
    start_time: datetime
    end_time: datetime
    dashas: DashaStack
    planets: Dict[str, PlanetEpochState]
    # Sidereal sign of the natal lagna (ascendant). Stable across all
    # epochs for a given chart; included on each epoch so rule
    # predicates can compute lagna-relative quantities (9th-lord,
    # maraka houses 2/7, lagna lord, etc.) without external lookup.
    natal_lagna_sign: str = ""
    # Pre-computed lord identities the DSL can reach via dot-paths
    # without invoking helper functions. Populated by
    # `epoch_emitter.emit_epochs`. Keys (canonical):
    #   lagna_lord, second_lord, third_lord, fourth_lord, fifth_lord,
    #   sixth_lord, seventh_lord, eighth_lord, ninth_lord, tenth_lord,
    #   eleventh_lord, twelfth_lord     ← native-lagna-relative
    #   father_lagna_sign,
    #   father_2L, father_7L, father_8L, father_12L  ← derived (BPHS Ch.8)
    #   sun_2nd_maraka, sun_7th_maraka  ← Sun-karaka maraka theory
    # Empty when the emitter wasn't able to derive these (e.g. unit
    # tests with hand-built minimal states).
    derived_lords: Dict[str, str] = field(default_factory=dict)
    # Bhinnashtakavarga (BAV) per planet + Sarvashtakavarga (SAV) per
    # BPHS Ch. 66. Chart-static — bindu counts depend only on natal
    # planet placements + lagna. Shape:
    #   {"Saturn": {"Aries": 4, "Taurus": 5, ..., "Pisces": 3},
    #    "Mars":   {... 12 sign keys ...},
    #    ...
    #    "SAV":    {"Aries": 28, ...}}
    # Reachable via DSL path "ashtakavarga.Saturn.Aries". Used to
    # GATE transit rules: a malefic transit through a low-bindu sign
    # carries classical maraka force; through a high-bindu sign it
    # does not (BPHS Ch. 66). See engine.ashtakavarga.bav_grid.
    ashtakavarga: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Native gender — "M", "F", or "" (unspecified). Sourced from
    # `BirthDetails.gender`. Reachable via DSL path "native_gender".
    # Used by gender-asymmetric karaka rules (spouse, certain progeny
    # configurations). Father / mother / self-longevity rules are
    # gender-independent per BPHS Ch. 32 and don't reference this
    # field.
    native_gender: str = ""

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "epoch_id": self.epoch_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "dashas": asdict(self.dashas),
            "natal_lagna_sign": self.natal_lagna_sign,
            "derived_lords": dict(self.derived_lords),
            "ashtakavarga": {
                planet: dict(grid)
                for planet, grid in self.ashtakavarga.items()
            },
            "native_gender": self.native_gender,
            "planets": {
                name: asdict(ps) for name, ps in self.planets.items()
            },
        }
        return out

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EpochState":
        planets = {
            name: PlanetEpochState(**ps)
            for name, ps in d["planets"].items()
        }
        return cls(
            epoch_id=d["epoch_id"],
            start_time=datetime.fromisoformat(d["start_time"]),
            end_time=datetime.fromisoformat(d["end_time"]),
            dashas=DashaStack(**d["dashas"]),
            natal_lagna_sign=d.get("natal_lagna_sign", ""),
            derived_lords=dict(d.get("derived_lords", {})),
            ashtakavarga={
                planet: dict(grid)
                for planet, grid in d.get("ashtakavarga", {}).items()
            },
            native_gender=d.get("native_gender", ""),
            planets=planets,
        )
