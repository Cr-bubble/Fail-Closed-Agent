#!/usr/bin/env python3
"""E6 pilot: fault-injection harness for the fail-closed guard stack.

What it does
------------
Per (testcase, mode) job it drives the agent IN-PROCESS through the case's
prompt.txt in REGEX/rules mode (no API key, no network: `LLMClient.available`
is False without a key and `Fallback.translate` then returns None, so the LLM
path is physically dead).  On exactly one designated transform line it injects
a corruption, then independently re-verifies the FINAL netlist with the
evaluator's own HARD-check machinery (ABC cec vs original, structural bound
recheck, basis purity, netlist round-trip) plus one extra structural check of
our own (no multi-driven net).

Corruption modes (all at the dispatch level -- the repo is never edited;
monkeypatching is per-line and in-memory only):

  m1   wrong numeric param, TIGHTENED  (fanout bound k-1 instead of k).
       Simulated router emits {intent, params} with k-1; fed straight to
       Agent._dispatch_intent, exactly where real LLM output lands.
  m1w  wrong numeric param, WEAKENED   (k+1 instead of k).
  m2   wrong basis / wrong sibling transform family (e.g. NOR_NOT when
       NAND_NOT was requested; xnor_to_nand when NOR-only was requested).
  m2u  basis OUTSIDE the closed world (e.g. "NAND_NOR", which names no
       implemented basis) -- probes the closed-world contract.
  m3   target/net param redirected to a DIFFERENT EXISTING net (rename
       collision, wrong cone output, wrong buffered net).  Existing names are
       chosen deterministically at run time so the corruption would also pass
       the agent's name-grounding gate, as a plausible hallucination would.
  m3u  unsafe TRANSFORM BODY: the dispatched engine function is wrapped (via
       unittest.mock.patch.object, for that one line only) so that after the
       legitimate rewrite it additionally swaps one load between two different
       nets -- a fanout-NEUTRAL, function-CHANGING rewire.  This is the
       "corrupted/unsafe transform" axis of plan E6; it is the case the
       pre-commit equivalence gate + rollback exist for.
  m4   swapped to an entirely different (but implemented) transform intent.

Dispatch fidelity: corrupted {intent, params} go through
`Agent._invalid_name_params` first (recorded as `grounding_flag`) and then
`Agent._dispatch_intent(intent, params, line)` with `agent.use_rules`
temporarily False, replicating the pure-LLM build (`--no-rules`), where the
text-based misroute patches inside _dispatch_intent are disabled by design.
Exceptions are caught exactly as Agent.handle does ("Could not complete...").

Classification of one injected run (independent of what the agent claimed):
  CAUGHT   guard rejected + rolled back (response says reverted AND the design
           is structurally unchanged across the line), or the corruption was
           rejected before mutating (closed-world/exception, design unchanged),
           or the transform committed but the final netlist still satisfies
           EVERY user-derived HARD requirement (benign commit, e.g. an
           over-delivering k-1 bound).
  DRIFT    final netlist is functionally EQUIVALENT to the original and
           structurally valid, but violates a user-derived structural/basis
           HARD requirement: the guards enforced the corrupted contract, not
           the user's sentence.  Semantic drift / under-delivery, not an
           unsafe commit.
  ESCAPED  the final netlist violates functional equivalence to the original,
           fails netlist validity / round-trip, or contains a multi-driven
           net.  This is the class the fail-closed claim says must be empty.
  UNDECIDED  ABC/yosys could not decide equivalence (counted separately,
           never silently as caught).

Sub-category recorded per run: guard_rollback | closed_world_reject |
benign_commit | benign_noop | rescue (if a layer re-routed) etc.

Usage
-----
  .venv/bin/python paper_exp/e6_fault_injection/harness.py --list
  .venv/bin/python ... --one test21:clean          # smoke test, no injection
  .venv/bin/python ... --one test21:m1
  .venv/bin/python ... --all [--par 6]             # every job, subprocesses
  .venv/bin/python ... --report                    # runs/*.json -> results.md

Each job writes runs/<case>__<mode>.json + .transcript.txt.  Jobs run inside a
throwaway sandbox cwd (a copy of the one testcase dir) so *_out.v and *.log
never touch the repo.  Repo files are never modified.

Pinned context: repo commit bbf5de5, date 2026-11-03, ABC at
/home/joey123230/ICCAD_A/abc/abc via configs/tools.yaml (ABC_BIN also exported
by --all for belt and braces).  Pure stdlib + the repo itself.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # .../ICCAD_A/Agent
sys.path.insert(0, ROOT)

RUNS_DIR = os.path.join(HERE, "runs")
ABC_DEFAULT = "/home/joey123230/ICCAD_A/abc/abc"

# --- repo imports (read-only use) ----------------------------------------
from cada.io_.config import load_config                      # noqa: E402
from cada.main import _configure_tools                       # noqa: E402
from cada.agent.agent import Agent                           # noqa: E402
from cada.transform import buffering, rewrite                # noqa: E402
from evaluator.requirements import derive                    # noqa: E402
from evaluator.evaluate import evaluate_case, GOLDEN_DIR     # noqa: E402


# ==========================================================================
# job table
# ==========================================================================
# line: 1-based index over NON-EMPTY prompt lines (same numbering the
# evaluator uses).  expect_rx: sanity regex the designated line must match,
# so a prompt edit can never silently shift the injection onto the wrong line.
# corrupt: ("dispatch", intent, params) | ("unsafe", engine_fn_name)
# Params may contain placeholders resolved against the live netlist:
#   $EXISTING_NET   first (sorted) internal gate-output net != the true target
#   $OTHER_HIFO     first (sorted) net with >4 loads that isn't the true net
JOBS = {
    # ---- test21: global fanout bound k=4 ("no gate drives more than 4") --
    "test21:m1":  dict(line=4, expect_rx=r"no gate drives more than 4",
                       corrupt=("dispatch", "insert_buffers", {"k": 3}),
                       note="k-1: tightened bound (task's m1 example)"),
    "test21:m1w": dict(line=4, expect_rx=r"no gate drives more than 4",
                       corrupt=("dispatch", "insert_buffers", {"k": 5}),
                       note="k+1: weakened bound"),
    "test21:m3u": dict(line=4, expect_rx=r"no gate drives more than 4",
                       corrupt=("unsafe", "limit_fanout"),
                       note="load-swap rewire inside the dispatched transform"),
    "test21:m4":  dict(line=4, expect_rx=r"no gate drives more than 4",
                       corrupt=("dispatch", "merge_duplicates", {}),
                       note="intent swap: buffers -> merge duplicates"),
    # ---- test25: renames + cone-scoped depth opt (NAND_NOT) --------------
    "test25:m2":  dict(line=8, expect_rx=r"only NAND and NOT",
                       corrupt=("dispatch", "minimize_depth",
                                {"basis": "NOR_NOT", "scope": "n11[0]"}),
                       note="opt basis NOR_NOT when NAND_NOT requested"),
    "test25:m3":  dict(line=7, expect_rx=r"wire n74 to renamed_wire",
                       corrupt=("dispatch", "rename",
                                {"old": "n74", "new": "$EXISTING_NET",
                                 "kind": "signal"}),
                       note="rename target redirected to an existing net"),
    "test25:m4":  dict(line=8, expect_rx=r"only NAND and NOT",
                       corrupt=("dispatch", "remove_dangling", {}),
                       note="intent swap: depth opt -> remove dangling"),
    # ---- test26: cone(n10) -> NOR_NOT conversion -------------------------
    "test26:m2":  dict(line=4, expect_rx=r"cone of n10 to use only NOR",
                       corrupt=("dispatch", "convert_basis",
                                {"basis": "NAND_NOT", "scope": "n10"}),
                       note="cone basis NAND_NOT when NOR_NOT requested"),
    "test26:m2u": dict(line=4, expect_rx=r"cone of n10 to use only NOR",
                       corrupt=("dispatch", "convert_basis",
                                {"basis": "NAND_NOR", "scope": "n10"}),
                       note="basis outside the closed world ({NAND,NOR})"),
    "test26:m3":  dict(line=4, expect_rx=r"cone of n10 to use only NOR",
                       corrupt=("dispatch", "convert_basis",
                                {"basis": "NOR_NOT", "scope": "$EXISTING_NET"}),
                       note="cone target redirected to a different net"),
    "test26:m4":  dict(line=4, expect_rx=r"cone of n10 to use only NOR",
                       corrupt=("dispatch", "collapse_inverters", {}),
                       note="intent swap: cone convert -> collapse inverters"),
    # ---- test29: whole-design remap to AND_NOT ---------------------------
    "test29:m2":  dict(line=4, expect_rx=r"only AND and NOT",
                       corrupt=("dispatch", "convert_basis",
                                {"basis": "NOR_NOT"}),
                       note="whole-design basis NOR_NOT when AND_NOT requested"),
    "test29:m2u": dict(line=4, expect_rx=r"only AND and NOT",
                       corrupt=("dispatch", "convert_basis",
                                {"basis": "NAND_NOR"}),
                       note="basis outside the closed world"),
    "test29:m3u": dict(line=4, expect_rx=r"only AND and NOT",
                       corrupt=("unsafe", "to_basis"),
                       note="load-swap rewire inside the basis remap"),
    "test29:m4":  dict(line=4, expect_rx=r"only AND and NOT",
                       corrupt=("dispatch", "remove_dangling", {}),
                       note="intent swap: remap -> remove dangling"),
    # ---- test35: replace-all XNOR->NOR (targeted), rename ----------------
    "test35:m2":  dict(line=4, expect_rx=r"XNOR gates .* NOR-only",
                       corrupt=("dispatch", "xnor_to_nand", {}),
                       note="sibling transform: NAND cell when NOR-only asked"),
    "test35:m3":  dict(line=10, expect_rx=r"signal n7431 to renamed_wire",
                       corrupt=("dispatch", "rename",
                                {"old": "n7431", "new": "$EXISTING_NET",
                                 "kind": "signal"}),
                       note="rename target redirected to an existing net"),
    "test35:m4":  dict(line=4, expect_rx=r"XNOR gates .* NOR-only",
                       corrupt=("dispatch", "collapse_inverters", {}),
                       note="intent swap: xnor conversion -> collapse"),
    # ---- test38: per-net fanout bound on reset n1 (k=4), rename ----------
    "test38:m1":  dict(line=4, expect_rx=r"reset signal n1 .* at most 4",
                       corrupt=("dispatch", "insert_buffers",
                                {"net": "n1", "k": 3}),
                       note="k-1 on a named net"),
    "test38:m1w": dict(line=4, expect_rx=r"reset signal n1 .* at most 4",
                       corrupt=("dispatch", "insert_buffers",
                                {"net": "n1", "k": 5}),
                       note="k+1 on a named net"),
    "test38:m3":  dict(line=4, expect_rx=r"reset signal n1 .* at most 4",
                       corrupt=("dispatch", "insert_buffers",
                                {"net": "$OTHER_HIFO", "k": 4}),
                       note="buffered net redirected to a different net"),
    "test38:m3r": dict(line=13, expect_rx=r"signal n440 to renamed_wire",
                       corrupt=("dispatch", "rename",
                                {"old": "n440", "new": "$EXISTING_NET",
                                 "kind": "signal"}),
                       note="rename target redirected to an existing net"),
    "test38:m3u": dict(line=4, expect_rx=r"reset signal n1 .* at most 4",
                       corrupt=("unsafe", "limit_fanout"),
                       note="load-swap rewire inside the buffer transform"),
    "test38:m4":  dict(line=4, expect_rx=r"reset signal n1 .* at most 4",
                       corrupt=("dispatch", "collapse_inverters", {}),
                       note="intent swap: buffers -> collapse inverters"),
}
CASES = sorted({k.split(":")[0] for k in JOBS}, key=lambda c: int(c[4:]))
ALL_JOBS = [f"{c}:clean" for c in CASES] + sorted(JOBS)

# Harness-level supplemental HARD requirements: user-sentence bounds that
# evaluator.requirements.derive() provably does NOT emit (measurement blind
# spot found by this pilot).  test38 L4 "insert buffers on the reset signal n1
# to reduce its fanout to at most 4 loads per driver" matches none of derive's
# fanout regexes, so without this the per-net bound is never graded.  Checked
# on the post-line snapshot AND the final netlist, for clean and corrupted
# runs alike.
EXTRA_REQS = {
    "test38": [dict(line=4, kind="fanout_net", net="n1", k=4)],
}

UNSAFE_TARGETS = {
    "limit_fanout": (buffering, "limit_fanout"),
    "to_basis": (rewrite, "to_basis"),
}


# ==========================================================================
# helpers
# ==========================================================================
def _sig(nl):
    """Structural signature for exact changed/unchanged comparison."""
    if nl is None:
        return None
    return (tuple(sorted((g.type, g.out, tuple(g.ins)) for g in nl.gates)),
            tuple(sorted((f.name, f.d, f.q, f.clk, str(f.rn), str(f.sn))
                         for f in nl.dffs)),
            tuple(sorted(nl.pi)), tuple(sorted(nl.po)))


def _multi_driver(nl):
    """Nets with more than one driver (gate out / DFF q / PI). Extra HARD
    check of our own: the evaluator's round-trip check does not flag these."""
    drv = {}
    for g in nl.gates:
        drv.setdefault(g.out, []).append("gate:" + g.name)
    for f in nl.dffs:
        drv.setdefault(f.q, []).append("dff:" + f.name)
    for p in nl.pi:
        drv.setdefault(p, []).append("pi:" + p)
    return {n: d for n, d in drv.items() if len(d) > 1}


