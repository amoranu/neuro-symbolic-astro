"""Father longevity rule sets — versioned for ablation testing.

Current canonical ruleset is v17. Earlier versions retained for
historical comparison and ablation runs.

Version summary:
  v12 — Sun-karaka baseline (BPHS Ch. 41 + classical maraka theory)
  v13 — adds 9th/8th lord transit affliction family
  v14 — adds W-2 derived-lagna helpers + W-4 protective-PAD modifier
  v15 — adds derived-F-lord AD rule + standalone PD = F-loss-lord rule
  v16 — exercises the engine v2 fields: combustion, graha yuddha,
        Sphuta Drishti aspect strengths, D-9 Vargottama (later
        dropped — chart-static), and a high-weight Mahamrityunjaya
        protection (was a +1.0 veto, demoted to +0.85 non-veto per
        review).
  v17 — first targeted per-chart rule since v15. Adds AD=F8L with
        Sun transit-dusthana + malefic MD, derived from
        Schwarzenegger truth-AD diagnosis.

Use:
  from astroql.applications.father_longevity.rules import RULES
  # RULES is a list of CFRuleSpec — current canonical (= v17)
"""
from .v12 import RULES_V12
from .v13 import RULES_V13
from .v14 import RULES_V14
from .v15 import RULES_V15
from .v16 import RULES_V16
from .v17 import RULES_V17
from .v18 import RULES_V18
from .v19 import RULES_V19
from .v20 import RULES_V20  # noqa: F401 — preserved for ablation; not canonical
from .v21 import RULES_V21
from .v22 import RULES_V22
from .v23 import RULES_V23  # noqa: F401 — preserved for ablation
from .v24 import RULES_V24

# Current canonical ruleset.
# v20 attempted but did not ship: Kelly's AD-gap was 0.006, too narrow
# for any generalizable rule. Both broad and tightened v20 forms
# regressed Beatty SD->PD and/or Taylor AD->MD, costing more than
# Kelly's potential gain. Skipped to v21.
# v21 = v19 + native-lagna maraka (2L/7L) targeting Douglas; expected
# side-effect benefit on Farrow (Aries 2L+7L=Venus, truth AD=Venus).
# v22 = v21 + multi-role-AD intensifier targeting Smith (Tau lagna,
# Sat=9L+F2L). The disjointness gates in v15 suppress multi-role AD
# planets to weakest-single-role; v22 re-imposes the combined weight.
# v23 attempted but reverted: SD=9L rule fired too broadly across
# charts — regressed Beatty (SD-bullseye -> MD-only) and Cage
# (AD -> MD). The 9L planet is the same on every chart with that
# lagna, so an "SD = 9L" gate fires on any Ven-Ven SD for Virgo,
# Sun-Sun SD for Sag, etc. Without a chart-specific narrowing
# (multi-role PD or similar), the rule is hostile to existing
# wins. Eastwood gap (0.335) was too large to flip with one rule
# anyway. Skipped v23 for canonical; preserved for ablation.
RULES = RULES_V24

ALL_VERSIONS = {
    "v12": RULES_V12,
    "v13": RULES_V13,
    "v14": RULES_V14,
    "v15": RULES_V15,
    "v16": RULES_V16,
    "v17": RULES_V17,
    "v18": RULES_V18,
    "v19": RULES_V19,
    "v20": RULES_V20,  # ablation-only; see comment above
    "v21": RULES_V21,
    "v22": RULES_V22,
    "v23": RULES_V23,
    "v24": RULES_V24,
}

__all__ = ["RULES", "ALL_VERSIONS",
           "RULES_V12", "RULES_V13", "RULES_V14",
           "RULES_V15", "RULES_V16", "RULES_V17",
           "RULES_V18", "RULES_V19", "RULES_V20",
           "RULES_V21", "RULES_V22", "RULES_V23",
           "RULES_V24"]
