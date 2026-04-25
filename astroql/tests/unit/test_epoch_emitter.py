"""Epoch state emitter + shadbala normalization + aspects tests."""
from __future__ import annotations

import datetime as _dt
from datetime import date

import pytest
from zoneinfo import ZoneInfo

from astroql.engine import aspects as _aspects
from astroql.engine import shadbala as _sb
from astroql.engine.epoch_emitter import (
    EpochEmissionError,
    emit_epochs,
)
from astroql.schemas.birth import BirthDetails
from astroql.schemas.epoch_state import EpochState


# ── Shadbala normalization ──────────────────────────────────────────

def test_classical_mu_at_required_threshold_is_one():
    # Sun required = 390 virupas
    assert _sb.classical_mu("Sun", 390.0) == pytest.approx(1.0)


def test_classical_mu_half_of_required_is_half():
    assert _sb.classical_mu("Mars", 150.0) == pytest.approx(0.5)


def test_classical_mu_caps_at_one_for_overshoot():
    assert _sb.classical_mu("Saturn", 1000.0) == 1.0


def test_classical_mu_negative_treated_as_zero():
    assert _sb.classical_mu("Moon", -50.0) == 0.0


def test_classical_mu_for_node_raises():
    with pytest.raises(ValueError, match="classical shadbala"):
        _sb.classical_mu("Rahu", 100.0)


def test_node_mu_inherits_from_dispositor():
    # Rahu in Leo → dispositor Sun
    classical = {"Sun": 0.8, "Moon": 0.5, "Mars": 0.3}
    mu = _sb.node_mu_via_dispositor("Rahu", "Leo", classical)
    assert mu == 0.8


def test_node_mu_unknown_sign_raises():
    with pytest.raises(ValueError):
        _sb.node_mu_via_dispositor("Ketu", "NotARealSign", {})


def test_normalize_all_full_table():
    raw = {
        "Sun": 390.0, "Moon": 180.0, "Mars": 300.0,
        "Mercury": 210.0, "Jupiter": 390.0, "Venus": 165.0,
        "Saturn": 150.0, "Rahu": 0.0, "Ketu": 0.0,
    }
    signs = {
        "Sun": "Leo", "Moon": "Cancer", "Mars": "Aries",
        "Mercury": "Gemini", "Jupiter": "Sagittarius",
        "Venus": "Taurus", "Saturn": "Capricorn",
        "Rahu": "Gemini",     # dispositor Mercury
        "Ketu": "Sagittarius",  # dispositor Jupiter
    }
    mu = _sb.normalize_all(raw, signs)
    assert mu["Sun"] == pytest.approx(1.0)
    assert mu["Moon"] == pytest.approx(0.5)
    assert mu["Mercury"] == pytest.approx(0.5)
    # Rahu inherits Mercury's μ (0.5)
    assert mu["Rahu"] == pytest.approx(0.5)
    # Ketu inherits Jupiter's μ (1.0)
    assert mu["Ketu"] == pytest.approx(1.0)


# ── Parashari aspects ───────────────────────────────────────────────

def test_sun_aspects_only_7th():
    # Sun in Aries (1) → 7th from Aries = Libra (7)
    assert _aspects.aspected_signs("Sun", 1) == [7]


def test_mars_aspects_4_7_8():
    # Mars in Aries (1) → 4th=Cancer(4), 7th=Libra(7), 8th=Scorpio(8)
    assert sorted(_aspects.aspected_signs("Mars", 1)) == [4, 7, 8]


def test_jupiter_aspects_5_7_9():
    # Jupiter in Capricorn (10) → 5th=Taurus(2), 7th=Cancer(4),
    # 9th=Virgo(6)
    assert sorted(_aspects.aspected_signs("Jupiter", 10)) == [2, 4, 6]


def test_saturn_aspects_3_7_10():
    # Saturn in Libra (7) → 3rd=Sagittarius(9), 7th=Aries(1),
    # 10th=Cancer(4)
    assert sorted(_aspects.aspected_signs("Saturn", 7)) == [1, 4, 9]


