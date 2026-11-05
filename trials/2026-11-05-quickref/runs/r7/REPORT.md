# Morning stockout model: report

## Recommendation
**Do not build or use a stockout model for the 7:00–9:00am window. Do not send the crew out on a prediction.** Stockouts in that window almost never happen, so there is nothing to predict and nothing worth spending a truck stop on. Keep the current practice. The costs are not close, even assuming a perfect model:

| | Count | Cost |
|---|---|---|
| Station-mornings where a station hit 0 bikes at 7–9am (dev, Jan 2025–Jun 2026, 16,225 station-days) | 2 | about $180 over 18 months |
| Same, holdout 2026Q3 (2,744 station-days, looked at once) | 1 | about $90 for the quarter |
| One truck stop | – | $40 |

A truck stop pays off only if the chance of a stockout at that station exceeds 40/90, about 44%. The base rate is about 0.01–0.04% per station-morning. No station-day in the data came near 44%.

I did not train a predictive model, because with 2 positive events in dev there is nothing to fit or validate. The only exploratory model was a logistic regression on a looser, near-empty target (at most 2 bikes in the window, 50 events in dev). It got an AUC of about 0.65 on 14 test positives, and its highest predicted probability was 0.5%. That is not usable. The baseline "predict no stockouts" costs about $90 a quarter in missed events.

## Where the stockouts are
Stockouts are common outside the commute window, and the 7:00 hour is a hard reset:
- Every station jumps up by about 4–9 bikes at one fixed hour every morning (07:00 in the controller clock in winter, 06:00 in summer). The jump is not in the truck log, so I don't know what causes it.
- Afternoon and overnight are the problem. The share of station-hours at 0 bikes is about 24% at 15:00 in summer and 9–13% overnight in summer. In the window it is about 0.00%.
- If operations care about stockouts, the question worth asking is about the afternoon and evening, 13:00–20:00 and overnight. That is a different question and a different decision, so I did not answer it. It needs a client conversation before any model.

## Decisions I made (nobody was available to ask)
1. **Clock (assumption, not confirmed).** `status.csv` has duplicate and missing hours on the March DST dates, and the morning jump moves from controller hour 7 to hour 6 in summer. I read this as the controller running on fixed standard time. I took local time as controller time plus 1 hour from the 2nd Sunday of March to the 1st Sunday of November. In my local-time check I used the month as an approximation, April–October. That is off by up to about a week at the boundaries and does not change the conclusions. Under this reading the jump happens at local 7:00 all year and the 7–9am window is after the jump.
   - The log timestamps line up with the controller clock all year, in every month, with the restock jump appearing in the reading stamped at the log time. So the log is on the controller clock, not DST-adjusted.
   - **If this is wrong,** and local 7–9am is actually controller 6–8 in winter, there is a pre-jump hour in the window with 0 bikes in about 2% of winter station-mornings (138 events at controller hour 6, Nov–Mar). The conclusion would then be weaker: a real but small, winter-only problem, and the jump at 7:00 would itself be the fix. Someone who knows the controller clock should confirm it. This is the largest open uncertainty.
2. **Label.** A station "runs out" if any OK-status reading at local 7, 8 or 9 shows 0 bikes. OFFLINE readings always show 0 bikes and are not stockouts, so I excluded them. About 0.9% of readings in the window are OFFLINE. A station that is offline gets no bikes, but that is a different failure.
3. **Duplicates.** I removed 52 duplicate station-hours at the DST fall-back and kept the last reading. They differ by 0–1 bike.
4. **Not used:**
   - `daily_features.csv`. `min_bikes_today` and `trips_today` are whole-day aggregates that are not known at 7:00, which is leakage. I did not use `visits_today` either.
   - `weather.csv`. It has `-999` sentinels in `temp_c`, and weather had no role once the base rate was this low. Its "local" timestamps also look like standard time, because the daily peak hour moves 15 → 14 in summer.
   - `stations.csv`. Station capacities change in Sept 2025 and Feb 2026, and a model would need a capacity-as-of-date join. It was not needed here.
5. **Holdout.** I looked at 2026Q3 once, for the base rate only, after the conclusion was already reached on dev data. No model, threshold or choice was tuned on it, and it is now spent for any later model. The ledger is `work/ledger.txt`.

## Caveats
- Two or three events on dev is far too few to say the rate is exactly zero. The 95% upper bound on the dev rate is about 0.04% per station-morning. Even at 10 times that, a model would not pay for its truck stops.
- The data is the 30 stations in the exports. Any station with a different pattern (new, much smaller, in an event area) is not covered.
- I did not check whether the weekday-only plan matters. Weekends make up the same share of the events, and there are almost none of either.

## Files
`work/prep.py`, `work/check.py` (exploratory checks; the numbers above come from these and from inline queries that I did not keep as scripts). There is no model artifact, by design.
