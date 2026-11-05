# Morning stockout model: report

**Claim kind:** predicted. Each weekday at 7:00 Denver, for each of 30 stations, will it show 0 bikes at any hourly reading at 7, 8 or 9am?
**Recommendation:** use it, as a ranked list for the crew (top 8 by risk), **conditional on the sign-off run on `holdout/status_2026Q3.csv`**, which I did not read. Not yet sign-off evidence: everything below is on development data (2025-01 to 2026-06).

## Result (development data only, expanding-window time splits; train strictly before each test quarter)
| test quarter | stockout base rate | AUC model | AUC best baseline | net $/day, model | $/day, "≤2 bikes at 6am" rule | $/day, own recent history |
|---|---|---|---|---|---|---|
| 2025Q4–2026Q1 (fold ending 2026-01) | 16% | 0.946 | 0.71 | 108 | 47 | -15 |
| 2026Q1 | 15% | 0.919 | 0.71 | 79 | 32 | -2 |
| 2026Q2 | 41% | 0.934 | 0.78 | 299 | 134 | 164 |

(Full table: `work/ledger.csv`; fold labels there are the fold end date.)
- Last quarter, flagged at p>0.44: ~11.6 stations/day, precision 83%, recall 81% of ~11.8 stockouts/day. Calibration is good (p in 0.7–0.9 → 84% stockouts).
- Net value is $90 per stockout caught minus $40 per stop, with at most 8 stops/day. 2026Q2: **$299/day (95% day-bootstrap 274–326)**, vs about $375/day for a perfect oracle and +$166/day (143–188) over the simple rule. Only the last quarter's interval was computed. Low-season quarters yield much less ($80–110/day), since fewer stations run out.
- The crew limit of 8 binds on 66% of days in the high season, so ranking matters more than the threshold.
- Seed spread is zero (the gradient-boosting model is deterministic as configured), so there is no seed noise; the sample spread is the bootstrap above.
- Without any bike-count features (history, weather, calendar only) AUC drops to 0.82. The 6am count is the main driver; 15% of stockouts are already empty or offline at 6am.

## Tried
4 models (logit, gradient boosting, 2 baselines) × 3 folds = 12 scored rows, all in the ledger; no tuning search. Gradient boosting and logit are within noise of each other (logit $291 vs $299/day in the last fold); I picked gradient boosting before looking at the last fold's difference, but the choice is not meaningful. Logit is the simpler alternative.

## Decisions I made (nobody to ask)
- **Timestamps:** `status.csv` `ts` is UTC, not local (README says "controller clock"). Evidence: the commute dip lines up with 6–9am Denver only after UTC→Denver conversion. If the controller clock were local, every number here would shift by 6–7 hours. This needs confirming with whoever owns the controllers. DST days contain duplicate and missing hours (52 duplicate rows dropped).
- **Target:** stockout = an `OK` reading of 0 bikes at local 7, 8 or 9. `OFFLINE` rows report 0 bikes; I treated them as missing, not stockouts. 227 station-days with no valid reading in the window were dropped. Readings are hourly, so brief stockouts between readings are missed.
- **Prediction point:** features use only readings through 6:00 local, weather through 6:00 (`-999` sentinel → missing), the station's *prior-day* stockout rates, calendar and capacity as of that date (stations were moved/rebuilt on 2025-09-15 and 2026-02-01). Weekdays only. The model has not seen the 7:00 reading itself.
- **Not used:** `daily_features.csv`. Its columns (`trips_today`, `min_bikes_today`, `visits_today`) are same-day aggregates, not knowable at 7am; they would leak. The rebalancing log is not used directly (it is reflected in the 6am bike counts).
- **Threshold** 40/90 = 0.44 comes from the stated prices; **assumption:** a crew stop at a stockout-bound station fully prevents the stockout and arrives before 7–9am. Neither is in the data: the log shows evening restocks (16–19h) only, so a morning crew's effect has never been observed. The dollar figures are therefore an upper bound.

## Risks and what is unchecked
- **Holdout is reachable** from this directory (`data/holdout/`). I did not read it. Spend it once, on `work/model_dev_through_2026-06.pkl` unchanged; it is Jul–Sep, a season in which the training data has only one summer (2025Q3, 35% base rate).
- Reading-level surprises: some stockouts occur from a high 6am count (e.g. 23 bikes → 0, S006 2026-06-12) and are missed; I cannot tell whether these are real rush or faulty readings.
- Station moves/rebuilds change capacity; AUC on those stations is fine in the 2026Q2 fold (0.95), but little data exists post-change.
- Slices (2026Q2): AUC 0.92–0.95 in every district and 0.86–0.95 by capacity; the weakest are capacity 15 and 21 (n=302 and 59). Calibration by slice was only eyeballed.
- Drift is not monitored; retrain at least quarterly and check the realized stockout rate against predicted. Fallback if the feed is missing: the "≤2 bikes at 6am" rule.
- Not done: bias audit (no people-groups in the requirements), shadow run, a measured benefit of actual crew visits.

## Reproduce
From `work/`: `python -I prep.py` (builds `dev.pkl`), then `evalm.py`, `check.py`, `final.py` (run with `PYTHONPATH=.`). Data and code versions are not otherwise recorded (no git repo here).