def test_aspect_wraps_around_zodiac():
    # Jupiter in Pisces (12) → 5th=Cancer(4), 7th=Virgo(6), 9th=Scorpio(8)
    assert sorted(_aspects.aspected_signs("Jupiter", 12)) == [4, 6, 8]


def test_aspects_receiving_excludes_self():
    # If Sun is in Aries and Mars is in Aries, and we ask what aspects
    # Sun's sign (Aries), Mars itself is skipped if Mars is the target,
    # but Mars CAN aspect Sun from the same sign via its 7th aspect...
    # actually Mars in Aries aspects 4th/7th/8th = Cancer/Libra/Scorpio,
    # not Aries. So no aspects on Sun from Mars when they're co-located.
    signs = {"Sun": 1, "Mars": 1}  # both in Aries
    assert _aspects.aspects_receiving("Sun", 1, signs) == []


def test_aspects_receiving_basic_case():
    # Saturn in Sagittarius (9); Sun in Gemini (3). Saturn's 7th aspect
    # from Sag is Gemini. So Sun receives Saturn.
    signs = {"Sun": 3, "Saturn": 9}
    assert _aspects.aspects_receiving("Sun", 3, signs) == ["Saturn"]


def test_invalid_sign_num_raises():
    with pytest.raises(ValueError):
        _aspects.aspected_signs("Sun", 13)
    with pytest.raises(ValueError):
        _aspects.aspected_signs("Sun", 0)


# ── Longitudinal aspect strengths (Sphuta Drishti) ──────────────────

def test_aspect_strength_exact_opposition_is_one():
    # Mars at 0° Aries (lon=0) opposes a target at 180° (Libra 0°).
    # 7th aspect (offset 6 = 180°) lands exactly on target → 1.0.
    s = _aspects.aspect_strength_between("Mars", 0.0, 180.0)
    assert s == pytest.approx(1.0)


def test_aspect_strength_decays_linearly_within_orb():
    # Saturn at 0° Aries; target at 175° (5° short of exact 7th).
    # With default orb=10°, strength = 1 - 5/10 = 0.5.
    s = _aspects.aspect_strength_between("Saturn", 0.0, 175.0)
    assert s == pytest.approx(0.5)


def test_aspect_strength_zero_outside_orb():
    # Mercury (only 7th aspect) at 0°; target 30° away from any
    # aspect point — well beyond the 10° orb.
    s = _aspects.aspect_strength_between("Mercury", 0.0, 30.0)
    assert s == 0.0


def test_aspect_strength_review_example_29_aries_to_1_scorpio():
    # Review's case: Mars at 29° Aries (lon=29) and Saturn at 1°
    # Scorpio (lon=210). Sign-based math says these are NOT in 7th
    # aspect (8th sign apart). Longitudinal math: Mars's 7th aspect
    # is exact at 209°; target at 210° → 1° away → strength 0.9.
    s = _aspects.aspect_strength_between(
        aspector="Mars", aspector_lon=29.0, target_lon=210.0,
    )
    assert s == pytest.approx(0.9)


def test_aspect_strengths_receiving_skips_self_and_zero_entries():
    # Two planets, only one of which has a non-zero aspect onto target.
    target_lon = 100.0
    aspector_lons = {
        "Saturn": 280.0,  # Saturn's 7th aspect: 280+180=460%360=100 → exact!
        "Mercury": 50.0,  # Mercury's 7th: 50+180=230 — 130° off → 0
        "TargetSelf": 100.0,
    }
    out = _aspects.aspect_strengths_receiving(
        target_lon=target_lon,
        aspector_lons=aspector_lons,
        skip_target="TargetSelf",
    )
    assert "Saturn" in out and out["Saturn"] == pytest.approx(1.0)
    assert "Mercury" not in out  # zero strength → omitted
    assert "TargetSelf" not in out


# ── Epoch emitter input contract ────────────────────────────────────