def _resolve_placeholders(params, nl, job_key):
    out = dict(params)
    true_nets = {str(v) for v in params.values() if isinstance(v, str)}
    for k, v in params.items():
        if v == "$EXISTING_NET":
            cands = sorted(g.out for g in nl.gates
                           if g.out not in true_nets and g.out not in nl.po)
            if not cands:
                raise RuntimeError(f"{job_key}: no candidate existing net")
            out[k] = cands[0]
        elif v == "$OTHER_HIFO":
            cands = sorted(g.out for g in nl.gates
                           if len(nl.loads(g.out)) > 4 and g.out not in true_nets)
            if not cands:
                cands = sorted(g.out for g in nl.gates
                               if g.out not in true_nets)
            out[k] = cands[0]
    return out


def _sim_eval(nl):
    """64-pattern random simulation over the IR (PI and DFF.Q are free
    sources, seeded rng, 64 patterns packed in one int).  Returns ev(net)."""
    import random
    rnd = random.Random(0xE6)
    M = (1 << 64) - 1
    drv = {g.out: g for g in nl.gates}
    val = {"1'b0": 0, "1'b1": M}
    for p in sorted(nl.pi):
        val[p] = rnd.getrandbits(64)
    for f in sorted(nl.dffs, key=lambda f: f.name):
        val[f.q] = rnd.getrandbits(64)
    sys.setrecursionlimit(1_000_000)

    def ev(n):
        if n in val:
            return val[n]
        g = drv.get(n)
        if g is None:
            val[n] = 0
            return 0
        a = ev(g.ins[0])
        b = ev(g.ins[1]) if len(g.ins) > 1 else None
        t = g.type
        if t == "and":
            r = a & b if b is not None else a
        elif t == "or":
            r = a | b if b is not None else a
        elif t == "nand":
            r = ~(a & b) & M if b is not None else ~a & M
        elif t == "nor":
            r = ~(a | b) & M if b is not None else ~a & M
        elif t == "xor":
            r = a ^ b if b is not None else a
        elif t == "xnor":
            r = ~(a ^ b) & M if b is not None else ~a & M
        elif t == "not":
            r = ~a & M
        else:                     # buf
            r = a
        val[n] = r
        return r
    return ev


