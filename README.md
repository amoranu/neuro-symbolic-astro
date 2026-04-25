# neuro-symbolic-astro

A neuro-symbolic certainty-factor (CF) engine for classical Vedic astrology.
Combines MYCIN-style CF inference, the Vimshottari dasha hierarchy, BPHS
classical-rule encodings, and an LLM critic loop that proposes new rules
gated by held-out regression on rank-based metrics.

## Architecture (5 modules)

| Module | Path | Purpose |
|---|---|---|
| **A. Time-slicer** | `astroql/engine/epoch_emitter.py` | Emits sookshma-granularity `EpochState`s over a window — natal chart, transit positions, dasha stack, derived lord identities, BAV grid. |
| **B. CF inference** | `astroql/engine/cf_engine.py` | Yoga-bhanga prune → veto short-circuit → modifier composition → shadbala μ modulation → correlation-group max-pool → MYCIN aggregate. |
| **C. RAG retrieval** | (delegated to astro-prod) | `engine/llm_critic.py` wraps astro-prod's `retrieve_for_tradition` for classical text lookup. |
| **D. LLM critic** | `astroql/engine/llm_critic.py` | Consumes a failing trace, pulls relevant classical text via RAG, synthesizes a candidate rule, gates via regression. |
| **E. Regression tester** | `astroql/engine/regression.py` | Held-out 50/50 split, deterministic by seed; `Hit@MD/AD/PD/SD` + `MRR` + top-k recall commit gates. |

## Why this engine

Classical Vedic astrology rules are **defeasible** — they have exceptions
(yoga-bhanga, cancellations) layered over them. Pure ML overfits on small
samples; pure symbolic rules don't generalize. This engine encodes:

- **MYCIN CFs** (Buchanan & Shortliffe 1984) for monotonic evidence
  combination, with a strict-open `(-1, 1)` invariant + ε-clip so vetos
  remain the only ±1 mechanism.
- **Veto subsumption** for yoga-bhanga: a benefic veto can defeat a
  malefic veto (e.g., Mahamrityunjaya cancels Sun-Saturn maraka).
- **Shadbala μ modulation** so a rule's contribution scales by its
  primary planet's natal strength.
- **Correlation groups** that max-pool highly-correlated evidence
  (e.g., Saturn-9H-transit + Saturn-aspect-9L) before MYCIN, killing
  the false-positive amplification MYCIN's independence assumption
  causes on astrological data.
- **Ashtakavarga gating** (BPHS Ch. 66) so transit rules suppress
  themselves through high-bindu signs.
- **JSON DSL** for rule conditions so an LLM critic can synthesize
  fully-executable rules without human Python authoring.

## Layout

```
astroql/
├── engine/
│   ├── cf_math.py          MYCIN math (combine, aggregate)
│   ├── cf_engine.py        infer_cf — modifier composition + max-pool + MYCIN
│   ├── cf_predict.py       predict_extreme_epoch (chart + window → date)
│   ├── dsl_evaluator.py    JSON-condition evaluator (LLM-autonomous path)
│   ├── epoch_emitter.py    sookshma-granularity EpochStates
│   ├── aspects.py          Parashari sign-aspects
│   ├── shadbala.py         classical Parashari shadbala
│   ├── ashtakavarga.py     BPHS Ch. 66 BAV/SAV (transit-gating)
│   ├── regression.py       held-out evaluation + commit gates
│   └── llm_critic.py       critic-RAG-regression cycle
├── schemas/                Rule, EpochState, Trace, BirthDetails, ...
├── rules/                  loader.py + features_schema.yaml
├── applications/
│   └── father_longevity/   v15 ruleset + eval/diagnose/analyze + GT
└── tests/unit/             172 unit tests
```

## Quick start

```bash
# Run the unit test suite
python -X utf8 -m pytest astroql/tests/unit/ -q

# Evaluate the canonical father_longevity ruleset (v15)
python -X utf8 -m astroql.applications.father_longevity.eval

# Per-chart diagnostic dump
python -X utf8 -m astroql.applications.father_longevity.diagnose 2

# Batch failure analysis with rule-firing comparison
python -X utf8 -m astroql.applications.father_longevity.analyze
```

## Current state (father_longevity, v15 ruleset, N=19 verified subjects)

| Metric | Value |
|---|---|
| Hit@MD | 18/19 (95%) |
| Hit@AD | 6/19 (32%) |
| Hit@PD | 1/19 (5%) |
| Hit@SD | 1/19 (5%) |
| median \|days_off\| | 375 days |
| ≤180d | 4/19 |

See `DESIGN.md` for the locked design decisions (CF formula, shadbala
normalization, sookshma granularity, yoga-bhanga, 50/50 split, dispositor
rule, time-range contract).

See `astroql/CAVEATS.md` (or astro-ml's `astroql/CAVEATS.md`) for the
gap tracker — known limitations and future work.

## Origin

Spun out of [`amoranu/astro-ml`](https://github.com/amoranu/astro-ml)
to give the neuro-symbolic engine its own home. Schemas (`astroql/schemas/`)
and the rule loader (`astroql/rules/loader.py`) are duplicated in both
repos because the parent `astro-ml` parser/planner/RAG infrastructure
also depends on them.

## License

MIT (see `LICENSE`).
