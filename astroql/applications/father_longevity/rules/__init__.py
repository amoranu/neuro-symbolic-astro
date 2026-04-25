"""Father longevity rule sets — versioned for ablation testing.

Current canonical ruleset is **v15**. v16 through v28 are retained
in ALL_VERSIONS for ablation/historical study only — they do not
generalize to held-out data; see "Held-out validation finding"
below.

Version summary:
  v12 — Sun-karaka baseline (BPHS Ch. 41 + classical maraka theory)
  v13 — adds 9th/8th lord transit affliction family
  v14 — adds W-2 derived-lagna helpers + W-4 protective-PAD modifier
  v15 — adds derived-F-lord AD rule + standalone PD = F-loss-lord rule
        ← CANONICAL (best held-out generalization)
  v16 — engine v2 fields: combustion, graha yuddha, Sphuta Drishti
        aspect strengths, Mahamrityunjaya non-veto. Cost held-out
        AD 11→10 and held-out PD 4→2.
  v17–v28 — per-chart targeted rules tuned against the original 19
        verified subjects. Each rule was validated against training
        only (no held-out check). Held-out 20-subject test (added
        2026-04-26) showed every one of these rules contributes ZERO
        held-out improvement.

Held-out validation finding (2026-04-26)
========================================

After expanding the dataset from 19 → 39, leave-one-out ablation
showed that v17–v28's per-chart rules are pure memorization:

  Cumulative version progression on held-out (n=20):
    v15:  MD=19  AD=11  PD=4  SD=0  mean=346d
    v16:  MD=19  AD=10  PD=2  SD=0  mean=387d  ← v16 already costs HO
    v17:  MD=19  AD=10  PD=2  SD=0  mean=387d  ← unchanged through v28
    v28:  MD=19  AD=10  PD=2  SD=0  mean=392d

  Removing each rule cf17..cf28 individually changes only its target
  chart in the training cohort and has zero effect on held-out.

  Net: v28 vs v15 on held-out = -1 AD, -2 PD, +46d mean. Worse on
  unseen data despite being "better" on the 19 training charts.

The narrow conjunctive gates (4–5 simultaneous lord-identity
constraints) that prevented training-set regressions also made every
rule a chart-specific lookup. Each fires for exactly one truth epoch
in the entire universe of charts.

Methodology going forward
=========================

The 20 charts added with ids 27..46 (Hans Scholl through Tim Holt)
are the **held-out test set**. They MUST NOT be used to design or
validate new rules. Any candidate rule must satisfy:

  1. Improves training metrics OR is neutral on training, AND
  2. Does not degrade held-out metrics (HO Hit@MD/AD/PD/SD,
     mean_days), AND
  3. Has a defensible classical justification (BPHS, Jaimini, KP),
     not a chart-specific gate.

A candidate rule that improves training but degrades held-out is
overfit and must be rejected — even if the targeted chart is the
"obvious" maraka activation. The held-out reduction is the priority
signal; training fit is secondary.

Use the harness `astroql.applications.father_longevity.eval_split`
(added 2026-04-26) to evaluate candidates with the proper
train/held-out split BEFORE merging into RULES.

Use:
  from astroql.applications.father_longevity.rules import RULES
  # RULES is a list of CFRuleSpec — current canonical (= v15)

  from astroql.applications.father_longevity.rules import ALL_VERSIONS
  # ALL_VERSIONS["v28"] available for ablation comparisons
"""
from .v12 import RULES_V12
from .v13 import RULES_V13
from .v14 import RULES_V14
from .v15 import RULES_V15
from .v16 import RULES_V16  # noqa: F401 — ablation only; HO regression
from .v17 import RULES_V17  # noqa: F401 — ablation only; HO no-op
from .v18 import RULES_V18  # noqa: F401 — ablation only
from .v19 import RULES_V19  # noqa: F401 — ablation only
from .v20 import RULES_V20  # noqa: F401 — ablation only
from .v21 import RULES_V21  # noqa: F401 — ablation only
from .v22 import RULES_V22  # noqa: F401 — ablation only
from .v23 import RULES_V23  # noqa: F401 — ablation only
from .v24 import RULES_V24  # noqa: F401 — ablation only
from .v25 import RULES_V25  # noqa: F401 — ablation only
from .v26 import RULES_V26  # noqa: F401 — ablation only
from .v27 import RULES_V27  # noqa: F401 — ablation only
from .v28 import RULES_V28  # noqa: F401 — ablation only

# Current canonical ruleset — v15 is the honest generalization point.
# See the module docstring for the held-out validation finding that
# led to this revert from v28.
RULES = RULES_V15

ALL_VERSIONS = {
    "v12": RULES_V12,
    "v13": RULES_V13,
    "v14": RULES_V14,
    "v15": RULES_V15,
    "v16": RULES_V16,
    "v17": RULES_V17,
    "v18": RULES_V18,
    "v19": RULES_V19,
    "v20": RULES_V20,
    "v21": RULES_V21,
    "v22": RULES_V22,
    "v23": RULES_V23,
    "v24": RULES_V24,
    "v25": RULES_V25,
    "v26": RULES_V26,
    "v27": RULES_V27,
    "v28": RULES_V28,
}

__all__ = ["RULES", "ALL_VERSIONS",
           "RULES_V12", "RULES_V13", "RULES_V14",
           "RULES_V15", "RULES_V16", "RULES_V17",
           "RULES_V18", "RULES_V19", "RULES_V20",
           "RULES_V21", "RULES_V22", "RULES_V23",
           "RULES_V24", "RULES_V25", "RULES_V26",
           "RULES_V27", "RULES_V28"]