def _birth() -> BirthDetails:
    # Arbitrary real birth — Delhi.
    return BirthDetails(
        date=date(1980, 6, 15),
        time="12:30:00",
        tz="Asia/Kolkata",
        lat=28.6139,
        lon=77.2090,
    )


def test_missing_query_start_rejected():
    with pytest.raises(EpochEmissionError, match="required"):
        emit_epochs(_birth(), None, _dt.datetime(2010, 1, 1))  # type: ignore[arg-type]


def test_missing_query_end_rejected():
    with pytest.raises(EpochEmissionError, match="required"):
        emit_epochs(_birth(), _dt.datetime(2010, 1, 1), None)  # type: ignore[arg-type]


def test_inverted_window_rejected():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2020, 1, 1, tzinfo=tz)
    b = _dt.datetime(2019, 1, 1, tzinfo=tz)
    with pytest.raises(EpochEmissionError, match="must be strictly after"):
        emit_epochs(_birth(), a, b)


def test_zero_window_rejected():
    tz = ZoneInfo("Asia/Kolkata")
    t = _dt.datetime(2020, 1, 1, tzinfo=tz)
    with pytest.raises(EpochEmissionError, match="must be strictly after"):
        emit_epochs(_birth(), t, t)


def test_window_over_max_rejected():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2010, 1, 1, tzinfo=tz)
    b = _dt.datetime(2025, 1, 1, tzinfo=tz)  # 15 years
    with pytest.raises(EpochEmissionError, match="max_window_years"):
        emit_epochs(_birth(), a, b, max_window_years=10.0)


def test_window_over_default_allowed_with_opt_in():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2010, 1, 1, tzinfo=tz)
    b = _dt.datetime(2021, 1, 1, tzinfo=tz)  # 11 years
    # No emission check — just ensure it does not reject on contract.
    # Actual emission hits astro-prod; tested separately.
    epochs = emit_epochs(_birth(), a, b, max_window_years=12.0)
    assert len(epochs) > 0


# ── Smoke test: real emission against astro-prod ────────────────────

def test_emit_real_small_window_smoke():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2020, 1, 1, tzinfo=tz)
    b = _dt.datetime(2020, 2, 1, tzinfo=tz)
    epochs = emit_epochs(_birth(), a, b)
    assert len(epochs) > 0
    first = epochs[0]
    assert isinstance(first, EpochState)
    # Every epoch lies within the query window (after clipping).
    for e in epochs:
        assert e.start_time >= a
        assert e.end_time <= b
        assert e.end_time > e.start_time
    # Dasha stack populated at all four levels.
    assert first.dashas.maha
    assert first.dashas.antar
    assert first.dashas.pratyantar
    assert first.dashas.sookshma
    # All 9 planets present (including Rahu/Ketu).
    expected = {"Sun", "Moon", "Mars", "Mercury", "Jupiter",
                "Venus", "Saturn", "Rahu", "Ketu"}
    assert set(first.planets.keys()) == expected
    # Shadbala μ in [0, 1].
    for p, ps in first.planets.items():
        assert 0.0 <= ps.shadbala_coefficient <= 1.0, (
            f"{p} μ={ps.shadbala_coefficient}"
        )
        assert 1 <= ps.transit_house <= 12
        assert 1 <= ps.natal_house <= 12


def test_emit_real_json_roundtrip():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2020, 1, 1, tzinfo=tz)
    b = _dt.datetime(2020, 1, 10, tzinfo=tz)
    epochs = emit_epochs(_birth(), a, b)
    assert len(epochs) > 0
    serialized = [e.to_dict() for e in epochs]
    restored = [EpochState.from_dict(d) for d in serialized]
    assert len(restored) == len(epochs)
    # Field-level equality on a spot-checked epoch.
    e0 = epochs[0]
    r0 = restored[0]
    assert r0.epoch_id == e0.epoch_id
    assert r0.start_time == e0.start_time
    assert r0.end_time == e0.end_time
    assert r0.dashas.sookshma == e0.dashas.sookshma
    p_name = next(iter(e0.planets.keys()))
    assert (
        r0.planets[p_name].shadbala_coefficient
        == e0.planets[p_name].shadbala_coefficient
    )


