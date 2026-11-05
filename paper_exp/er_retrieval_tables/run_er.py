"""Experiment ER: retrieval-side numbers for paper Table 1 (BM25 backend only).

Recomputes, locally and without any API:
  1. label-recall@k, k in {5,10,25,50,100}
  2. rank-of-first-correct-op distribution (median, p90, % never in top-100)
  3. BM25 top-1 op accuracy, top-5 majority op accuracy (kNN cross-check)
  4. bank stats (rows, unique (text,op) pairs, cross-testcase repeats,
     op coverage vs eval truth labels, unreachable ops)
  5. per-query latency at k=50 (mean / p95 ms, time.perf_counter)

Protocol: eval queries = the 1,420 rows of cada/llm/examples.jsonl with case
test101-171; bank = cada/llm/public_examples.jsonl (940 rows); every query is
run with exclude_case=<its own case> (leave-one-testcase-out), exactly like
the production evaluation.  Ranks are positions in the deduplicated,
case-excluded list that Retriever.top_k returns — i.e. what the prompt sees.

Run:  cd /home/joey123230/ICCAD_A/Agent && .venv/bin/python paper_exp/er_retrieval_tables/run_er.py
"""
import csv
import json
import math
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict

REPO = "/home/joey123230/ICCAD_A/Agent"
OUT = os.path.join(REPO, "paper_exp", "er_retrieval_tables")
sys.path.insert(0, REPO)

from cada.llm.retrieval import Bm25Retriever, load_bank  # noqa: E402

KS = [5, 10, 25, 50, 100]


def case_num(case):
    m = re.match(r"test(\d+)$", case or "")
    return int(m.group(1)) if m else None


def pctl(sorted_vals, q):
    """Nearest-rank percentile on an already-sorted list."""
    if not sorted_vals:
        return None
    idx = min(int(math.ceil(q * len(sorted_vals))) - 1, len(sorted_vals) - 1)
    return sorted_vals[max(idx, 0)]


