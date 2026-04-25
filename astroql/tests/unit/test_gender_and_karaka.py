"""Tests for the gender plumbing + karaka resolver.

Covers:
  - BirthDetails accepts/validates `gender`
  - EpochState exposes `native_gender` and round-trips via to/from_dict
  - emit_epochs propagates birth.gender to every EpochState
  - DSL conditions can read `native_gender` via dot-path
  - karaka resolver returns the right planet per (relationship, gender)
  - resolver raises for unknown relationships and missing-gender on
    gender-required relationships
"""
from __future__ import annotations

import datetime as _dt
from datetime import date

import pytest
from zoneinfo import ZoneInfo

from astroql.engine.dsl_evaluator import evaluate
from astroql.engine.epoch_emitter import emit_epochs
from astroql.engine.karaka import (
    KarakaResolutionError,
    known_relationships,
    target_karaka_planet,
)
from astroql.schemas.birth import BirthDetails
from astroql.schemas.epoch_state import (
    DashaStack, EpochState, PlanetEpochState,
)


# ── BirthDetails gender field ───────────────────────────────────────

def test_birth_details_default_gender_is_none():
    b = BirthDetails(
        date=date(1980, 1, 1), time="12:00", tz="UTC",
        lat=0.0, lon=0.0,
    )
    assert b.gender is None


def test_birth_details_accepts_M_F_None():
    for g in ("M", "F", None):
        b = BirthDetails(
            date=date(1980, 1, 1), time="12:00", tz="UTC",
            lat=0.0, lon=0.0, gender=g,
        )
        assert b.gender == g


def test_birth_details_rejects_invalid_gender():
    for bad in ("male", "Female", "X", "", "MALE"):
        with pytest.raises(ValueError, match="gender must be one of"):
            BirthDetails(
                date=date(1980, 1, 1), time="12:00", tz="UTC",
                lat=0.0, lon=0.0, gender=bad,
            )


# ── EpochState native_gender field ──────────────────────────────────

def _stub_epoch(gender: str = "") -> EpochState:
    return EpochState(
        epoch_id="e1",
        start_time=_dt.datetime(2020, 1, 1),
        end_time=_dt.datetime(2020, 1, 2),
        dashas=DashaStack(maha="Sun", antar="Sun",
                          pratyantar="Sun", sookshma="Sun"),
        planets={"Sun": PlanetEpochState(
            transit_sign="Aries", transit_house=1, natal_house=1,
            shadbala_coefficient=0.8, is_retrograde=False,
        )},
        native_gender=gender,
    )


def test_epoch_state_default_native_gender_is_empty_string():
    e = _stub_epoch()
    assert e.native_gender == ""


def test_epoch_state_native_gender_round_trips_via_dict():
    e = _stub_epoch(gender="F")
    restored = EpochState.from_dict(e.to_dict())
    assert restored.native_gender == "F"


def test_epoch_state_legacy_dict_without_native_gender_loads():
    """A dict serialized BEFORE the gender plumbing must still load
    cleanly with native_gender defaulting to ''. Important for any
    persisted traces from earlier engine versions."""
    e = _stub_epoch()
    d = e.to_dict()
    d.pop("native_gender")
    restored = EpochState.from_dict(d)
    assert restored.native_gender == ""


# ── DSL conditions can read native_gender ───────────────────────────

def test_dsl_condition_can_read_native_gender_equals():
    e = _stub_epoch(gender="F")
    cond = {"path": "native_gender", "op": "==", "value": "F"}
    assert evaluate(cond, e) is True
    cond_neg = {"path": "native_gender", "op": "==", "value": "M"}
    assert evaluate(cond_neg, e) is False


def test_dsl_condition_can_check_native_gender_in_set():
    e = _stub_epoch(gender="M")
    cond = {"path": "native_gender", "op": "in",
            "value": ["M", "F"]}
    assert evaluate(cond, e) is True
    e2 = _stub_epoch()  # gender unspecified
    assert evaluate(cond, e2) is False


