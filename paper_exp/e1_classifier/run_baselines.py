#!/usr/bin/env python
"""E1: supervised intent-classifier baselines for NL->op routing.

Answers: could a trained classifier replace the LLM for intent (op) selection?
Scope: predicts `op` ONLY — no param extraction (the LLM pipeline also fills a
params schema; keep that scope difference in mind when comparing numbers).

Protocols (both leave-one-testcase-out at CASE granularity — a sentence's own
case never contributes training rows):
  a (resource-matched): train only on public_examples.jsonl rows with
     case != query case.  NOTE: the public bank contains no test101-171 case
     names, so the exclusion is vacuous there and one fit covers all folds.
  b (max-data): train on public_examples.jsonl + examples.jsonl rows with
     case != query case, deduplicating identical (text, op) pairs (first
     occurrence wins, public bank first).

Models (all deterministic, seeds fixed):
  tfidf_logreg    TF-IDF union (word 1-2gram + char_wb 3-5gram) +
                  LogisticRegression(random_state=0, max_iter=2000)
  tfidf_linearsvc same features + LinearSVC(random_state=0)
  bm25_top1       cada.llm.retrieval.Bm25Retriever, top-1 neighbour's op
  bm25_vote5      same retriever, majority vote over top-5 (ties -> the op
                  whose first occurrence ranks highest)

Eval set: examples.jsonl rows whose case matches ^test(\\d+)$ with
101 <= n <= 171 (exactly 1,420 rows, 71 cases x 20 lines).

Usage (from the repo root, with the E1 venv):
  paper_exp/e1_classifier/.venv/bin/python paper_exp/e1_classifier/run_baselines.py \
      --repo /home/joey123230/ICCAD_A/Agent \
      --out  /home/joey123230/ICCAD_A/Agent/paper_exp/e1_classifier \
      --jobs 8
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

# Keep BLAS threads modest; parallelism lives at the fold level.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

CASE_RE = re.compile(r"^test(\d+)$")
EVAL_LO, EVAL_HI = 101, 171
MODELS = ["tfidf_logreg", "tfidf_linearsvc", "bm25_top1", "bm25_vote5"]
PROTOCOLS = ["a", "b"]

_REPO = None  # set in main / inherited by forked workers


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def eval_case_num(case):
    m = CASE_RE.match(case or "")
    if not m:
        return None
    n = int(m.group(1))
    return n if EVAL_LO <= n <= EVAL_HI else None


def dedup_text_op(rows):
    out, seen = [], set()
    for r in rows:
        key = (r["text"], r["op"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def make_sklearn_models():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.svm import LinearSVC

    def features():
        return FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2))),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))),
        ])

    return {
        "tfidf_logreg": Pipeline([
            ("feat", features()),
            ("clf", LogisticRegression(random_state=0, max_iter=2000)),
        ]),
        "tfidf_linearsvc": Pipeline([
            ("feat", features()),
            ("clf", LinearSVC(random_state=0)),
        ]),
    }


def bm25_predict(retriever, text, case):
    hits = retriever.top_k(text, 5, exclude_case=case)
    ops = [h["op"] for h in hits]
    top1 = ops[0] if ops else "<no-prediction>"
    if ops:
        cnt = Counter(ops)
        best = max(cnt.values())
        vote = next(op for op in ops if cnt[op] == best)  # tie -> best rank
    else:
        vote = "<no-prediction>"
    return top1, vote


def run_pool(args):
    """One unique training pool: fit every model once, predict its eval rows.

    args = (protocol, train_rows, eval_rows); eval_rows carry their own case.
    Returns per-row prediction dicts.  Deterministic: fixed seeds, fixed row
    order, no state shared across pools.
    """
    protocol, train_rows, eval_rows = args
    sys.path.insert(0, _REPO)
    from cada.llm.retrieval import Bm25Retriever

    texts = [r["text"] for r in train_rows]
    labels = [r["op"] for r in train_rows]
    train_ops = set(labels)

    fitted = {}
    for name, model in make_sklearn_models().items():
        model.fit(texts, labels)
        fitted[name] = model
    retriever = Bm25Retriever(train_rows)

    eval_texts = [r["text"] for r in eval_rows]
    sk_preds = {name: list(m.predict(eval_texts)) for name, m in fitted.items()}

    out = []
    for i, r in enumerate(eval_rows):
        top1, vote = bm25_predict(retriever, r["text"], r["case"])
        preds = {
            "tfidf_logreg": sk_preds["tfidf_logreg"][i],
            "tfidf_linearsvc": sk_preds["tfidf_linearsvc"][i],
            "bm25_top1": top1,
            "bm25_vote5": vote,
        }
        out.append({
            "protocol": protocol,
            "case": r["case"],
            "line": r["line"],
            "text": r["text"],
            "gold": r["op"],
            "gold_reachable": r["op"] in train_ops,
            "train_size": len(train_rows),
            "preds": preds,
        })
    return out


def build_tasks(protocol, public, examples, eval_rows, cases):
    """Group per-case folds by identical training pool (saves vacuous refits)."""
    pool = public if protocol == "a" else public + examples
    pool_cases = {r["case"] for r in pool}
    groups = {}
    for case in cases:
        key = case if case in pool_cases else "__full__"
        groups.setdefault(key, []).append(case)
    tasks = []
    for key, case_list in sorted(groups.items()):
        if key == "__full__":
            train = list(pool)
        else:
            train = [r for r in pool if r["case"] != key]
        if protocol == "b":
            train = dedup_text_op(train)
        evs = [r for r in eval_rows if r["case"] in set(case_list)]
        tasks.append((protocol, train, evs))
    return tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/home/joey123230/ICCAD_A/Agent")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--limit-cases", type=int, default=0,
                    help="smoke test: only the first N eval cases")
    args = ap.parse_args()

    global _REPO
    _REPO = os.path.abspath(args.repo)
    sys.path.insert(0, _REPO)
    os.makedirs(args.out, exist_ok=True)

    t0 = time.time()
    examples = load_jsonl(os.path.join(_REPO, "cada/llm/examples.jsonl"))
    public = load_jsonl(os.path.join(_REPO, "cada/llm/public_examples.jsonl"))
    eval_rows = [r for r in examples if eval_case_num(r.get("case")) is not None]
    cases = sorted({r["case"] for r in eval_rows}, key=lambda c: int(c[4:]))
    if args.limit_cases:
        cases = cases[: args.limit_cases]
        eval_rows = [r for r in eval_rows if r["case"] in set(cases)]
    assert args.limit_cases or len(eval_rows) == 1420, len(eval_rows)

    all_tasks = []
    for protocol in PROTOCOLS:
        all_tasks += build_tasks(protocol, public, examples, eval_rows, cases)
    print(f"{len(eval_rows)} eval rows, {len(cases)} cases, "
          f"{len(all_tasks)} unique training pools", flush=True)

    rows_out = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, res in enumerate(ex.map(run_pool, all_tasks)):
            rows_out.extend(res)
            if (i + 1) % 10 == 0 or i + 1 == len(all_tasks):
                print(f"  pools done: {i + 1}/{len(all_tasks)} "
                      f"({time.time() - t0:.0f}s)", flush=True)
    rows_out.sort(key=lambda r: (r["protocol"], int(r["case"][4:]), r["line"]))

    with open(os.path.join(args.out, "predictions.jsonl"), "w",
              encoding="utf-8") as fh:
        for r in rows_out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Accuracy table
    import sklearn
    results = []
    for protocol in PROTOCOLS:
        sub = [r for r in rows_out if r["protocol"] == protocol]
        if not sub:
            continue
        n_unreach = sum(1 for r in sub if not r["gold_reachable"])
        for model in MODELS:
            n_ok = sum(1 for r in sub if r["preds"][model] == r["gold"])
            ok_reach = sum(1 for r in sub
                           if r["gold_reachable"] and r["preds"][model] == r["gold"])
            n_reach = len(sub) - n_unreach
            results.append({
                "model": model, "protocol": protocol, "n_eval": len(sub),
                "n_correct": n_ok, "accuracy": round(n_ok / len(sub), 4),
                "n_gold_unreachable": n_unreach,
                "accuracy_on_reachable": round(ok_reach / n_reach, 4) if n_reach else "",
            })
    with open(os.path.join(args.out, "results.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

    # Confusions for the best (model, protocol)
    best = max(results, key=lambda r: (r["accuracy"], r["model"]))
    sub = [r for r in rows_out if r["protocol"] == best["protocol"]]
    conf = Counter((r["gold"], r["preds"][best["model"]]) for r in sub
                   if r["preds"][best["model"]] != r["gold"])
    with open(os.path.join(args.out, "confusion_best.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gold", "pred", "count"])
        for (g, p), c in conf.most_common():
            w.writerow([g, p, c])

    meta = {
        "date": "2026-11-03",
        "repo_commit": "bbf5de5",
        "python": sys.version.split()[0],
        "sklearn": sklearn.__version__,
        "eval_rows": len(eval_rows),
        "eval_cases": len(cases),
        "runtime_sec": round(time.time() - t0, 1),
        "best": best,
    }
    with open(os.path.join(args.out, "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)

    print(json.dumps(meta, indent=2))
    for r in results:
        print(f"{r['model']:16s} protocol={r['protocol']}  "
              f"acc={r['accuracy']:.4f} ({r['n_correct']}/{r['n_eval']})  "
              f"reachable-only={r['accuracy_on_reachable']}")


if __name__ == "__main__":
    main()
