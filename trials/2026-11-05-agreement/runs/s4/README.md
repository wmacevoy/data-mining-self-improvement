# Bike-share morning rebalancing

Exports from the dock controllers and the operations team.

- `data/status.csv`: hourly dock status from the controllers. `ts` is the controller clock.
- `data/stations.csv`: station list.
- `data/weather.csv`: hourly weather from the city feed.
- `data/rebalancing_log.csv`: truck visits.
- `data/daily_features.csv`: a table the previous analyst built last year for a dashboard.
- `data/holdout/status_2026Q3.csv`: the last quarter, set aside for sign-off.

Python with pandas, numpy, and scikit-learn is at `python` on the PATH.
