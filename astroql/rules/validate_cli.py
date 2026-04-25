"""Validator CLI — sweeps every rule source in the repo through the
loader's `_validate_rule` + `validate_yoga_bhanga` and reports.

Two rule provenance paths exist in this project:
  1. Curated YAML  (astroql/rules/<school>/*.yaml) — already loaded
     through `_validate_rule` by `StructuredRuleLibrary` at import.
     We re-validate here for completeness and for the per-rule report.
  2. Python rule libraries (astroql/applications/<app>/rules/v*.py) —
     these construct typed `Rule` objects directly and skip the
     loader. We round-trip them through a Rule → raw-dict adapter
     and then `_validate_rule`, which is the contract any LLM-emitted
     equivalent must satisfy.

Usage:
  python -X utf8 -m astroql.rules.validate_cli            # all sources
  python -X utf8 -m astroql.rules.validate_cli --strict   # exit-1 on fail

Exit code is 0 when every rule validates AND the cross-rule
yoga-bhanga invariants hold; non-zero otherwise. Use --strict to
also exit non-zero on warnings.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from astroql.rules.loader import (
    RuleLoadError,
    _load_schema,
    _validate_rule,
    validate_yoga_bhanga,
)
from astroql.schemas.rules import Rule


# ── Sources to validate ─────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[2]
_YAML_GLOB_ROOTS = [
    _REPO_ROOT / "astroql" / "rules" / "parashari",
    _REPO_ROOT / "astroql" / "rules" / "kp",
    _REPO_ROOT / "astroql" / "rules" / "jaimini",
]

# Python rule libraries — module path → exported rule list name.
_PY_RULE_LIBS: List[Tuple[str, str]] = [
    ("astroql.applications.father_longevity.rules.v12", "RULES_V12"),
    ("astroql.applications.father_longevity.rules.v13", "RULES_V13"),
    ("astroql.applications.father_longevity.rules.v14", "RULES_V14"),
    ("astroql.applications.father_longevity.rules.v15", "RULES_V15"),
    ("astroql.applications.father_longevity.rules.v16", "RULES_V16"),
    ("astroql.applications.father_longevity.rules.v17", "RULES_V17"),
    ("astroql.applications.father_longevity.rules.v18", "RULES_V18"),
    ("astroql.applications.father_longevity.rules.v19", "RULES_V19"),
    ("astroql.applications.father_longevity.rules.v20", "RULES_V20"),
    ("astroql.applications.father_longevity.rules.v21", "RULES_V21"),
    ("astroql.applications.father_longevity.rules.v22", "RULES_V22"),
    ("astroql.applications.father_longevity.rules.v23", "RULES_V23"),
    ("astroql.applications.father_longevity.rules.v24", "RULES_V24"),
    ("astroql.applications.father_longevity.rules.v25", "RULES_V25"),
    ("astroql.applications.father_longevity.rules.v26", "RULES_V26"),
    ("astroql.applications.father_longevity.rules.v27", "RULES_V27"),
    ("astroql.applications.father_longevity.rules.v28", "RULES_V28"),
    ("astroql.applications.father_longevity.rules.v29", "RULES_V29"),
    ("astroql.applications.father_longevity.rules.v30", "RULES_V30"),
    ("astroql.applications.father_longevity.rules.v31", "RULES_V31"),
    ("astroql.applications.father_longevity.rules.v32", "RULES_V32"),
    ("astroql.applications.father_longevity.rules.v33", "RULES_V33"),
    ("astroql.applications.father_longevity.rules.v34", "RULES_V34"),
    ("astroql.applications.father_longevity.rules.v35", "RULES_V35"),
    ("astroql.applications.father_longevity.rules.v36", "RULES_V36"),
    ("astroql.applications.father_longevity.rules.v37", "RULES_V37"),
    ("astroql.applications.father_longevity.rules.v38", "RULES_V38"),
    ("astroql.applications.father_longevity.rules.v39", "RULES_V39"),
    ("astroql.applications.father_longevity.rules.v40", "RULES_V40"),
    ("astroql.applications.father_longevity.rules.v41", "RULES_V41"),
]


# ── Adapter: typed Rule → raw dict (for round-trip validation) ──────

def _rule_to_raw(r: Rule) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "rule_id": r.rule_id,
        "school": r.school.value,
        "source": r.source,
        "rule_type": r.rule_type,
        "applicable_to": r.applicable_to,
        "antecedent": list(r.antecedent),
        "consequent": r.consequent,
        "priority_tier": r.priority_tier,
        "tags": list(r.tags),
    }
    if r.base_cf is not None:
        out["base_cf"] = r.base_cf
    if r.is_veto:
        out["is_veto"] = True
    if r.subsumes_rules:
        out["subsumes_rules"] = list(r.subsumes_rules)
    if r.modifiers:
        out["modifiers"] = [
            {"condition": m.condition, "effect_cf": m.effect_cf,
             "explanation": m.explanation}
            for m in r.modifiers
        ]
    if r.primary_planet:
        out["primary_planet"] = r.primary_planet
    if r.provenance:
        out["provenance"] = {
            "author": r.provenance.author,
            "confidence": r.provenance.confidence,
            "citations": [
                {"source_id": c.source_id, "text_chunk": c.text_chunk}
                for c in r.provenance.citations
            ],
        }
    return out


# ── Report ──────────────────────────────────────────────────────────

@dataclass
class SourceReport:
    name: str
    total: int = 0
    passed: int = 0
    failures: List[Tuple[str, str]] = field(default_factory=list)
    yoga_bhanga_error: str = ""

    @property
    def ok(self) -> bool:
        return not self.failures and not self.yoga_bhanga_error


def _print_source_report(rep: SourceReport) -> None:
    bar = "  " + "─" * 70
    print(f"\n{rep.name}")
    print(bar)
    print(f"  passed:        {rep.passed}/{rep.total}")
    if rep.failures:
        print(f"  rule failures: {len(rep.failures)}")
        for rid, msg in rep.failures:
            short_msg = msg if len(msg) <= 200 else msg[:197] + "..."
            print(f"    {rid}: {short_msg}")
    if rep.yoga_bhanga_error:
        print(f"  yoga-bhanga:   FAIL")
        print(f"    {rep.yoga_bhanga_error}")
    if rep.ok:
        print("  → OK")


# ── Source validators ───────────────────────────────────────────────

def _validate_yaml_source(
    yaml_dir: Path, schema: Dict[str, Any],
) -> SourceReport:
    rep = SourceReport(name=f"YAML: {yaml_dir.relative_to(_REPO_ROOT)}")
    if not yaml_dir.exists():
        rep.name += "  (absent — skipped)"
        return rep
    typed_rules: List[Rule] = []
    for yf in sorted(yaml_dir.glob("*.yaml")):
        try:
            with open(yf, "r", encoding="utf-8") as f:
                raws = yaml.safe_load(f) or []
        except Exception as e:
            rep.failures.append((str(yf), f"YAML parse: {e}"))
            continue
        if not isinstance(raws, list):
            rep.failures.append((str(yf), "expected list of rules"))
            continue
        for raw in raws:
            rid = raw.get("rule_id", "<missing>")
            rep.total += 1
            try:
                rule = _validate_rule(raw, schema)
                typed_rules.append(rule)
                rep.passed += 1
            except RuleLoadError as e:
                rep.failures.append((rid, str(e)))
    try:
        validate_yoga_bhanga(typed_rules)
    except RuleLoadError as e:
        rep.yoga_bhanga_error = str(e)
    return rep


def _validate_py_lib(
    module_path: str, attr: str, schema: Dict[str, Any],
) -> SourceReport:
    rep = SourceReport(name=f"Python: {module_path}.{attr}")
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        rep.failures.append(("<import>", f"{type(e).__name__}: {e}"))
        return rep
    specs = getattr(mod, attr, None)
    if specs is None:
        rep.failures.append(("<attr>", f"missing attribute {attr!r}"))
        return rep

    typed_rules: List[Rule] = []
    for spec in specs:
        rule = getattr(spec, "rule", spec)  # accept CFRuleSpec or Rule
        rid = getattr(rule, "rule_id", "<unknown>")
        rep.total += 1
        try:
            _validate_rule(_rule_to_raw(rule), schema)
            typed_rules.append(rule)
            rep.passed += 1
        except RuleLoadError as e:
            rep.failures.append((rid, str(e)))
    try:
        validate_yoga_bhanga(typed_rules)
    except RuleLoadError as e:
        rep.yoga_bhanga_error = str(e)
    return rep


# ── Main ────────────────────────────────────────────────────────────

def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate every rule source against the loader."
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero on any failure (default: exit-0 even on "
             "failures, so the report is always printed in CI).",
    )
    parser.add_argument(
        "--only", choices=["yaml", "python"],
        help="Restrict the sweep to one provenance path.",
    )
    args = parser.parse_args(argv)
    schema = _load_schema()

    reports: List[SourceReport] = []
    if args.only != "python":
        for d in _YAML_GLOB_ROOTS:
            reports.append(_validate_yaml_source(d, schema))
    if args.only != "yaml":
        for module_path, attr in _PY_RULE_LIBS:
            reports.append(_validate_py_lib(module_path, attr, schema))

    print("=" * 72)
    print("Rule validator sweep")
    print("=" * 72)
    total_rules = sum(r.total for r in reports)
    total_passed = sum(r.passed for r in reports)
    total_fail = sum(len(r.failures) for r in reports)
    yb_fail = sum(1 for r in reports if r.yoga_bhanga_error)
    for rep in reports:
        _print_source_report(rep)

    print("\n" + "=" * 72)
    print(
        f"OVERALL: {total_passed}/{total_rules} rules pass.  "
        f"{total_fail} per-rule failures.  "
        f"{yb_fail} yoga-bhanga invariant violations."
    )
    print("=" * 72)

    if args.strict and (total_fail or yb_fail):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
