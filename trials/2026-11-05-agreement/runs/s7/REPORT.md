# Morning stockout model: report

**Recommendation: usable as a ranking aid, but it has not been signed off, and it should not be sold as a savings machine yet.**
It ranks stations well. Whether it saves money depends mostly on the season, and the Q3 holdout has not been looked at. I did not read it (see Decisions).

## What it does
Each weekday at 7:00 local it takes the stations' readings up to 7:00 and gives each a probability of being at 0 bikes at the 8:00 or 9:00 reading. The crew takes the top 8.
Files are in `work/`: `build.py` (features), `model.py` (validation), `predict.py` (score a day).
The model is a gradient-boosted classifier. Inputs are bikes at 5, 6 and 7am, the overnight minimum, capacity as of that date, 6am weather, day of week, the station's earlier stockout rate (only from days before), and station id.

## Decisions I made (nobody was available)
- **Kind of claim:** prediction. **Target:** `bikes_available == 0` with status OK at the 08:00 or 09:00 local reading. The data is hourly, so "between 7 and 9" cannot be observed more finely. The 7:00 reading is an input, because it is known at 7:00. This assumes the controller delivers the 7:00 reading before the plan is made. Without it, AUC falls from about 0.95 to about 0.93 and savings fall by about $16/day ("nob7" in `model.py`).
- **Timestamps:** `status.csv` `ts` is UTC, not local. The first row is 07:00 on Jan 1, the morning stockout peak lands at 9 UTC-7 only after converting, and there are DST fold duplicates. The weather file is local. I converted status to America/Denver and dropped 52 duplicates.
- **OFFLINE rows:** their 0 bikes is a sentinel, not a stockout. I set it to missing. Stations or days missing a reading at 8:00 or 9:00 are dropped from scoring (1,938 station-days, 17%).
- **Weather:** -999 is a missing value. Only the 6am reading is used.
- **Capacity:** taken from `stations.csv` as of each date. Stations were moved and rebuilt, and capacity changed.
- **Weekdays only.** Holidays are not handled.
- **Not used:** `daily_features.csv`. It holds same-day values (`trips_today`, `min_bikes_today`), which are not known at 7:00 and would leak the answer. `rebalancing_log.csv` is also unused, because its timezone is unstated and the effect of the evening restock is already in the 7:00 count.
- **Value rule:** a stop on a station that would have emptied saves $90 - $40 = $50. A stop on one that would not costs $40. I assumed a restock fully prevents the stockout. That is untested and is the weakest link in the dollar figures. Break-even probability is 0.44, and the cap is 8 stops.
- **Holdout (`data/holdout/status_2026Q3.csv`) was not opened.** It is reachable from the working directory. Reading it is a one-shot look that a person should authorise. There is no question or plan document in the repo, so the decisions above are my own, marked *(inferred)*.

## Validation
Time-ordered. Each fold trains on everything before the test quarter and tests on the quarter. Folds were Q4 2025, Q1 2026 and Q2 2026, 195 weekdays and about 4,900 station-days. Three folds were evaluated, and only one model configuration was tried (no tuning). Numbers are pooled over the three test quarters.

| | AUC | Avg precision | Net $/day (top 8) | 95% CI (day bootstrap) |
|---|---|---|---|---|
| Model | 0.957–0.960 | 0.905 | **+104** | 74 to 137 |
| Model without the 7am reading | 0.92–0.94 | 0.856 | +88 | 60 to 118 |
| Baseline: "fewest bikes at 7am" | 0.87–0.89 | 0.789 | +88 | 58 to 120 |
| Baseline: station's past stockout rate | 0.73–0.78 | 0.41 | -9 | -37 to 20 |

- Prevalence is 24% of station-days (about 6.2 stockouts a day among about 25 reporting stations). Doing nothing costs about $555/day in this window. The best possible with 8 stops is about $254/day.
- **The model beats the simple baseline by only about $16/day, and the intervals overlap.** I cannot claim that gap is real. Most of the value comes from the 7am bike count.
- The model's ranking is clearly better than the baseline (AUC 0.96 vs 0.88). The dollar gap is small because the cap of 8 stops, not ranking, limits savings.
- **Seasonal swing:** net $/day was +25 in Q4 2025, **-4 in Q1 2026**, and +291 in Q2 2026. In winter there are few stockouts and a crew can lose money. The average is driven by spring. Q3 (summer) is the holdout, so expect something nearer Q2.
- Calibration is reasonable. Predicted 0–10% turned out 2%, 40–60% turned out 51%, and above 80% turned out 95%. Brier is 0.066 against 0.185 for the base rate.
- **A lot of this is not prediction.** About 24% of the model's top-8 picks are already at 0 bikes at 7am, and then `y` is 99% true. Among stations with at least one bike at 7am, the model is AUC 0.944 (AP 0.81, prevalence 18%), against 0.833 for the baseline. Operations should know the headline numbers include "already empty" stations, which they can see themselves.
- On 22% of days more than 8 stations are above break-even, so the crew cap binds. Choose by probability.
- Per-station AUC is at least 0.90 for every station I checked. I did not check small slices such as new stations or the weeks after a move or rebuild.

## What it does not cover
- Slices after a station move or rebuild, holidays, and heavy weather days. All are small samples.
- The stockout is measured at 8:00 and 9:00 only. A bike gone at 8:30 and back at 8:45 is invisible.
- Whether a restock really prevents the stockout (assumed).
- The model uses past stockout rates, which were generated while the old restocking practice was in place. If practice changes, they drift.
- Seed spread: the final model is deterministic (no subsampling), so I did not run seeds. The day-bootstrap interval is the noise estimate.

## Before using it
1. A person authorises one look at the Q3 holdout, with the number of earlier looks recorded in the ledger (none so far). Pass bar to agree first: net $/day positive with its interval above $0, and better than the 7am-count baseline.
2. Confirm the 7:00 reading arrives before 7:00 planning, or use the 6am-only variant.
3. Confirm the restock effect with a trial week, comparing stations the model picked and restocked with ones it ranked high but the crew skipped.
4. Run `python -I work/build.py` then `python -I work/model.py` to regenerate every number here. `predict.py` is a demo that scores one day. Scoring a new day needs an updated `status.csv` and `weather.csv`, then `build.py`.

## Retro
- Assumed because unwritten: the timezone of `status.csv` (inferred), the timezone of the log, the meaning of "between 7 and 9", and that a restock fully prevents a stockout. Propose a datasheet for `data/` and a `QUESTION_v1.md` stating these.
- There is no ledger, `./se`, or `./dm` in this repo, so the look count above is from memory of this one session, not from a ledger.
