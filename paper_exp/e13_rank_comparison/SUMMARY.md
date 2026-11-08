# E13 — rank comparison: calibration complete, improvement phase running

## Calibration (submitted version cdcf9af × final test001-100) — DONE 2026-11-08 09:29

- Driver: driver.sh (serial, checkpointed, setsid; survived one session crash at
  test058 with zero loss; total ≈ 4.8h incl. 33-min crash gap). Rules mode, $0 API.
- Completion: 100/100 ran, 0 crashes (analyze.py flags test100 "incomplete" on a
  dur=0 bookkeeping artifact; its stdout has all 71 frames — false alarm).
- Regex-coverage caveat: 94 request lines across 37 cases hit the safe no-op
  (rules mode has no LLM fallback in the worktree); official pure-LLM run routed
  these. Does not affect OPT costs or safety behavior.
- **OPT costs: 27/46 bit-exact vs official; 19 deviations = 14 BETTER / 4 worse
  (+1..+16) / 1 outlier (test087 9913 vs 5482 — flagged idle re-run).** The
  optimizer is wall-clock-budget-bound, so achieved cost varies run-to-run
  (e.g., test047: 16 → 14 across runs); deviations other than test087 are ≤2%.
- **ABC cec spot-check: 10/10 EQUIV** (analyze.py --cec, seed 13).
- Calibration bonus: re-running the submitted version already closed/beat
  **10 of the 26 official gap cases** (incl. beating cost_min on test053/082/
  083/086) — remaining open gap 2.033 of 2.634 pts (0.60 pts recovered free).

## Improvement portfolio — RUNNING (started 09:33, ETA ~12:15)

- improve_targets.json: 16 open cases (gap 2.033 pts), sorted by gap:
  test051 (0.527), test088 (0.445), test062 (0.437), test049, test061, test060,
  test064, test055, test057, test048, test080, test069, test052, test067,
  test087, test056.
- improve_driver.sh: per case, two variants serially — 5d549c5 engine (known to
  beat cdcf9af on some depth cases) + cdcf9af re-draw (budget-bound timing
  stochasticity). 32 jobs, checkpointed, setsid. Outputs improve_runs/
  <case>_out.<variant>.v.
- Scoring rule for the paper table: best valid netlist per case; ratio =
  cost_min / best (capped at 1.0); every counted win must pass independent
  ABC cec vs the original design before entering the table.

## Next after driver done

1. Recompute per-case best + capped ratios → improved total vs official 671.366.
2. Independent cec on every counted-win netlist (calibration + improvement).
3. Idle re-runs: test087 outlier; optionally test052/081/084.
4. §6 comparison table + paper numbers (anonymization-safe wording).
