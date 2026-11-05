# Morning stockout model: report

**Recommendation: use it, as an advisory ranking, not as a proven money-saver.** On the Q3-2026 holdout it picked the right stations well. Its dollar benefit depends on one assumption nobody could confirm: that a restock fully prevents the stockout.

## What it does
Each weekday at 7:00 local it takes the readings up to 06:00 local. It estimates, for each station, P(bikes = 0 at the 07:00, 08:00 or 09:00 reading). It proposes up to 8 stations, highest probability first, and only those above P = 40/90 = 0.44, the point where a $40 stop beats a $90 expected loss.
Code is in `work/`: `build.py` (dataset), `model.py` (model, evaluation), `predict.py` (`PYTHONPATH=. python predict.py 2026-09-30`).
The model is a gradient-boosted classifier. Its inputs are:
- bikes at 00:00, 05:00 and 06:00, and the overnight minimum;
- capacity at that date, dock fill, and OFFLINE at 06:00;
- the station's trailing stockout rates;
- weekday, 06:00 temperature and recent rain.

## Result (holdout 2026-07-01 to 09-30, 1,654 weekday station-mornings, touched once, after choosing features on Apr–Jun 2026)
| | AUC | $/day (30 stations) |
|---|---|---|
| do nothing | – | 1,117 |
| trailing 28-day stockout rate | 0.76 | 901 |
| simple rule: "low bikes at 06:00" | 0.86 | 856 |
| **model** | **0.95** | **804** |
| oracle (perfect knowledge, 8-station cap) | – | 753 |

- The model saves about **$313/day** against doing nothing. The ceiling at 8 stops/day is about $364, so it gets roughly 86% of it. The simple rule gets about 72%.
- The model is calibrated: predicted 0.6 means about 60% observed. In the holdout, the stations it picked were stockouts 92% of the time, at about 7.3 picks/day.
- At roughly 260 weekdays this is about $80k/year, but only under the assumption below.

## Caveats
1. **K4 assumption, not tested:** a restock is assumed to fully prevent the stockout. I could not check it. `rebalancing_log.csv` is the *reaction* to stockouts, not an experiment: every station visited that day had a stockout (100%). It also stops 2026-06-30. Whether a truck stop of the usual size covers a 7–9am rush is a question for Operations. If a restock only prevents half the loss, the benefit roughly halves; the ranking is still the right order.
2. **The summer holdout is easy.** Stockouts are seasonal: about 15–25% of station-mornings in winter and 40–57% in May–Sep. The holdout is all summer, and in summer far more than 8 stations are at risk each day, so the 8-station cap binds. In a winter backtest (Jan–Mar 2026, trained on 2025 only) AUC was 0.92 but the dollar gain over doing nothing was small: $86/day for the model vs $77/day for the simple rule, since few stations are at risk. Winter value is real but modest, and only one winter exists to test on.
3. **Decisions I made, any of which can be changed:**
   - `ts` in the status files is **UTC**, not local. Evidence: the commute drawdown sits at ts 13–16 in winter and 12–15 in summer, and the midnight refill at ts 07/06. I converted to America/Denver. The duplicated rows at the DST change (~52) were de-duplicated, keeping the last.
   - "Between 7:00 and 9:00" means the 07, 08 and 09 readings. Features stop at 06:00 so nothing from the window leaks in.
   - A stockout is an OK reading of 0 bikes. OFFLINE readings report 0 bikes, which is a dead controller, not an empty station, so they are not counted. Station-mornings with an OFFLINE reading and no OK zero have an unknown label and were dropped (~6%).
   - Weekdays only. Weekend stockout rate is about 2.5% vs 21%.
   - Capacity comes from `stations.csv` as of the date (some stations moved or were rebuilt in 2025-09 and 2026-02). Weather `-999` is a missing-value sentinel and was treated as missing.
   - I did **not** use `daily_features.csv`. Its `min_bikes_today`, `trips_today` and `visits_today` are same-day values, which are only known after the morning, so they leak the answer.
4. Not checked: model drift after the data ends. Retrain regularly, and watch the picks' hit rate (about 90% expected; a fall below about 70% means something changed). Station moves or rebuilds change behavior and the history for them is short.
5. `predict.py` was run once on the last day of the data as a smoke test. It has no tests, no alerting, and nothing handles a missing 06:00 reading beyond passing it to the model as missing (4.8% of the holdout).
6. The log times (16:00–19:00) don't match when the status data shows refills (local midnight). I don't know which clock the log uses or what happens at midnight; worth asking Operations.

## Open questions for Operations
- Does a restock prevent the stockout, and how many bikes does a stop deliver?
- What is the midnight refill in the status data, and why do stations still run out after it?
- Is a missed stockout really $90 in every season?
