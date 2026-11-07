# E4 — variance + the retrieval-bank discovery (2026-11-08, commit 48bf180 era)

## gpt-4o-mini, N=5 each, test101-171 (1,420), LOCO, serial jobs

| config | runs | mean | range |
|---|---|---|---|
| catalog-only | 88.3 88.3 88.4 88.5 88.7 | **88.44%** | 0.4 |
| BM25 k=50, production bank (public 940) | 88.6 88.9 89.0 89.0 89.2 | **88.94%** | 0.6 |

Logs/JSONL: gpt_{catalog,k50}_run{1..5}.{log,jsonl}. Variance is tiny — single-run
noise ≈ ±0.2-0.3 pt at temperature 0.2.

## The discrepancy and its resolution

Historical ladder said k=50 ⇒ 95.3%. Fresh runs gave 88.9%. Hypothesis: the
historical gpt ladder (86.9→94.3→95.3) was measured with the retrieval bank =
examples.jsonl (legacy, 2,130 rows, LOCO, recall@50 96.4%), BEFORE production
switched retrieval to public_examples.jsonl (940 rows, recall@50 82.1%); nobody
re-measured e2e after the switch.

**Verification (gpt_k50_legacybank_run1.log): k=50 + `--retrieval-bank
cada/llm/examples.jsonl` ⇒ 95.1%** — reproduces the historical number in its own
configuration. The 6-point gap is entirely the bank switch.

## Current-config picture (all on production bank unless noted)

- gpt-4o-mini: catalog 88.4 (N=5) → +BM25 k50 **88.9** (N=5) → legacy bank **95.1** (N=1)
- claude-haiku-4-5: k50 **97.4** (N=1, E3)
- Model gap at identical config: **+8.5 pt** (97.4 vs 88.9) — far larger than the
  historical +2.5, and larger than any retrieval engineering.
- Decoupling claim becomes CONDITIONAL: haiku decouples from recall (82% recall →
  97.4%); gpt-4o-mini is sensitive to bank quality (+6.2 pt).

Deployability note: the legacy bank contains labeled sentences from the same
distribution as the eval set — usable only as a LOCO measurement upper bound,
not shippable; the production bank is what the contest binary shipped.

## Remaining for E4

- 4 more legacy-bank gpt runs (N→5) — launched 2026-11-08.
- haiku N=5 (k50 production) ≈ $5.5 — awaiting user approval per cost rule.
- McNemar between adjacent rungs once N complete.
