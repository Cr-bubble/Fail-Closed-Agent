# E6 corruption modes — exact semantics

Injection point: the corrupted `{intent, params}` object is fed to
`Agent._dispatch_intent(intent, params, line)` — the exact landing point of
real LLM router output — with `agent.use_rules=False` for that one call, so
the text-based misroute patches (which exist only in rules builds and are
disabled in the shipped pure-LLM binary via `--no-rules`) cannot rescue it.
The object is first shown to `Agent._invalid_name_params` (the name-grounding
gate); its verdict is recorded as `grounding_flag` but, as in the real
pipeline with an unreachable retranslation LLM, the object is dispatched
regardless. All other lines of the case run through the normal regex router
(rules mode, LLM physically unavailable: no API key loaded).

| mode | corruption | guard layer it probes |
|------|-----------|------------------------|
| m1   | numeric param tightened: fanout bound k-1 | contract-vs-sentence gap (benign direction) |
| m1w  | numeric param weakened: k+1 | contract-vs-sentence gap (harmful direction) |
| m2   | wrong-but-implemented basis / sibling transform (NOR_NOT for NAND_NOT; xnor_to_nand for "NOR-only") | basis-purity gate enforces the corrupted contract |
| m2u  | basis outside the closed world ("NAND_NOR") | closed-world contract (`assert basis in BASES`) |
| m3/m3r | name param redirected to a DIFFERENT existing net (rename collision; wrong cone output; wrong buffered net) — existing names chosen so the name-grounding gate passes | name-grounding + whatever guards the op has (rename has none) |
| m3u  | transform BODY corrupted: after the legitimate rewrite, one load is swapped between two different nets (fanout-neutral, function-changing) via `unittest.mock.patch.object` on the engine fn for that line only | pre-commit equivalence gate (ABC cec) + snapshot rollback |
| m4   | swapped to an entirely different implemented transform intent | nothing: measures bounded damage of pure misrouting |

Outcome classes (decided from independent re-verification of the final
netlist, never from the agent's own claims):

- **CAUGHT / guard_rollback** — response says reverted AND the design is
  bit-identical across the line (structural signature compare).
- **CAUGHT / closed_world_reject** — explicit refusal ("Could not
  complete/determine ..."), design unchanged.
- **CAUGHT / benign_commit|benign_noop** — corruption executed but the final
  netlist still satisfies EVERY user-derived HARD requirement.
- **DRIFT** — final netlist functionally equivalent + structurally valid, but
  a user-derived structural/basis HARD requirement is violated (guards
  enforced the corrupted contract, not the sentence). Includes swapped
  intents that no-op while the user's transform never happens.
- **ESCAPED** — final netlist not equivalent to original, or invalid
  (round-trip fail / multi-driven net). The fail-closed claim says this class
  must be empty.
- **UNDECIDED** — equivalence oracle returned neither True nor False.

Independent verification per run = evaluator's own HARD derivation
(`evaluator.requirements.derive` + `evaluator.evaluate.evaluate_case`):
ABC cec final-vs-original, per-line structural bound recheck, basis purity,
gate-absence, netlist round-trip — plus one harness-added check: no
multi-driven net (the round-trip check alone does not flag driver merges).