def _tfi_nets(nl, net):
    """All nets in the transitive fanin of ``net`` (iterative)."""
    drv = {g.out: g for g in nl.gates}
    seen, stack = set(), [net]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        g = drv.get(n)
        if g is not None:
            stack.extend(g.ins)
    return seen


def _swap_two_loads(nl):
    """Fanout-neutral, FUNCTION-CHANGING rewire: swap ins[0] of the first two
    (sorted) gates whose first inputs simulate DIFFERENTLY under 64 random
    patterns (so the corruption is functionally real, not a swap of two
    copies of the same signal) and whose swap creates no combinational
    cycle.  Deterministic (fixed seed, sorted iteration)."""
    gs = sorted((g for g in nl.gates if g.ins), key=lambda g: g.name)
    ev = _sim_eval(nl)
    fallback = None
    for i, g1 in enumerate(gs):
        for g2 in gs[i + 1:]:
            a, b = g1.ins[0], g2.ins[0]
            if a == b or b == g1.out or a == g2.out:
                continue
            if fallback is None:
                fallback = (g1, g2)
            if ev(a) == ev(b):
                continue
            # no cycle: g1 must not feed b's cone, g2 must not feed a's cone
            if g1.out in _tfi_nets(nl, b) or g2.out in _tfi_nets(nl, a):
                continue
            g1.ins[0], g2.ins[0] = b, a
            return (f"swapped load: {g1.name}.in0 {a}->{b}, "
                    f"{g2.name}.in0 {b}->{a} (sim-verified differing)")
    if fallback is not None:                      # last resort, may be benign
        g1, g2 = fallback
        a, b = g1.ins[0], g2.ins[0]
        g1.ins[0], g2.ins[0] = b, a
        return (f"swapped load: {g1.name}.in0 {a}->{b}, {g2.name}.in0 "
                f"{b}->{a} (NO differing pair found; may be equivalent)")
    raise RuntimeError("no swappable load pair found")