# ── New v2 fields: D-9, combustion, graha yuddha, aspect strengths ──

def test_emit_populates_navamsha_signs():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2020, 1, 1, tzinfo=tz)
    b = _dt.datetime(2020, 1, 5, tzinfo=tz)
    epochs = emit_epochs(_birth(), a, b)
    valid_signs = {
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn",
        "Aquarius", "Pisces",
    }
    for ep in epochs:
        for p, ps in ep.planets.items():
            # D-9 is chart-static, so every planet must carry a sign.
            assert ps.navamsha_sign in valid_signs, (
                f"{p}: navamsha_sign={ps.navamsha_sign!r}"
            )
            assert isinstance(ps.is_vargottama, bool)
            # Vargottama iff D-1 == D-9.
            if ps.is_vargottama:
                assert ps.navamsha_sign == ps.natal_sign


def test_emit_populates_combustion_and_yuddha_flags():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2020, 1, 1, tzinfo=tz)
    b = _dt.datetime(2020, 1, 10, tzinfo=tz)
    epochs = emit_epochs(_birth(), a, b)
    for ep in epochs:
        # Sun is never combust by classical convention.
        assert ep.planets["Sun"].is_combust is False
        # Nodes have no classical combustion.
        assert ep.planets["Rahu"].is_combust is False
        assert ep.planets["Ketu"].is_combust is False
        # Yuddha is only for the five true planets — Sun/Moon/Nodes
        # are never marked.
        for p in ("Sun", "Moon", "Rahu", "Ketu"):
            assert ep.planets[p].is_in_graha_yuddha is False, (
                f"{p} should never be in yuddha"
            )
        # When a planet is in yuddha, it has an opponent and a
        # win/lose flag.
        for p, ps in ep.planets.items():
            if ps.is_in_graha_yuddha:
                assert ps.graha_yuddha_opponent != ""
                # Opponent must be one of the five true planets.
                assert ps.graha_yuddha_opponent in (
                    "Mars", "Mercury", "Jupiter", "Venus", "Saturn"
                )


def test_emit_populates_aspect_strengths_in_unit_range():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2020, 1, 1, tzinfo=tz)
    b = _dt.datetime(2020, 1, 10, tzinfo=tz)
    epochs = emit_epochs(_birth(), a, b)
    # Every aspect strength is in (0, 1] when present (zero entries
    # are pruned from the dict at emit time).
    for ep in epochs:
        for ps in ep.planets.values():
            for s in ps.aspect_strengths_receiving.values():
                assert 0.0 < s <= 1.0
            for s in ps.aspect_strengths_on_natal.values():
                assert 0.0 < s <= 1.0


def test_emit_split_on_ingress_yields_more_epochs():
    # Over a 6-month window, slow-planet ingresses should at least
    # match (and typically exceed) the SD count from the legacy
    # midpoint-only emission.
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2020, 1, 1, tzinfo=tz)
    b = _dt.datetime(2020, 7, 1, tzinfo=tz)
    legacy = emit_epochs(_birth(), a, b, split_on_ingress=False)
    split = emit_epochs(_birth(), a, b, split_on_ingress=True)
    assert len(split) >= len(legacy)
    # Chunked SDs use ".cN" suffix; legacy IDs never carry one.
    assert all(".c" not in e.epoch_id for e in legacy)


def test_emit_split_chunks_have_non_overlapping_intervals():
    tz = ZoneInfo("Asia/Kolkata")
    a = _dt.datetime(2020, 1, 1, tzinfo=tz)
    b = _dt.datetime(2020, 4, 1, tzinfo=tz)
    epochs = emit_epochs(_birth(), a, b, split_on_ingress=True)
    # Adjacent epochs must be contiguous and non-overlapping.
    for i in range(1, len(epochs)):
        assert epochs[i].start_time >= epochs[i - 1].end_time
        assert epochs[i].end_time > epochs[i].start_time
