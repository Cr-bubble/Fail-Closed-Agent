# E6 pilot — fault injection against the fail-closed guard stack

- Date: 2026-11-03.  Repo: /home/joey123230/ICCAD_A/Agent, branch paper/routing-study, commit bbf5de5 (no tracked file modified; everything lives under paper_exp/e6_fault_injection/).
- Model ids: NONE — no LLM call is made anywhere in this experiment. The agent runs in REGEX/rules mode with no API key loaded (`LLMClient.available=False`), and corrupted `{intent, params}` objects are injected directly at `Agent._dispatch_intent`, the exact landing point of real router output. ABC: /home/joey123230/ICCAD_A/abc/abc (via configs/tools.yaml; ABC_BIN also exported). Python: .venv/bin/python (3.12), PYTHONHASHSEED=0.

## Commands (re-runnable)
```
cd /home/joey123230/ICCAD_A/Agent
.venv/bin/python paper_exp/e6_fault_injection/harness.py --list        # 6 clean + 24 corrupted jobs
.venv/bin/python paper_exp/e6_fault_injection/harness.py --one test21:clean   # smoke test (run first)
.venv/bin/python paper_exp/e6_fault_injection/harness.py --all --par 6 # full grid -> runs/*.json + results.md
.venv/bin/python paper_exp/e6_fault_injection/harness.py --report      # rebuild results.md from runs/
```
Artifacts: `harness.py` (documented), `MODES.md` (exact corruption semantics + outcome classes), `results.md` (case x mode table), `runs/<case>__<mode>.json` + `.transcript.txt` (per-run evidence), `run_all.log`.

## Setup
6 transform-heavy public cases (test21, test25, test26, test29, test35, test38; 398-34,853 gates), one designated transform line per run, corruption probability 1.0 on that line, all other lines through the normal regex router. Modes: m1 (numeric param k-1), m1w (k+1), m2 (wrong-but-implemented basis / sibling transform), m2u (basis outside the closed world, "NAND_NOR"), m3/m3r (target param redirected to a different EXISTING net — passes name-grounding by construction), m3u (transform body corrupted: sim-verified function-changing load swap injected inside the dispatched engine fn, via per-line `mock.patch.object`), m4 (swapped to a different implemented transform intent). For the corrupted call `use_rules=False`, so the text-based misroute patches (absent from the shipped pure-LLM binary) cannot rescue it; the name-grounding verdict is recorded but, as in the real pipeline with no retranslation LLM reachable, the object dispatches anyway.

Verification per run is independent of the agent's claims: evaluator's own HARD derivation (`evaluator.requirements.derive` + `evaluate_case`: ABC cec final-vs-original, structural bound recheck, basis purity, gate-absence, round-trip) plus two harness additions — (a) no-multi-driven-net check, (b) the test38 L4 per-net bound that `derive()` provably misses (see blind spots). Rollback is verified by bit-identical structural signature across the corrupted line.

## Headline numbers (24 injected runs; 6/6 clean baselines pass all HARD checks)
| outcome | n | share | runs |
|---|---|---|---|
| CAUGHT — guard_rollback (cec gate + snapshot restore) | 3 | 12.5% | 21:m3u, 29:m3u, 38:m3u |
| CAUGHT — closed_world_reject (`assert basis in BASES`, design untouched) | 2 | 8.3% | 26:m2u, 29:m2u |
| CAUGHT — benign commit/no-op (final still meets every user HARD req) | 9 | 37.5% | 21:m1, 25:m2, 25:m4, 26:m2/m3/m4, 35:m2, 38:m1, 38:m1w |
| DRIFT — semantic drift, not unsafe commit | 7 | 29.2% | 21:m1w, 21:m4, 29:m2, 29:m4, 35:m4, 38:m3, 38:m4 |
| ESCAPED — unsafe/invalid final netlist | 3 | 12.5% | 25:m3, 35:m3, 38:m3r |

**Guarded-path result: 21/21 runs whose corrupted operation goes through the guarded commit path (`_commit`/validators or the resynth cec gate) produced ZERO unsafe commits** — every final netlist was ABC-equivalent to the original and structurally valid. All 3 function-breaking body corruptions (m3u, sim-verified real) were intercepted by the pre-commit equivalence gate and rolled back bit-exactly; both closed-world violations were rejected without mutation.

**All 3 escapes share one root cause: `op_rename` is the single design-mutating operation NOT routed through the guard stack** (no snapshot, no validators, no commit gate — `cada/agent/agent.py:2821` calls `naming.rename_net` raw; the rules-path h_rename does the same). Corruption `rename(old=X, new=<existing net>)` merges two drivers onto one net; the agent answers "Renamed signal ... and updated all references." and the corrupt netlist survives to write-out. Evidence: test25:m3 (n74->n100: g628+g659 both drive n100; ABC says NOT EQUIVALENT), test38:m3r (n440->cw1: NOT EQUIVALENT), test35:m3 (n7431->cw1: double-driven, ABC returns NA). Name-grounding cannot catch it: only `old` is checked for existence, `new` is by design a fresh name. Fix is one line (reject `new` already naming a net, or route rename through `_commit`); full E6 should land the fix and show escapes -> 0, which turns the fail-closed claim from "falsified at one op" into exact.

