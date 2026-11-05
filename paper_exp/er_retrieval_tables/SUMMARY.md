# Experiment ER — retrieval-side numbers for paper Table 1 (BM25 only)

- Date: 2026-11-03
- Repo: /home/joey123230/ICCAD_A/Agent, branch `paper/routing-study`, commit `bbf5de5`
- Model ids: N/A — no API calls; pure local BM25 (`cada.llm.retrieval.Bm25Retriever`)
- Python: `.venv/bin/python` (CPython 3.12.13, stdlib only)
- Commands (run from repo root):
  - `.venv/bin/python paper_exp/er_retrieval_tables/run_er.py` (headline protocol; ~1.8 s total)
  - `.venv/bin/python paper_exp/er_retrieval_tables/run_er_diag_legacy_bank.py` (bank-variant diagnostics)

## Protocol (assigned)

Eval queries = the 1,420 rows of `cada/llm/examples.jsonl` with case test101–171
(verified: exactly 1,420; 71 distinct truth ops). Retrieval bank =
`cada/llm/public_examples.jsonl` (verified: 940 rows; cases test01–40 (459 rows)
+ beta0813_test21–91 (481 rows); 68 distinct ops). Every query passed
`exclude_case=<its case>` to `Bm25Retriever.top_k` — leave-one-testcase-out,
exactly as `scripts/route_eval.py` does in production. NOTE: bank case names
never overlap eval case names, so under this protocol `exclude_case` excludes
nothing (mean eligible deduped ranking length = 531.0 for every query).
Ranks are positions in the deduplicated ((text,op) seen-set), case-excluded
list `top_k` returns — i.e. exactly what the prompt would see.
ONNX/dense backend NOT measurable: `cada/llm/embed_model/` and
`cada/llm/example_vecs.npy` are gitignored build artifacts absent from the
repo (would need `scripts/fetch_embed_model.py` + `scripts/build_vectors.py`).

## 1. Label-recall@k (headline, assigned protocol) — `recall_at_k.csv`

| k | hits/1420 | label-recall |
|---|---|---|
| 5 | 855 | 60.21% |
| 10 | 944 | 66.48% |
| 25 | 1084 | 76.34% |
| 50 | 1166 | 82.11% |
| 100 | 1216 | 85.63% |

## 2. Rank of first correct op — `rank_stats.csv`, `rank_of_first_correct_hist.csv`

- median = 2, p90 = 109 (over the 1,360 queries where the op is retrievable at all)
- counting never-retrieved as +inf: median = 2, p90 = 162
- never retrieved at k=100: 204/1420 = **14.37%**
- never anywhere in the full ranking: 60/1420 = 4.23% (exactly the 3 ops with zero
  bank examples, 20 queries each) → recall@∞ caps at 95.77% under this bank
- p90/p95 use nearest-rank percentile

## 3. BM25-kNN op accuracy (cross-check for E1) — `knn_accuracy.csv`

- top-1 op accuracy: 673/1420 = **47.39%**
- top-5 majority op accuracy: 461/1420 = **32.46%** (majority over deduped top-5;
  ties broken by best rank)
- top-5 < top-1 is real, not a bug: dedup makes the correct pair appear once while
  a confusable neighbour op fills ranks 2–5 (261 queries have top-1 right but
  top-5-majority wrong; most common flips: max_fanout_of→fanout,
  deepest_output→largest_fanin_cone, reg_to_reg_paths→reg_to_reg_depth).
- Diagnostic, legacy 2130-row bank (E1 protocol (b) style, LOTO): top-1 70.56%,
  top-5-majority 55.21% (`diagnostic_bank_variants_recall.csv`).

## 4. Bank stats — `bank_stats.csv`, `unreachable_ops.csv`

- bank rows: 940; unique (text,op) pairs: **531**
- rows that duplicate an earlier pair: **409** → the documented "repeats 409 of
  940" in `retrieval.py` is VERIFIED under the reading "409 rows are duplicates"
  (940 − 531). Pairs spanning >1 testcase: 181 (that reading would NOT give 409).
