# Morning stockout model — report

**Recommendation: use it, as a ranked list, pending one holdout sign-off look (not done; see below).** Each weekday at 07:00 it ranks stations by P(stockout 7–9am); the crew restocks the top 8.
On Jan–Jun 2026 (never trained on) that caught **5.1 of 8.2 stockouts/day** vs 4.6 for "lowest bike fraction at 6am" and 3.9 for each station's 28-day stockout rate. This is the claim I ran; the dollar figure below rests on an assumption I could not check.

## What I decided (nobody was available)
- **Claim type: predicted.** Unit = station × weekday. Label = `bikes_available == 0` on any 07:00, 08:00 or 09:00 local reading. Hourly readings miss stockouts that start and end between readings, so the true rate is a bit higher.
- **Clock:** `ts` in status.csv is **UTC, not local** (inferred, not documented). The overnight jump in bikes is at 07:00 in January and 06:00 in July, which is local midnight across DST. Everything is converted to America/Denver. Reading `ts` as local would put the "7–9am" window in the wrong hours. rebalancing_log.csv appears to use the same clock (its restocks line up with the jump to bikes after a run of zeros), so its "16–19:00" visits are ~09:00–12:00 local. Also inferred. Because of that I do not use the log as a feature.
- **Prediction point:** features use only information up to the 06:00 local reading, weather through 06:00 and yesterday's data. The 07:00 reading is excluded because it isn't in hand when the plan is made. Using it would likely help; I did not test it.
- OFFLINE rows (6,137, bikes reported as 0) are treated as missing, not as stockouts. Days with no valid reading in the window (227) are dropped. 52 duplicate rows at DST changes keep the last. Weather has a -999 sentinel, set to missing. Capacity is looked up as of each date from stations.csv, which has moves and rebuilds.
- **`daily_features.csv` was not used.** It has same-day `min_bikes_today`, `trips_today` and `visits_today`, none of which exist at 07:00. Using it would leak the answer.
- **Model:** gradient boosting (scikit-learn), 5 seeds averaged, on 17 features. Features: capacity, bike fractions at 00/03/05/06 local, previous-day minimum and 18:00 level, yesterday's outcome, station stockout rate (28-day and overall), weekday, month, temperature, rain, district.

## How good (validation = 2026-01-01 to 2026-06-30, 3,785 station-days, trained on 2025 only)
This is a single split, with 1 model configuration tried plus the 4 baselines. I did not tune on it. It does not predict future quarters — Q3 has summer behaviour and was never seen.

| ranking | AUC | stockouts caught/day (top 8 of ~8.2) | net $/day |
|---|---|---|---|
| model | 0.935 | 5.06 | +136 |
| 6am low bikes | 0.850 | 4.61 | +95 |
| 28-day station rate | 0.800 | 3.94 | +34 |
| yesterday's outcome | 0.746 | 3.74 | +17 |
| random | 0.50 | 2.27 | -116 |

- Net = $90 × stockouts caught − $40 × 8 stops. 95% interval for the model (bootstrap over days): **$99 to $171/day**. About 250 weekdays gives roughly $25–43k/yr. This **assumes a restock at a flagged station prevents its stockout**, which I can't check: the data has no restock-before-7am events. Break-even needs about 3.6 of the 5.1 caught stockouts to be truly prevented (320/90), i.e. restocks must work about 70% of the time; below that the plan loses money. The "6am low bikes" rule gets most of the way there, at a lower but still positive value.
- Probabilities are well calibrated (top decile predicted 0.96 vs 0.97 observed; bottom half < 0.01–0.04). Brier 0.090 vs 0.202 for a constant.
- Stops: k=8 beat k=4 ($109) and k=12 ($105) in this period. A threshold rule (p > 0.44, which is the $40/$90 break-even) gives about 7.8 stops/day with 78% precision. So on average about 8 stations clear the break-even each day, close to crew capacity; some days fewer are worth a stop.
- Districts: AUC 0.93 Central, 0.93 North, 0.94 East. East has the lowest stockout rate (12% vs 38% Central).
- Station moves/rebuilds (Feb 2026) did not break it in the validation window, but I did not test those stations separately.

## What could make this wrong
- Q3 (summer, never seen) is the real test; validation covers only winter and spring.
- Station-day outcomes are not independent (same weather and day), so intervals are by day, not row, and are still approximate.
- Dependence on the overnight restocking pattern: the strongest signal is the 06:00 level. If operations change how stations are filled overnight, retrain.
- A too-good-looking number (AUC 0.93): I checked that no feature is from after 06:00 by construction (`prep.py`), but I did **not** trace individual predictions to rows or test with a planted leak.

## Holdout (not looked at)
`data/holdout/status_2026Q3.csv` is reachable from the working directory. I did not evaluate on it: sign-off is a one-look, human decision. (I ran `head -3` on it by accident while listing files: header and the 07:00 July 1 rows of one station only; no scores.) To do it: concatenate status.csv with the holdout file (for history features), run `work/prep.py` on that, and score only July–September with `work/final.py score`; log the look. Not done: the weather file already covers Q3, so that part is ready. Rows must be capped at 2026-09-30.

## Not done / next
- No requirement or question file exists in this directory (`QUESTION_v1.md` / `PLAN_v1.md`); the task text is the requirement *(inferred)*. No `./dm` or `./se` exists, so no doctor was run.
- No datasheet; the clocks above are inferences and should be confirmed with whoever runs the controllers.
- No bias audit (stations are not people). Not run: a live pipeline, per-station slices, the 07:00-reading variant, ledger of runs (this report states the count: one model, 4 baselines).
- Retro: I had to infer the timezone of two files. Write it in the README.

## Files
`work/prep.py` (features and label), `work/fit.py` (validation, rerun: `python -I work/prep.py data data/status.csv work/train_all.csv && python -I work/fit.py work/train_all.csv`), `work/final.py` (final model, trained on all pre-holdout data, `model.pkl`).