def main():
    bank = load_bank(os.path.join(REPO, "cada", "llm", "public_examples.jsonl"))
    rows = [json.loads(l) for l in open(os.path.join(REPO, "cada", "llm", "examples.jsonl"),
                                        encoding="utf-8") if l.strip()]
    queries = [r for r in rows if case_num(r["case"]) is not None
               and 101 <= case_num(r["case"]) <= 171]
    assert len(queries) == 1420, len(queries)
    assert len(bank) == 940, len(bank)

    ret = Bm25Retriever(bank)

    # ---------- bank stats ----------
    pair_cases = defaultdict(set)   # (text,op) -> set of cases
    pair_rows = Counter()           # (text,op) -> row count
    for r in bank:
        pair_cases[(r["text"], r["op"])].add(r.get("case"))
        pair_rows[(r["text"], r["op"])] += 1
    unique_pairs = len(pair_cases)
    pairs_multi_case = sum(1 for cs in pair_cases.values() if len(cs) > 1)
    rows_dup_of_earlier = 940 - unique_pairs
    bank_ops = Counter(r["op"] for r in bank)
    eval_ops = Counter(r["op"] for r in queries)
    unreachable = sorted(op for op in eval_ops if op not in bank_ops)

    # ---------- main retrieval pass: full ranking per query ----------
    full_k = len(bank)  # top_k dedups; asking for the whole bank gives the full ranking
    ranks = []          # rank of first row with op == truth (1-indexed), or None
    top1_hits = 0
    top5_major_hits = 0
    per_query = []
    for q in queries:
        hits = ret.top_k(q["text"], k=full_k, exclude_case=q["case"])
        truth = q["op"]
        rank = None
        for i, h in enumerate(hits, 1):
            if h["op"] == truth:
                rank = i
                break
        ranks.append(rank)
        top1_op = hits[0]["op"] if hits else None
        if top1_op == truth:
            top1_hits += 1
        top5_ops = [h["op"] for h in hits[:5]]
        c = Counter(top5_ops)
        best_n = max(c.values()) if c else 0
        # majority vote, ties broken by best (earliest) rank among tied ops
        top5_major = next((op for op in top5_ops if c[op] == best_n), None)
        if top5_major == truth:
            top5_major_hits += 1
        per_query.append({"case": q["case"], "line": q.get("line"), "truth_op": truth,
                          "first_correct_rank": rank if rank is not None else "",
                          "top1_op": top1_op, "top5_majority_op": top5_major,
                          "n_retrieved": len(hits)})

    n = len(queries)
    recall = {k: sum(1 for r in ranks if r is not None and r <= k) / n for k in KS}

    found = sorted(r for r in ranks if r is not None)
    never_100 = sum(1 for r in ranks if r is None or r > 100)
    never_any = sum(1 for r in ranks if r is None)
    med_found = statistics.median(found) if found else None
    p90_found = pctl(found, 0.90)
    # with never-retrieved treated as +inf
    all_ranks_inf = sorted((r if r is not None else math.inf) for r in ranks)
    med_all = statistics.median(all_ranks_inf)
    p90_all = pctl(all_ranks_inf, 0.90)

    # ---------- latency pass at k=50 ----------
    lat_ms = []
    for q in queries:
        t0 = time.perf_counter()
        ret.top_k(q["text"], k=50, exclude_case=q["case"])
        lat_ms.append((time.perf_counter() - t0) * 1000.0)
    lat_sorted = sorted(lat_ms)
    lat_mean = sum(lat_ms) / len(lat_ms)
    lat_p50 = statistics.median(lat_sorted)
    lat_p95 = pctl(lat_sorted, 0.95)
    lat_max = lat_sorted[-1]

    # ---------- write CSVs ----------
    with open(os.path.join(OUT, "recall_at_k.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["k", "hits", "n_queries", "label_recall"])
        for k in KS:
            w.writerow([k, sum(1 for r in ranks if r is not None and r <= k), n,
                        f"{recall[k]:.6f}"])

    rank_hist = Counter(r for r in ranks if r is not None)
    with open(os.path.join(OUT, "rank_of_first_correct_hist.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "n_queries"])
        for r in sorted(rank_hist):
            w.writerow([r, rank_hist[r]])
        w.writerow(["never_in_full_ranking", never_any])

    with open(os.path.join(OUT, "rank_stats.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["median_rank_found_only", med_found])
        w.writerow(["p90_rank_found_only", p90_found])
        w.writerow(["median_rank_never_as_inf", med_all])
        w.writerow(["p90_rank_never_as_inf", p90_all])
        w.writerow(["pct_never_retrieved_at_k100", f"{never_100 / n:.6f}"])
        w.writerow(["n_never_retrieved_at_k100", never_100])
        w.writerow(["n_never_in_full_ranking", never_any])

    with open(os.path.join(OUT, "knn_accuracy.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "hits", "n_queries", "accuracy"])
        w.writerow(["bm25_top1_op_accuracy", top1_hits, n, f"{top1_hits / n:.6f}"])
        w.writerow(["bm25_top5_majority_op_accuracy", top5_major_hits, n,
                    f"{top5_major_hits / n:.6f}"])

    with open(os.path.join(OUT, "bank_stats.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stat", "value"])
        w.writerow(["bank_rows", len(bank)])
        w.writerow(["unique_text_op_pairs", unique_pairs])
        w.writerow(["pairs_in_more_than_one_testcase", pairs_multi_case])
        w.writerow(["rows_that_duplicate_an_earlier_pair", rows_dup_of_earlier])
        w.writerow(["bank_distinct_ops", len(bank_ops)])
        w.writerow(["eval_distinct_truth_ops", len(eval_ops)])
        w.writerow(["eval_ops_with_zero_bank_examples", len(unreachable)])
        w.writerow(["bank_ops_not_in_eval", len(set(bank_ops) - set(eval_ops))])

    with open(os.path.join(OUT, "unreachable_ops.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["op", "n_eval_queries"])
        for op in unreachable:
            w.writerow([op, eval_ops[op]])

    with open(os.path.join(OUT, "latency_k50.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "ms"])
        w.writerow(["mean", f"{lat_mean:.4f}"])
        w.writerow(["p50", f"{lat_p50:.4f}"])
        w.writerow(["p95", f"{lat_p95:.4f}"])
        w.writerow(["max", f"{lat_max:.4f}"])
        w.writerow(["n_queries", len(lat_ms)])

    with open(os.path.join(OUT, "per_query_results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["case", "line", "truth_op", "first_correct_rank",
                                          "top1_op", "top5_majority_op", "n_retrieved"])
        w.writeheader()
        w.writerows(per_query)

    # ---------- console report ----------
    print("eval queries:", n, " bank rows:", len(bank))
    for k in KS:
        print(f"label-recall@{k}: {recall[k]*100:.2f}%")
    print(f"rank-of-first-correct: median={med_found} p90={p90_found} (found only); "
          f"median={med_all} p90={p90_all} (never=inf); "
          f"never@100={never_100} ({never_100/n*100:.2f}%); never in full ranking={never_any}")
    print(f"top1 acc: {top1_hits}/{n} = {top1_hits/n*100:.2f}%")
    print(f"top5 majority acc: {top5_major_hits}/{n} = {top5_major_hits/n*100:.2f}%")
    print(f"bank: rows=940 unique_pairs={unique_pairs} multi_case_pairs={pairs_multi_case} "
          f"dup_rows={rows_dup_of_earlier} bank_ops={len(bank_ops)} eval_ops={len(eval_ops)} "
          f"unreachable={unreachable}")
    print(f"latency k=50: mean={lat_mean:.3f}ms p50={lat_p50:.3f}ms p95={lat_p95:.3f}ms "
          f"max={lat_max:.3f}ms")
    # mean retrieved-list length at full k (dedup + exclusion ceiling)
    mean_ret = sum(p["n_retrieved"] for p in per_query) / n
    print(f"mean full-ranking length after dedup+exclusion: {mean_ret:.1f}")


if __name__ == "__main__":
    main()
