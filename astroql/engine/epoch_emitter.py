"""Epoch state emitter (Module A of NEUROSYMBOLIC_ENGINE_DESIGN.md).

Given a birth chart and an **explicit** [query_start, query_end] window,
emit a list of `EpochState` snapshots at sookshma dasha granularity
(MD → AD → PD → SD).

Hard contract (design §3.A, locked 2026-04-24):
  * `query_start` and `query_end` are required — there is no lifetime /
    open-ended default, anywhere in the stack.
  * `query_end - query_start` must be positive and ≤ `max_window_years`
    (default 10 years). Callers opt in to longer windows explicitly.

Natal-chart derived data (signs, natal houses, shadbala μ) is computed
once and reused for every epoch. Only transit positions + aspects +
dasha lords change per epoch.
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from ..schemas.birth import BirthDetails
from ..schemas.epoch_state import (
    DashaStack,
    EpochState,
    PlanetEpochState,
)
from . import aspects as _aspects
from . import ashtakavarga as _ashtakavarga
from . import shadbala as _sb


# Planets eligible for Graha Yuddha (BPHS): the five true planets only.
# Sun/Moon/Rahu/Ketu are excluded per classical convention.
_YUDDHA_PLANETS = ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")
# Yuddha orb: planets within 1° of longitude.
_YUDDHA_ORB_DEG = 1.0


# astro-prod engine import (mirrors astroql/chart/computer.py).
_ASTRO_PROD_PATH = Path(
    "C:/Users/ravii/.gemini/antigravity/playground/astro-prod"
)
if str(_ASTRO_PROD_PATH) not in sys.path:
    sys.path.insert(0, str(_ASTRO_PROD_PATH))

from astro_engine import AstroEngine  # noqa: E402


DEFAULT_MAX_WINDOW_YEARS = 10.0

# Default planets whose sign ingresses split an SD into sub-epochs.
# Excludes Moon (~2.25 days/sign — would explode epoch count). Sun /
# Mercury / Venus ingress every ~20-30 days; Mars / Jupiter / Saturn /
# Rahu / Ketu are slower. Callers can override via `ingress_planets`.
SLOW_INGRESS_PLANETS: tuple = (
    "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu",
)
# Sampling step for ingress detection. Bracketing samples this far
# apart will not skip a slow-planet ingress (Moon ingress requires a
# tighter step; opt in via `include_moon_ingresses`).
_INGRESS_SAMPLE_HOURS_DEFAULT = 24.0
_INGRESS_SAMPLE_HOURS_WITH_MOON = 6.0
# Binary-search precision (seconds) for nailing ingress moment.
_INGRESS_SEARCH_PRECISION_SEC = 60.0


class EpochEmissionError(RuntimeError):
    pass


def _birth_to_datetime(birth: BirthDetails) -> _dt.datetime:
    if ZoneInfo is None:
        raise EpochEmissionError("zoneinfo unavailable; Python 3.9+ required")
    time_str = birth.time or "12:00:00"
    parts = time_str.split(":")
    hh = int(parts[0])
    mm = int(parts[1]) if len(parts) > 1 else 0
    ss = int(parts[2]) if len(parts) > 2 else 0
    try:
        zone = ZoneInfo(birth.tz)
    except Exception as e:
        raise EpochEmissionError(f"unknown tz {birth.tz!r}: {e}") from e
    return _dt.datetime(
        birth.date.year, birth.date.month, birth.date.day,
        hh, mm, ss, tzinfo=zone,
    )


def _whole_sign_house(planet_sign_num: int, lagna_sign_num: int) -> int:
    return ((planet_sign_num - lagna_sign_num) % 12) + 1


_SIGN_ORDER = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

_HOUSE_NAMES = (
    "lagna_lord", "second_lord", "third_lord", "fourth_lord",
    "fifth_lord", "sixth_lord", "seventh_lord", "eighth_lord",
    "ninth_lord", "tenth_lord", "eleventh_lord", "twelfth_lord",
)


def _nth_sign_from(sign: str, n: int) -> str:
    """Return the nth sign forward from `sign` (1-indexed: n=1 → sign)."""
    try:
        i = _SIGN_ORDER.index(sign)
    except ValueError:
        return ""
    return _SIGN_ORDER[(i + n - 1) % 12]


def _compute_derived_lords(
    natal_lagna_sign: str,
    sun_natal_sign: str,
) -> Dict[str, str]:
    """Pre-compute every lord identity that the JSON DSL might query.

    Returns a flat dict the rule author can reference via dot-paths:
      "derived_lords.ninth_lord", "derived_lords.father_8L", etc.

    All values are planet names (e.g. "Saturn"). Empty string when
    a lord cannot be derived (typically chart not fully populated).
    """
    out: Dict[str, str] = {}
    if not natal_lagna_sign:
        return out
    # Native-lagna-relative house lords (1L..12L).
    for house_idx, key in enumerate(_HOUSE_NAMES, start=1):
        sign = _nth_sign_from(natal_lagna_sign, house_idx)
        out[key] = _sb.sign_lord(sign) if sign else ""
    # Derived father-lagna lords (BPHS Ch. 8). Father's lagna =
    # native's 9H sign; F2L/F7L/F8L/F12L are 2nd/7th/8th/12th from
    # that derived lagna.
    father_lagna = _nth_sign_from(natal_lagna_sign, 9)
    out["father_lagna_sign"] = father_lagna
    if father_lagna:
        out["father_2L"] = _sb.sign_lord(_nth_sign_from(father_lagna, 2))
        out["father_7L"] = _sb.sign_lord(_nth_sign_from(father_lagna, 7))
        out["father_8L"] = _sb.sign_lord(_nth_sign_from(father_lagna, 8))
        out["father_12L"] = _sb.sign_lord(_nth_sign_from(father_lagna, 12))
    # Sun-karaka marakas for father (2nd/7th from natal Sun).
    if sun_natal_sign:
        out["sun_2nd_maraka"] = _sb.sign_lord(
            _nth_sign_from(sun_natal_sign, 2))
        out["sun_7th_maraka"] = _sb.sign_lord(
            _nth_sign_from(sun_natal_sign, 7))
    return out


def _ensure_aware(dt: _dt.datetime, fallback_tz: str) -> _dt.datetime:
    """Promote naive datetimes to tz-aware using fallback_tz."""
    if dt.tzinfo is not None:
        return dt
    if ZoneInfo is None:
        raise EpochEmissionError("zoneinfo unavailable")
    return dt.replace(tzinfo=ZoneInfo(fallback_tz))


def _parse_sd_date(s: str, tz_name: str) -> _dt.datetime:
    """Parse astro-prod's 'YYYY-MM-DD' SD boundary as tz-aware at
    start-of-day in the birth tz (matches dasha calculation semantics).
    """
    if ZoneInfo is None:
        raise EpochEmissionError("zoneinfo unavailable")
    d = _dt.date.fromisoformat(s)
    return _dt.datetime(
        d.year, d.month, d.day, 0, 0, 0,
        tzinfo=ZoneInfo(tz_name),
    )


def _detect_graha_yuddha(
    tr_positions: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Identify Graha Yuddha pairs in a transit snapshot.

    Returns `{planet_name: {"opponent": str, "lost": bool}}` for every
    true planet within `_YUDDHA_ORB_DEG` of another. The "loser" is
    the slower-moving planet (smaller |daily_speed|); when speeds are
    equal we mark the alphabetically-later one as loser to keep the
    decision deterministic. Planets not in yuddha are absent from the
    result.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for i, p1 in enumerate(_YUDDHA_PLANETS):
        d1 = tr_positions.get(p1)
        if d1 is None:
            continue
        for p2 in _YUDDHA_PLANETS[i + 1:]:
            d2 = tr_positions.get(p2)
            if d2 is None:
                continue
            diff = abs(float(d1["longitude"]) - float(d2["longitude"])) % 360
            if diff > 180:
                diff = 360 - diff
            if diff >= _YUDDHA_ORB_DEG:
                continue
            spd1 = abs(float(d1.get("daily_speed") or 0.0))
            spd2 = abs(float(d2.get("daily_speed") or 0.0))
            if spd1 > spd2:
                winner, loser = p1, p2
            elif spd2 > spd1:
                winner, loser = p2, p1
            else:
                # Tie-break deterministically.
                winner, loser = sorted((p1, p2))
            out[loser] = {"opponent": winner, "lost": True}
            out[winner] = {"opponent": loser, "lost": False}
    return out


def _sign_num_at(
    engine: Any,
    when: _dt.datetime,
    lat: float,
    lon: float,
    planet: str,
) -> Optional[int]:
    """Single-planet sign_num lookup at a moment. Returns None if the
    engine doesn't return that planet (e.g. outer-only configs)."""
    pos = engine.calculate_planetary_positions(when, lat, lon)
    rec = pos.get(planet)
    if rec is None:
        return None
    return int(rec["sign_num"])


