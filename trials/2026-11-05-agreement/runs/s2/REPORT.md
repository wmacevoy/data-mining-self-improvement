# Morning stockout model: report

**Recommendation: yes, use it, as a ranked list for the crew. Treat the dollar figure as an upper bound until two assumptions below are confirmed, and run the one-time holdout sign-off first.**

## What it does
At 7:00 America/Denver on a weekday it gives each of the 30 stations a probability of hitting 0 bikes at a 7:00, 8:00 or 9:00 hourly reading that day. The crew stops at the top 8 stations whose probability is above 0.44 (= $40 / $90, the break-even point). Code: `work/build.py`. Run `python -I work/build.py data work`. It writes `work/station_days.csv` and `work/results.json`.

## Decisions I made (nobody was available to ask)
- **Claim type:** predicted. This is the inferred requirement. No `QUESTION`/`PLAN`/datasheet exists, and the task text was the spec.
- **Target:** a station-day is positive if any `OK` reading at local 7, 8 or 9 shows 0 bikes. Stockouts between hourly readings are invisible. `OFFLINE` rows report 0 bikes, so I treated them as unknown rather than as stockouts. 172 station-days with no usable reading in the window are dropped.
- **Clock:** `status.ts` is **UTC**, not local. This is inferred, not documented. The nightly reset and the commute drawdown each move by one clock hour at DST, and stockouts peak at the clock hour that equals 9:00 Denver in both seasons. Please confirm with whoever owns the controllers. If I'm wrong, every number here is wrong.
- **Information at 7:00:** only readings up to the 6:00 local reading, weather through 6:00, the previous day's rain, and past stockout history. I did not use the 7:00 reading. Weather is actuals, not forecasts, but only through 6am.
- **Not used:** `daily_features.csv`. `min_bikes_today`, `trips_today` and `visits_today` are same-day values that aren't known at 7am. I also did not use the rebalancing log.
- **Cleaning:** 52 duplicate rows (the DST-change hour) dropped. Weather `-999` treated as missing. Capacity is taken as of each date from `stations.csv`, because stations were moved and rebuilt.
- **Split:** train on 2025 (7,688 station-days). Validate on Jan–Jun 2026 (3,785). **I did not open `data/holdout/`**. It is reachable from this directory, and reading it is a sign-off decision for the owner. Holdout looks used: 0.
- **Model:** gradient-boosted trees, one configuration, no tuning. I tried 1 model and 3 baselines, and made 1 diagnostic pass on validation.

## How good (validation, Jan–Jun 2026)
Stockout base rate is 28% of station-days, about 8.2 stockouts per day. It is 9–15% in Jan–Feb and 34–44% in Apr–Jun.

| Predictor | AUC | Avg precision | Cost/day* |
|---|---|---|---|
| Do nothing | | | $737 |
| Station × month historical rate | 0.79 | 0.58 | $666 |
| Yesterday's stockout | 0.61 | 0.36 | $715 |
| Low 6am bikes (simple rule) | 0.85 | 0.75 | $642 |
| **Model** | **0.94** | **0.87** | **$554** |

\*Cost = $40 per stop + $90 per stockout not stopped at. This **assumes a stop fully prevents that day's stockout**. That is my assumption and the biggest uncertainty.

- Saving vs doing nothing is about $183/day (95% day-bootstrap interval $157–209). Saving vs the historical-rate policy is about $112/day ($97–128). The model beats the simple 6am rule by about $88/day, with no interval computed for that gap.
- The model proposes 5.7 stops/day on average. The 8-stop cap rarely binds on this period.
- **Calibration:** predicted 0.8–1.0 came true 93% of the time. Predicted 0.4–0.5 came true 46%. Predicted <0.1 came true 3%. Probabilities are usable as stated.
- **Slices:** AUC is 0.93–0.95 in all three districts and 0.90–0.93 in every month. The January AUC is lower, and January has few positives.
- **Too good to be true?** I traced it. Most of the signal is simple: stations with ≤5 bikes at 6am usually run out (the 6am bike count alone gives 0.85), and 6am is known before the 7am decision. The model still scores 0.93 AUC among stations that are not already empty at 6am, and 0.92 with the 6am-level features removed. Only 8% of stockouts are at stations already at 0 at 6am. I found no leak.
- **Seed spread:** none to report. This model has no randomness, so the 5 "seeds" give identical results. The uncertainty is in the interval above and not in seeds.

## Caveats
1. **Season:** validation is Jan–Jun. Training had only one full year, so summer is represented once (2025). Q3 resembles the May–June peak, which was the high-rate period.
2. **Prevention assumption:** the saving shrinks in proportion to how often a restock fails to prevent a stockout. Check with ops. Also check the "about 8 per crew" number against actual stops per day.
3. **Hourly readings only:** real stockouts and their cost may be higher than those counted here.
4. **Fairness/people:** no data about people is used.
5. **Not done:** no retrain policy, no monitoring and no pipeline for 7am operation. The weather feature must come from the live feed at 6:00, not from this history file.

## What I'd do next (for the owner)
1. Confirm the UTC clock and the "stop prevents the stockout" assumption.
2. Do one look at `data/holdout/status_2026Q3.csv`, with the model trained on everything before it, and log that look. Use the same features and thresholds, with no retuning.
3. Run the crew list alongside the current process for a few weeks before relying on it.

## Retro
I assumed the unit of "run out" was an hourly reading and the DST/UTC reading above, because no datasheet existed. A short datasheet for `status.csv` (clock, `OFFLINE` semantics, duplicates) and a `QUESTION_v1.md` would have saved most of the investigation.
