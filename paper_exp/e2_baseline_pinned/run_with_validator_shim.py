#!/usr/bin/env python3
"""scripts/route_eval.py with ONE evaluator-harness bugfix applied at runtime.

Bug (found in E2 run1, 2026-11-03, commit bbf5de5): in
cada/llm/allowed_intents.py:1281, ``_validate_param_values`` does
``if b not in BASIS_VALUES:`` where ``BASIS_VALUES`` is a set.  When the
model returns a non-string ``basis`` param (e.g. a dict or list), the set
membership test raises ``TypeError: unhashable type``, the evaluation
worker crashes, and route_eval's fail-fast aborts the whole run as
INVALID (observed on 2 test143 minimize_area sentences; 563 targets were
never attempted).

Intended fail-closed semantics: a malformed param value must *return a
validation error string* — which gives the model its single corrective
round-trip and otherwise counts as a routing failure — never crash the
harness.  This wrapper converts the TypeError into that error string and
changes nothing for any value the original code handles without raising.
Tracked repo files are not modified; the fix should be upstreamed later.

Usage: identical CLI to scripts/route_eval.py, e.g.
    .venv/bin/python paper_exp/e2_baseline_pinned/run_with_validator_shim.py \
        --cases test101-171 --retriever none --config configs/api_key.yaml ...
"""
import os
import sys

ROOT = "/home/joey123230/ICCAD_A/Agent"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import cada.llm.allowed_intents as ai  # noqa: E402

_orig_validate_param_values = ai._validate_param_values


def _safe_validate_param_values(intent, params):
    try:
        return _orig_validate_param_values(intent, params)
    except TypeError as exc:
        return (f'Invalid param value type for intent "{intent}" ({exc}); '
                'param values must be plain JSON strings or numbers as shown '
                'in the catalog.')


ai._validate_param_values = _safe_validate_param_values

import route_eval  # noqa: E402  (scripts/route_eval.py)

if __name__ == "__main__":
    raise SystemExit(route_eval.main())
