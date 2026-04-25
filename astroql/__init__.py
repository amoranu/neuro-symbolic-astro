"""Neuro-symbolic CF engine over Parashari + Vedic astrology.

The package layout intentionally keeps the `astroql` namespace from
the originating project so existing imports (`from astroql.engine
import cf_predict`) work unchanged. The legacy clause-based
`RuleEngine` (used by parser/planner/RAG infrastructure) lives in
the parent `astro-ml` repo; only the neuro-symbolic CF engine and
its application(s) live here.

Key entry points:
    astroql.engine.cf_predict.predict_extreme_epoch
    astroql.engine.dsl_evaluator.evaluate
    astroql.engine.regression.evaluate, evaluate_ranks
    astroql.applications.father_longevity (eval / diagnose / analyze)

Design doc: ../DESIGN.md
"""

__version__ = "0.1.0"
