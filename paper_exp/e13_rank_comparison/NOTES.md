# E13 — rank comparison vs official final scores

## 2026-11-08 submission-version fingerprinting (workflow wf_89e8a999-cdb + serial tiebreaker)

Method: run candidate commits on 6 small final OPT cases in detached worktrees
(calib_cdcf9af / calib_5d549c5), rules mode, ABC_BIN=~/ICCAD_A/abc/abc,
PYTHONHASHSEED=0; compare achieved depth (report cross-checked by recomputation
from the written netlist) against the official per-request costs in
final_release_cada1125.xlsx.

| case    | official | cdcf9af            | 5d549c5 |
|---------|----------|--------------------|---------|
| test047 | 16       | 16 ✓               | 15 (better) |
| test051 | 55       | 55 ✓ (already-optimal reply) | 55 ✓ |
| test060 | 9        | 9 ✓                | 9 ✓ |
| test061 | 8        | 8 ✓                | 8 ✓ |
| test064 | 10       | 12 under load → **10 serial ✓** | 10 ✓ |
| test070 | 13       | 13 ✓               | 12 (better) |

**Conclusion: the submitted FINAL version is `cdcf9af` (high confidence).**
6/6 exact once CPU contention removed; the optimizer is wall-clock budgeted, so
the round-1 test064=12 was a load artifact (two calibrations ran in parallel).
5d549c5 deviates on exactly the two cases where the versions differ, both in the
"locally better" direction — for it to be the submitted version, the contest
machine would have to lose exactly 1 level on exactly those two cases and land
exactly on cdcf9af's numbers. Definitive confirmation (hash of the actually
submitted tarball/binary) still welcome if the artifact is found.

## Early improvement candidates (candidates/)

Bonus from the calibration: the OLDER 5d549c5 engine beats the submitted version
on two of the 26 OPT gap cases — evidence that a multi-version/budget portfolio
closes gaps:

- `test070_out.5d549c5.v` — depth **12 = cost_min** (official 13, gap 0.0769 pts → fully recoverable)
- `test047_out.5d549c5.v` — depth **15** (official 16, cost_min 14 → 0.0625 of the 0.125 gap)
- `test064_out.5d549c5.v` / `.rerun.v` — depth 10 (= official; control)

All were produced by the engine's own cec-gated commit path; re-verify
equivalence independently with ABC before using them in the paper table.

## Next steps

1. Full calibration: cdcf9af on all 100 final cases (46 OPT requests dominate
   runtime: ~46×5min; parallel lanes OK but keep lanes ≤ 4 so the wall-clock
   budget isn't starved — or run OPT cases strictly serial for fidelity).
2. Improved run: paper/routing-study HEAD on the 26 gap cases with a portfolio
   (current engine, 5d549c5 engine, longer budgets) → new ratios from the GIVEN
   cost_min (cap at 1.0).
3. Table: improved vs official 671.366 vs top-2/3 (scores TBC).