- bank distinct ops: 68; eval distinct truth ops: 71; bank ops not in eval: 0
- eval ops with ZERO bank examples (unreachable by retrieval): **minimize_area,
  reg_to_po_depth, same_clock** — 20 eval queries each, 60 total (4.23%)

## 5. Latency (BM25, k=50, exclude_case set, 1,420 queries) — `latency_k50.csv`

mean 0.515 ms, p50 0.466 ms, p95 0.985 ms, max 9.33 ms per query
(time.perf_counter around each `top_k`; WSL2, 16 cores, single-threaded).
Matches the documented "BM25 0.5ms".

## 6. Cross-check vs documented numbers — ANOMALY FOUND AND EXPLAINED

Documented (retrieval.py docstrings + docs/ROUTING_ACCURACY_RESULTS_ZH.md):
bm25 recall@25 93.9%, bm25 recall@50 96.4% (§3.3) / 97.0% (§3.2), union@50
98.7–98.8%. The assigned-protocol numbers above are 17–18 pt LOWER (76.3@25,
82.1@50). This is NOT a measurement error — the documented numbers were taken
against a DIFFERENT retrieval bank (`diagnostic_bank_variants_recall.csv`):

| bank variant | recall@25 | recall@50 | matches documented |
|---|---|---|---|
| legacy `examples.jsonl` 2130 rows, LOTO, PRE-dedup top-k | **93.94%** | **96.41%** | = 93.9 / 96.4 (§3.3, retrieval.py) exactly |
| legacy `examples.jsonl` 2130 rows, LOTO, dedup (current code) | 94.51% | **97.04%** | = 97.0 (§3.2) exactly |
| test91–100 only, 710 rows | **97.54%** | 98.73% | = 97.5%@25 (§3.1) exactly |
| `public_examples.jsonl` 940 (assigned, production default) | 76.34% | 82.11% | — (new number) |
| public 940 + examples 2130, LOTO | 94.01% | 96.62% | — |

So: 93.9/96.4 were measured with retrieval bank = `examples.jsonl` itself
(2130 rows, cases test91–171, where leave-one-testcase-out actually binds)
and with the pre-dedup top-k; 97.0 is the same bank after dedup was added.
`scripts/route_eval.py` has since split banks ("The evaluation target and
retrieval bank are deliberately separate") and production now retrieves from
`public_examples.jsonl` — whose sentences come from different testcases
(test01–40 + beta0813) and cover only 68/71 eval ops. union@50 98.7% could not
be checked (no ONNX assets in repo).

**Paper implication:** Table 1 must state the bank protocol explicitly. The
production-bank retrieval recall (82.1%@50, 14.4% never@100, 3 ops structurally
unreachable) is far below the legacy in-distribution figure (96–97%), which
actually STRENGTHENS the paper's "recall and e2e are decoupled / retrieval is
additive-only" claim, but the historical 93.9/96.4/98.7 values must be labeled
as legacy-bank (examples.jsonl LOTO) numbers, not production-bank numbers.

## Files

- `run_er.py` — headline run (writes all CSVs below except the diagnostic one)
- `recall_at_k.csv`, `rank_stats.csv`, `rank_of_first_correct_hist.csv`,
  `knn_accuracy.csv`, `bank_stats.csv`, `unreachable_ops.csv`,
  `latency_k50.csv`, `per_query_results.csv` (per-sentence raw)
- `run_er_diag_legacy_bank.py`, `diagnostic_bank_variants_recall.csv` — bank-variant diagnostics

## Caveats

- Single run; BM25 is deterministic so variance is nil, latency is environment-
  dependent (WSL2, warm cache).
- Dense/union/qdrant rows of Table 1 cannot be recomputed from this repo state
  (missing gitignored ONNX model + vectors); only BM25 is fresh.
- Top-5 majority tie-break (best-rank-first) is this script's choice; a different
  tie-break shifts top-5 majority accuracy slightly.
- `exclude_case` is a no-op under the assigned protocol (no case overlap);
  kept to mirror production code paths.