# ── emit_epochs propagates gender (smoke test against astro-prod) ──

def test_emit_epochs_propagates_gender_to_each_epoch():
    tz = ZoneInfo("Asia/Kolkata")
    birth = BirthDetails(
        date=date(1980, 6, 15), time="12:30:00", tz="Asia/Kolkata",
        lat=28.6139, lon=77.2090, gender="M",
    )
    eps = emit_epochs(
        birth,
        _dt.datetime(2020, 1, 1, tzinfo=tz),
        _dt.datetime(2020, 1, 5, tzinfo=tz),
    )
    assert len(eps) > 0
    for e in eps:
        assert e.native_gender == "M"


def test_emit_epochs_unspecified_gender_defaults_to_empty():
    tz = ZoneInfo("Asia/Kolkata")
    birth = BirthDetails(
        date=date(1980, 6, 15), time="12:30:00", tz="Asia/Kolkata",
        lat=28.6139, lon=77.2090,
        # gender not passed → defaults to None
    )
    eps = emit_epochs(
        birth,
        _dt.datetime(2020, 1, 1, tzinfo=tz),
        _dt.datetime(2020, 1, 3, tzinfo=tz),
    )
    assert len(eps) > 0
    for e in eps:
        assert e.native_gender == ""


# ── Karaka resolver — universal (gender-independent) karakas ────────

def test_father_karaka_is_sun_universal():
    assert target_karaka_planet("father") == "Sun"
    assert target_karaka_planet("father", "M") == "Sun"
    assert target_karaka_planet("father", "F") == "Sun"


def test_mother_karaka_is_moon_universal():
    assert target_karaka_planet("mother") == "Moon"
    assert target_karaka_planet("mother", "M") == "Moon"
    assert target_karaka_planet("mother", "F") == "Moon"


def test_longevity_karaka_is_saturn_universal():
    assert target_karaka_planet("longevity") == "Saturn"
    assert target_karaka_planet("self", "F") == "Saturn"


def test_children_karaka_is_jupiter_universal():
    assert target_karaka_planet("children") == "Jupiter"


# ── Karaka resolver — gender-asymmetric ─────────────────────────────

def test_spouse_karaka_is_gender_asymmetric():
    assert target_karaka_planet("spouse", "M") == "Venus"
    assert target_karaka_planet("spouse", "F") == "Jupiter"


def test_spouse_without_gender_raises():
    with pytest.raises(KarakaResolutionError, match="gender"):
        target_karaka_planet("spouse")
    with pytest.raises(KarakaResolutionError, match="gender"):
        target_karaka_planet("spouse", None)


def test_relationship_karaka_is_gender_asymmetric():
    assert target_karaka_planet("relationship", "M") == "Mars"
    assert target_karaka_planet("relationship", "F") == "Venus"


# ── Karaka resolver — input validation ──────────────────────────────

def test_unknown_relationship_raises():
    with pytest.raises(KarakaResolutionError, match="unknown"):
        target_karaka_planet("aliens")


def test_invalid_gender_value_raises():
    with pytest.raises(KarakaResolutionError, match="gender must be"):
        target_karaka_planet("father", "male")
    with pytest.raises(KarakaResolutionError, match="gender must be"):
        target_karaka_planet("father", "X")


def test_relationship_argument_canonicalized():
    """Whitespace + case shouldn't matter at the boundary."""
    assert target_karaka_planet("FATHER") == "Sun"
    assert target_karaka_planet("  Mother  ") == "Moon"
    assert target_karaka_planet("Spouse", "M") == "Venus"


def test_known_relationships_returns_sorted_unique_list():
    rels = known_relationships()
    assert sorted(rels) == rels  # already sorted
    assert len(rels) == len(set(rels))  # unique
    # Spot-check the canonical relationships are present.
    for expected in ("father", "mother", "spouse", "children",
                     "longevity", "self", "career"):
        assert expected in rels
