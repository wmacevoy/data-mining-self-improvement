# Morning stockout model — report

**Recommendation: use it as a pilot, not yet as the standing process.** On three out-of-time test quarters it beats every simple rule by a wide margin. It has **not** been run on the sign-off quarter (`holdout/status_2026Q3.csv`), which I deliberately did not read. Run the sign-off once before relying on it. That step is not built yet; see "Not done".

No `QUESTION`/`PLAN`/`./se`/`./dm` existed. The task text is the requirement *(inferred)* and the decisions below are mine.

## What it predicts
For each station, each weekday, at 07:00 local (America/Denver): will any hourly reading at 07:00, 08:00 or 09:00 show 0 bikes? "Between 7 and 9" is ambiguous, so I took all three readings. Features use only data up to the 06:00 reading and prior days. The 07:00 reading is excluded because the crew plans at 07:00.

The rule for acting: visit the stations with p > 40/90 = 0.44 (a truck stop costs $40 against a $90 stockout), highest p first, at most 8.

Code is in `work/`: `prep.py` builds the table, `evaluate.py` runs the evaluation and writes `work/ledger.csv`. Model: gradient-boosted trees (scikit-learn `HistGradientBoostingClassifier`, 150 iterations, depth 4). The features are bike fraction of capacity at 00:00, 03:00 and 06:00 local, the overnight minimum, the station's previous-weekday stockouts (1, 14 and 60 days back), capacity, overnight and previous-day rain, 06:00 temperature, weekday and month, and station id.

## How good (rolling-origin, trained only on earlier data, dev data only)
Net $ saved per weekday versus doing nothing, assuming a visit prevents that station's stockout:

| Test period | Stockout rate | Model | Best simple baseline | Perfect-foresight ceiling | Model AUC |
|---|---|---|---|---|---|
| 2025-10 to 12 | 16% | $98 | $0 | $219 | 0.95 |
| 2026-01 to 03 | 15% | $75 | $0 | $212 | 0.92 |
| 2026-04 to 06 | 41% | $299 | $108 (station's 60-day rate) | $375 | 0.93 |

- Baselines: "no visits", "repeat yesterday" (it loses money, -$44 to -$52/day in the two low-rate quarters), and "station's 60-day stockout rate".
- The mean is about $157/day. That is roughly $35–40k per 250 weekdays, **if** the assumptions below hold. Quarter-to-quarter swing is large (see Caveats). I have no confidence interval beyond these three folds, which is a very small number of independent periods.
- Brier score is 0.065–0.10, against 0.15–0.41 for the base rate.
- Seed spread is zero: this model has no randomness (no subsampling), so I did not claim noise bounds from seeds.
- Number of configurations tried: 2 model variants (with and without station id), both in `ledger.csv`. They are within noise of each other. I kept the station-id version.
- I traced why AUC is so high, since it looked too good. It is real signal, not a leak. Dropping the 06:00 and overnight readings still gives AUC 0.91 and about $162/day on 2026 Q1–Q2. History and weather alone give 0.90. Stations at 0 bikes at 06:00 (2.6% of rows) are always stockouts.
- The model is better in summer (high base rate, more money) than in winter, where it only saves $75–98/day. Winter has fewer stockouts to catch.

## Data problems found and how I handled them
- `status.csv` `ts` is **UTC**, not local: the commute drop shifts by an hour between January and July. I converted to Denver time. This was inferred from the diurnal pattern, not documented. Confirm with whoever owns the controllers, because everything depends on it.
- `OFFLINE` rows (6,137) report 0 bikes. That is a sentinel, not a stockout. I treated them as missing. 172 station-days with no usable 07–09 reading were dropped, and station-days with some offline readings were kept using the readings available (understating stockouts slightly).
- The DST fall-back repeats an hour (52 duplicate rows). I kept the first.
- `weather.csv` has −999 for temperature: set to missing.
- `stations.csv` has capacity changes (moves/rebuilds on 2025-09-15 and 2026-02-01). I joined capacity by effective date, so "bikes" is expressed as a fraction of the capacity in force.
- **`daily_features.csv` was not used.** It has `min_bikes_today`, `trips_today` and `visits_today`, all computed over the same day and therefore not knowable at 07:00. A model built on it would look great and be useless.
- The rebalancing log's timestamp zone is undocumented, and visits occur at 16–19h. I did not use it. Any intervention effect on stockouts is not modeled.

## Caveats / what could make this wrong
1. **"A visit prevents the stockout" is assumed.** I cannot measure it from this data. If a restock only partly helps, savings shrink. If a visit fixes a stockout only 50% of the time, the p > 0.44 cutoff should rise to about 0.9, which would make it nearly useless. Please confirm with Operations. Money numbers are only as good as this.
2. The crew limit (8) is applied per day. In summer the base rate is 41%, so about 12 stations stock out each day and the crew can cover only 8. The ceiling column reflects that limit.
3. Only three test quarters, one of them a summer. Seasons repeat but I have no Q3 evidence except the sealed holdout.
4. The training data's stockouts happened under the existing evening restocking practice. A different practice would shift the distribution.
5. Station identity matters (station-level rates range from 1% to 60%). Adding stations or changing capacity again needs retraining or monitoring.

## Not done (and why)
- **Holdout not read.** Reading the sign-off set is a one-time look, and the decision to spend it belongs to a human. To sign off: train on all of `status.csv`, build features for 2026 Q3 with the same `prep.py` (the 60-day history needs the end of dev data prepended), score once, and record the result. Pass bar I'd suggest: beats `station_rate60` on net $/day. This is not scripted yet, because I could not test it without touching the holdout.
- Not deployed or scheduled; there is no serving code. The model is not saved, and `evaluate.py` re-trains from `dev.csv`.
- No bias or people-data concerns arise (stations only), so no audit.
- No tests beyond the evaluation itself; `prep.py` joins have no row-count assertions yet.
- No drift monitoring. Suggested: log each morning's predictions and compare to the next actuals weekly.

## Retro
Assumed without documentation: that `ts` is UTC, that the 06:00 reading is available at 07:00, and that a visit fully prevents a stockout. Worth writing a datasheet for `status.csv` (clock, OFFLINE sentinel) and a `QUESTION_v1.md` with these decisions.
