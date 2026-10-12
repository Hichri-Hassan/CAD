# Round-Trip Failure Forensic Analysis

## Executive Summary

This report analyzes all **87** models that are fully parsed by the CAD Copilot parser (`valid` status, no unsupported features) but **fail during compilation**.

These 87 failures sit between the 134 fully-parsed candidates and the 47 models that currently pass end-to-end round-trip validation (35.1% pass rate among fully-parsed models).

Every failure was reproduced via stepwise FreeCAD compilation in freecadcmd. The exact FreeCAD error and earliest failing operation were captured for all 87 models.

### Key Findings

1. **Dominant failure mode:** Unclosed sketch/profile — 62 models (71.3%).
2. **Failures cluster into two recurring issues**, not 87 unrelated bugs: unclosed profiles (62) and invalid dress-up edge references (24).
3. **Unclosed profiles are a parser+compiler gap:** JSON contains sketch entities but zero constraints; compiler adds geometry without solving constraints.
4. **Dress-up failures are a compiler topology problem:** edge selectors from the source model do not resolve after upstream geometry differs.
5. **16 models** also emit deprecated `Midplane` warnings during Pad/Pocket compile (secondary, non-blocking).

## Failure Distribution

| Root Cause | Models | % | Est. Recovery | Difficulty | Origin |
|---|---:|---:|---:|---|---|
| Unclosed sketch/profile | 62 | 71.3% | 62 | Medium | parser + compiler |
| Invalid fillet/chamfer edge references | 23 | 26.4% | 21 | Hard | compiler (topology) |
| Invalid chamfer edge references | 1 | 1.1% | 0 | Hard | compiler (topology) |
| Invalid operation parameters | 1 | 1.1% | 0 | Medium | compiler |

## Failing Operation Types

| Operation Type | Failures |
|---|---:|
| Pad | 50 |
| Fillet | 20 |
| Pocket | 13 |
| Chamfer | 4 |

## Subsystem Attribution

| Subsystem | Failures | % |
|---|---:|---:|
| parser+compiler | 62 | 71.3% |
| compiler | 25 | 28.7% |

## Root-Cause Analysis

### Unclosed sketch/profile (62 models, 71.3%)

- **Estimated fix difficulty:** Medium
- **Estimated recovery if fixed:** 62 models
- **Recommended fix:** Apply sketch constraints at compile time or validate closure.

**Representative examples:**

- `000003.FCStd` — fails at `op_002` (Pad): `op_002: Wire is not closed.`
- `000004.FCStd` — fails at `op_002` (Pad): `op_002: Wire is not closed.`
- `000010.FCStd` — fails at `op_004` (Pocket): `op_004: Wire is not closed.`

### Invalid fillet/chamfer edge references (23 models, 26.4%)

- **Estimated fix difficulty:** Hard
- **Estimated recovery if fixed:** 21 models
- **Recommended fix:** Requires topology-stable edge mapping or semantic selectors.

**Representative examples:**

- `000061.FCStd` — fails at `op_008` (Fillet): `<Exception> FeatureDressUp.cpp(217): Invalid edge link: Edge41`
- `000062.FCStd` — fails at `op_006` (Fillet): `<Exception> FeatureDressUp.cpp(217): Invalid edge link: Face19`
- `000400.FCStd` — fails at `op_006` (Fillet): `<Exception> FeatureDressUp.cpp(217): Invalid edge link: Edge33`

### Invalid chamfer edge references (1 models, 1.1%)

- **Estimated fix difficulty:** Hard
- **Estimated recovery if fixed:** 0 models
- **Recommended fix:** Same as fillet; edge mapping after upstream changes.

**Representative examples:**

- `000162.FCStd` — fails at `op_007` (Chamfer): `op_007: BRep_API: command not done`

### Invalid operation parameters (1 models, 1.1%)

- **Estimated fix difficulty:** Medium
- **Estimated recovery if fixed:** 0 models
- **Recommended fix:** Validate pocket depth/extent and reject zero-length extrusions.

**Representative examples:**

- `002234.FCStd` — fails at `op_011` (Pocket): `Cannot create a pocket with a total length of zero.`

## Priority Ranking of Fixes

| Priority | Root Cause | Recovery | Difficulty |
|---|---|---:|---|
| 1 | Unclosed sketch/profile | 62 | Medium |
| 2 | Invalid fillet/chamfer edge references | 21 | Hard |
| 3 | Invalid operation parameters | 0 | Medium |
| 4 | Invalid chamfer edge references | 0 | Hard |

## Recommendations

- Fixing the top two root causes could recover an estimated **83** of the 87 failed models.
- Prioritize **sketch constraint application in the compiler** before expanding parser operation coverage.
- Treat **fillet/chamfer edge selectors** as a topology-mapping problem, not a parser extraction problem.
- Replace deprecated **`Midplane`** usage in pad compilation (easy win, small but clean fix).
- Use this report to define **Dataset V2** scope: target 134 fully-parsed models after compiler fixes.

## Output Files

- `roundtrip_failure_breakdown.csv` — one row per failed model
