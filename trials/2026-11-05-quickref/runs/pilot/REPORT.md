# Morning stockout model: report

**Recommendation: yes, use it, as a ranking aid for the 7:00am restock list, and review it after a month.** It reliably beats simple rules on data it never saw. The dollar figure below rests on one assumption I could not check (see Caveats).

## What I built
A gradient-boosted classifier (`work/model.py`, data prep in `work/prep.py`). Each weekday at 7:00 local it scores every station with a reading, giving the probability that the station is empty at an 8:00 or 9:00 reading. Dispatch rule: restock the top 8 stations by probability, and only those above 0.44 (= $40 / $90, the break-even).
Inputs, all known by 7:00: bikes at 7:00, 6:00 and 5:00, capacity, fill ratio, day of week, month, temperature and rain at 7:00, yesterday's morning minimum, yesterday's 7:00 bikes, and whether yesterday had a stockout.

## How good it is
The sign-off set (2026 Q3) was used **once**, after all choices were made. Model trained on all of 2025-01 to 2026-06; 66 weekdays, 1,770 station-mornings.

Harder question: stations that have bikes at 7:00 and are empty at 8 or 9. There were 7.1 per day.

| | AUC | net $/day vs. doing nothing | stops/day | stockouts caught/day |
|---|---|---|---|---|
| **GBM (final)** | **0.936** | **$207** | 6.3 | 5.1 |
| logistic regression | 0.919 | $198 | 6.4 | 5.1 |
| rule: fill < 15% | 0.719 | $149 | 3.7 | 3.3 |
| rule: bikes ≤ 2 | 0.670 | $120 | 2.6 | 2.5 |

- The final model catches about 5 of 7 stockouts per day, with roughly 1.2 wasted stops per day.
- Calibration is decent. Stations scored below 0.1 stocked out 2% of the time; those scored above 0.8, 93%. The 0.3–0.44 band is underconfident (observed 50%).
- Results were similar in each of Jul, Aug and Sep (AUC 0.93–0.94).
- Before touching the sign-off set I validated on time-ordered splits (train 2025 → test 2026 H1, and train 2025 H1 → test 2025 H2). Results were consistent (AUC 0.92–0.93; $94–97/day on the harder target).
- The simple logistic model is nearly as good as the GBM. If the team wants something easier to maintain, it is a reasonable substitute.

On the easier "any empty reading 7–9, including already empty at 7:00" target, AUC is 0.96 and net is about $320/day. That headline is inflated, because the 7:00 reading is both a feature and part of the label. Do not quote it.

## Decisions I made (nobody was available to ask)
1. **Controller clock is UTC, not local.** `ts` in the status files is UTC. I inferred this from the data: the morning drawdown sits 7 hours after local in winter and 6 in summer, and the DST duplicate rows fall on the US spring-forward date at 2am Mountain. I converted to `America/Denver`. This is an inference, not documented. If the zone is wrong, everything is shifted and the model is wrong. **Please confirm with whoever owns the controllers.**
2. **Target:** "empty (0 bikes, status OK) at any hourly reading at 7:00, 8:00 or 9:00 local." Weekdays only. OFFLINE readings are not stockouts.
3. **Not used: `daily_features.csv`.** It holds same-day values (`trips_today`, `min_bikes_today`, `visits_today`) that are not known at 7:00; using them would leak the answer. I rebuilt features from raw status.
4. **Data cleaning:** dropped 52 duplicate timestamp rows (DST day); weather `-999` is a missing-value sentinel and was set to NaN; capacity taken from `stations.csv` by `effective_from` date (stations were moved and rebuilt, changing capacity).
5. Station-mornings with no 7:00 reading (station OFFLINE, about 8% in the holdout) are not scored.

## Caveats
- **Biggest assumption: a restock fully prevents the stockout.** Dollar figures assume a $90 loss is avoided for each caught station and $40 spent per stop. The real prevention rate, and how many bikes a stop adds, are not in the data. The `rebalancing_log` shows only evening visits (16:00–19:00), none in the morning. At a 50% prevention rate the net would be about $60–70/day, still positive, but I did not model this carefully.
- **Hourly data:** a station that empties and refills between readings is invisible, so true stockouts are likely undercounted.
- **Weather:** I used observed weather at 7:00. If there is no live feed at 7:00, use the 7:00 observation, not a forecast; the model has not seen forecast error.
- **Seasonality:** the training data covers each season only once (Jan 2025 to Jun 2026 includes one winter and one summer plus part of the next). Stockout rates were higher in the sign-off quarter (about 43% of station-mornings vs about 26% in training), and performance held, but a second winter has not been seen.
- Only 66 test days; the $/day estimate is noisy (roughly ±$30).
- Weekdays only; holidays are not handled.
- The 8-stop crew limit was rarely binding (6.3 stops/day on average), though busy days may hit it.
- I did not build a production scoring job or a live pipeline; this is the model and evaluation.

## Suggested next steps
1. Confirm the controller timezone.
2. Run it in shadow mode for 2–4 weeks next to the current process, logging the 7:00 inputs and predictions.
3. Measure the real effect of a morning stop on stockouts (start by logging morning visits).
4. Retrain monthly, and re-check after the first winter.

Files: `work/prep.py` (features and label), `work/model.py` (models and evaluation), `work/holdout_result.txt` (sign-off output).
