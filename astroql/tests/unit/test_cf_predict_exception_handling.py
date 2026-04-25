"""Pins the narrowed exception handling in cf_predict (review #2).

The predict loop must swallow exactly the exceptions that legitimately
mean "this rule does not apply to this epoch" (DSLEvalError /
AttributeError / KeyError / TypeError) and propagate everything else
(NameError, CFInvariantError, custom errors) so authoring + math bugs
crash loudly instead of silently dropping rules from evaluation.
"""
from __future__ import annotations

import datetime as _dt
from typing import List

import pytest

from astroql.engine.cf_predict import (
    CFRuleSpec,
    _PREDICATE_NON_APPLICABLE_EXC,
    predict_extreme_epoch,
)
from astroql.engine.dsl_evaluator import DSLEvalError
from astroql.schemas.birth import BirthDetails
from astroql.schemas.enums import School
from astroql.schemas.epoch_state import (
    DashaStack, EpochState, PlanetEpochState,
)
from astroql.schemas.rules import Rule


def _minimal_rule(rule_id: str = "test.r") -> Rule:
    return Rule(
        rule_id=rule_id, school=School.PARASHARI, source="t",
        base_cf=-0.5, primary_planet="Sun",
    )


def _minimal_epoch() -> EpochState:
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
    )


# ── The recognized non-applicable set ───────────────────────────────

def test_recognized_non_applicable_exceptions_are_documented():
    """`_PREDICATE_NON_APPLICABLE_EXC` is the contract: anything in
    here is silently treated as 'rule doesn't apply'. Adding a new
    type to this tuple is a deliberate decision — the test pins the
    current set so accidental broadening is caught in review."""
    expected = {DSLEvalError, AttributeError, KeyError, TypeError}
    assert set(_PREDICATE_NON_APPLICABLE_EXC) == expected


# ── Direct predicate behavior via fires_when ────────────────────────

class _Sentinel(RuntimeError):
    """A 'real' bug exception that must NOT be swallowed."""


def _raises(exc_cls):
    def _pred(_ep):
        raise exc_cls("synthetic")
    return _pred


def _passing_pred(_ep):
    return True


def test_dsl_eval_error_in_fires_when_swallowed(monkeypatch):
    """A DSL path that doesn't resolve raises DSLEvalError. The
    predict loop must treat that as 'rule doesn't apply' and
    continue, not crash."""
    from astroql.engine import cf_predict, epoch_emitter

    monkeypatch.setattr(
        epoch_emitter, "emit_epochs", lambda *a, **k: [_minimal_epoch()],
    )
    rule = _minimal_rule()
    spec = CFRuleSpec(rule=rule, fires_when=_raises(DSLEvalError))
    birth = BirthDetails(
        date=_dt.date(1980, 1, 1), time="12:00", tz="UTC",
        lat=0.0, lon=0.0,
    )
    result = predict_extreme_epoch(
        birth, _dt.datetime(2020, 1, 1), _dt.datetime(2020, 1, 2),
        [spec], polarity="negative",
    )
    # No rule fired → no extreme epoch found.
    assert result is None


def test_attribute_error_in_fires_when_swallowed(monkeypatch):
    from astroql.engine import cf_predict, epoch_emitter
    monkeypatch.setattr(
        epoch_emitter, "emit_epochs", lambda *a, **k: [_minimal_epoch()],
    )
    spec = CFRuleSpec(
        rule=_minimal_rule(), fires_when=_raises(AttributeError),
    )
    birth = BirthDetails(
        date=_dt.date(1980, 1, 1), time="12:00", tz="UTC",
        lat=0.0, lon=0.0,
    )
    assert predict_extreme_epoch(
        birth, _dt.datetime(2020, 1, 1), _dt.datetime(2020, 1, 2),
        [spec],
    ) is None


def test_unrelated_exception_in_fires_when_propagates(monkeypatch):
    """A real bug (e.g. NameError, custom RuntimeError, NotImplemented)
    must NOT be swallowed. This is the whole point of review #2."""
    from astroql.engine import epoch_emitter
    monkeypatch.setattr(
        epoch_emitter, "emit_epochs", lambda *a, **k: [_minimal_epoch()],
    )
    spec = CFRuleSpec(
        rule=_minimal_rule(), fires_when=_raises(_Sentinel),
    )
    birth = BirthDetails(
        date=_dt.date(1980, 1, 1), time="12:00", tz="UTC",
        lat=0.0, lon=0.0,
    )
    with pytest.raises(_Sentinel):
        predict_extreme_epoch(
            birth, _dt.datetime(2020, 1, 1),
            _dt.datetime(2020, 1, 2), [spec],
        )


def test_name_error_in_modifier_predicate_propagates(monkeypatch):
    """Modifier predicates have the same narrowed catch — typos
    (NameError) must surface."""
    from astroql.engine import epoch_emitter
    monkeypatch.setattr(
        epoch_emitter, "emit_epochs", lambda *a, **k: [_minimal_epoch()],
    )
    spec = CFRuleSpec(
        rule=_minimal_rule(),
        fires_when=_passing_pred,
        modifier_predicates=[_raises(NameError)],
    )
    birth = BirthDetails(
        date=_dt.date(1980, 1, 1), time="12:00", tz="UTC",
        lat=0.0, lon=0.0,
    )
    with pytest.raises(NameError):
        predict_extreme_epoch(
            birth, _dt.datetime(2020, 1, 1),
            _dt.datetime(2020, 1, 2), [spec],
        )


def test_key_error_in_modifier_predicate_swallowed(monkeypatch):
    from astroql.engine import epoch_emitter
    monkeypatch.setattr(
        epoch_emitter, "emit_epochs", lambda *a, **k: [_minimal_epoch()],
    )
    spec = CFRuleSpec(
        rule=_minimal_rule(),
        fires_when=_passing_pred,
        modifier_predicates=[_raises(KeyError)],
    )
    birth = BirthDetails(
        date=_dt.date(1980, 1, 1), time="12:00", tz="UTC",
        lat=0.0, lon=0.0,
    )
    # KeyError in modifier is treated as "modifier doesn't apply" —
    # the rule still fires; the predict run completes normally.
    result = predict_extreme_epoch(
        birth, _dt.datetime(2020, 1, 1),
        _dt.datetime(2020, 1, 2), [spec],
    )
    assert result is not None
    assert result.cf < 0  # base_cf=-0.5 modulated by μ=0.8 = -0.4
