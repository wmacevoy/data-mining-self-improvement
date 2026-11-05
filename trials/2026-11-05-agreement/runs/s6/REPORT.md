# Morning stockout model: report

**Recommendation: use it, as a ranked list for the crew, not yet as a committed plan. Run the sign-off on the 2026Q3 holdout first.**
On Jan–Jun 2026 data it would have cut the cost of 7–9am stockouts and truck stops by about 25%, which is $23.5k over 129 weekdays (95% interval $20.3k–$26.9k). The estimate rests on one assumption I could not check (see Assumptions).

## What it does
Each weekday at 7:00 local, for each of the 30 stations, it gives P(station hits 0 bikes at the 7:00, 8:00 or 9:00 reading). Restock the stations with P > 0.44 (that is $40 / $90, the break-even), highest first, at most 8.
Inputs are the 0:00–6:00 local bike counts, capacity, weekday, 6am temperature, 6-hour rain, and the station's recent stockout history. Model: gradient boosting (`work/model.py`, `work/final_eval.py`).

## How good (validated on Jan–Jun 2026; trained on 2025 only; holdout not touched)
Cost = $40 per truck stop + $90 per uncaught stockout. Doing nothing costs $95,130 over the 129 weekdays (1,057 stockouts).

| Policy | Cost | Saved vs nothing |
|---|---|---|
| No action | $95,130 | – |
| Restock yesterday's stockouts | $90,620 | $4.5k |
| Restock the 8 stations emptiest at 6am (no model) | $82,770 | $12.4k |
| Logistic regression on 6am fill level | $75,210 | $19.9k |
| **Gradient boosting (shipped)** | **$71,430** | **$23.7k** |

- AUC 0.933 (0.925–0.942, bootstrap over days). Brier 0.091. Calibration is good: of the stations given P in 0.6–0.8, 70% ran out; of those over 0.8, 95% did; of those under 0.1, 3.7%.
- About 5 truck stops a day on average, 663 in total, catching 558 of 1,057 stockouts. It misses about half. Many stockouts happen at stations that were fine at 6am and are not predictable from the data we have.
- Stable across months (AUC 0.89–0.93) and districts (0.93–0.94).
- The main signal is the 6am bike count: a station at 0 at 6am was out in the window 99.6% of the time. So much of the value is "what is already empty or nearly so". The simple emptiest-8 rule captures about half of the model's saving. The model's extra comes from using fill level, capacity, history and weather together, and from sending fewer trucks on quiet days.

## Things I decided (nobody was available to ask)
- **Target:** a station-weekday is a stockout if any 7:00, 8:00 or 9:00 local reading is OK with 0 bikes. Weekdays only. Public holidays are not excluded.
- **Prediction point:** only readings up to and including 6:00 local are used, so the 7:00 reading is not an input. If the 6am reading can in fact be fetched at 7:00, a 7:00 reading would help, but I did not assume it.
- **Timezone:** `status.ts` is not local time. The commute dip lands at 15–16h in the file and shifts with daylight saving, so I treated it as UTC and converted to America/Denver. The README says "controller clock"; please confirm this with whoever owns the controllers. If it is wrong, every number here is wrong.
- **OFFLINE rows** show 0 bikes. I did not count them as stockouts or as real zeros. A station offline for the whole window is dropped (no outcome); in total 5.8% of 6am readings were offline. 52 duplicate rows at the spring-forward hour were de-duplicated (kept the last).
- **Weather:** `-999` in `temp_c` treated as missing.
- **Capacity** is taken as of each date from `stations.csv` (it changed in 2025-09 and 2026-02).
- **`daily_features.csv` is not used.** It holds same-day values (`min_bikes_today`, `trips_today`) that are not known at 7:00; using it would leak the answer. I did not need it. Its `visits_today` also depends on trucks that the model is meant to schedule.
- **Rebalancing log** was not used as a feature (visits are mostly 16–19h, and their effect is already in the 0–6am counts).
- **Threshold** 0.44 comes straight from your two prices. It is your decision to change.

## Assumptions and risks, not checked
1. **A truck stop is assumed to prevent that station's stockout fully.** The log has no outcomes, so I can't measure it. If a stop only helps half the time, the saving falls a lot; the threshold should rise to 40/(90×effect). This is the biggest assumption in the dollar figures.
2. **Only 18 months of data, one year of training.** Spring/summer 2026 was validated on a model that saw one summer. Stockout rates swing from about 10% (winter) to about 44% (May–Jun), and a new system change (like the Feb 2026 rebuilds) could shift things. Retrain quarterly and watch the weekly calibration.
3. **Operations needs the 6am readings by 7:00 and a fallback if they are missing.** Where the 6am reading was missing (275 rows, 2.4%) the model still runs, but I did not evaluate those rows separately. If the feed is down, use the "emptiest 8" rule.
4. **Days with more than 8 candidates** (up to 21) are capped at 8; the cost figures include that cap.
5. **Uncertainty:** the interval is a bootstrap over days (same-station days are correlated, so it is likely a little narrow). The seed spread was not measured: the boosting model is deterministic here, so identical seeds gave identical results.
6. **Holdout:** I did not read any file in `data/holdout/`. It is reachable from the working directory, so it is not protected mechanically. Please move it.

## What was tried (the ledger)
`work/ledger.jsonl` records every configuration scored on the validation period (3 baselines, 9 boosting runs over 3 feature sets, plus the logistic and emptiest-k rules and the final model; seeds repeated, so the real count of distinct models is about 8). "Best of about 8 on validation, holdout untouched." The feature set was the same in all of them apart from ablations, and ablations moved cost by <$1.1k. Weather helped little ($40 in cost); I kept it for plausibility.

## Next steps
1. Someone with authority runs the 2026Q3 holdout once as sign-off: retrain nothing, apply `model_trained_to_2025.pkl` by the same pipeline (`prep.load_status` then `prep.build`), and judge it against the bar you set. I did not set a bar for "good enough"; that is your call. I suggest at least the $12.4k saving of the no-model rule, with a clear margin.
2. Measure what a truck stop actually does to a station's morning stockouts (a week with a random half of stops skipped would do).
3. Retrain on all data through the latest quarter before production; the saved model is the validated one (trained through Dec 2025).

## Files
`work/prep.py` (data → features and target), `work/model.py` (baselines, policy cost, ledger), `work/final_eval.py` (final comparison, intervals, slices), `work/ledger.jsonl`, `work/model_trained_to_2025.pkl`. Run from `work/` with `python -I prep.py` helpers; `dev.pkl` is produced by `prep.build`. I have not made a single one-command raw-to-report script.

## Retro
I had to infer the timezone and the dedupe rules from the data; nobody wrote them down. Suggest adding a datasheet to `data/` with the clock, sentinels, and when each column becomes known, and an explicit marker on the holdout directory.
