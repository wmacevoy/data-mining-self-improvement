# Morning stockout model: report

**Recommendation: do not use a model for this. Do not adopt a per-station stockout list as the basis for the 7:00 plan.** In this data, a station almost never runs out of bikes between 7:00 and 9:00am, so there is nothing for the crew to prevent. I built a model anyway and it does not help (details below). Decisions I made without anyone to ask are marked **[decision]**.

## What the data says
- **Real 7–9am stockouts are about 0.02% of station-days.** I counted a station as out when it reported status OK and 0 bikes in any of the 7:00, 8:00 or 9:00 readings.
  - Training (2025-01 to 2026-06): 4 events in 16,293 station-days.
  - Holdout (2026-Q3): 1 event in 2,750 station-days. It was on a weekend, and weekdays are all that matters here.
  - Weekdays only, training plus holdout: 2 events in 13,608 station-days.
- **The 1.3% figure you get from a naive "min bikes = 0" count is wrong.** `OFFLINE` rows report 0 bikes, and they account for nearly all of that 1.3%. An offline dock is a comms problem, not a stockout, and a truck can't fix it. **[decision]** I excluded OFFLINE readings from the target.
- **Stations do empty, but not in the window.** Zeros are common from about 13:00 to 06:00 and almost absent from 07:00 to 12:00. Mean bikes jump from about 7–12 to about 12.5 at exactly 7:00 local, every day of the year. That is the opposite of a morning depletion pattern. The log shows only evening restocks (16–19h, weekdays), so I can't explain the jump. Something outside the data resets stations at 7:00. Ask the controller or ops team, because if it stopped, stockouts would appear.
- **The "almost out" event is rare too.** At 2 bikes or fewer, the rate is 0.3–0.4% of station-days. That is still far below the break-even rate.

## Economics
A stop costs $40 and a miss costs $90, so a stop only pays if P(stockout) > 40/90 ≈ 44%.
- Base rate is about 0.015% (weekdays), which works out to roughly $0.01 per station-day in expected misses.
- The holdout had 66 weekdays and 0 weekday stockouts. "Never visit" cost $0 on the 7–9 target. Sending the crew to 8 stations a day would have cost about $21,000 for nothing.
- Only a model that could single out stations with >44% risk would pay. No such stations exist in this data.

## The model
Code is in `work/` (`load.py`, `model.py`). It is a gradient-boosted classifier using only information available at 7:00:
- 5:00 and 6:00 bike counts
- prior evening minimum
- yesterday's morning minimum
- whether the station was restocked yesterday evening
- weekday
- overnight weather
- whether the station was offline yesterday

It was trained on data up to 2026-06-30 and scored on the untouched 2026-Q3 holdout.

| Target | Training positives | Holdout positives | Holdout AUC | Holdout average precision (base rate) |
|---|---|---|---|---|
| real stockout | 4 | 1 | 0.70 | 0.001 (0.0004) |
| ≤2 bikes | 52 | 12 | 0.61 | 0.006 (0.0044) |

- With 4 training events and 1 holdout event, **the first row cannot say anything.** Its AUC of 0.70 is from one positive and is noise.
- The ≤2 bikes proxy has enough events to see that the model has essentially no skill (AUC 0.61, precision roughly the base rate).
- It would flag 1 station-day above the 44% threshold on the real target, and 0 on the proxy.
- **So the model is not good enough to use, and no honest model could be, given this data.** I would rather say that than hand over a tuned model that looks fine.

## Problems in the inputs
1. **Controller clock is wrong during daylight saving time.** `ts` is standard time all year, so it is 1h behind local time from 2025-03-09 to 2025-11-02 and from 2026-03-08 to 2026-11-01. I confirmed this because the 7:00 jump shifts to controller hour 6 in those months and lines up after correcting. **[decision]** I added 1h in those windows. Without that fix, the "7–9am" window would really be 6–8am in summer.
   - 52 duplicate rows appear on the two spring-forward mornings (09:00 controller). I kept the last.
   - Two of the five "real" stockouts are readings of 0 at 7:00 on 2026-03-08, the transition day, and I suspect they are clock artifacts. That would leave 3 events in 16,293 station-days.
2. **`daily_features.csv` should not be used.** `trips_today`, `visits_today` and `min_bikes_today` are same-day values, which you don't know at 7:00. Its `min_bikes_today` is zero on 29% of days because it covers the whole day (and OFFLINE zeros), not 7–9am. A model built on it would look excellent and be useless. I did not use it.
3. **Weather has -999 sentinel values** (184 rows). I set them to missing.
4. **Stations change.** `stations.csv` has moves and rebuilds with changed capacities (e.g. S001: 19, 23, 21). I did not need capacity for the final model, but any capacity-based feature must use the version in effect on that date.
5. About 12% of station-days are missing at least one 7–9am reading. 1.3% have an OFFLINE reading.

## Caveats and what I did not do
- The window is hourly readings at 7, 8 and 9. A stockout between readings would be invisible. **[decision]** I treated 9:00 as inside the window.
- I did not use the 7:00 reading as a feature. Using it would be allowed at 7:00 but nearly all of the signal would be the unexplained jump, and I would not trust it.
- **[decision]** Weekends excluded from cost figures because planning is weekday-only. I kept them in training.
- Not done: hyperparameter tuning, per-station models, and calibration. With 4 events they would only overfit.

## What I'd suggest instead
1. Find out what happens at 7:00 that moves stations from ~7 to ~12.5 bikes. It decides whether the morning is safe. If it is not a permanent process, the finding above does not hold.
2. Fix the DST handling in the export, or document it.
3. If the real worry is the afternoon/evening, or overnight emptiness, tell us. Zeros are common there (peak around 16:00), and a model of that would have real data to learn from. That is a different question from the one asked, and I did not answer it.
4. Offline stations (about 1% of station-days) might be worth a separate alert. They do not need a truck, but a human should look.
5. Recheck this analysis after any change to the 7:00 process, or if demand shifts, and monitor real (status OK) zeros in 7–9am weekly. If the weekly count rises, revisit this.