## Semantic-drift honesty note
The 7 DRIFT runs are exactly the predicted phenomenon: **the guards enforce the corrupted contract, not the user's sentence.** A weakened bound (21:m1w: k=5 enforced and verified, final max-fanout 5 > user's 4), a wrong whole-design basis (29:m2: NOR_NOT delivered, AND_NOT asked), a wrong buffered net (38:m3: n1189 buffered, n1 left at fanout 444), and intent swaps (21:m4, 29:m4, 35:m4, 38:m4) all commit cleanly, stay functionally equivalent, and under-deliver. In every drift run the response claims success ("...max-fanout bound and equivalence verified.") — answer-level damage, never an unsafe netlist. These are classified separately from escapes, as required. The benign direction is the same coin: 21:m1 (k=3) over-delivers with 72 vs 22 buffers — the damage metric of the full E6 must count cost, not just safety.

## Evaluator blind spots found by the pilot (feed into paper §5 Measurement Integrity)
1. `derive()` emits NO fanout requirement for test38 L4 "insert buffers on the reset signal n1 to reduce its fanout to at most 4 loads per driver" (its `max_fanout_net` regex wants reduce/fanout BEFORE "signal"). Harness adds the check; without it, 38:m3/m4 would have graded as caught.
2. On a double-driven netlist ABC can return NA, and `evaluate_case` counts NA as non-failure — test35:m3's corrupt netlist passes the stock HARD gate with 0 fails; only the harness's multi-driven-net check (and 823 s of ABC time) exposes it. Recommendation: NA => fail (fail-closed grading) + add the multi-driver check to evaluator/checks.py.
3. `valid-output-netlist` (writer round-trip) PASSES on double-driven netlists.
4. test35:m2's "NOR-only" sentence is derived only as "no XNOR remain", so a NAND-cell substitution grades as caught/benign (1548 XNOR -> 6192 NANDs); arguably drift in spirit.

## Caveats
- test26 L4's cone of n10 holds no combinational gates (register boundary), so 26:m2/m3/m4 are vacuous probes (0 gates rewritten; 3 of the 9 "benign" catches). m2u on the same line is still a real closed-world probe.
- 25:m2 benign is real but lucky: resynth enforced the corrupted NOR_NOT contract, yet the winning cone reduces to inverters/wires, satisfying both NOR_NOT and the user's NAND_NOT simultaneously.
- 38:m1w benign is tree-arithmetic luck: with k=5 the buffer tree happens to leave fanout(n1)=4.
- Single injected line per run at p=1.0, one deterministic run each (rules mode + fixed seeds; identical results between the initial grid and re-runs). No repeats yet; resynth-bearing runs cost ~290 s each (request-budget bound), test35:m3's post-corruption cec cost 823 s.
- Injection models corrupted router OUTPUT; it does not exercise the JSON-syntax gate or retranslation loop (those act before dispatch), nor the rules-build text-rescue layer (disabled here by design — it could only raise the catch rate on rules builds).
- m3u corrupts the transform body through the dispatch's own commit path — it models an unsafe/buggy transform (plan's 不安全轉換), the case the cec gate exists for; pure param corruption cannot break equivalence when the engine is correct, which is itself the architecture's point.

## What the FULL E6 needs
1. **Coverage**: corrupt p% in {5, 20, 50} of ALL transform/optimize dispatches across all 40 public cases (not one line per run), uniform mode mix, n >= 5 seeded repeats per (p, mode); report catch/drift/escape with CIs.
2. **Fix-then-remeasure**: guard rename (one line), rerun — expected escapes 0; also patch evaluator NA-as-fail + multi-driver check first so the oracle itself is fail-closed.
3. **Answer-level damage metric**: per-line response correctness vs golden under corruption (count false-success claims and contaminated downstream answers, e.g. delta queries after a swapped intent), yielding the damage curve (Fig. 4): hard-failure rate vs p for guarded vs guard-ablated (validators stubbed) agent — the ablated arm turns every m3u/m3 into a zero-score case and is the paper's money contrast.
4. **Per-layer attribution**: closed-world syntax gate, name-grounding, basis/bound/cec gates, rollback — which layer caught each injection (the pilot's JSONs already carry this; formalize the field).
5. **Guard overhead**: p50/p95 wall cost of the cec gate per transform (pilot: ms-scale at 398 gates to ~15 s at 35 k gates; one 823 s pathological cec on a corrupt netlist argues for a cec timeout => reject policy).
6. Optional LLM-in-the-loop replication on a subset to confirm dispatch-level injection is a faithful stand-in for real corrupted router output.

## POST-FIX ADDENDUM (2026-11-08)

Both root-cause fixes landed on paper/routing-study as commit 23e5587
(`_rename_collision` guarding all three rename entry points; `_bad_choice`
hardening seven enum validations against unhashable LLM params).

- Escape re-runs: test25:m3, test38:m3r, test35:m3 → all now `benign_noop`
  with zero hard fails; corrupted rename refused with an explicit collision
  reply. **Post-fix tally: 24/24 injections, zero unsafe commits (claim exact).**
- Serial tiebreaker note: the pilot's test064 cdcf9af=12 was a CPU-contention
  artifact (wall-clock-budgeted optimizer); serial rerun reproduces official 10.
- Full regression: evaluator over all 40 public cases — HARD 84/84 PASS
  (5th attempt, 2026-11-08). The 2 DERIVED failures (test32 L5, test37 L10
  PI/PO counts) and the OPT-case GOLDEN drifts reproduce IDENTICALLY on a
  pristine main worktree (cdcf9af, no fixes) → pre-existing on main since the
  opt merge; goldens need re-pinning upstream, unrelated to these fixes.
  Upstream TODO: cherry-pick 23e5587 to main + fix test32/37 answers + repin.
