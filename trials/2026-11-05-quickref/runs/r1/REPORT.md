# Morning stockout model: report

**Recommendation: use it, as a ranking tool for the 8 daily stops, and run it alongside the current practice for a few weeks first.** It is clearly better than the simple alternatives. Most of its dollar value rests on one assumption I could not check (below).

## What was built
- Each weekday it scores every station for P(zero bikes at any OK reading at 07:00, 08:00 or 09:00 local). It then picks up to 8 stations with p > 0.44, which is the break-even point of $40 per stop against $90 per stockout.
- Features are all known by the 06:00 local reading: bikes at 00:00, 03:00 and 06:00, capacity (as of that date), yesterday's afternoon minimum, the trailing 7- and 28-day stockout rates, 06:00 weather, weekday and month.
- Model: gradient boosting, with logistic regression and four simple rules as baselines. Code is in `work/` (`prep.py` builds the table, `evalh.py` is the harness, `dev.py` and `final.py` are the runs). Run it with `PYTHONPATH=work python -s work/final.py`.

## Results
Sign-off quarter (2026-07-01 to 09-30), 66 weekdays, 1,926 station-days, trained on everything before it. Holdout looked at once.

| model | AUC | cost / day (30 stations) | stockouts prevented |
|---|---|---|---|
| no rebalancing | .50 | $1,117 | 0% |
| yesterday's result | .60 | $1,010 | 31% |
| station's 28-day rate | .78 | $929 | 45% |
| rule: low 06:00 count | .62 | $980 | 32% |
| logistic regression | .91 | $829 | 54% |
| **gradient boosting** | **.93** | **$823** | **53%** |

- Against no action it saves about $294/day (95% bootstrap interval over days: $263 to $325). That is about 26%.
- Against the best simple rule it saves about $157/day ($138 to $177).
- Gradient boosting versus logistic regression is a tie (interval -$15 to +$4). The simpler logistic model would do; I kept gradient boosting only because it was slightly ahead on validation.
- The bar I set before the holdout was to beat no-action and the best baseline on cost with an interval excluding zero. It was met.
- Calibration is good. Stations scored 0.7 to 0.9 stocked out 87% of the time, and those scored over 0.9 did so 98%. Stations under 0.1 stocked out 2%. The day's 8 picks were right 84% of the time.
- Results are consistent across districts (AUC .91 to .93) and across the three months.
- In validation (2026 H1, trained on 2025 only) the numbers were similar: AUC .931 and about $186/day saved against no action. The gradient-boosting AUC did not change across 5 seeds, because the model has no randomness here.
- Models tried: 6 on validation, 6 on the holdout (one look, no tuning afterwards).

## Caveats
1. **Restock is assumed to prevent the stockout.** The data do not show whether a stop works. The truck log is evening-only and the effect is not identifiable from it. If a stop prevents only half the stockouts, the savings shrink a lot. Measure this in the trial.
2. **The crew limit binds in summer.** The summer stockout rate is about 43%, which is about 13 stockouts a day against 8 stops. Even a perfect model leaves stockouts unprevented. The real lever there is more capacity, or restocking the stations with the highest p first, which is what the tool does.
3. **Only 53% of stockouts are caught.** The rest are mostly unpredictable from 06:00 information, or fall outside the 8-stop cap.
4. **The label is hourly.** A stockout between readings is invisible, so real stockouts are undercounted. A 07:00 reading with zero bikes counts as a stockout in the window even though it is observed at the start of it.
5. **Predictions use a 06:00 cutoff.** If operations can plan at 07:00 using the 07:00 reading, accuracy would rise, but that reading is partly the answer, so I did not use it.
6. **Holidays are not excluded.** Weekends are excluded, since the stockout rate is about 2% then and the crew plans weekdays only.

## Decisions I made (nobody was available to ask)
- **Clock.** `status.ts` is treated as **UTC**, with local time America/Denver. Evidence: the overnight refill jump appears at 07:00 in winter and 06:00 in summer, which is local midnight, and the afternoon trough lands at 7 to 9am local. The city is not named anywhere; if it isn't Mountain time, the labels shift and everything here needs rerunning. Please confirm.
- **Offline rows.** Rows marked OFFLINE report 0 bikes. They are treated as unknown and never as stockouts. Station-days with no OK reading in the window (196 in the development data, 49 in the holdout) are dropped.
- **Duplicates.** 52 duplicate rows fall on DST days with conflicting values. I kept the first.
- **Weather.** The -999 temperature values (184 rows) are treated as missing.
- **Capacity.** It is taken from `stations.csv` as of each date, since stations were moved or rebuilt in 2025-09 and 2026-02.
- **`daily_features.csv` is not used.** It contains same-day outcomes (`min_bikes_today`, `trips_today`), which are leakage.
- **Truck log.** Not used as a feature. Visit times are ambiguous and I had no evidence of their effect.

## Before relying on it
- **Operations:** confirm the time zone, and what a restock does to the stockout (rule 1 above).
- **Run it in shadow** next to the current practice for 2 to 4 weeks, logging picks and outcomes, and keep a small random set of stops that don't follow the model so its effect can be measured.
- **Retrain** at least monthly and after any station rebuild. Capacity changes and a rate that moves between seasons are the main drift risks. The holdout quarter's rate (43%) was higher than anything in training, and the model still held up, but that is one observation.
- **Fallback:** if the 06:00 feed is missing, use the station's 28-day stockout rate. It is a weaker baseline but works without live data.
- The holdout is now spent; further tuning needs a new set (the next quarter).