def _corrupted_dispatch(agent, line, intent, params):
    """Feed corrupted {intent, params} where real LLM output lands.

    use_rules is forced False for the one call so the text-based misroute
    patches inside _dispatch_intent stay off, as in the pure-LLM build this
    models.  Exceptions are rendered exactly as Agent.handle renders them.
    """
    obj = {"intent": intent, "params": params}
    grounding = agent._invalid_name_params(obj)   # telemetry only: with no LLM
    saved = agent.use_rules                       # available, handle() would
    agent.use_rules = False                       # dispatch the object anyway
    try:
        return agent._dispatch_intent(intent, params, line), grounding
    except Exception as exc:
        return f"Could not complete the request ({exc}).", grounding
    finally:
        agent.use_rules = saved


# ==========================================================================
# one job
# ==========================================================================
def run_job(job_key: str) -> dict:
    case, mode = job_key.split(":")
    job = None if mode == "clean" else JOBS[job_key]
    case_dir = os.path.join(ROOT, "testcase", case)
    prompt = os.path.join(case_dir, "prompt.txt")
    with open(prompt) as fh:
        raw = [ln.strip() for ln in fh if ln.strip()]
    if job is not None:
        li = job["line"]
        assert re.search(job["expect_rx"], raw[li - 1]), \
            f"{job_key}: line {li} does not match {job['expect_rx']!r}: {raw[li-1]!r}"

    # sandbox cwd: copy of this one testcase dir; *_out.v / *.log land here
    sandbox = tempfile.mkdtemp(prefix=f"e6_{case}_{mode}_")
    oldcwd = os.getcwd()
    shutil.copytree(case_dir, os.path.join(sandbox, "testcase", case),
                    ignore=shutil.ignore_patterns("*_out.v"))
    os.chdir(sandbox)
    t0 = time.time()
    try:
        cfg = load_config(None)                 # defaults; NO api key -> LLM dead
        _configure_tools(cfg, None)             # registers configs/tools.yaml (abc)
        agent = Agent(cfg, use_rules=True, use_bm25=False)

        lines, responses, specs, snaps = [], [], [], {}
        extra_snaps = {}
        transform_before, seen_transform = [], False
        inj = {"applied": False}
        for i, line in enumerate(raw, start=1):
            spec = derive(line)
            if job is not None and i == job["line"]:
                sig_before = _sig(agent.state.current)
                kind = job["corrupt"][0]
                if kind == "dispatch":
                    intent, params = job["corrupt"][1], dict(job["corrupt"][2])
                    params = _resolve_placeholders(params, agent.state.current,
                                                   job_key)
                    resp, grounding = _corrupted_dispatch(agent, line, intent,
                                                          params)
                    inj.update(kind="dispatch", intent=intent, params=params,
                               grounding_flag=grounding)
                else:                                     # unsafe engine body
                    modobj, fname = UNSAFE_TARGETS[job["corrupt"][1]]
                    realfn, detail = getattr(modobj, fname), {}

                    def wrapped(nl, *a, **kw):
                        r = realfn(nl, *a, **kw)
                        detail["rewire"] = _swap_two_loads(nl)
                        return r
                    with mock.patch.object(modobj, fname, wrapped):
                        resp = agent.handle(line, i)
                    inj.update(kind="unsafe", target=job["corrupt"][1],
                               rewire=detail.get("rewire", "NOT APPLIED"))
                sig_after = _sig(agent.state.current)
                inj.update(applied=True, line=i, line_text=line,
                           response=resp,
                           design_changed=(sig_before != sig_after))
            else:
                resp = agent.handle(line, i)
            lines.append(line); responses.append(resp); specs.append(spec)
            transform_before.append(seen_transform)
            if any(r.kind in ("basis", "gate_absent", "max_fanout",
                              "max_fanout_net") for r in spec.requirements) \
                    and agent.state.current is not None:
                snaps[i] = agent.state.current.snapshot()
            if any(x["line"] == i for x in EXTRA_REQS.get(case, ())) \
                    and agent.state.current is not None:
                extra_snaps[i] = agent.state.current.snapshot()
            if spec.is_transform:
                seen_transform = True

        run = {"case": case, "lines": lines, "responses": responses,
               "specs": specs, "snaps": snaps,
               "transform_before": transform_before,
               "original": agent.state.original,
               "final": agent.state.current,
               "vfile": os.path.join(case_dir, f"{case}.v")}
        results = evaluate_case(run, GOLDEN_DIR, update_golden=False)
        mdrv = _multi_driver(agent.state.current) \
            if agent.state.current is not None else {}
        extra_hard = []
        from evaluator import checks as ev_checks
        for xr in EXTRA_REQS.get(case, ()):
            if xr["kind"] != "fanout_net":
                continue
            vals = {}
            snap = extra_snaps.get(xr["line"])
            if snap is not None:
                vals["post-line"] = ev_checks.fanout_of(snap, xr["net"])
            if agent.state.current is not None:
                vals["final"] = ev_checks.fanout_of(agent.state.current,
                                                    xr["net"])
            ok = vals and all(v <= xr["k"] for v in vals.values())
            extra_hard.append(dict(
                label=f"L{xr['line']} fanout({xr['net']})<={xr['k']} "
                      "[harness-extra]",
                status="PASS" if ok else "FAIL",
                detail=json.dumps(vals)))
    finally:
        os.chdir(oldcwd)
        shutil.rmtree(sandbox, ignore_errors=True)

    hard = [dict(label=c.label, status=c.status, detail=c.detail)
            for c in results if c.group == "HARD"] + extra_hard
    other = [dict(group=c.group, label=c.label, status=c.status,
                  detail=c.detail) for c in results if c.group != "HARD"]
    if mdrv:
        hard.append(dict(label="no-multi-driven-net", status="FAIL",
                         detail=json.dumps({k: v for k, v in
                                            list(mdrv.items())[:3]})))
    else:
        hard.append(dict(label="no-multi-driven-net", status="PASS", detail=""))

    out = {"job": job_key, "case": case, "mode": mode,
           "date": "2026-11-03", "commit": "bbf5de5",
           "note": (job or {}).get("note", "uncorrupted baseline"),
           "injection": inj, "hard": hard, "other": other,
           "wall_s": round(time.time() - t0, 1)}
    out["outcome"] = _classify(out)

    os.makedirs(RUNS_DIR, exist_ok=True)
    base = os.path.join(RUNS_DIR, f"{case}__{mode}")
    with open(base + ".transcript.txt", "w") as fh:
        for i, (l, r) in enumerate(zip(lines, responses), 1):
            mark = " [CORRUPTED]" if inj.get("line") == i else ""
            fh.write(f"--- L{i}{mark} ---\n> {l}\n{r}\n")
    with open(base + ".json", "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    return out


def _classify(out) -> dict:
    """CAUGHT / DRIFT / ESCAPED / UNDECIDED per the rules in the docstring."""
    hard = out["hard"]
    inj = out["injection"]
    fails = [h for h in hard if h["status"] == "FAIL"]
    nas = [h for h in hard if h["status"] == "NA"]
    equiv_bad = [h for h in fails if h["label"] in
                 ("equiv-to-original", "valid-output-netlist",
                  "no-multi-driven-net")]
    if out["mode"] == "clean":
        st = "BASELINE_PASS" if not fails and not nas else "BASELINE_FAIL"
        return {"status": st, "sub": "", "hard_fails": [h["label"] for h in fails]}

    resp = inj.get("response", "")
    changed = inj.get("design_changed", True)
    rolled = (not changed) and ("reverted" in resp)
    # A REJECT is an explicit refusal before/at commit (exception surfaced or
    # parameter outside the closed world).  A swapped intent that merely
    # happens to no-op is NOT a reject: the agent reported doing something
    # else, so an unmet user requirement there is semantic drift.
    rejected = (not changed) and (resp.startswith("Could not complete")
                                  or resp.startswith("Could not determine"))

    if equiv_bad:
        return {"status": "ESCAPED",
                "sub": "unsafe final netlist",
                "hard_fails": [h["label"] for h in fails]}
    if rolled:
        return {"status": "CAUGHT", "sub": "guard_rollback",
                "hard_fails": [h["label"] for h in fails]}
    if rejected:
        return {"status": "CAUGHT", "sub": "closed_world_reject",
                "hard_fails": [h["label"] for h in fails]}
    if nas:
        return {"status": "UNDECIDED", "sub": "equivalence NA",
                "hard_fails": [h["label"] for h in fails]}
    if not fails:
        return {"status": "CAUGHT",
                "sub": "benign_commit" if changed else "benign_noop",
                "hard_fails": []}
    return {"status": "DRIFT",
            "sub": ("corrupted contract enforced" if changed
                    else "no-op under corrupted intent, request unfulfilled"),
            "hard_fails": [h["label"] for h in fails]}


# ==========================================================================
# driver / report
# ==========================================================================
def run_all(par: int):
    env = dict(os.environ, PYTHONHASHSEED="0", ABC_BIN=ABC_DEFAULT)
    pending = list(ALL_JOBS)
    procs, done = {}, []
    while pending or procs:
        while pending and len(procs) < par:
            jk = pending.pop(0)
            p = subprocess.Popen([sys.executable, os.path.abspath(__file__),
                                  "--one", jk],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.PIPE, text=True, env=env,
                                 cwd=ROOT)
            procs[jk] = (p, time.time())
        time.sleep(2)
        for jk, (p, t0) in list(procs.items()):
            if p.poll() is not None:
                err = p.stderr.read()[-2000:]
                done.append(jk)
                print(f"[{len(done)}/{len(ALL_JOBS)}] {jk}: rc={p.returncode} "
                      f"({time.time()-t0:.0f}s)" + (f"\n{err}" if p.returncode else ""),
                      flush=True)
                del procs[jk]
            elif time.time() - t0 > 2400:
                p.kill()
                print(f"TIMEOUT {jk}", flush=True)
                del procs[jk]
    report()


def report():
    rows = []
    for f in sorted(os.listdir(RUNS_DIR)):
        if f.endswith(".json"):
            rows.append(json.load(open(os.path.join(RUNS_DIR, f))))
    for r in rows:                      # re-classify from stored evidence so a
        r["outcome"] = _classify(r)     # classifier fix never needs re-running
    rows.sort(key=lambda r: (int(r["case"][4:]), r["mode"]))
    lines = ["| case | mode | outcome | sub-category | HARD fails | corrupted-line response (head) | s |",
             "|---|---|---|---|---|---|---|"]
    tally = {}
    for r in rows:
        o = r["outcome"]
        tally[o["status"]] = tally.get(o["status"], 0) + 1
        resp = (r["injection"].get("response", "") or "")[:90].replace("|", "/")
        lines.append(f"| {r['case']} | {r['mode']} | {o['status']} | {o['sub']} | "
                     f"{', '.join(o['hard_fails']) or '-'} | {resp} | {r['wall_s']} |")
    lines.append("")
    lines.append("Tally: " + ", ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    txt = "\n".join(lines)
    with open(os.path.join(HERE, "results.md"), "w") as fh:
        fh.write("# E6 pilot results (case x mode)\n\n" + txt + "\n")
    print(txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", help="run one job, e.g. test21:m1 or test21:clean")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--par", type=int, default=6)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.list:
        for jk in ALL_JOBS:
            j = JOBS.get(jk, {})
            print(jk, "-", j.get("note", "clean baseline"))
        return 0
    if args.one:
        out = run_job(args.one)
        print(json.dumps(out["outcome"], indent=1))
        print("corrupted-line response:",
              out["injection"].get("response", "(clean)")[:200])
        return 0
    if args.all:
        run_all(args.par)
        return 0
    if args.report:
        report()
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
