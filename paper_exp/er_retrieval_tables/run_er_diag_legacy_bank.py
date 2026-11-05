"""ER diagnostic: reproduce the DOCUMENTED historical recall numbers.

Hypothesis: the numbers in cada/llm/retrieval.py docstrings and
docs/ROUTING_ACCURACY_RESULTS_ZH.md §3.3 (bm25 recall@25 93.9%, recall@50
96.4%, union@50 98.7%) were measured with the retrieval bank =
cada/llm/examples.jsonl itself (2130 rows, cases test91-171), where
leave-one-testcase-out actually excludes rows.  The current production bank
(public_examples.jsonl, 940 rows, cases test01-40 + beta0813_*) shares no
case names with the eval queries, so exclude_case is a no-op there.

This script re-runs the same recall measurement with the legacy bank.
Diagnostic only — the headline ER numbers stay on the assigned protocol.

Run:  cd /home/joey123230/ICCAD_A/Agent && .venv/bin/python paper_exp/er_retrieval_tables/run_er_diag_legacy_bank.py
"""
import csv
import json
import os
import re
import sys

REPO = "/home/joey123230/ICCAD_A/Agent"
OUT = os.path.join(REPO, "paper_exp", "er_retrieval_tables")
sys.path.insert(0, REPO)

from cada.llm.retrieval import Bm25Retriever, load_bank  # noqa: E402

KS = [5, 10, 25, 50, 100]


def case_num(case):
    m = re.match(r"test(\d+)$", case or "")
    return int(m.group(1)) if m else None


def topk_nodedup(ret, query, k, exclude_case):
    """Emulate the pre-dedup top_k: same ranking, no (text,op) seen-set."""
    ranked = sorted(range(len(ret.bank)), key=ret.scores(query).__getitem__,
                    reverse=True)
    out = []
    for i in ranked:
        row = ret.bank[i]
        if exclude_case and row.get("case") == exclude_case:
            continue
        out.append(row)
        if len(out) >= k:
            break
    return out


def recall_run(bank, queries, label, dedup=True, knn=False):
    from collections import Counter
    ret = Bm25Retriever(bank)
    ranks = []
    top1 = top5 = 0
    for q in queries:
        if dedup:
            hits = ret.top_k(q["text"], k=100, exclude_case=q["case"])
        else:
            hits = topk_nodedup(ret, q["text"], 100, q["case"])
        rank = next((i for i, h in enumerate(hits, 1) if h["op"] == q["op"]), None)
        ranks.append(rank)
        if knn and hits:
            if hits[0]["op"] == q["op"]:
                top1 += 1
            ops5 = [h["op"] for h in hits[:5]]
            c = Counter(ops5)
            best = max(c.values())
            if next(op for op in ops5 if c[op] == best) == q["op"]:
                top5 += 1
    n = len(queries)
    out = {k: sum(1 for r in ranks if r is not None and r <= k) / n for k in KS}
    print(f"[{label}] bank_rows={len(bank)} dedup={dedup}")
    for k in KS:
        print(f"  label-recall@{k}: {out[k]*100:.2f}%")
    if knn:
        out["top1"] = top1 / n
        out["top5_majority"] = top5 / n
        print(f"  top1={top1/n*100:.2f}%  top5-majority={top5/n*100:.2f}%")
    return out


def main():
    rows = [json.loads(l) for l in open(os.path.join(REPO, "cada", "llm", "examples.jsonl"),
                                        encoding="utf-8") if l.strip()]
    queries = [r for r in rows if case_num(r["case"]) is not None
               and 101 <= case_num(r["case"]) <= 171]
    assert len(queries) == 1420

    results = {}
    # A: legacy bank = examples.jsonl itself (2130 rows), LOTO bites, dedup (current code)
    results["legacy_examples2130_loto_dedup"] = recall_run(
        rows, queries, "legacy examples.jsonl 2130 LOTO", knn=True)
    # A': same, PRE-dedup top-k (the code before the dedup seen-set was added)
    results["legacy_examples2130_loto_nodedup"] = recall_run(
        rows, queries, "legacy examples.jsonl 2130 LOTO pre-dedup", dedup=False)
    # B: bank = test91-100 split only (710 rows), natural leave-out
    b91 = [r for r in rows if case_num(r["case"]) is not None and case_num(r["case"]) <= 100]
    results[f"test91_100_bank{len(b91)}_dedup"] = recall_run(b91, queries, "test91-100 bank")
    # C: assigned protocol again for side-by-side (public bank 940)
    pub = load_bank(os.path.join(REPO, "cada", "llm", "public_examples.jsonl"))
    results["public940_assigned_dedup"] = recall_run(pub, queries, "public_examples.jsonl 940")
    # D: combined public + examples (LOTO)
    results["public940_plus_examples2130_loto_dedup"] = recall_run(
        pub + rows, queries, "public940+examples2130 LOTO")

    with open(os.path.join(OUT, "diagnostic_bank_variants_recall.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bank_variant"] + [f"recall@{k}" for k in KS] +
                   ["top1_acc", "top5_majority_acc"])
        for name, rec in results.items():
            w.writerow([name] + [f"{rec[k]:.6f}" for k in KS] +
                       [f"{rec[x]:.6f}" if x in rec else "" for x in ("top1", "top5_majority")])
    print("documented (legacy): bm25 recall@25=93.9%, recall@50=96.4% (results doc §3.3) "
          "/ 97.0% (§3.2); union@50=98.7-98.8% (needs ONNX, not reproducible here)")


if __name__ == "__main__":
    main()
