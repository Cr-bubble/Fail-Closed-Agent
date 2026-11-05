# E1 — Supervised intent-classifier baselines (local, no API)

- Date: 2026-11-03.  Repo commit: `bbf5de5` (branch `paper/routing-study`).
- Question: could a trained classifier replace the LLM for intent selection?
- Answer: **no — best classifier 73.3% vs LLM references 95.3% / 97.8%, a gap of >= 22 points that is itself conservative** (see Scope).

## Commands (exact)

```bash
# isolated env (nothing installed into the project .venv)
uv venv paper_exp/e1_classifier/.venv --python 3.12
uv pip install -p paper_exp/e1_classifier/.venv/bin/python scikit-learn   # -> scikit-learn 1.9.1, scipy 1.18.1

# full run (292 s wall, 8 workers, 16-core WSL2)
cd /home/joey123230/ICCAD_A/Agent
paper_exp/e1_classifier/.venv/bin/python paper_exp/e1_classifier/run_baselines.py --jobs 8
```

Env: Python 3.12.13, scikit-learn 1.9.1. No API calls; the LLM reference numbers
quoted below come from the existing pipeline measurements (gpt-4o-mini k=50 and
claude-haiku-4-5 k=50).

## Setup

- Eval: the 1,420 rows of `cada/llm/examples.jsonl` with case `test101`..`test171`
  (71 cases x 20 lines). Label = `op` (71 distinct ops in eval; 71 in the full pool).
- Leave-one-testcase-out at CASE granularity; per-case folds, identical training
  pools collapsed into one fit (deterministic either way).
  - Protocol (a) resource-matched: train = `public_examples.jsonl` rows with
    case != query case. The public bank contains no `test101`-`test171` case names,
    so the exclusion is vacuous there: one pool of 940 rows covers all folds.
  - Protocol (b) max-data: train = (public + examples) rows with case != query
    case, dedup of identical (text, op) pairs after the case filter
    (public-first). Fold train size 2,228-2,238.
- Models (seeds fixed, run is byte-for-byte reproducible — verified by rerun+diff):
  1. TF-IDF union (word 1-2gram + char_wb 3-5gram) + `LogisticRegression(random_state=0, max_iter=2000)` (max_iter raised only for convergence; zero convergence warnings in the log).
  2. Same features + `LinearSVC(random_state=0)`.
  3. `cada.llm.retrieval.Bm25Retriever` (imported from the repo): top-1 op, and
     majority vote over top-5 (tie -> best-ranked op). Note `top_k` dedups
     identical (text,op) hits by design, so the vote is over 5 distinct pairs.

## Results (op accuracy on the 1,420 eval rows)

| model            | protocol a (public-only) | protocol b (max-data) |
|------------------|--------------------------|-----------------------|
| TF-IDF + LogReg  | 32.3% (459)              | 48.5% (688)           |
| TF-IDF + LinearSVC | 44.7% (635)            | **73.3% (1041)**      |
| BM25 top-1       | 47.4% (673)              | 70.9% (1007)          |
| BM25 vote@5      | 32.5% (461)              | 56.6% (804)           |
| LLM pipeline, gpt-4o-mini k=50 | — | 95.3% (intent+params) |
| LLM pipeline, claude-haiku-4-5 k=50 | — | 97.8% (intent+params) |

Best classifier: **TF-IDF + LinearSVC, protocol (b), 73.3% (1041/1420)**.
Best resource-matched: BM25 top-1, 47.4%.

## Scope difference (write this in the paper)

Classifiers predict `op` only — they cannot extract params. The LLM reference
numbers were scored on intent+params (all-or-nothing), so the LLM's op-only
accuracy is >= 95.3% / 97.8%; the >= 22-point gap is therefore **conservative in
the LLM's favor**. The classifier also has no path to params, name-grounding, or
the fail-closed guards — it answers a strictly easier subtask and still loses.

## Top-10 confused op pairs (TF-IDF+LinearSVC, protocol b; gold -> pred, count)

1. connected_to_net -> rename (8)
2. count_gates -> cone_type_counts (6)
3. path_exists -> dominator (6)
4. rename -> connected_to_net (5)
5. transitive_fanout -> reachable_from (5)
6. articulation -> dominator (4)
7. cone_type_counts -> count_gates (4)
8. connected_to_output -> successors (4)
9. deepest_output -> largest_fanin_cone (4)
10. dominator -> path_exists (4)

Near-synonym graph-query intents dominate — the same confusion family the LLM
failure analysis identified (transitive_fanout <-> reachable_from etc.), but at
~10x the error rate.

## Caveats

- Protocol (a) ceiling: 3 eval ops (`minimize_area`, `reg_to_po_depth`,
  `same_clock`; 60 rows = 4.2%) never occur in the public bank, so no (a)
  classifier can reach them — ceiling 95.8%. `results.csv` also reports
  accuracy on reachable rows only (best (a): BM25 top-1 49.5%). The LLM does not
  share this ceiling: the full intent catalog is always in its static prompt
  ("retrieve demonstrations, not the tool list").
- Exact-text repeats across cases give classifiers free points: 57 eval rows
  (protocol a) / 351 (protocol b, 24.7%) have their exact text in some other
  case of the training pool. Despite that, (b) tops out at 73.3%.
- BM25 vote@5 < top-1 in both protocols: neighbor majority voting hurts here,
  consistent with the repo's design that retrieval supplies demonstrations, not
  a kNN classifier.
- LogReg default C=1 underfits this 71-class problem relative to LinearSVC; no
  hyperparameter tuning was done for any model (baselines as specified).
- Protocol (a) trains on the 940 raw rows (incl. 409 duplicated (text,op)
  pairs) — the task specifies dedup only for (b). Single run, but fully
  deterministic (fixed seeds; rerun diffed byte-identical), so no variance bars.

## Files

- `run_baselines.py` — re-runnable script (usage in header).
- `results.csv` — model x protocol accuracies (+ reachable-only accuracy).
- `confusion_best.csv` — all error (gold, pred) counts for the best model.
- `predictions.jsonl` — per-sentence raw output, 2,840 rows (2 protocols x 1,420).
- `meta.json`, `run.log` — environment, runtime, progress log.
