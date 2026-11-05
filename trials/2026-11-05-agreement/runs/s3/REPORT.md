# Morning stockout model: report

**Recommendation: use it, on trial.** It picks the 8 stations to restock each weekday and in validation did so at roughly **$200 net per day** over doing nothing (95% CI $178–229 over 129 days). The $200 rests on an assumption I could not check: that a restock stop prevents the stockout. The Q3 holdout has **not** been scored, so sign-off is still open.

## What it does
At 7:00 local each weekday it scores every station with P(bikes hit 0 at the 7, 8 or 9:00 reading). It recommends the top 8 stations, and only those with P > 0.31. That cut-off is $40 / ($40 + $90): a stop pays off when 0.31 × $90 > $40, assuming a stop prevents the stockout. On average it recommends about 6 stops a day, because fewer than 8 stations clear the bar on most days.

## How good (validation: trained on 2025, scored on Jan–Jun 2026, 3,785 station-days, 28% stockout rate)
| model | AUC | $/day net |
|---|---|---|
| station base rate only | 0.74 | 39 |
| "emptiest at 7am" rule (no model) | 0.92 | 139 |
| logistic regression | 0.944 | 193 |
| **gradient boosting (chosen)** | **0.951** | **203** |
| oracle (perfect foresight, same 8-stop cap) | | 294 |

- Calibration is reasonable: stations scored 0.9 or higher stocked out 99% of the time, and those scored 0.1 or lower 3%.
- AUC is 0.93–0.96 in every month and every district.
- The model barely beats the simple "emptiest at 7am" rule: +$64/day, versus +$100/day for that rule over nothing. Most of the value comes from a station's 7am bike count.
- **37% of the positives (391 of 1,057) were already at 0 bikes at 7:00.** Those are easy catches. On stations not empty at 7:00, AUC is 0.92 and the stockout rate is 20%.
- About 8.5% of days lose money (worst day −$80). On about 45% of days more than 8 stations clear the bar, so the crew cap is binding and some stockouts are left uncaught.
- Seed spread: zero. The boosting model is deterministic, so I did not test seed sensitivity. Uncertainty comes from the day-level bootstrap only.
- Tried: 4 configurations, all on the same split, plus a final refit. See `work/ledger.csv`.
- Only 18 months of data, so one summer and one winter. Seasonal shifts are untested. A new station, or one with changed capacity, behaves as the model has not seen.

## Calls I made (nobody was available)
- **The controller clock in `status.csv` is UTC, not local time.** I found this from the 1-hour shift of the commute and restock patterns at the DST dates. All 7am snapshots are built from local time. Anyone reading `ts` as local would score the wrong hour.
- **Label:** a station is "out" if an OK reading at 7, 8 or 9:00 local shows 0 bikes. Readings are hourly, so a stockout between readings is invisible. OFFLINE rows report 0 bikes; I treated them as unknown rather than empty. 227 station-days with no usable reading were dropped. Weekdays only; holidays are not excluded because there is no holiday list.
- **Excluded `daily_features.csv`.** It holds same-day values (`min_bikes_today`, `trips_today`, `visits_today`) that are not known at 7am. Using them would leak the answer.
- **Weather:** the `-999` temperature sentinel became missing. I used only readings at or before 7:00. Capacity comes from `stations.csv` as of each date, because stations were moved or rebuilt in Sep 2025 and Feb 2026.
- **Holdout:** not read, not scored. Scoring it is a one-shot decision for you. Do it once, against the bar below, and say so if you spend it.
- **Cost model:** $90 saved per stockout caught, $40 per stop, no other effects. A stop's effectiveness is assumed to be 100%. If a stop prevents only half the stockouts, the cut-off should be about 0.6. Please check the real figure; it is the most important number here.
- **Restocks are already in the data.** The rebalancing log shows past stops, so past stockout rates already reflect trucks. The model learns "given what happened under past rebalancing" and may drift if the policy changes.

## What I'd check before relying on it
1. Score the Q3 holdout once. A fail means AUC below about 0.90 or net value at or below the "emptiest at 7am" rule.
2. Run it in shadow for 2–4 weeks next to the current plan, logging its picks and what happened.
3. Retrain each quarter. Re-check after any capacity or station changes.

Not done: holiday handling, weekend service, a live data feed for the 7am snapshot, per-station cost differences.

## Files (`work/`)
`build.py` raw to features; `model.py` validation, which appends to `ledger.csv`; `extra.py` the checks above; `final.py` the deployed fit, saved as `model.pkl` with the threshold and cap. Run with `PYTHONPATH=work python -W ignore work/model.py`.

## Retro
Nobody had written down that the clock is UTC, how a stop affects a stockout, or what the pre-built table's `_today` columns contain; I assumed all three, as stated above. Worth adding to a datasheet in the repo, which does not exist yet.
