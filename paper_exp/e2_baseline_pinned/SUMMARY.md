# E2 — Pinned catalog-only baseline (replaces unrecorded 86.9%)

- Date: 2026-11-03 (logs carry UTC timestamps 2026-11-02T17:4x)
- Repo: /home/joey123230/ICCAD_A/Agent, branch paper/routing-study, commit bbf5de5
- Model (exact, from script's own `model=` line): **gpt-4o-mini**, provider openai (config default; no --provider override)
- Eval set: test101-171 from cada/llm/examples.jsonl = 1,420 sentences; retriever none (catalog-only)

## Verdict per run

| run | command | result |
|---|---|---|
| run1 | `.venv/bin/python scripts/route_eval.py --cases test101-171 --retriever none --config configs/api_key.yaml --workers 12 --out paper_exp/e2_baseline_pinned/run1.jsonl` | **INVALID** (exit 2) — 2 evaluator worker exceptions, 563 targets aborted by fail-fast. NOT quota: `TypeError: unhashable type: 'dict'` from `cada/llm/allowed_intents.py:1281` (`if b not in BASIS_VALUES:` with BASIS_VALUES a set) when the model returns a non-string `basis` param. Hit on test143 lines 6 & 16 (minimize_area). Wall 1m29s. No accuracy reported (script refuses; the partial prefix in run1.jsonl is forensic only, not reportable). |
| smoke | `.venv/bin/python paper_exp/e2_baseline_pinned/run_with_validator_shim.py --cases test143-143 --retriever none --config configs/api_key.yaml --workers 8 --out .../smoke_test143.jsonl` | VALID (exit 0), 20/20 attempted, 19/20 intent; both formerly-crashing lines recover via the one corrective round-trip and route correctly. Wall 15s. |
| **run2 (headline)** | `.venv/bin/python paper_exp/e2_baseline_pinned/run_with_validator_shim.py --cases test101-171 --retriever none --config configs/api_key.yaml --workers 12 --out paper_exp/e2_baseline_pinned/run2.jsonl` | **VALID** (exit 0, run_valid=true on all 1,420 rows, 0 degraded, 0 aborted). Wall **2m27s** (17:45:27Z→17:47:54Z). |

## Headline numbers (run2)

- **Intent accuracy 1257/1420 = 88.5%** (safe 355/355 = 100.0%, hard 902/1065 = 84.7%)
- Params accuracy 1201/1419 = 84.6% (exact, normalized); object accuracy 1136/1419 = 80.1% (1 intent-only row omitted)
- Intent failures 163: **gave up 50 (31%), wrong op 113 (69%)**
- Top confusions: pi_to_po_depth→global_max_depth (11), check_floating→check_dangling (10), const1_gates→report_const_gates (6), gates_driven_by→fanout (6), pi_to_dff_depth→global_max_depth (6), transitive_fanout→reachable_from (5)
- Top gave-up ops: const_propagate (11), const1_gates (9), exists_nand_pair (6)

## Comparison vs historical

Historical catalog-only baseline was **86.9% with the model id unrecorded**. Pinned replacement: **88.5% on gpt-4o-mini** (+1.6 pt, same regime; consistent with the old number having been 4o-mini-class). Use 88.5%/gpt-4o-mini as the paper's E2 number; retire 86.9%.

## Caveats

1. **Evaluator bug found (upstream fix needed; tracked files deliberately not modified on this run):** `cada/llm/allowed_intents.py:1281` crashes with `TypeError: unhashable type` when the LLM emits a non-string `basis` value, and route_eval's fail-fast then invalidates the whole run. run2/smoke ran through `run_with_validator_shim.py` (in this dir), which wraps `_validate_param_values` to convert that TypeError into the intended validation-error string (fail-closed: model gets its single corrective round-trip, else counts as failure). Shim changes nothing for values the original code handles without raising. Reproducer: `validate_intent_object({'intent':'minimize_area','params':{'basis':{'x':1}}})`.
2. Single run (N=1); variance/CI is E4's job.
3. Cost estimate printed by script: ~$0.15/full run with caching; run1 (partial) + smoke + run2 ≈ $0.25-0.30 total spent on E2.
4. `--workers 12` used (script default 8); allowed on this 16-core box, serial with all other eval jobs.
5. params_ok is scored independently of intent_ok by the script (params can be "ok" on a wrong-intent row); object accuracy is the strict joint number.

## Files

- run1.log / run1.jsonl — invalid run record (keep as measurement-integrity exhibit)
- smoke_test143.log / smoke_test143.jsonl — targeted shim validation (20 sentences)
- run2.log / run2.jsonl — the valid headline run
- run_with_validator_shim.py — exact wrapper used
