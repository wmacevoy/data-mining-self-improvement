# Morning stockout model: report

**Recommendation: use it, as a ranking for the crew's 8 stops, and treat the dollar figures as an estimate.** It flags stockouts far better than the simple rules I tried. The savings assume a truck stop actually prevents the stockout, which the data cannot show. The Q3 holdout has not been read, so this is not a sign-off number. Reproduce with `python -I work/build.py && python -I work/evaluate.py`.

## What I decided (nobody was available to ask)
- **Claim type:** predicted. At 07:00 America/Denver each weekday, for each station: will it be at 0 bikes at any OK reading at 07:00, 08:00 or 09:00 local? (Inferred from the task text. I read "between 7 and 9" as inclusive.)
- **Controller clock is UTC, not local.** The nightly bike reset lands at 07:00 ts in winter and 06:00 ts in summer, which is local midnight. The morning drain also shifts one hour with DST. I converted to America/Denver. The 52 duplicate rows on the two spring-forward days were deduplicated. This is an inference from the data; if wrong, the label window is misaligned.
- **OFFLINE rows are not stockouts.** They report 0 bikes and 0 docks. I treated them as missing. 227 of 11,927 station-days had no OK reading in the window and were dropped.
- **Features use only data before 07:00 local:** the 06:00 and 05:00 bike counts, the 3-hour change, offline hours overnight, as-of capacity, trailing 28-day stockout rate and fill, yesterday's outcome, weekday, month, and 06:00 temperature and rain. The 07:00 reading itself is excluded as a conservative choice. Using it would likely help; I did not test that.
- **Capacity is taken as of each date.** Stations were resized on 2025-09-15 and 2026-02-01.
- **Weather -999 was treated as missing.**
- **Not used: `daily_features.csv`.** It holds same-day values (`min_bikes_today`, `trips_today`, `visits_today`) that are not known at 07:00. Using them would leak the answer.
- **Split:** train 2025-01 to 2026-02 (about 9,100 station-days). Validate 2026-03 to 2026-06 (2,540 station-days, 87 days). The validation base rate is 36% against 26% overall, because spring and summer have more stockouts.
- **Model:** a gradient-boosted classifier with one fixed configuration and no search. The ledger is `work/ledger.csv`: 3 baselines, 5 seeds of the same model, and 1 logistic regression. Nothing was tuned on the validation set.
- **Decision rule:** flag a station if p ≥ 40/90 = 0.44, capped at 8 per day, highest p first. This is the break-even where a $40 stop equals the expected $90 loss. It assumes a stop fully prevents the stockout.

## Results (validation, 87 weekdays, ~10.4 stockouts per day on average)
| | AUC | Avg. precision | Cost, top-8 policy | Cost, threshold policy |
|---|---|---|---|---|
| Do nothing | | | $81,540 | |
| Station's trailing stockout rate | 0.80 | 0.67 | $70,050 | $69,740 |
| 06:00 fill level alone | 0.85 | 0.80 | $64,830 | $64,830 |
| Logistic regression (4 features) | 0.92 | 0.88 | $61,770 | $60,000 |
| **Boosted model** | **0.93** | **0.89** | $61,410 | **$59,860** |

- **Saving:** about $21.7k over 87 days (~$250 per day) against doing nothing, under the threshold policy. A day-level bootstrap puts the top-8 saving at $14.4k to $17.1k (5th to 95th percentile). The model beats the trailing-rate rule by $5.9k to $8.4k.
- **Misses:** the model flags about 556 stops and catches 488 of 906 stockouts. The 8-stop cap leaves about 40% uncaught, because there are on average more than 10 stockouts per day. These misses cost real money, and a second crew would be worth pricing.
- **Seed spread:** the 5 seeds gave identical results because this configuration has no randomness. That is no evidence of stability; I did not measure variation across data splits.
- **Calibration:** reasonable but a little low. The predicted-probability buckets of 0.02 to 0.5 ran roughly 3 to 8 points below the observed rates. The Brier score is 0.102, against 0.245 for a constant prediction.
- **Slices (AUC):** March 0.93, April 0.92, May 0.93, June 0.93. Central 0.92, North 0.93, East 0.93. These are in-sample, per-slice figures, with no formal intervals.

## Caveats and what I did not do
- **The holdout (`data/holdout/status_2026Q3.csv`) was not opened.** It is reachable from this directory. Before relying on the model, spend one look on it, count it, and expect summer to be an easy season for the base rate. The model has seen one summer.
- **Treatment effect is unmeasured.** The rebalancing log shows weekday visits at 16–19 ts (about 09:00 to 13:00 local), after the window. The log therefore says nothing about whether a 07:00 stop prevents stockouts. A short pilot, with some flagged stations deliberately left unvisited, is the way to measure it.
- **Stockout is the only outcome.** I did not check whether stations that run out also fill up elsewhere, or measure lost rides directly. The $90 figure is operations' own.
- **Data gaps:** East stations S025–S030 have about 30% fewer status rows (9.1k–9.3k against 13.1k). I do not know why, and the rows that are present may not be representative. Weekends were left out, because the crew works weekdays.
- **Not checked:** per-station accuracy, how the model degrades after another resize, and a retrain schedule. Capacity changes were the only drift I looked at. Retrain monthly and track the flagged-versus-actual rate.
- **Retro:** the facts I had to infer, which should be written down in the repository, are the controller timezone, whether OFFLINE counts as a stockout, and the 07:00 availability. The first thing to add is a datasheet for `status.csv`.
