"""Father longevity rule sets — versioned for ablation testing.

Current canonical ruleset is **v39** (v15 baseline + four sphuta-
aspect refinements: v31 at AD/5°, v37 at AD/3°, v38 at PD/3°, v39
any-malefic/3°). v16 through v28 are retained in ALL_VERSIONS for
ablation/historical study only — they do not generalize to held-out
data; see "Held-out validation finding" below.

Version summary:
  v12 — Sun-karaka baseline (BPHS Ch. 41 + classical maraka theory)
  v13 — adds 9th/8th lord transit affliction family
  v14 — adds W-2 derived-lagna helpers + W-4 protective-PAD modifier
  v15 — adds derived-F-lord AD rule + standalone PD = F-loss-lord rule
        ← previous canonical (honest baseline)
  v16 — engine v2 fields: combustion, graha yuddha, Sphuta Drishti
        aspect strengths, Mahamrityunjaya non-veto. Cost held-out
        AD 11→10 and held-out PD 4→2.
  v17–v28 — per-chart targeted rules tuned against the original 19
        verified subjects. Each rule was validated against training
        only (no held-out check). Held-out 20-subject test (added
        2026-04-26) showed every one of these rules contributes ZERO
        held-out improvement.
  v29–v30 — REJECTED candidates under the new HO+Train methodology
        (broad transit-position rules that fired too often at non-
        truth epochs and regressed training).
  v31 — sphuta-aspect refinement of v15's binary aspect rules at 5°
        orb. ACCEPTED.
  v32–v36 — additional candidates, each REJECTED:
        v32 PD-level sphuta — train mean drift +5.7%
        v33 9L-target sphuta — train AD -1
        v34 combust+F-role AD — too narrow, no signal
        v35 graha-yuddha-lost AD — HO regression -3 deeper hits
        v36 9L-as-aspector — HO PD -1
  v37 — AD-level inner-orb (3°) refinement of v31, stacking.
        ACCEPTED.
  v38 — PD-level inner-orb (3°) sphuta-aspect on Sun, stacking on
        top of v37 (paired with v37 since v32's PD-level @ 5° was
        too noisy). ACCEPTED.
  v39 — ANY-malefic tight-orb (3°) sphuta-aspect on Sun (catches
        the case where the malefic-aspector is not the dasha-lord),
        gated by MD context. Strongest accept yet:
          Train: +1 AD, +1 PD, -11d mean, -34d median
          HO:    same hits, +1d mean, -15d median
        ACCEPTED. ← CANONICAL.

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
from .v29 import RULES_V29  # noqa: F401 — REJECTED (HO+train methodology)
from .v30 import RULES_V30  # noqa: F401 — REJECTED (HO+train methodology)
from .v31 import RULES_V31
from .v32 import RULES_V32  # noqa: F401 — REJECTED (HO+train methodology)
from .v33 import RULES_V33  # noqa: F401 — REJECTED (HO+train methodology)
from .v34 import RULES_V34  # noqa: F401 — REJECTED (HO+train methodology)
from .v35 import RULES_V35  # noqa: F401 — REJECTED (HO+train methodology)
from .v36 import RULES_V36  # noqa: F401 — REJECTED (HO+train methodology)
from .v37 import RULES_V37
from .v38 import RULES_V38
from .v39 import RULES_V39

# Current canonical ruleset.
#
# v15 was the honest baseline (see module docstring for the held-out
# finding that led to the revert from v28).
#
# v31 = v15 + AD-level sphuta-aspect on natal Sun (>= 0.5 orb)
# v37 = v31 + AD-level inner-orb (>= 0.7) refinement, stacking
# v38 = v37 + PD-level inner-orb (>= 0.7) sphuta-aspect on Sun
# v39 = v38 + ANY-malefic tight-orb (>= 0.7) sphuta-aspect on Sun
#       (not restricted to dasha-lord), gated by MD context
# v32-v36 each rejected (see those modules for rejection reasons).
# v39 acceptance vs v15 cumulative:
#   Train: +2 AD (6→8), +1 PD (1→2), mean 417d → 394d (-23d)
#   HO:    same hits, mean 347d → 330d (-17d), median 316 → 271 (-45d)
RULES = RULES_V39

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
    "v29": RULES_V29,
    "v30": RULES_V30,
    "v31": RULES_V31,
    "v32": RULES_V32,
    "v33": RULES_V33,
    "v34": RULES_V34,
    "v35": RULES_V35,
    "v36": RULES_V36,
    "v37": RULES_V37,
    "v38": RULES_V38,
    "v39": RULES_V39,
}

__all__ = ["RULES", "ALL_VERSIONS",
           "RULES_V12", "RULES_V13", "RULES_V14",
           "RULES_V15", "RULES_V16", "RULES_V17",
           "RULES_V18", "RULES_V19", "RULES_V20",
           "RULES_V21", "RULES_V22", "RULES_V23",
           "RULES_V24", "RULES_V25", "RULES_V26",
           "RULES_V27", "RULES_V28", "RULES_V29",
           "RULES_V30", "RULES_V31", "RULES_V32",
           "RULES_V33", "RULES_V34", "RULES_V35",
           "RULES_V36", "RULES_V37", "RULES_V38",
           "RULES_V39"]
