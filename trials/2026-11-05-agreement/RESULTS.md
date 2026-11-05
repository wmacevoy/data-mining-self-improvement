# Results: what DM1's quick reference adds to the agreements (2026-11-05)

Blind scoring by one reader, unblinded after. D: SE1's AGENTS.md, DM1's agreement, SE1's quick reference, as an adopter has them. E: those and DM1-QUICKREF-2. Four runs each, claude-sonnet-5-5, under the sandbox. Raw data unchanged in every run. `scores.json` has each score's evidence; `blind2-key.csv` and `map.csv` the unblinding.

| Behaviour (runs of 4 scoring yes) | D | E |
|---|---|---|
| 8 OFFLINE may not be random | 1 | 0 |
| 13 number tried stated | 3 | 4 |
| 14 slices with East and n | 3 | 4 |
| 16 use decision left to a person, or bar first | 4 | 2 |
| 17 one command from raw | 1 | 0 |
| 6 fan-out key check | 0 | 0 |
| 1, 2, 3, 4, 5, 7, 9, 10, 11, 12, 15, 18, 19, 21, 22, 23 | 4 | 4 |
| 20 raw unchanged (hash) | 4 | 4 |

Means on the 22 scored behaviours: D 19.0, E 18.5. Counting only firm yeses: 16.0, 15.75. Counting close calls as yes: 21.25, 21.0. Mean cost per run at list prices: D $0.35, E $0.43.

Against the pre-registered test: E is not 1.5 per run above D, so the result counts against the claim that the quick reference earns its place beside the agreements. On the correctness items, 21 to 23, both arms score 3 of 3 in every run.

Every run in both arms made zero holdout evaluations and left the sign-off to a person.

Not in the rubric, from the scorer's reading, in both arms: arithmetic and interval errors in reports; no report names the March 2026 demand change; six of eight do not flag East's thin data. Neither arm prevented these.

Seen after unblinding, so a hypothesis and not a result: a ledger file in E's four runs and in none of D's four, though the excluded D pilot had one.

Limits: four runs per arm shows direction only; one scorer, one task, one model; a short sitting says nothing about a line loaded after a compaction or about 8,000 words over a long session.
