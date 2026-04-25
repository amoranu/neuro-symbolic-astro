"""Train/held-out split eval harness for father-longevity rules.

Splits the 39-subject verified dataset by `id`:
  * Training cohort: ids 3..26  (19 subjects, original cohort against
    which v17–v28 per-chart rules were tuned).
  * Held-out cohort: ids 27..46 (20 subjects added 2026-04-26 from
    AstroDatabank AA-rated records, never used to design rules).

Reports metrics for each cohort separately. When a candidate ruleset
is given, also reports the held-out delta vs the v15 baseline and
emits an ACCEPT / REJECT verdict per the methodology in
`rules/__init__.py`:

  ACCEPT iff:
    1. Held-out Hit@MD does not decrease.
    2. Held-out Hit@AD/PD/SD do not collectively decrease (sum of
       deeper-level hits is non-decreasing).
    3. Held-out mean |days_off| does not increase by more than 5%
       (small fluctuations from rule re-ranking are tolerated).

REJECT triggers a non-zero exit code so the harness can gate CI.

Run:
  # Eval current canonical with split metrics:
  python -X utf8 -m astroql.applications.father_longevity.eval_split

  # Compare a candidate version against v15 baseline on held-out:
  python -X utf8 -m astroql.applications.father_longevity.eval_split \
      --candidate v28

  # Quiet mode (summary lines only, suitable for CI):
  python -X utf8 -m astroql.applications.father_longevity.eval_split \
      --candidate v28 --quiet

The held-out cohort MUST NOT be used to design or validate new
rules. It is the unbiased generalization test. A candidate that
improves training but degrades held-out is overfit, even when the
training improvement looks principled.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Optional

from .eval import DATA_PATH, evaluate
from .rules import ALL_VERSIONS, RULES


# IDs assigned to the original 19-subject training cohort. Anything
# outside this set is held-out by construction.
TRAINING_IDS = frozenset({3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 17, 18,
                          19, 20, 21, 22, 24, 26})


def _split_results(results: List[Dict[str, Any]],
                   records: List[Dict[str, Any]]):
    """Split a flat results list into (training, held_out) by id."""
    by_idx_id = {i: rec.get("id") for i, rec in enumerate(records)}
    train, held = [], []
    for r in results:
        rec_id = by_idx_id.get(r["i"])
        if rec_id in TRAINING_IDS:
            train.append(r)
        else:
            held.append(r)
    return train, held


def _summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    levels = [r["match_level"] for r in rows]
    md = sum(1 for m in levels if m in ("MD", "AD", "PD", "SD"))
    ad = sum(1 for m in levels if m in ("AD", "PD", "SD"))
    pd = sum(1 for m in levels if m in ("PD", "SD"))
    sd = sum(1 for m in levels if m == "SD")
    days = [abs(r["days_off"]) for r in rows if r["days_off"] is not None]
    return {
        "n": n,
        "MD": md, "AD": ad, "PD": pd, "SD": sd,
        "mean": mean(days) if days else 0.0,
        "median": median(days) if days else 0.0,
        "le30": sum(1 for d in days if d <= 30),
        "le90": sum(1 for d in days if d <= 90),
        "le180": sum(1 for d in days if d <= 180),
    }


def _print_cohort(name: str, summary: Dict[str, Any]) -> None:
    n = summary["n"]
    print(f"  {name:8s} n={n:2d}  "
          f"MD={summary['MD']:2d} ({summary['MD']/max(n,1):.0%})  "
          f"AD={summary['AD']:2d} ({summary['AD']/max(n,1):.0%})  "
          f"PD={summary['PD']:2d} ({summary['PD']/max(n,1):.0%})  "
          f"SD={summary['SD']:2d} ({summary['SD']/max(n,1):.0%})  "
          f"mean={summary['mean']:5.0f}d median={summary['median']:4.0f}d")


def _print_delta(name: str, base: Dict[str, Any],
                 cand: Dict[str, Any]) -> None:
    dMD = cand["MD"] - base["MD"]
    dAD = cand["AD"] - base["AD"]
    dPD = cand["PD"] - base["PD"]
    dSD = cand["SD"] - base["SD"]
    dmean = cand["mean"] - base["mean"]
    dmedian = cand["median"] - base["median"]
    deeper_delta = dAD + dPD + dSD
    print(f"  {name:8s} "
          f"ΔMD={dMD:+2d}  ΔAD={dAD:+2d}  ΔPD={dPD:+2d}  ΔSD={dSD:+2d}  "
          f"Δmean={dmean:+5.0f}d  Δmedian={dmedian:+5.0f}d  "
          f"Δ(AD+PD+SD)={deeper_delta:+2d}")


def _verdict(base_held: Dict[str, Any],
             cand_held: Dict[str, Any]) -> tuple[str, List[str]]:
    """Apply the held-out acceptance criteria and return (verdict,
    reasons). verdict is ACCEPT or REJECT."""
    reasons: List[str] = []
    if cand_held["MD"] < base_held["MD"]:
        reasons.append(
            f"Held-out Hit@MD decreased "
            f"{base_held['MD']} → {cand_held['MD']}"
        )
    deeper_base = base_held["AD"] + base_held["PD"] + base_held["SD"]
    deeper_cand = cand_held["AD"] + cand_held["PD"] + cand_held["SD"]
    if deeper_cand < deeper_base:
        reasons.append(
            f"Held-out (AD+PD+SD) total decreased "
            f"{deeper_base} → {deeper_cand}"
        )
    base_mean = max(base_held["mean"], 1.0)
    if cand_held["mean"] > base_mean * 1.05:
        reasons.append(
            f"Held-out mean |days_off| increased >5% "
            f"({base_held['mean']:.0f}d → {cand_held['mean']:.0f}d)"
        )
    return ("ACCEPT" if not reasons else "REJECT", reasons)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Train/held-out split evaluator for father-"
                    "longevity rules.")
    p.add_argument("--candidate", default=None,
                   help="Version key in ALL_VERSIONS (e.g. v28) to "
                        "evaluate as a candidate against v15 baseline. "
                        "If omitted, evaluates current canonical RULES "
                        "without comparison.")
    p.add_argument("--baseline", default="v15",
                   help="Baseline version for comparison (default: v15).")
    p.add_argument("--quiet", action="store_true",
                   help="Print only summary + verdict, not per-chart "
                        "tables.")
    args = p.parse_args()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    if args.candidate is None:
        # Single-set mode: just run current canonical and split.
        verbose = not args.quiet
        if not args.quiet:
            print(f"Ruleset: current canonical ({len(RULES)} rules)")
        result = evaluate(RULES, records, verbose=verbose)
        train, held = _split_results(result["results"], records)
        train_s = _summarize(train)
        held_s = _summarize(held)
        print()
        print("Train/held-out split metrics:")
        _print_cohort("train", train_s)
        _print_cohort("held",  held_s)
        return 0

    # Candidate mode.
    if args.candidate not in ALL_VERSIONS:
        print(f"Unknown candidate: {args.candidate!r}. Available: "
              f"{list(ALL_VERSIONS.keys())}", file=sys.stderr)
        return 2
    if args.baseline not in ALL_VERSIONS:
        print(f"Unknown baseline: {args.baseline!r}. Available: "
              f"{list(ALL_VERSIONS.keys())}", file=sys.stderr)
        return 2

    base_rules = ALL_VERSIONS[args.baseline]
    cand_rules = ALL_VERSIONS[args.candidate]

    if not args.quiet:
        print(f"Baseline: {args.baseline} ({len(base_rules)} rules)")
        print(f"Candidate: {args.candidate} ({len(cand_rules)} rules)")
        print()

    base_result = evaluate(base_rules, records,
                           verbose=not args.quiet)
    cand_result = evaluate(cand_rules, records,
                           verbose=False)

    base_train, base_held = _split_results(base_result["results"], records)
    cand_train, cand_held = _split_results(cand_result["results"], records)

    base_train_s = _summarize(base_train)
    base_held_s  = _summarize(base_held)
    cand_train_s = _summarize(cand_train)
    cand_held_s  = _summarize(cand_held)

    print()
    print(f"Baseline ({args.baseline}):")
    _print_cohort("train", base_train_s)
    _print_cohort("held",  base_held_s)
    print(f"Candidate ({args.candidate}):")
    _print_cohort("train", cand_train_s)
    _print_cohort("held",  cand_held_s)
    print()
    print("Delta (candidate - baseline):")
    _print_delta("train", base_train_s, cand_train_s)
    _print_delta("held",  base_held_s,  cand_held_s)
    print()

    verdict, reasons = _verdict(base_held_s, cand_held_s)
    print(f"VERDICT: {verdict}")
    if reasons:
        for r in reasons:
            print(f"  - {r}")
    else:
        print("  - Held-out Hit@MD non-decreasing.")
        print("  - Held-out (AD+PD+SD) total non-decreasing.")
        print("  - Held-out mean |days_off| within +5%.")

    return 0 if verdict == "ACCEPT" else 1


if __name__ == "__main__":
    sys.exit(main())
