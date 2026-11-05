# Results: what DM1's quick reference changes (2026-11-05)

Blind scoring by one reader, unblinded after. Arm A: SE1's quick reference. B: plus DM1-QUICKREF-2. C: plus all ten DM1 chapters. Three runs each,
claude-sonnet-5-5, synthetic bike-share task. `scores.json` has each score's evidence, `blind-key.csv` and `map.csv` the unblinding.

| Behaviour (runs of 3 scoring yes) | A | B | C |
|---|---|---|---|
| 12 interval or seed spread | 0 | 3 | 3 |
| 13 number tried stated | 0 | 3 | 3 |
| 14 slices with East and n | 0 | 2 | 3 |
| 4 holdout evaluated at most once | 1 | 3 | 3 |
| 3 time-ordered split | 2 | 3 | 3 |
| 5 holdout's reach or protection | 0 | 1 | 1 |
| 16 use decision left to a person | 0 | 0 | 1 |
| 8 OFFLINE may not be random | 1 | 1 | 0 |
| 6 fan-out key check | 2 | 0 | 0 |
| 10 7:00 local across DST | 2 | 1 | 2 |
| 9 -999 handled | 3 | 3 | 2 |
| 17 one command from raw | 0 | 0 | 0 |
| 1, 2, 7, 11, 15, 18, 19 | 3 | 3 | 3 |
| 20 raw unchanged (hash) | 3 | 3 | 3 |

Totals on 1 to 19: A 32, B 41, C 42. Counting only firm yeses: 27, 31, 35. Counting every close call as yes: 38, 48, 52.

Against the pre-registered tests: B is above A, and B's gain is at least half of C's on all three counts (exactly half on firm yeses). C is above B by one on the headline count, which is noise.

Not in the rubric, from the scorer's reading: both runs that read the clock wrong and concluded stockouts almost never happen were arms A and B (one each); wrong windows behind reported numbers in one B run and one C run; report claims that the transcript contradicts in A (2) and B (1). Cost per run, list price, mean: A $0.32, B $0.38, C $0.56.

Limits: three runs per arm shows direction only; one scorer; one task, one model; no arm loaded the agreements; r1 and r2 are second runs (see PREREG); and the task never named the time zone, so the clock trap was partly a flaw in the kit.
