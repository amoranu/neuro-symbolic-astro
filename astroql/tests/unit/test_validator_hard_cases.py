"""Hard-case corpus for the rule loader validator.

Covers what the LLM critic and human authors are most likely to get
wrong when writing CF-native rules — typo footguns, ambiguous shapes,
boundary numeric values, and invariant-violating cross-rule patterns.

Each test pins one specific failure mode. When the validator gains
new strictness, add a row here. When the validator gets relaxed,
remove (don't comment out) the obsolete row.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from astroql.rules.loader import (
    RuleLoadError,
    _validate_dsl_condition,
    _validate_rule,
    validate_yoga_bhanga,
)
from astroql.schemas.enums import School
from astroql.schemas.rules import Rule


@pytest.fixture(scope="module")
def schema() -> dict:
    p = Path(__file__).resolve().parents[2] / "rules" / (
        "features_schema.yaml"
    )
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _base(**over) -> dict:
    raw = {
        "rule_id": "test.rule",
        "school": "parashari",
        "source": "test",
        "antecedent": [],
        "base_cf": -0.5,
        "primary_planet": "Sun",
    }
    raw.update(over)
    return raw


# ── Group A: DSL combinator edge cases ──────────────────────────────

def test_dsl_mixed_all_and_any_rejected(schema):
    """Two combinator keys in one node is ambiguous — author probably
    meant nested combinators. Reject so the typo surfaces instead of
    silently picking one."""
    raw = _base(modifiers=[{
        "condition": {
            "all": [{"path": "dashas.maha", "op": "==", "value": "Sun"}],
            "any": [{"path": "dashas.antar", "op": "==", "value": "Sun"}],
        },
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="combinator"):
        _validate_rule(raw, schema)


def test_dsl_mixed_all_and_not_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {
            "all": [{"path": "dashas.maha", "op": "==", "value": "Sun"}],
            "not": {"path": "dashas.antar", "op": "==", "value": "Sun"},
        },
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="combinator"):
        _validate_rule(raw, schema)


def test_dsl_deeply_nested_combinator_accepted(schema):
    """5-level nesting must validate without recursion error or
    silent acceptance of malformed inner clauses."""
    deep = {"path": "dashas.maha", "op": "==", "value": "Sun"}
    for _ in range(5):
        deep = {"all": [deep, {"not": deep}]}
    raw = _base(modifiers=[{"condition": deep, "effect_cf": -0.1}])
    rule = _validate_rule(raw, schema)
    assert rule.modifiers[0].condition is not None


def test_dsl_combinator_non_list_clauses_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {
            "all": {"path": "dashas.maha", "op": "==", "value": "Sun"},
        },
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="non-empty list"):
        _validate_rule(raw, schema)


def test_dsl_not_with_list_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {"not": [
            {"path": "dashas.maha", "op": "==", "value": "Sun"},
        ]},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="must be a dict"):
        _validate_rule(raw, schema)


# ── Group B: DSL leaf edge cases ────────────────────────────────────

def test_dsl_unknown_op_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {"path": "dashas.maha", "op": "approx",
                      "value": "Sun"},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="unknown DSL op"):
        _validate_rule(raw, schema)


def test_dsl_legacy_yaml_op_in_dsl_form_rejected(schema):
    """Legacy YAML uses 'eq' / 'gte' / 'lte'; DSL uses '==' / '>=' /
    '<='. Mixing — e.g. an LLM emitting a `path` with `op: eq` —
    is a footgun and should be rejected so the author switches to
    DSL-correct ops."""
    raw = _base(modifiers=[{
        "condition": {"path": "dashas.maha", "op": "eq", "value": "Sun"},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="unknown DSL op"):
        _validate_rule(raw, schema)


def test_dsl_unary_op_with_value_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {"path": "planets.Saturn.is_retrograde",
                      "op": "truthy", "value": True},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="must not carry"):
        _validate_rule(raw, schema)


def test_dsl_binary_op_without_value_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {"path": "dashas.maha", "op": "=="},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="requires a 'value'"):
        _validate_rule(raw, schema)


def test_dsl_empty_path_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {"path": "", "op": "==", "value": "Sun"},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="non-empty"):
        _validate_rule(raw, schema)


def test_dsl_non_string_path_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {"path": 42, "op": "==", "value": "Sun"},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="non-empty"):
        _validate_rule(raw, schema)


def test_dsl_extra_unknown_key_rejected(schema):
    """Author typo'd a field name. Without strict-key checking this
    silently misfires — e.g. `description` instead of `explanation`,
    or `not_value` instead of `value`. Reject so the author sees it."""
    raw = _base(modifiers=[{
        "condition": {"path": "dashas.maha", "op": "==",
                      "value": "Sun", "explanation_typo": "x"},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="unknown"):
        _validate_rule(raw, schema)


def test_dsl_dunder_path_segment_rejected(schema):
    """Defensive: LLM-emitted paths must not walk dunder attributes
    (potential class-hierarchy traversal). EpochState's own paths
    never start with a dunder, so this is purely a sanity guard."""
    raw = _base(modifiers=[{
        "condition": {"path": "planets.__class__", "op": "truthy"},
        "effect_cf": -0.1,
    }])
    with pytest.raises(RuleLoadError, match="dunder"):
        _validate_rule(raw, schema)


# ── Group C: Rule-level boundary conditions ─────────────────────────

def test_base_cf_just_inside_strict_open_interval_accepted(schema):
    rule = _validate_rule(_base(base_cf=0.999_999_999), schema)
    assert rule.base_cf == pytest.approx(0.999_999_999)


def test_base_cf_at_unit_boundary_rejected_for_non_veto(schema):
    with pytest.raises(RuleLoadError, match="open interval"):
        _validate_rule(_base(base_cf=1.0), schema)


def test_modifier_effect_cf_just_outside_interval_rejected(schema):
    raw = _base(modifiers=[{
        "condition": {"path": "dashas.maha", "op": "==", "value": "Sun"},
        "effect_cf": 1.0,  # closed-interval boundary — rejected
    }])
    with pytest.raises(RuleLoadError, match="open interval"):
        _validate_rule(raw, schema)


def test_provenance_confidence_at_zero_accepted(schema):
    raw = _base(provenance={
        "author": "human", "confidence": 0.0,
        "citations": [{"source_id": "s", "text_chunk": "t"}],
    })
    rule = _validate_rule(raw, schema)
    assert rule.provenance.confidence == 0.0


def test_provenance_confidence_above_one_rejected(schema):
    raw = _base(provenance={
        "author": "human", "confidence": 1.5,
        "citations": [],
    })
    with pytest.raises(RuleLoadError, match="confidence"):
        _validate_rule(raw, schema)


def test_veto_with_modifier_rejected(schema):
    raw = _base(
        rule_id="test.veto_with_mod",
        is_veto=True, base_cf=-1.0,
        primary_planet=None,
        modifiers=[{"condition": {}, "effect_cf": -0.1}],
    )
    with pytest.raises(RuleLoadError, match="veto rules cannot"):
        _validate_rule(raw, schema)


def test_cf_native_non_veto_without_primary_planet_rejected(schema):
    raw = _base()
    raw.pop("primary_planet")
    with pytest.raises(RuleLoadError, match="primary_planet"):
        _validate_rule(raw, schema)


def test_unknown_primary_planet_rejected(schema):
    with pytest.raises(RuleLoadError, match="primary_planet"):
        _validate_rule(_base(primary_planet="Pluto"), schema)


# ── Group D: Cross-rule yoga-bhanga edge cases ──────────────────────

def _veto(rid: str, subsumes=()) -> Rule:
    return Rule(
        rule_id=rid, school=School.PARASHARI, source="t",
        is_veto=True, base_cf=+1.0, subsumes_rules=list(subsumes),
    )


def _non_veto(rid: str, subsumes=()) -> Rule:
    return Rule(
        rule_id=rid, school=School.PARASHARI, source="t",
        base_cf=-0.4, primary_planet="Sun",
        subsumes_rules=list(subsumes),
    )


def test_yoga_bhanga_veto_self_subsumption_rejected():
    """A veto subsuming itself is structurally meaningless and almost
    always a copy-paste error. Reject."""
    with pytest.raises(RuleLoadError, match="self"):
        validate_yoga_bhanga([_veto("v.a", subsumes=["v.a"])])


def test_yoga_bhanga_veto_cycle_rejected():
    """A↔B mutual veto subsumption is undefined (which yoga-bhangs
    which?). Reject so the author breaks the tie."""
    a = _veto("v.a", subsumes=["v.b"])
    b = _veto("v.b", subsumes=["v.a"])
    with pytest.raises(RuleLoadError, match="cycle"):
        validate_yoga_bhanga([a, b])


def test_yoga_bhanga_legitimate_chain_accepted():
    """A subsumes B subsumes C is a legitimate hierarchy — no cycle."""
    a = _veto("v.a", subsumes=["v.b"])
    b = _veto("v.b", subsumes=["v.c"])
    c = _veto("v.c")
    validate_yoga_bhanga([a, b, c])  # no exception


def test_yoga_bhanga_non_veto_subsumes_veto_rejected():
    """Already-tested invariant — included here for completeness."""
    a = _non_veto("r.a", subsumes=["v.b"])
    b = _veto("v.b")
    with pytest.raises(RuleLoadError, match="non-veto"):
        validate_yoga_bhanga([a, b])


# ── Group F: dynamic primary_planet tokens ──────────────────────────

def test_primary_planet_dynamic_ad_lord_token_accepted(schema):
    """Loader must accept <ad_lord> as a valid primary_planet — it's
    resolved per-epoch by cf_engine, not at load time."""
    raw = _base(primary_planet="<ad_lord>")
    rule = _validate_rule(raw, schema)
    assert rule.primary_planet == "<ad_lord>"


def test_primary_planet_all_dasha_tokens_accepted(schema):
    for token in ("<md_lord>", "<ad_lord>", "<pd_lord>", "<sd_lord>"):
        rule = _validate_rule(_base(primary_planet=token), schema)
        assert rule.primary_planet == token


def test_primary_planet_unknown_token_rejected(schema):
    """Must look like one of the recognized dynamic tokens or be a
    Parashari planet name. A typo like '<karaka>' or 'AD_lord' is
    not a recognized form."""
    for bad in ("<karaka>", "AD_lord", "<atmakaraka>", "<>", "<lord>"):
        with pytest.raises(RuleLoadError, match="must be one of"):
            _validate_rule(_base(primary_planet=bad), schema)


# ── Group E: Direct DSL validator (no rule wrapping) ────────────────

def test_validate_dsl_condition_combinator_recursion_caps_at_typeerror():
    """Recursing through a non-dict combinator value should error
    cleanly, not RecursionError."""
    cond = {"all": [{"all": "not-a-list"}]}
    with pytest.raises(RuleLoadError):
        _validate_dsl_condition(cond, "rid", "loc")


def test_validate_dsl_condition_value_field_with_combinator_rejected():
    """`{all: [...], value: x}` is ambiguous — value is a leaf-only
    field. Combinator + value should reject."""
    cond = {"all": [{"path": "x", "op": "truthy"}], "value": 1}
    with pytest.raises(RuleLoadError):
        _validate_dsl_condition(cond, "rid", "loc")
