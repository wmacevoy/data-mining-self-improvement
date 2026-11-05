# Morning stockout model: report

**Recommendation: use it, as a ranking tool for the 7:00 plan, on a trial basis.** Each weekday it picks up to 8 stations to restock. On the sign-off quarter (2026 Q3) it beat every simple rule I tried. It is not proven for winter, and the dollar figures rest on an assumption nobody could confirm (see "Decided without asking").

## What was built
- **Question:** at 7:00 local on a weekday, which stations will have 0 bikes at an hourly reading at 7, 8 or 9:00 local? Output is a probability per station.
- **Rule:** restock a station if p > 40/90 = 0.44, highest p first, at most 8 stops. That is the break-even where a $40 stop saves a $90 stockout. It is the crew limit applied to the ranking, not a fitted parameter.
- **Model:** gradient boosting (scikit-learn), 3-seed average. Inputs are the station's capacity, its bike counts at 00:00, 03:00, 05:00 and 06:00 local and the last known one, its stockout history for prior days, weekday, month and station.
- **Code:** `work/prep.py` (clock, labels, features), `work/model.py` (model, baselines, value), `work/final.py` (the holdout run). Run each from `work/` with `PYTHONPATH=. python <file>.py`; plain `python -I` cannot import the sibling modules. The `data/` files were not modified.

## How good it is (2026 Q3 holdout, 66 weekdays, looked at once)
| | Model | Best simple rule (last 28 days' stockout rate) | Station average | Oracle (perfect, still capped at 8 stops) |
|---|---|---|---|---|
| Net $/day vs. no restocking | **+293** (95% CI 253–327) | +189 | +147 | +364 |
| AUC | 0.93 | 0.78 | 0.79 | – |

- The model beats the best simple rule by about $103/day (bootstrap by day, 95% CI $83–124).
- Of the stops it makes, about 85% were stations that really ran out. It averages 7.95 stops/day. It catches about 55% of the 12.4 stockouts per day, and the 8-stop cap is the main limit: summer has more stockouts than the crew can cover.
- Calibration is good. Predicted and observed rates match within a few points in every bin (for example, bin 0.7–0.9: predicted 0.80, observed 0.86). Results are similar in all three districts (AUC 0.91–0.93) and in Jul/Aug/Sep.
- Development used four forward-chained quarterly folds (2025 Q3 through 2026 Q2). Model AUC there was 0.91–0.93. Value ranged from about $76/day in winter to $289/day in spring. Winter is therefore weak in value terms, because there are few stockouts to catch.
- Without the 06:00 reading (only data up to 05:00), AUC drops to 0.885 and value to $273/day. Even a late or missing 06:00 feed keeps most of the value.

## Decided without asking (each is an assumption; please confirm)
1. **The controller clock is UTC, not local.** Evidence: `status.csv` starts at 07:00 on 1 Jan, and after converting to America/Denver the rush-hour drain lines up at the same local hour in winter and summer. I used local time throughout. The 52 duplicate rows at the two spring DST changes were de-duplicated, keeping the last. Anyone reading `ts` as local would label the wrong hours.
2. **A stockout means an `OK` reading of 0 bikes at 7, 8 or 9 local.** `OFFLINE` rows report 0 bikes but are not observations (a dead controller), so they are not counted as stockouts and were set to missing. Days with all three readings offline were dropped (283 of 16,380 station-days). Readings are hourly, so a stockout between readings is missed, which understates the true rate.
3. **Weekdays only.** Weekend stockouts are about 2%, and the plan runs on weekdays.
4. **The 06:00 reading is available at the 7:00 plan.** This needs a check with Operations. The 05:00 variant above shows what is lost if it is not.
5. **Restocking a station prevents its stockout, and a stop costs $40 regardless of the station.** The data cannot test this; the value figures depend on it entirely. It makes the dollar numbers an upper bound, but the ranking against baselines holds either way. I also did not model what current practice earns. `rebalancing_log.csv` shows evening visits, not morning ones. Compare with the crew's current practice in a trial.
6. **Not used:** `daily_features.csv`. Its columns (`trips_today`, `min_bikes_today`, `visits_today`) are end-of-day totals that include the outcome window, so using them would leak the answer. I did not check it against the raw data. It should be pulled from the dashboard or have its definitions fixed before anyone reuses it.
7. **Station capacity changes** (moves and rebuilds on 2025-09-15 and 2026-02-01) are applied by effective date.

## Caveats
- **The score is high enough to deserve suspicion** (AUC 0.93 against 0.78 for history alone). Most of it comes from the early-morning bike level. A station that starts low at 6:00 and has strong demand will empty. I checked that ablations behave sensibly, that the clock alignment is consistent across seasons, and that the model used no data after 06:00. I did not trace an individual prediction back to its source rows, which a second reviewer should do.
- **Looks:** about 30 scored configurations on development folds (4 folds × 5 methods, plus 5 ablations) and one holdout run. I changed nothing after the holdout run, but it is now spent as a clean sign-off set; the next sign-off needs a fresh period.
- **Seasonal coverage:** the holdout is summer and early autumn. The training data holds one winter and one summer, so the model has seen only one year of seasonality. Winter 2026–27 is untested.
- **Feedback loop:** if crews restock the predicted stations, those stations stop stocking out, and next year's history looks like the model was wrong. Retrain with a note of which stations were restocked on each day, and keep a few randomly chosen stations unrestocked for a clean read.
- **New stations or capacity changes:** the model has the station ID as a feature, so a new station gets a poor forecast until it has history. Fall back to the last-28-day rule there.

## Before relying on it
1. Run it in shadow for 2–4 weeks beside current practice, and compare stops and stockouts.
2. Operations confirms the 06:00 availability, and whether a restock really prevents the stockout.
3. Check again before winter and after any retrain.
