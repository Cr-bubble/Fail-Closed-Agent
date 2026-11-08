# E13 calibration report — cdcf9af on final_release_100 (2026-11-08)

- complete cases: 99/100; crashed: 0
- OPT exact cost matches: 27/46

## MISMATCHES (flagged for idle re-run)

| case | metric | achieved | official | cost_min | text | dur_s | load@start |
|---|---|---|---|---|---|---|---|
| test047 | depth | 14 | 16 | 14 | 14 | 288 | 1.54 |
| test049 | gate_count | 888 | 922 | 773 | 888 | 287 | 1.13 |
| test052 | gate_count | 4415 | 4399 | 4350 | 16 | 283 | 1.07 |
| test053 | gate_count | 2535 | 2573 | 2573 | 2535 | 288 | 1.15 |
| test059 | depth | 18 | 19 | 18 | 18 | 290 | 1.05 |
| test065 | depth | 23 | 26 | 23 | 23 | 293 | 1.13 |
| test067 | gate_count | 13966 | 13968 | 13852 | 16 | 285 | 1.1 |
| test068 | depth | 11 | 12 | 11 | 11 | 286 | 1.08 |
| test070 | depth | 12 | 13 | 12 | 12 | 287 | 1.0 |
| test078 | depth | 13 | 14 | 13 | 13 | 287 | 1.05 |
| test080 | gate_count | 1380 | 1388 | 1359 | 16 | 283 | 1.29 |
| test081 | gate_count | 5353 | 5340 | 5340 | 5353 | 287 | 1.15 |
| test082 | gate_count | 5376 | 5431 | 5383 | 5376 | 288 | 1.3 |
| test083 | gate_count | 5404 | 5448 | 5416 | 5404 | 286 | 1.05 |
| test084 | gate_count | 323 | 322 | 322 | 323 | 287 | 1.06 |
| test086 | gate_count | 5189 | 5256 | 5197 | 5189 | 286 | 1.17 |
| test087 | gate_count | 9913 | 5482 | 5444 | 9913 | 289 | 1.03 |
| test088 | gate_count | 10434 | 10444 | 5796 | 10434 | 287 | 1.16 |
| test090 | gate_count | 10920 | 11047 | 10920 | 10920 | 287 | 1.15 |

## All 46 OPT requests

| case | req | metric | achieved(recomputed) | text | official | cost_min | match | gap | ach/min |
|---|---|---|---|---|---|---|---|---|---|
| test046 | 4 | depth | 10 | 10 | 10 | 10 | Y |  |  |
| test047 | 4 | depth | 14 | 14 | 16 | 14 | N | Y | 1.0 |
| test048 | 4 | gate_count | 10493 | 16 | 10493 | 10205 | Y | Y | 1.0282 |
| test049 | 4 | gate_count | 888 | 888 | 922 | 773 | N | Y | 1.1488 |
| test050 | 4 | depth | 12 | 12 | 12 | 12 | Y |  |  |
| test051 | 4 | depth | 55 | 55 | 55 | 26 | Y | Y | 2.1154 |
| test052 | 4 | gate_count | 4415 | 16 | 4399 | 4350 | N | Y | 1.0149 |
| test053 | 4 | gate_count | 2535 | 2535 | 2573 | 2573 | N |  |  |
| test054 | 4 | depth | 7 | 7 | 7 | 7 | Y |  |  |
| test055 | 4 | gate_count | 1538 | 16 | 1538 | 1479 | Y | Y | 1.0399 |
| test056 | 4 | gate_count | 2660 | 16 | 2660 | 2654 | Y | Y | 1.0023 |
| test057 | 4 | depth | 56 | 56 | 56 | 54 | Y | Y | 1.037 |
| test058 | 4 | depth | 12 | 12 | 12 | 12 | Y |  |  |
| test059 | 4 | depth | 18 | 18 | 19 | 18 | N | Y | 1.0 |
| test060 | 4 | depth | 9 | 9 | 9 | 8 | Y | Y | 1.125 |
| test061 | 4 | depth | 8 | 8 | 8 | 7 | Y | Y | 1.1429 |
| test062 | 4 | depth | 286 | 286 | 286 | 161 | Y | Y | 1.7764 |
| test063 | 4 | depth | 17 | 17 | 17 | 17 | Y |  |  |
| test064 | 4 | depth | 10 | 10 | 10 | 9 | Y | Y | 1.1111 |
| test065 | 4 | depth | 23 | 23 | 26 | 23 | N | Y | 1.0 |
| test066 | 4 | depth | 17 | 17 | 17 | 17 | Y |  |  |
| test067 | 4 | gate_count | 13966 | 16 | 13968 | 13852 | N | Y | 1.0082 |
| test068 | 4 | depth | 11 | 11 | 12 | 11 | N | Y | 1.0 |
| test069 | 4 | gate_count | 11088 | 16 | 11088 | 10937 | Y | Y | 1.0138 |
| test070 | 4 | depth | 12 | 12 | 13 | 12 | N | Y | 1.0 |
| test071 | 4 | depth | 5 | 5 | 5 | 5 | Y |  |  |
| test072 | 4 | depth | 6 | 6 | 6 | 6 | Y |  |  |
| test073 | 4 | depth | 11 | 11 | 11 | 11 | Y |  |  |
| test074 | 4 | depth | 8 | 8 | 8 | 8 | Y |  |  |
| test075 | 4 | gate_count | 53 | 53 | 53 | 53 | Y |  |  |
| test076 | 4 | depth | 6 | 6 | 6 | 6 | Y |  |  |
| test077 | 4 | depth | 1 | 1 | 1 | 1 | Y |  |  |
| test078 | 4 | depth | 13 | 13 | 14 | 13 | N | Y | 1.0 |
| test079 | 4 | gate_count | 32 | 16 | 32 | 32 | Y |  |  |
| test080 | 4 | gate_count | 1380 | 16 | 1388 | 1359 | N | Y | 1.0155 |
| test081 | 3 | gate_count | 5353 | 5353 | 5340 | 5340 | N |  |  |
| test082 | 3 | gate_count | 5376 | 5376 | 5431 | 5383 | N | Y | 0.9987 |
| test083 | 3 | gate_count | 5404 | 5404 | 5448 | 5416 | N | Y | 0.9978 |
| test084 | 3 | gate_count | 323 | 323 | 322 | 322 | N |  |  |
| test085 | 3 | gate_count | 15510 | 15510 | 15510 | 15510 | Y |  |  |
| test086 | 3 | gate_count | 5189 | 5189 | 5256 | 5197 | N | Y | 0.9985 |
| test087 | 3 | gate_count | 9913 | 9913 | 5482 | 5444 | N | Y | 1.8209 |
| test088 | 3 | gate_count | 10434 | 10434 | 10444 | 5796 | N | Y | 1.8002 |
| test089 | 3 | gate_count | 10760 | 10760 | 10760 | 10760 | Y |  |  |
| test090 | 3 | gate_count | 10920 | 10920 | 11047 | 10920 | N | Y | 1.0 |
| test096 | 4 | gate_count | 9457 | 16 | 9457 | 9457 | Y |  |  |

## Incomplete/crashed cases: ['test100']
