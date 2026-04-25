"""Neuro-symbolic CF inference engine.

Modules:
    cf_math         MYCIN math (combine, aggregate) with strict-open invariant
    cf_engine       Module B: yoga-bhanga prune, modifier composition, MYCIN
    cf_predict      End-to-end predict_extreme_epoch (chart + window → date)
    dsl_evaluator   JSON-condition evaluator (LLM-autonomous rule path)
    epoch_emitter   Module A: emit sookshma-granularity EpochStates
    aspects         Parashari sign-aspects (Mars 4/7/8, Saturn 3/7/10, etc.)
    shadbala        Classical Parashari shadbala normalization
    ashtakavarga    BPHS Ch. 66 BAV/SAV computation (transit-gating)
    regression      Held-out 50/50 split + Hit + RankMetrics commit gates
    llm_critic      Module D: critic loop (RAG → propose → regression-gate)

The legacy clause-based `RuleEngine` lives in the originating
astro-ml repo; this engine is the neuro-symbolic CF stack only.
"""
