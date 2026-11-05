# E6 pilot results (case x mode)

| case | mode | outcome | sub-category | HARD fails | corrupted-line response (head) | s |
|---|---|---|---|---|---|---|
| test21 | clean | BASELINE_PASS |  | - |  | 0.1 |
| test21 | m1 | CAUGHT | benign_commit | - | Inserted 72 buffer(s) so that no driver exceeds 3 loads; max-fanout bound and equivalence  | 0.1 |
| test21 | m1w | DRIFT | corrupted contract enforced | L4 max-fanout<=4 (gates) | Inserted 22 buffer(s) so that no driver exceeds 5 loads; max-fanout bound and equivalence  | 0.1 |
| test21 | m3u | CAUGHT | guard_rollback | L4 max-fanout<=4 (gates) | The buffer insertion was reverted: functional equivalence violated. | 0.1 |
| test21 | m4 | DRIFT | no-op under corrupted intent, request unfulfilled | L4 max-fanout<=4 (gates) | Merged 0 structurally-duplicate gate(s); equivalence verified. | 0.1 |
| test25 | clean | BASELINE_PASS |  | - |  | 287.1 |
| test25 | m2 | CAUGHT | benign_commit | - | Reduced the maximum logic depth from 49 to 11 (basis preserved); equivalence verified. | 287.0 |
| test25 | m3 | ESCAPED | unsafe final netlist | equiv-to-original, no-multi-driven-net | Renamed signal n74 to n100 and updated all references. | 288.7 |
| test25 | m4 | CAUGHT | benign_noop | - | Removed 0 dangling gate(s) that do not affect any primary output; equivalence verified. | 0.2 |
| test26 | clean | BASELINE_PASS |  | - |  | 287.1 |
| test26 | m2 | CAUGHT | benign_noop | - | Remapped the cone to NAND+NOT gates (0 gates rewritten); functional equivalence verified. | 287.6 |
| test26 | m2u | CAUGHT | closed_world_reject | - | Could not complete the request (). | 287.0 |
| test26 | m3 | CAUGHT | benign_noop | - | Remapped the cone to NOR+NOT gates (0 gates rewritten); functional equivalence verified. | 287.1 |
| test26 | m4 | CAUGHT | benign_noop | - | Collapsed 0 back-to-back inverter pair(s) into direct wires; equivalence verified. | 287.2 |
| test29 | clean | BASELINE_PASS |  | - |  | 290.3 |
| test29 | m2 | DRIFT | corrupted contract enforced | L4 basis AND_NOT | Remapped the entire design to NOR+NOT gates (1769 gates rewritten); functional equivalence | 289.9 |
| test29 | m2u | CAUGHT | closed_world_reject | L4 basis AND_NOT | Could not complete the request (). | 289.3 |
| test29 | m3u | CAUGHT | guard_rollback | L4 basis AND_NOT | The basis remap was reverted: functional equivalence violated. | 289.4 |
| test29 | m4 | DRIFT | no-op under corrupted intent, request unfulfilled | L4 basis AND_NOT | Removed 0 dangling gate(s) that do not affect any primary output; equivalence verified. | 288.5 |
| test35 | clean | BASELINE_PASS |  | - |  | 12.6 |
| test35 | m2 | CAUGHT | benign_commit | - | Converted 1548 XNOR gate(s) to NAND-only logic (6192 NAND gates added); functional equival | 15.7 |
| test35 | m3 | ESCAPED | unsafe final netlist | no-multi-driven-net | Renamed signal n7431 to cw1 and updated all references. | 823.0 |
| test35 | m4 | DRIFT | corrupted contract enforced | L4 no XNOR | Collapsed 54 back-to-back inverter pair(s) into direct wires; equivalence verified. | 12.7 |
| test38 | clean | BASELINE_PASS |  | - |  | 1.1 |
| test38 | m1 | CAUGHT | benign_commit | - | Inserted 221 buffer(s) on n1 so each driver has at most 3 loads; equivalence verified. | 1.1 |
| test38 | m1w | CAUGHT | benign_commit | - | Inserted 110 buffer(s) on n1 so each driver has at most 5 loads; equivalence verified. | 1.1 |
| test38 | m3 | DRIFT | corrupted contract enforced | L4 fanout(n1)<=4 [harness-extra] | Inserted 5 buffer(s) on n1189 so each driver has at most 4 loads; equivalence verified. | 1.1 |
| test38 | m3r | ESCAPED | unsafe final netlist | equiv-to-original, no-multi-driven-net | Renamed signal n440 to cw1 and updated all references. | 47.3 |
| test38 | m3u | CAUGHT | guard_rollback | L4 fanout(n1)<=4 [harness-extra] | The buffer insertion was reverted: functional equivalence violated. | 1.1 |
| test38 | m4 | DRIFT | corrupted contract enforced | L4 fanout(n1)<=4 [harness-extra] | Collapsed 2 back-to-back inverter pair(s) into direct wires; equivalence verified. | 1.1 |

Tally: BASELINE_PASS=6, CAUGHT=14, DRIFT=7, ESCAPED=3
