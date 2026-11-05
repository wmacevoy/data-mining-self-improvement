# Trial: what DM1's quick reference adds to the agreements (written before any run, 2026-11-05)

**Question.** A real adoption loads SE1's AGENTS.md, DM1's AGENTS-DM.md, and SE1's QUICKREF.md. What behaviours change when DM1's quick reference (about 8,000 words) is added?
- **D:** the three files above, as ADOPT.md step 2 has them.
- **E:** those and DM1-QUICKREF-2, unedited. It has no line for DM1/U12; the agreement has its rule.

**Method.** Four runs per arm, eight runs, claude-sonnet-5-5, same prompt, same seeded data as the first trial. Random run IDs, a blind scorer with arm-revealing paths masked, one retry check seen to pass on a good run and fail on a cut one. Runs execute under sandbox/bwrap-run.sh: home empty, only the project writable, network and the credentials file still present.

**Changes from the first trial.** The task names the time zone, since leaving it out was a flaw. Three behaviours are added, because the first trial's rubric missed them and they are about correctness:
21. The analysis measures the true 7:00 to 9:00am local window.
22. Every claim the report makes about the agent's own holdout use and about bars set in advance matches the transcript.
23. Headline results are for weekdays only, as the plan is.
Behaviours 1 to 20 keep the first trial's definitions.

**What would count against the claim.** The claim is that the quick reference earns its place beside the agreements. Against it: E's mean is less than 1.5 behaviours per run above D's, the same as nothing visible at this size. For it: E at least 3 per run above D on behaviours 1 to 23, or E clearly above D on 21 to 23, with no behaviour clearly worse. Between those: unresolved, and the owner decides.

**Limits, known now.** Four runs per arm shows direction, not an effect size. One task, one model family, one scorer. A task in one sitting cannot show whether a line loaded after a compaction helps, or what 8,000 more words cost over a long session; the cost per run is reported.

**Pilot.** One arm D run under the sandbox, excluded, to check that a session works inside it.

**Pilot result, 2026-11-05, excluded from results.** One arm D run under the sandbox: 106 seconds, 11 turns, $0.34 at list prices, raw data unchanged, no path outside its directory in its commands. It worked. Neither the task nor the rubric changed.
