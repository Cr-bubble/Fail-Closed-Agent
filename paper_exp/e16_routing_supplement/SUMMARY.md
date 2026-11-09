# E16 — routing supplement (2026-11-09), requested by the second review

Commands (serial, repo HEAD ~4d6d0ad):
- `.venv/bin/python paper_exp/e14_bare_llm/run_bare.py --provider openai --out paper_exp/e16_routing_supplement/bare_gpt_run{2,3}.jsonl`
- `.venv/bin/python scripts/route_eval.py --cases test101-171 --provider anthropic --retriever none --out paper_exp/e16_routing_supplement/haiku_catalog_run{1,2,3}.jsonl`

All runs valid (no degraded calls).

| Setting | Intent acc. (runs) | Mean | Exact obj. mean |
|---|---|---|---|
| gpt-4o-mini, bare intent list (with E14 run 1) | 61.4 / 61.1 / 61.8 | 61.4 | 55.4 |
| claude-haiku-4.5, full catalog, no retrieval | 96.3 / 96.3 / 96.5 | 96.4 | 91.4 |

Findings:
- Bare-list baseline is stable (range 0.8 pt); catalog gain for gpt stays +27.0 pt.
- Retrieval from the production bank adds little for EITHER model: +0.5 (gpt,
  88.4 -> 88.9, N=5) and +1.0 (haiku, 96.4 -> 97.4, N=1). The earlier claim
  "a stronger model needs less help from retrieval" is NOT supported and was
  removed; the catalog carries most of the accuracy (haiku 96.4% without
  retrieval despite 82.1% production-bank recall@50).
- Model gap: 17.3 pt with bare list, 8.0 pt with the full catalog.