def _find_ingresses_in_window(
    engine: Any,
    start: _dt.datetime,
    end: _dt.datetime,
    lat: float,
    lon: float,
    tracked_planets: Iterable[str],
    sample_hours: float,
) -> List[_dt.datetime]:
    """Return sorted, deduplicated ingress timestamps in (start, end)
    for any of `tracked_planets`. Each timestamp is the moment the
    planet's sidereal sign_num changes, located by binary search
    between bracketing samples to within `_INGRESS_SEARCH_PRECISION_SEC`.

    The samples at `start` and `end` themselves are not returned as
    ingresses; only interior crossings.
    """
    duration = (end - start).total_seconds()
    if duration <= 0:
        return []
    # Build the sample grid: start, start+step, ..., end (clamped).
    step = max(60.0, sample_hours * 3600.0)
    n_steps = max(1, int(duration // step))
    samples: List[_dt.datetime] = [start]
    for i in range(1, n_steps):
        samples.append(start + _dt.timedelta(seconds=step * i))
    samples.append(end)

    # Snapshot positions at every sample — one engine call per sample.
    snapshot_signs: List[Dict[str, int]] = []
    for s in samples:
        pos = engine.calculate_planetary_positions(s, lat, lon)
        snapshot_signs.append({
            p: int(pos[p]["sign_num"])
            for p in tracked_planets
            if p in pos
        })

    ingress_moments: List[_dt.datetime] = []
    for i in range(len(samples) - 1):
        t0, t1 = samples[i], samples[i + 1]
        s0, s1 = snapshot_signs[i], snapshot_signs[i + 1]
        for planet in tracked_planets:
            sn0 = s0.get(planet)
            sn1 = s1.get(planet)
            if sn0 is None or sn1 is None or sn0 == sn1:
                continue
            # Binary-search the ingress between t0 and t1. The end
            # sign at t1 is the post-ingress sign; we find the
            # earliest moment whose sign != sn0.
            lo, hi = t0, t1
            target_post = sn1
            while (hi - lo).total_seconds() > _INGRESS_SEARCH_PRECISION_SEC:
                mid = lo + (hi - lo) / 2
                sn_mid = _sign_num_at(engine, mid, lat, lon, planet)
                if sn_mid is None:
                    break
                if sn_mid == sn0:
                    lo = mid
                else:
                    hi = mid
            # Use `hi` — the first known sample on the post-ingress
            # side. Drop if it landed at the window boundary.
            if start < hi < end:
                ingress_moments.append(hi)

    # Dedup and sort. Two planets ingressing within 1 minute collapse
    # to a single split moment.
    ingress_moments.sort()
    deduped: List[_dt.datetime] = []
    for t in ingress_moments:
        if not deduped or (t - deduped[-1]).total_seconds() > 60.0:
            deduped.append(t)
    return deduped


def emit_epochs(
    birth: BirthDetails,
    query_start: _dt.datetime,
    query_end: _dt.datetime,
    max_window_years: float = DEFAULT_MAX_WINDOW_YEARS,
    include_aspects: bool = True,
    split_on_ingress: bool = True,
    include_moon_ingresses: bool = False,
    ingress_planets: Optional[Iterable[str]] = None,
) -> List[EpochState]:
    """Emit sookshma-granularity `EpochState`s covering [query_start,
    query_end]. Both boundaries are required.

    Raises `EpochEmissionError` for any input-contract violation
    (missing / inverted / oversized window).
    """
    # ── Input-contract validation (design §3.A) ─────────────────────
    if query_start is None or query_end is None:
        raise EpochEmissionError(
            "query_start and query_end are required — no lifetime / "
            "open-ended queries are accepted."
        )
    query_start = _ensure_aware(query_start, birth.tz)
    query_end = _ensure_aware(query_end, birth.tz)
    if query_end <= query_start:
        raise EpochEmissionError(
            f"query_end ({query_end.isoformat()}) must be strictly "
            f"after query_start ({query_start.isoformat()})"
        )
    duration_days = (query_end - query_start).total_seconds() / 86400.0
    max_days = max_window_years * 365.25
    if duration_days > max_days:
        raise EpochEmissionError(
            f"query window is {duration_days:.1f} days > "
            f"{max_days:.1f} (max_window_years={max_window_years}). "
            f"Pass a larger max_window_years explicitly if intentional."
        )

    engine = AstroEngine()
    birth_dt = _birth_to_datetime(birth)

    # ── Natal chart — computed once ─────────────────────────────────
    natal_positions_raw = engine.calculate_planetary_positions(
        birth_dt, birth.lat, birth.lon,
    )
    # astro-prod may include outer planets (Uranus/Neptune/Pluto).
    # Filter to the 9-planet classical Parashari set.
    natal_positions: Dict[str, Any] = {
        p: d for p, d in natal_positions_raw.items()
        if p in _sb.PARASHARI_PLANETS
    }
    natal_lagna = engine.calculate_lagna(birth_dt, birth.lat, birth.lon)
    natal_lagna_sign_num = int(natal_lagna["sign_num"])

    natal_sign_by_planet: Dict[str, str] = {
        p: d["rashi"] for p, d in natal_positions.items()
    }
    natal_sign_num_by_planet: Dict[str, int] = {
        p: int(d["sign_num"]) for p, d in natal_positions.items()
    }
    natal_house_by_planet: Dict[str, int] = {
        p: _whole_sign_house(int(d["sign_num"]), natal_lagna_sign_num)
        for p, d in natal_positions.items()
    }

    # ── Natal D-9 (Navamsha) chart — chart-static, computed once ────
    # `get_divisional_chart` returns {planet: {"rashi": ..., "sign_num": ...}}
    # for the full input set; we filter to the Parashari planets after.
    try:
        natal_d9_raw = engine.get_divisional_chart(natal_positions, 9)
    except Exception:
        natal_d9_raw = {}
    natal_navamsha_sign_by_planet: Dict[str, str] = {
        p: d.get("rashi", "")
        for p, d in natal_d9_raw.items()
        if p in _sb.PARASHARI_PLANETS
    }
    natal_vargottama_by_planet: Dict[str, bool] = {
        p: bool(natal_navamsha_sign_by_planet.get(p) == natal_sign_by_planet.get(p)
                and natal_navamsha_sign_by_planet.get(p))
        for p in natal_sign_by_planet
    }

    natal_shadbala = engine.calculate_shadbala(
        natal_positions,
        {
            "longitude": float(natal_lagna["longitude"]),
            "sign_num": natal_lagna_sign_num,
            "rashi": natal_lagna["rashi"],
        },
    )
    natal_virupas: Dict[str, float] = {
        p: float(v.get("score", 0.0))
        for p, v in natal_shadbala.items()
        if p in _sb.PARASHARI_PLANETS
    }
    mu_by_planet: Dict[str, float] = _sb.normalize_all(
        natal_virupas, natal_sign_by_planet,
    )

    # ── Pre-computed lord identities (chart-static) ──────────────
    # Exposed on every EpochState so DSL paths (e.g. "derived_lords.
    # ninth_lord") resolve without invoking helper functions. This
    # is what unblocks LLM-emitted rules that reference house lords
    # via JSON conditions (see dsl_evaluator.evaluate).
    derived_lords = _compute_derived_lords(
        natal_lagna_sign=natal_lagna["rashi"],
        sun_natal_sign=natal_sign_by_planet.get("Sun", ""),
    )

    # ── Bhinnashtakavarga grid (chart-static, BPHS Ch. 66) ───────
    # Computed once from natal positions; reused across all SD
    # epochs. Used to GATE transit rules — see
    # `engine.ashtakavarga` for the gating-pattern docstring.
    try:
        bav_table = _ashtakavarga.bav_grid(
            sign_by_planet=natal_sign_by_planet,
            lagna_sign=natal_lagna["rashi"],
        )
    except Exception:
        # If natal data is incomplete, leave the grid empty. DSL
        # rules that reference ashtakavarga.* will fail to fire
        # (treated as a missing path); the rest of the engine
        # continues to work. This matches existing tolerance for
        # incomplete shadbala / nodes.
        bav_table = {}

    # ── Sookshma-depth dasha sequence, clipped to query window ──────
    moon_lon = float(natal_positions["Moon"]["longitude"])
    raw_seq = engine.calculate_dasha_sequence(
        moon_lon=moon_lon,
        birth_date=birth_dt,
        start_date=query_start,
        end_date=query_end,
        include_sookshma=True,
    )
    sd_records = [r for r in raw_seq if r.get("type") == "SD"]

    # Resolve which planets' ingresses split SDs.
    if ingress_planets is None:
        tracked_planets: List[str] = list(SLOW_INGRESS_PLANETS)
        if include_moon_ingresses:
            tracked_planets.append("Moon")
    else:
        tracked_planets = [p for p in ingress_planets]
    sample_hours = (
        _INGRESS_SAMPLE_HOURS_WITH_MOON
        if "Moon" in tracked_planets
        else _INGRESS_SAMPLE_HOURS_DEFAULT
    )

    epochs: List[EpochState] = []
    for idx, rec in enumerate(sd_records):
        start = _parse_sd_date(rec["start"], birth.tz)
        end = _parse_sd_date(rec["end"], birth.tz)
        # Clip to query window.
        if start < query_start:
            start = query_start
        if end > query_end:
            end = query_end
        if end <= start:
            continue

        # ── Build chunk boundaries ──────────────────────────────────
        # Default: one chunk = the full SD (legacy behavior). With
        # `split_on_ingress=True`, additional split points are inserted
        # at every tracked-planet sign ingress within the SD window.
        if split_on_ingress and tracked_planets:
            ingresses = _find_ingresses_in_window(
                engine=engine,
                start=start,
                end=end,
                lat=birth.lat,
                lon=birth.lon,
                tracked_planets=tracked_planets,
                sample_hours=sample_hours,
            )
            chunk_boundaries = [start, *ingresses, end]
        else:
            chunk_boundaries = [start, end]

        for chunk_idx in range(len(chunk_boundaries) - 1):
            chunk_start = chunk_boundaries[chunk_idx]
            chunk_end = chunk_boundaries[chunk_idx + 1]
            if chunk_end <= chunk_start:
                continue
            epochs.append(_build_epoch_for_chunk(
                engine=engine,
                birth=birth,
                rec=rec,
                idx=idx,
                chunk_idx=chunk_idx,
                chunk_total=len(chunk_boundaries) - 1,
                chunk_start=chunk_start,
                chunk_end=chunk_end,
                include_aspects=include_aspects,
                natal_lagna=natal_lagna,
                natal_lagna_sign_num=natal_lagna_sign_num,
                natal_sign_by_planet=natal_sign_by_planet,
                natal_sign_num_by_planet=natal_sign_num_by_planet,
                natal_house_by_planet=natal_house_by_planet,
                natal_positions=natal_positions,
                natal_navamsha_sign_by_planet=natal_navamsha_sign_by_planet,
                natal_vargottama_by_planet=natal_vargottama_by_planet,
                natal_virupas=natal_virupas,
                mu_by_planet=mu_by_planet,
                derived_lords=derived_lords,
                bav_table=bav_table,
            ))
    return epochs


def _build_epoch_for_chunk(
    engine: Any,
    birth: BirthDetails,
    rec: Dict[str, Any],
    idx: int,
    chunk_idx: int,
    chunk_total: int,
    chunk_start: _dt.datetime,
    chunk_end: _dt.datetime,
    include_aspects: bool,
    natal_lagna: Dict[str, Any],
    natal_lagna_sign_num: int,
    natal_sign_by_planet: Dict[str, str],
    natal_sign_num_by_planet: Dict[str, int],
    natal_house_by_planet: Dict[str, int],
    natal_positions: Dict[str, Any],
    natal_navamsha_sign_by_planet: Dict[str, str],
    natal_vargottama_by_planet: Dict[str, bool],
    natal_virupas: Dict[str, float],
    mu_by_planet: Dict[str, float],
    derived_lords: Dict[str, str],
    bav_table: Dict[str, Dict[str, int]],
) -> EpochState:
    """Build a single EpochState for one [chunk_start, chunk_end]
    chunk of an SD. Transit positions are evaluated at the chunk
    midpoint; chunk boundaries are guaranteed by the caller to NOT
    contain any tracked-planet sign ingress, so midpoint sampling is
    sound for the chunk."""
    start = chunk_start
    end = chunk_end
    mid = start + (end - start) / 2
    tr_positions_raw = engine.calculate_planetary_positions(
        mid, birth.lat, birth.lon,
    )
    tr_positions: Dict[str, Any] = {
        p: d for p, d in tr_positions_raw.items()
        if p in _sb.PARASHARI_PLANETS
    }
    tr_sign_by_planet: Dict[str, str] = {
        p: d["rashi"] for p, d in tr_positions.items()
    }
    tr_sign_num_by_planet: Dict[str, int] = {
        p: int(d["sign_num"]) for p, d in tr_positions.items()
    }
    tr_retro_by_planet: Dict[str, bool] = {
        p: bool(d.get("is_retrograde", False))
        for p, d in tr_positions.items()
    }
    # AstroEngine populates is_combust per-planet on the snapshot
    # (within classical solar orb, see _COMBUSTION_ORBS). Sun has
    # is_combust=False by construction. Nodes have is_combust=False
    # (no classical combustion).
    tr_combust_by_planet: Dict[str, bool] = {
        p: bool(d.get("is_combust", False))
        for p, d in tr_positions.items()
    }
    # Graha Yuddha among the five true planets at this snapshot.
    yuddha_by_planet = _detect_graha_yuddha(tr_positions)

    planets_out: Dict[str, PlanetEpochState] = {}
    # Longitudes for longitudinal aspect math.
    tr_lon_by_planet: Dict[str, float] = {
        p: float(d["longitude"]) for p, d in tr_positions.items()
    }
    natal_lon_by_planet: Dict[str, float] = {
        p: float(d["longitude"]) for p, d in natal_positions.items()
    }
    for planet in tr_positions.keys():
        tr_sign = tr_sign_by_planet[planet]
        tr_sign_num = tr_sign_num_by_planet[planet]
        tr_house = _whole_sign_house(
            tr_sign_num, natal_lagna_sign_num,
        )
        rec_aspects: List[str] = []
        on_natal: List[str] = []
        rec_strengths: Dict[str, float] = {}
        on_natal_strengths: Dict[str, float] = {}
        if include_aspects:
            rec_aspects = _aspects.aspects_receiving(
                planet, tr_sign_num, tr_sign_num_by_planet,
            )
            rec_strengths = _aspects.aspect_strengths_receiving(
                target_lon=tr_lon_by_planet[planet],
                aspector_lons=tr_lon_by_planet,
                skip_target=planet,
            )
            # Transit-on-natal: which transiting planets aspect
            # *this* planet's natal sign? Computed against the
            # current transit-position table for the *aspectors*,
            # but the target sign is this planet's natal sign.
            natal_sign_num = natal_sign_num_by_planet.get(planet)
            if natal_sign_num is not None:
                on_natal = _aspects.aspects_receiving(
                    planet, natal_sign_num, tr_sign_num_by_planet,
                )
            natal_lon = natal_lon_by_planet.get(planet)
            if natal_lon is not None:
                on_natal_strengths = _aspects.aspect_strengths_receiving(
                    target_lon=natal_lon,
                    aspector_lons=tr_lon_by_planet,
                    skip_target=planet,
                )
        yu = yuddha_by_planet.get(planet, {})
        planets_out[planet] = PlanetEpochState(
            transit_sign=tr_sign,
            transit_house=tr_house,
            natal_house=natal_house_by_planet.get(planet, 0),
            shadbala_coefficient=mu_by_planet.get(planet, 0.0),
            shadbala_virupas=natal_virupas.get(planet),
            is_retrograde=tr_retro_by_planet[planet],
            aspects_receiving=rec_aspects,
            aspects_on_natal=on_natal,
            aspect_strengths_receiving=rec_strengths,
            aspect_strengths_on_natal=on_natal_strengths,
            natal_sign=natal_sign_by_planet.get(planet, ""),
            is_combust=tr_combust_by_planet.get(planet, False),
            is_in_graha_yuddha=bool(yu),
            graha_yuddha_opponent=yu.get("opponent", "") if yu else "",
            graha_yuddha_lost=bool(yu.get("lost", False)) if yu else False,
            navamsha_sign=natal_navamsha_sign_by_planet.get(planet, ""),
            is_vargottama=natal_vargottama_by_planet.get(planet, False),
        )

    dashas = DashaStack(
        maha=rec.get("lord") or "",
        antar=rec.get("sub_lord") or "",
        pratyantar=rec.get("prat_lord") or "",
        sookshma=rec.get("sookshma_lord") or "",
    )
    # Multi-chunk SDs: include chunk_idx in the epoch_id so each chunk
    # is uniquely identified. Single-chunk SDs preserve the legacy
    # epoch_id format (no chunk suffix) for backwards compatibility.
    chunk_suffix = f".c{chunk_idx}" if chunk_total > 1 else ""
    epoch_id = (
        f"{dashas.maha}-{dashas.antar}-{dashas.pratyantar}-"
        f"{dashas.sookshma}@{start.date().isoformat()}#{idx}{chunk_suffix}"
    )
    return EpochState(
        epoch_id=epoch_id,
        start_time=start,
        end_time=end,
        dashas=dashas,
        planets=planets_out,
        natal_lagna_sign=natal_lagna["rashi"],
        derived_lords=derived_lords,
        ashtakavarga=bav_table,
    )
