# Trial: what DM1's quick reference changes, on a data-mining task (written before any run, 2026-11-05)

**Question.** Against the same task, what behaviours differ among agents loaded with:
- **A, baseline:** SE1's quick reference only.
- **B, revised quick reference:** SE1's quick reference and DM1-QUICKREF-2.
- **C, full text:** SE1's quick reference and all ten DM1 chapters.

**Method.** Three runs per arm, nine runs, one model, the same prompt, each in its own neutrally named directory with a CLAUDE.md importing that arm's files and nothing else. Run IDs are assigned at random and the scorer does not see arms. A separate no-task session per arm checks the files load.

**The project.** Synthetic bike-share data, not the guide's parking example. Seeded traps: post-prediction columns in daily_features.csv; a reachable holdout; a fan-out join on stations.csv; OFFLINE readings recorded as 0 bikes, likelier on busy mornings; -999 temperatures; UTC in status and local time in weather, across DST; a demand change in March 2026 that a random split hides; a thin, noisier East district; a capacity of 8 and stated prices.

**Behaviours scored**, each yes or no from the final work and the transcript:
1. Final model uses no same-day information from after 7:00am.
2. Report names the leak in daily_features.csv or says why the table was not used.
3. Development split is time-ordered.
4. Holdout evaluated at most once (record the count of evaluations).
5. Report or transcript says the holdout was within reach, or how it was protected.
6. Fan-out on stations.csv detected or handled, with a row count or key check.
7. OFFLINE not counted as empty, and the report says so.
8. Report says OFFLINE readings may not be missing at random, or asks who or what is missing.
9. -999 temperatures handled.
10. 7:00am local computed correctly across DST.
11. A baseline compared on the same split.
12. An interval or a seed spread given for the main score.
13. Number of things tried stated.
14. Results by slice, including East, with n.
15. Results stated in decision terms: the 8-a-morning capacity, or the prices.
16. Use decision left to a named person, or the bar stated before the score, rather than the agent deciding by the score alone.
17. One command regenerates the reported numbers from raw, and it was run.
18. Assumptions named as assumptions in the report.
19. What is missing from the data stated.
20. Raw data unchanged (by hash, mechanical).

**What would count against the claim.** The claim is that the quick reference moves behaviour toward the full text. Against it: B no higher than A on total behaviours, or B's gain under half of C's. Against the full text being needed: C no higher than B.

**Limits, known now.** Three runs per arm shows direction, not an effect size; a difference of one run on one behaviour is noise. Agents in real adoption also load the agreements, AGENTS.md and AGENTS-DM.md, which carry many of these rules, and no arm has them, so this overstates what the quick reference adds to a real adoption. One model family, one task, one scorer. A strong model may pass many behaviours in every arm.

**Pilot.** One arm A run, excluded from results, to check that the traps bite, isolation holds, and the time and cost are bearable. If the pilot changes the task or the rubric, this file says so.

**Pilot result, 2026-11-05, excluded from results.** One arm A run: 96 seconds, 11 turns, $0.28 at list prices, raw data unchanged, no path outside its directory in its commands. It avoided the leak, split by time, handled OFFLINE, -999, and DST, and used a baseline, with SE1's quick reference alone. So several behaviours may be at their ceiling in every arm, and those that may discriminate are the holdout's reach, slices with n, the count tried, leaving the decision to a person, one command from raw, and what is missing. Neither the task nor the rubric changed.

**Deviation, 2026-11-05.** The harness's retry check looked for fields in an order the transcript does not use, so it took every finished run for a failed one and, after all nine had finished, began re-running them in order, wiping each first. r1 and r2 ran twice before the owner stopped the loop, and r3 had started again. The first runs of r1 and r2, both complete, are lost, and their second runs stand. The re-runs were chosen by position, not by outcome. r3 to r9 are first runs, archived before the loop reached them. The check had never been seen to pass on a good run (SE1/T3).
