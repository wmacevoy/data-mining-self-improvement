# Morning stock-out model: report

**Recommendation: yes, use it as a ranking aid, starting now, and plan on a short trial.** I'd treat the dollar figure below as an upper bound until you've seen real restocks prevent stock-outs. This was written by an agent and needs a person to read it before anyone acts on it.

## What the model does
At 7:00am local it estimates, for each station, the chance of an empty dock-side (0 bikes) at one of the 7, 8 or 9am readings. Each day, restock the stations with the highest probability, up to 8, but only those above **p = 0.44**.
- **Where 0.44 comes from:** restocking costs $40 and prevents a $90 loss, so it pays when p > 40/90.
- **Threshold sensitivity:** on validation, 0.30, 0.44 and 0.60 all gave about the same savings (130, 132 and 127 $/day). The exact threshold doesn't matter much.

Inputs, all known by 06:00 local:
- the bike counts at 06:00 (or the last reading we have), at 03:00 and at 00:00;
- the overnight minimum and the station's capacity;
- the day of week and the month;
- the 06:00 temperature, overnight rain, and the station's own trailing 28-day stock-out rate.

The model is a gradient-boosted tree (`work/model.py`).

## How good it is

Numbers are from stations/days where all three morning readings were seen. "Cost" is $ per day across all stations, with the crew cap of 8 applied.

| | Validation (2026 Jan–Jun, trained on 2025) | **Holdout (2026 Jul–Sep), one look** |
|---|---|---|
| Stock-out rate | 21% | 32% |
| AUC (model) | 0.955 | **0.958** |
| AUC "bikes at 6am ≤ 3" rule | 0.65 | 0.64 |
| Daily cost, do nothing | $468 | $692 |
| Daily cost, model | $336 | $481 |
| Saving, model vs nothing | $132/day (95% CI 110–153) | **$211/day (95% CI 178–245)** |
| Saving, "≤3 bikes" rule vs nothing | $76/day | $102/day |

- **Calibration holds up on holdout.** Predicted 0.1–0.2 happened 19% of the time, 0.6–0.8 happened 75%, and above 0.8 happened 97%.
- **All three districts work.** Holdout AUC was 0.95 (Central), 0.97 (East) and 0.97 (North).
- **The model barely loses ground over time.** July to September AUC was 0.94, 0.97 and 0.96.
- **It beats the simple rule clearly.** A model with only a naive baseline (same stock-out rate as last year) scores AUC 0.5; a per-station trailing rate scores 0.76.
- **The intervals cover the 211/day.** They come from resampling days. They don't include the assumption risks below.

## Why I believe the 0.96 AUC (it is high, so I checked)
- The data is exactly the kind where the 6am count predicts 7–9am: the count at 6am alone has AUC 0.89, at 5am 0.80 and at 7am 0.95. This is a smooth ramp as the morning peak begins, not a jump.
- The controller `ts` column is **UTC, not local.** I inferred this because the daily minimum falls at local 9am in every month once converted with US Mountain time (Denver), across both daylight-saving changes. I used that conversion.
- If that inference is wrong by one hour, the 06:00 feature would really be 07:00 and the result would be inflated. I think this is unlikely given the evidence, but **someone who knows the controllers should confirm "ts is UTC"**. That is the single most load-bearing assumption.
- I did not use `data/daily_features.csv`. Its columns (`min_bikes_today`, `trips_today`, `visits_today`) describe the whole day, including the 7–9am window, so using them would leak the answer.

## Decisions I made without asking (please read)
1. **Definition of a stock-out:** 0 bikes at any of the hourly readings at local 07:00, 08:00 and 09:00. Hourly data cannot see a stock-out that happens and ends between readings, so true stock-outs are under-counted. Operations should say whether "empty for 15 minutes" is the real pain.
2. **Missing data:** 30% of East-district hourly readings are missing at random (checked: missing-ness doesn't depend on bike count). I labeled only days where all three readings were seen. East is therefore under-represented (about 8–17% of rows in validation/holdout), and its results are thinner. Offline readings (bikes shown as 0) are treated as unknown, never as stock-outs.
3. **Capacity:** I used bikes + docks from the reading itself. Stations were re-built or moved (September 2025, February 2026). `stations.csv` lists capacity changes the status feed already reflects.
4. **Duplicates:** I dropped 52 duplicate rows at the spring daylight-saving hour, keeping the last.
5. **Weather:** I replaced the `-999` temperature placeholder with unknown and used only values up to 06:00, since there is no forecast in the data.
6. **Truck log:** `rebalancing_log.csv` has evening restocks only (16:00–19:00, clock unknown) and I did not use it.

## Counting my looks
- One model configuration, picked a priori, not tuned. HistGradientBoosting seeds give identical results (deterministic), so there is no seed spread to report.
- Baselines: 3. Validation threshold sweep: 3 values.
- The holdout was scored **once**, after everything was fixed. I had already looked at one summary of the holdout inputs (average bike counts, row counts), not at stock-outs.
- Every run is in `work/LEDGER.jsonl`.

## What could make this worse than reported
- **The $ savings assume a restock fully prevents the stock-out and that the truck is there by about 7:00.** The crew cannot arrive before 7:00, and the 7am reading is one of the three. The saving is optimistic by the share of stock-outs that happen at 7am. I did not measure that share; it is the first thing to check in a trial.
- **A model whose predictions get acted on changes the data it would be retrained on:** once you restock, those stock-outs stop appearing. Keep a small random set of stations unrestocked (or log decisions) so future training still sees the truth.
- **Seasonality:** the stock-out rate varies 12% (winter) to 35% (summer); the holdout is summer. Winter performance on a new year is untested (validation was Jan–Jun 2026, trained on 2025).
- **Late feed:** if the 06:00 reading is missing at 7am, the model uses the last one seen (`age_last` feature), but I did not test long outages. Fall back to "restock stations that were lowest at 6am".
- **Crew cap:** with about 24 stations a day and a 32% stock-out rate, more than 8 stations need restocking on many summer days. The ranking only decides which 8.

## Not done
- No decision-quality (judged) sign-off exists: *whether this is good enough to change what the crew does* is operations' call. I recorded no verdict.
- No fairness slicing beyond district. I did not check, for example, the smallest stations.
- No monitoring or deploy code.

## Reproduce
`cd work && python -I prep.py && python -I model.py && python -I final.py` (the third script scores the holdout; don't re-run it to tune).
Note `final.py` and `model.py` assume the files in `work/` and `data/` paths as laid out here.
