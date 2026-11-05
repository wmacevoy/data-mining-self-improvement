# Morning stockout model: report

**Recommendation: use it, as a ranked list for the crew, with a pilot check on whether a restock actually prevents the stockout.** On the untouched Q3-2026 holdout, restocking the model's top 8 stations per day cost about **$55.8k, against $76.2k for doing nothing** (92 days, 30 stations). That is about $220 per day. It assumes a truck stop fully prevents a stockout. It still pays if stops prevent only about half of them (see "Cost").

## What it predicts
For each station and weekday, whether it has **zero bikes at any OK reading at local 07:00, 08:00 or 09:00**. I read "between 7 and 9" as inclusive of 09:00. Weekends hardly matter (about 2% stockout rate).

Features use only information available **at 06:00 local**: that morning's bikes at 06:00, 05:00 and 01:00, the 00:00–06:00 minimum, fill fraction, capacity, offline hours, weekday, month, 06:00 temperature, rain so far, and the station's historical weekday stockout rate. The model is a gradient-boosted classifier. The decision rule is: restock if p > 40/90 = 0.44, at most 8 per day, highest p first.

## How good (holdout 2026-07-01 to 2026-09-30, used once, after all choices were made)
| | AUC | Cost, 92 days | Stockouts caught / stops |
|---|---|---|---|
| Do nothing | – | $76.2k (847 stockouts) | 0 / 0 |
| Station's historical rate | 0.85 | $66.5k | 277 / 381 |
| Rule: bikes at 06:00 ≤ 3 | 0.64 | $64.6k | 250 / 271 |
| **Model, top 8/day** | **0.96** | **$55.8k** | **437 / 472 (93% precise)** |

- Calibration holds on the holdout: p in 0.6–0.8 gave 84% actual stockouts, p>0.8 gave 96%, p<0.1 gave 2.4%.
- AUC is stable across July, August and September (0.96–0.97). A model trained on shuffled labels scored 0.44, so the pipeline does not leak.
- Before touching the holdout I validated on 2026-01 to 2026-06 with training on earlier data (AUC 0.956), and the result matched.
- **The 8-truck cap is the binding limit.** Of 847 stockouts, 437 are caught. A second crew (k=12) would reduce cost to about $49.9k. Each extra stop is still worth it while p stays above 0.44.
- The simple "bikes ≤ 3 at 06:00" rule captures a lot of the value (about $11.6k saved versus about $20.4k for the model). If the team wants something to run by hand, that is the fallback.

## Cost
Assumes a stop costs $40 and avoids a $90 loss only if the station would have run out. **I assumed a stop prevents 100% of the stockout; the data cannot tell me.** Break-even: with 93% precision, stops pay if they prevent more than about 48% of stockouts. Check this in a pilot: log which stations were restocked each morning, then compare outcomes.

## Calls I made, and where I may be wrong
- **Timezones (inferred, not confirmed).** `status.csv` timestamps are on a UTC clock, and local time is `America/Denver`. Evidence: the series starts at 07:00 in January and 06:00 in July, the overnight reset jump moves one hour with DST, and the 7–9am drawdown only lines up after converting. If the real zone differs, labels shift by an hour and results change. Weather is already local.
- **DST duplicates.** 52 duplicated timestamps at the March spring-forward hour were deduplicated, keeping the last.
- **Offline readings** (`OFFLINE` rows show 0 bikes, 0 docks) are not stockouts. They are excluded from labels and features. A station with no OK reading in 7–9 has no label that day (16,097 of 16,380 station-days kept in training, about 1.7% dropped).
- **Weather `-999`** is a missing sentinel, set to NaN (184 rows).
- **`daily_features.csv` was not used.** It holds same-day outcomes (`min_bikes_today` alone scores AUC 0.94 against the target) and would not be known at 7:00.
- **`stations.csv` capacity changes ("moved", "rebuilt") are not reflected in the dock data.** bikes+docks stayed constant for every station through 2026-Q3. I used the observed constant and did not use stations.csv capacity. Someone should find out which is right.
- **Rebalancing log** (trucks arrive 16:00–19:00, apparently an evening operation) was not used. I could not tell how it relates to the overnight reset, so I did not model it.
- **Planning time.** Using the 07:00 reading itself would make predictions sharper but is too late to act on; I stopped at 06:00. Fewer hours would be possible if the 06:00 reading is not delivered in time.

## Risks
- Holdout is one summer quarter, with a 31% stockout rate versus 19% in training. Training spans only about 1.5 years, so winter 2026-27 and any new season are untested for the 2026 regime. Re-check weekly, and retrain once there is another quarter.
- The model depends on the overnight reset pattern. If operations change how stations are reset overnight, retrain.
- The model assumes the stockout target is observable. If a station goes offline during 7–9, we won't know.

## Reproduce
`work/prep.py` (loading, labels, features), `work/model.py` (model, policy, validation), `work/final.py` (one-shot holdout run). Run with `python -I work/final.py` after `python -I work/model.py` (which writes `work/d.pkl`). No tests beyond those checks were written; the pipeline is a script, not a service, and no scheduled job or deployment has been set up.
