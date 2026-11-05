# Morning stockout model: how good is it, and should Operations use it?

**Verdict: yes, use it to rank stations for the 8-stop crew. Do not treat it as a stockout predictor you can plan around, and do not expect it to be much better than a one-line rule.** It was built without access to anyone, so every call below is mine and is listed under "Decisions and assumptions".

## What it predicts
For each weekday and station, at 07:00 local: will the station show 0 bikes (status OK) on any hourly reading at 07:00, 08:00 or 09:00 local? Features use only information from before 07:00: bike counts at 00:00–06:00, capacity (as of that date), yesterday's outcome, 7/28-day stockout rates, day of week, month, overnight temperature and rain, and whether a truck visited yesterday. Weekends are excluded because the crew doesn't plan them and the stockout rate is about 2%.

## How good (holdout 2026-07-01 to 2026-09-30, looked at once, 1,852 station-days, 66 weekdays)
| | Result |
|---|---|
| Stockout base rate | 45% (training: 27%) |
| AUC | 0.968 (validation on Jan–Jun 2026 gave 0.963) |
| Brier score | 0.072 (always guess the training rate: 0.279) |
| Calibration | Close. Predicted 0.95 → observed 0.98; predicted 0.53 → observed 0.62; predicted 0.15 → observed 0.11. Mid-range slightly under-predicts. |
| Stations S025–S030 | AUC 0.945 vs 0.969 for the others; the model over-predicts S025–S030 a little (23% predicted, 21% observed). |

**Dollar value** (rule: each day restock up to 8 stations with p > 40/90 = 0.44, the break-even point for $40 vs $90):

| Strategy | Quarter cost | Notes |
|---|---|---|
| Do nothing | $75,330 | 837 stockouts |
| Model | $53,140 | 478 stops, 378 stockouts missed |
| Best simple rule (restock if bikes at 06:00 ≤ 4; threshold tuned on pre-holdout data only) | $54,840 | |
| 28-day station stockout rate | $61,350 | |

The model saves about **$336/day** over doing nothing (95% bootstrap over days: $309–$361), and about **$26/day** over the simple rule ($12–$40). That last gap is real but small, about $1.7k a quarter. The simple rule captures nearly all of the value, because the 06:00 bike count carries almost all of the signal. The dollar figures include the assumption below (restocking prevents the stockout).

**The 8-stop cap is the binding constraint, not the model.** The holdout averaged about 12.7 stockouts per weekday against 8 stops. Even a perfect model would miss most of the cap's overflow. A second crew, or more stops on summer days, is worth more than model improvements. (Cost with no cap on training-period validation: $59.8k vs $68.5k capped, a $9k difference over 129 days.)

## Decisions and assumptions (K4s — please confirm)
1. **The controller clock is UTC, not local time.** The README says only "controller clock". The evidence: the controller's hour-of-day pattern shifts by exactly one hour at the US daylight-saving dates, and truck visits (logged on the same clock) are at 16–19 in the log but land at 09:00–11:00 local only if UTC→Pacific is applied. I used America/Los_Angeles. The offset is inferred, not confirmed. **If wrong, every number here is wrong.** Reading the clock as local time instead gives a near-zero stockout rate in the 07:00–09:00 window, which contradicts the business premise. This is the first thing to confirm with someone who knows the controllers.
2. **The window includes the 09:00 reading.** Readings are hourly, so a stockout between readings is invisible. The true stockout rate is probably higher than the labels say.
3. **A restock prevents the stockout.** This is what the dollar figures assume. The truck log shows visits at 09:00–11:00 local, after most stockouts have begun, and refills appear in the data at the log hour. A truck dispatched at 07:00 may not get there before 08:00. If restocks arrive too late, the savings shrink toward zero. Please check actual crew timing. I could not test this from the data.
4. **OFFLINE readings are not stockouts.** Offline docks report 0 bikes, which would be a false stockout. A day with offline readings in the window and no real zero is dropped from training and scoring (about 4% of weekday rows; 118 holdout rows). In production, an offline station has no forecast. Flag it for a human.
5. **Features use only data before 07:00 local.** The 07:00 reading is excluded even though it may be available at 07:00. Weather is overnight temperature and rain only, since morning rain isn't known at planning time. This costs some accuracy and avoids leakage. A forecast feed would likely help.
6. **Duplicate controller rows** (52, on the two spring DST dates) are resolved by keeping the first. Station moves and rebuilds change capacity (2025-09-15, 2026-02-01); I use capacity as of the date.

## What I did not use, and why
`data/daily_features.csv` was not used. Its columns `min_bikes_today`, `trips_today` and `visits_today` summarise the day being predicted, so using them would be leakage (the minimum over the day contains the answer). Its date/clock convention is also undocumented. Anyone reusing the dashboard table for forecasting should know.

The `-999` weather sentinel (184 rows) is set to missing.

## Known weaknesses
- **Season shift.** Base rate was 27% in training and 45% in the holdout (summer). The model held up, but only one summer of training exists, so next summer is not independent evidence. Check calibration monthly.
- **Missing readings.** S025–S030 have many missing hourly rows (about 30% fewer rows than the other stations). Their labels are built from fewer readings in the window and likely understate stockouts; the model is somewhat weaker there. Why readings go missing (and whether it correlates with busy hours) is unknown.
- **Feedback.** The model drives where trucks go, and truck visits change next day's bike counts. Future training data will reflect the model's own interventions. Keep logging what the model recommended against what happened, and consider leaving a random few stations unaided to keep an unbiased signal.
- **Truck visits as a feature.** Visits are logged as reactions to empty stations, so they are a feature about yesterday only. I did not use them for same-day prediction.
- **No hyperparameter search.** One configuration (gradient boosting, depth 3, 150 iterations), no tuning, so the validation and holdout figures aren't inflated by search. Five seeds on validation gave identical AUC (the method is deterministic without subsampling), so seed spread is not informative.
- Looks at the data: I explored the training period and the clock question on pre-holdout data only. The holdout was scored once, plus one quick check of the holdout's file structure. It is now spent for sign-off purposes. A new quarter is needed for any further model change.

## Recommendation
1. Confirm the clock (assumption 1) and crew timing (assumption 3) before relying on the dollar figures.
2. If both hold, run the model each morning and send the crew to the top 8 stations by probability above 0.44. Keep the simple rule (bikes at 06:00 ≤ 4) as the fallback when data are missing or the model fails. It is almost as good.
3. Trial it for 2–4 weeks in shadow mode (log recommendations, don't act) or alongside the current process, and compare to the stockouts that actually happened.
4. Add a feed of the 06:00 readings with a freshness check. If the 06:00 reading is missing or stale, fall back to the rule or a human.

## Reproduce
Scripts are in `work/`: `build.py` (labels and features), `model.py` (model, cost function, validation on Jan–Jun 2026), `final.py` (one-shot holdout scoring). Run each with `python -I <script>`. These are not unit-tested. There is no fixture or CI, and no ledger beyond what is stated in this report.
