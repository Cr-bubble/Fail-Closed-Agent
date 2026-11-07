# E3 — haiku + BM25 k=50 post-dedup rerun (re-validation of 97.8%) — SKIPPED: QUOTA

- Date: 2026-11-03 (log UTC timestamps 2026-11-02T17:49)
- Repo: /home/joey123230/ICCAD_A/Agent, branch paper/routing-study, commit bbf5de5
- Model (exact, from script's `model=` line): **claude-haiku-4-5**, provider anthropic; retriever **bm25/k=50**; retrieval bank cada/llm/public_examples.jsonl (940 rows, post-dedup), eval bank cada/llm/examples.jsonl

## Verdict: smoke run INVALID (quota) → full run NOT ATTEMPTED (per protocol)

| run | command | result |
|---|---|---|
| smoke | `.venv/bin/python paper_exp/e3_haiku_k50/run_with_validator_shim.py --limit 50 --provider anthropic --retriever bm25 --top-k 50 --config configs/api_key.yaml --out paper_exp/e3_haiku_k50/smoke.jsonl` | **INVALID** (exit 2): `LLM client reported 8 exhausted/fatal completion(s); 42 target(s) not attempted after fail-fast`. Root cause: Anthropic API 400 `invalid_request_error` — "**Your credit balance is too low to access the Anthropic API**" on every call (8 fatal before fail-fast; request ids in smoke.log, e.g. req_011CgeXKFGyGRpCmA9rJxiDg). Wall 2.1s. |
| full (test101-171, 1,420 sentences) | not run | Skipped by rule: quota failure on smoke → record INVALID and do not retry-loop; the 67.2% incident showed degraded runs must never be scored. |

- Accuracy: **none reported** (script refuses on invalid runs; smoke.jsonl rows carry run_valid=false). Giveups/wrong-op: n/a.
- This is a billing failure (credit balance), not a rate limit — retrying cannot fix it; it needs credits purchased on the Anthropic account used by configs/api_key.yaml.

## Comparison vs historical

The pre-dedup, quota-interrupted **97.8%** headline remains UNVALIDATED. Do not cite it as confirmed; E3 must be re-run after Anthropic credits are topped up (then: same smoke-first protocol, serial, ~$1 full-run estimate; script's own estimate was $0.04/50 sentences ≈ $1.1/1,420 with caching).

## Caveats

1. Run used the same `run_with_validator_shim.py` as E2 run2 (wraps `allowed_intents._validate_param_values` so a non-string param value returns a validation error instead of crashing the harness — see E2 SUMMARY caveat 1). Irrelevant to this failure (no call succeeded) but keep using it on the re-run for comparability until the upstream fix lands.
2. The openai key on the same config worked minutes earlier (E2), so this is specific to the Anthropic account's balance, not the config file's structure.
3. BM25 retrieval path itself was verified locally pre-run (build_retriever('bm25') over 940-row bank returns 50 hits; no API involved).

## Files

- smoke.log — full stdout incl. the 8 fatal-error lines and INVALID banner
- smoke.jsonl — 50 rows, all run_valid=false (8 attempted-degraded, 42 aborted)
- run_with_validator_shim.py — wrapper (identical to E2's)
- run1.jsonl / run1.log — intentionally absent: full run never started

## 2026-11-08 FULL RUN — VALID (credits restored)

- Command: `.venv/bin/python scripts/route_eval.py --cases test101-171 --provider anthropic --retriever bm25 --top-k 50 --out paper_exp/e3_haiku_k50/run1.jsonl` (smoke `--limit 20` passed first; logs: smoke2.log, run1.log)
- Model: claude-haiku-4-5 (from script's model= line), retriever bm25/k=50, post-dedup bank, repo commit 6b5cac2 + fixes.
- **intent 1383/1420 = 97.4% | params 94.1% | object 92.7%**; failures 37 = 10 gave-up / 27 wrong-op.
- No degraded calls / INVALID banner → run valid. Cost ≈ $1.
- vs historical pre-dedup 97.8%: −0.4pt (6 sentences), consistent with dedup shrinking the example bank. N=1; CI comes with E4.
