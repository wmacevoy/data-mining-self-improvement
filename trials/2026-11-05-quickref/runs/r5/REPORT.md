# Morning stockout model: report

## Recommendation
**Use it, as a pilot, alongside the current practice for a few weeks first.** Each weekday at 7:00, restock the stations the model scores above 0.44, at most 8 of them.

On the held-out 2026 Q3 (66 weekdays, spent once), that plan cost about **$290/day**. Doing nothing cost about **$387/day**, so the saving is **about $97/day** (95% interval $70–125, bootstrapped over days).

- On a typical day it sends the crew to about 4 stations. About 71% of those stops were at stations that really ran out (precision), and it caught about 67% of all stockouts (recall).
- Two simpler rules did worse. "Restock stations that ran out yesterday" cost $460/day, worse than doing nothing. "Restock stations with 2 or fewer bikes at 6:00" cost $377/day.
- **Not tested:** I did not compare against what operations does today. `rebalancing_log.csv` shows the trucks but not their reasoning, so the saving is versus doing nothing. Run it beside the current planner before relying on it.

## What was predicted
- **Row:** one station on one weekday. Weekends are excluded because ops plans only on weekdays.
- **Outcome:** the station had status OK and 0 bikes at any hourly reading at 7:00, 8:00 or 9:00 local time.
- **Prediction point:** features use data up to the 06:00 local reading, so they are available at 7:00. These are the 6:00 and 5:00 bike counts, capacity, the station's recent stockout history, day of week, month, and temperature and rain up to 6:00.
- **Model:** a small gradient-boosted classifier (`work/model.py`), with the 0.444 threshold taken from the costs ($40 / $90).

## Numbers
All numbers below are on the holdout and use 1,759 usable station-days.

| | holdout 2026 Q3 |
|---|---|
| Stockouts per day, 30 stations | 4.3 (rate 16%) |
| AUC | 0.92 |
| Average precision | 0.76 |
| Cost/day: model, threshold 0.444, max 8 | $290 |
| Cost/day: nothing | $387 |
| Cost/day: yesterday's stockout | $460 |
| Cost/day: 6:00 bikes ≤ 2 | $377 |

- **Calibration:** at 0.44–0.70 predicted, 59% actually ran out. At 0.70 and above, 89% did.
- **Tuning on validation:** I tried 7 configurations, all scored on the 2026 H1 validation period. That is the full count.
- **Model choice:** on validation, gradient boosting (AUC 0.939) was close to logistic regression (0.930).
- **Holdout use:** it was read once, by `final.py`, which refuses to run again. There was no tuning after the look.

## Decisions I made and the assumptions behind them
1. **Controller `ts` is UTC, not local.** Demand drops hourly at 12:00 in winter and 11:00 in summer. The shift lands on 2025-03-09, 2025-11-02 and 2026-03-08, which are the US daylight-saving dates. I converted to **America/New_York**. The timezone is inferred from the daylight-saving dates; I could not confirm it. If the city is in another US zone, the window is wrong. Please confirm this first.
2. **`daily_features.csv` is not used.** It holds same-day values (`trips_today`, `min_bikes_today`, `visits_today`) that are not known at 7:00. They would leak the answer.
3. **OFFLINE rows** show 0 bikes and 0 docks. They are not stockouts. Station-days with any OFFLINE reading in the window, or no 6:00 reading, are dropped from training and scoring (about 11% of the holdout, 212 of 1,971). The model says nothing about those stations.
4. **Capacity** is joined by `effective_from` from `stations.csv`. Several stations were moved or rebuilt in 2025–26.
5. **Weather:** `-999` in the weather file is a sentinel and is treated as missing. I use observed weather up to 6:00 only, because no forecast was provided.
6. **Other data fixes:** DST-day duplicate readings keep the last one. Gaps in the six later stations (S025–S030) are left as missing.
7. **Restock effect:** I assume restocking a station prevents its stockout. This is not in the data and drives the whole dollar figure. If a restock only helps part of the time, the saving shrinks in proportion.
8. **Costs:** $40 per stop and $90 per stockout are taken as given. A bad-day stockout costing more would lower the threshold.

## Weaknesses
- **Only 18 months of history, about 1.5 seasons.** Validation underpredicted spring (March–April) and the Central district (observed 15%, predicted 11%). On the holdout the errors went the other way for Central, East and North, and the bins were within about 5–10 points. It is reasonably calibrated but not exact.
- **The base rate is rising.** It was 8% in training, 11% in H1 2026, and 16% in Q3. Retraining monthly is needed.
- **The saving is moderate.** The model's value comes mainly from skipping stops, not from catching more stockouts.
- **Gaps in the check:**
  - Unseen stations or capacity changes are not flagged; there is no out-of-envelope check.
  - There are no per-group fairness checks beyond district.
  - Stations that are OFFLINE all morning are invisible to it.
- **Rebalancing log not used as a feature.** Truck visits are mostly at 16–19h. I did not model whether a visit the previous evening changes the 6:00 level.

## Operating notes
- Ops should log which stations the model flagged and what happened, so the next review has labels. Keep a small random share of days unscored, because restocking changes the data the model learns from.
- Fall back to "restock stations with 2 or fewer bikes at 6:00" if the 6:00 feed is missing or the model is unavailable. It is the only simple rule that beat doing nothing.

## Files
- `work/prep.py`: builds the station-day table.
- `work/model.py`: model, baselines and cost function.
- `work/final.py`: the one-shot holdout run.
- `work/holdout_result.json`, `work/ledger_dev.json`: numbers behind this report.
