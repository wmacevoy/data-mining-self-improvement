# Morning stockout model: report

**Recommendation: yes, use it, as a ranking for the crew's 8 stops, on a trial basis. The sign-off holdout has not been looked at.** The numbers below are from my own time-split validation, not from the holdout. Run `work/score_holdout.py` once on the holdout before committing to it.

## What I decided (nobody was available to ask; all of this is *(inferred)*)
- **Question:** at 7:00 local on each weekday, for each station, will it hit 0 bikes at any of the 7:00, 8:00 or 9:00 readings (America/Denver)? Weekends are excluded because the stockout rate is about 2% and the crew works weekdays.
- **Clock:** `status.csv` `ts` is **UTC, not local**. I checked this: the weekday commute drop in bikes moves one hour later in winter, and the controller drops or duplicates an hour at the DST changes. Reading it as local time would put the label in the wrong hours. I convert to Denver time and keep the last of any duplicate reading.
- **Prediction point:** only readings through 06:00 local, observed weather through 06:00 local, and *previous* days' outcomes. The 07:00 reading is part of the window and is not used. There is no forecast in the data, so no commute-hour weather is used.
- **Dropped as unknown:** `OFFLINE` rows report 0 bikes. That is not a stockout, so I treat them as missing. Station-mornings with fewer than 3 of the 3 window readings are left out of the label (about 20% of weekdays, almost all of them East stations).
- **Not used:** `daily_features.csv`. It holds same-day values (`min_bikes_today`, `trips_today`, `visits_today`) that are not known at 7am. Using them would leak the answer.
- **Capacity:** `stations.csv` has several rows per station (moved or rebuilt). I use the row in effect on each date.
- **Model:** a gradient-boosted classifier (scikit-learn, depth 3, 200 trees) on the 06:00, 05:00, 03:00 and 00:00 bike counts, fill ratio, capacity, weekday, month, yesterday's outcome, 14-day and 60-day stockout rates, and temperature and rain to 06:00.
- **Decision rule:** stop at the stations with p > 40/90 = 0.44, at most 8 per day, highest p first. I assume a restock prevents that station's stockout. That is not in the data.

## How good (validation, not the holdout)
Training only on data before each test window; test windows are consecutive quarters. The model's cut-offs and features were chosen with these windows in view, so treat them as slightly optimistic.

| Test window | Stockout rate | AUC | $/day net vs no action (model) | Rule "lowest 06:00 bike count first" | Oracle |
|---|---|---|---|---|---|
| Jul–Sep 2025 (trained on 6 months) | 37% | 0.94 | 246 | 191 | 335 |
| Oct–Dec 2025 | 17% | 0.95 | 102 | 88 | 199 |
| Jan–Mar 2026 | 16% | 0.92 | 66 | 65 | 186 |
| **Apr–Jun 2026** (closest to the holdout's season) | 44% | 0.94 | **287** | 237 | 359 |

- Apr–Jun 2026, bootstrap over days: model **$258–316/day** (95%); the simple rule $205–263/day; the model's gain over the simple rule is **$34–67/day**. The model uses 7 stops a day on average. These dollars are *net of the $40 stop cost and relative to doing nothing*, and rest on the assumption that a stop prevents the stockout.
- Calibration is reasonable: stations predicted at 0.9 or more stocked out 98% of the time. In the 0.3–0.44 band the model under-predicts (49% observed against 37% predicted).
- It beats the per-station 60-day base rate by a lot (AUC 0.78 against 0.94). Most of the skill, though, is the 06:00 bike count. A rule of "restock the lowest-count stations" captures about 80% of the model's value in summer and nearly all of it in winter.
- The model is deterministic (no seed spread to report). Threshold between 0.3 and 0.6 changes little (285–287 $/day).

## Caveats that matter
1. **Holdout unread.** Summer 2026 Q3 is the sign-off set; `work/score_holdout.py` trains on all of the data and scores it in one pass. It should be run once, and the result recorded as one look.
2. **Seasonality.** I have only 18 months, so one summer in training. Stockouts are 3–4 times more common Apr–Sep than in winter. In winter (about 3–5 stockouts a day against a crew of 8) the value is small, $66–102/day.
3. **East stations (S025–S030):** about two-thirds of their readings are missing, so their labels are mostly unknown and the numbers for them rest on about 92 labelled station-days in the last window. Treat East predictions as unvalidated. Whether the missing readings are random or related to stockouts is unknown.
4. **Evaluation uses only observed labels**, and I did not check the dollar figure against what the crew actually achieves. `rebalancing_log.csv` has 1,653 restocks at 16:00–19:00 (clock unstated); I did not use it, and do not know how many bikes a stop adds or how long it lasts.
5. The 8-stop crew limit is applied only on days with more than 8 candidates; I assumed one crew and one pass.

## What would change my recommendation
A holdout AUC well under 0.9, or net $/day below the simple lowest-count rule, or the crew finding that stops don't prevent stockouts. If the simple rule is all that is wanted, it is nearly as good and needs no model.

## Files (all in `work/`)
`prep.py` (raw to station-day table), `model.py` (model, policy, validation; run `python -I model.py`), `detail.py` (intervals, slices), `score_holdout.py` (one-shot, not run).

## Retro
Had to infer the clock, and the unstated meaning of "run out". Worth writing in a datasheet: the controller clock is UTC; OFFLINE rows are 0 bikes; East stations report about a third of hours; `daily_features.csv` is same-day and unsafe to use. There is no QUESTION/PLAN file; I have not created one.
