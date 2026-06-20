# Forecasting Model — Decision Log

## Decision
**Production forecast method: historical mean per (cluster_id, time_band).**
LightGBM was tested and rejected — not because of a bug, but because it
does not beat the simple baseline given the available data volume.

## What was tested (full dataset, 23 weeks, chronological split at 2024-02-26,
## 4,677 train rows / 2,282 test rows)

| Method                         | MAE (next-week violation count) | RMSE   |
|---------------------------------|----------------------------------|--------|
| **Historical mean (winner)**    | **13.09**                        | **37.27** |
| LightGBM (lag/rolling features) | 15.02                            | 43.64  |
| Naive lag-1 ("repeat last week")| 16.18                            | 49.01  |

Additional variants tested on sample data (all underperformed the flat
expanding mean; not re-run on full data since the direction was
unambiguous):
- EWMA at spans 2, 3, 4, 6, 8 — recency-weighting consistently *hurt*
  accuracy. These series behave as roughly stationary around a stable
  per-cluster level rather than trending, so down-weighting older weeks
  throws away useful information instead of adapting to drift.
- Expanding median, expanding trimmed mean — more robust to single-week
  spikes, still lost to the flat mean.
- Ensemble blend of LightGBM + historical mean at weights 0.0–1.0 — MAE
  rose monotonically with LightGBM's weight; weight = 0 (pure mean) was
  best at every point tested.

## Why this is the right call, not a fallback

- LightGBM does beat the naive lag-1 baseline, so it's not learning
  nothing — but the gap between "beats naive" and "beats the mean" is
  exactly where 23 weeks of history runs out. Tree-based models need
  more rows per series than this to out-perform a well-estimated mean.
- With ~200+ active (cluster_id, time_band) series, most having only a
  handful of usable training weeks, the model overfits to weekly noise.
  This is a data-volume ceiling, not a hyperparameter problem — stronger
  regularization would, at best, asymptotically approach what the mean
  baseline already provides directly.
- Forcing a more complex model to "win" by construction (e.g. picking
  favorable hyperparameters post-hoc) would produce a result that looks
  more sophisticated but generalizes worse — the opposite of what
  "best possible results" should mean here.

## What would change this decision

If/when more weeks of historical data accumulate (e.g. a live complaint
feed extends the series well past 23 weeks), re-run
`train_forecast_model.py` and re-compare against the mean baseline.
The training code is kept in the repo specifically for this — once
enough history exists, the model has a real chance to win, and the same
validation discipline (chronological split, baseline comparison) should
be applied again before switching production over to it.

## Production forecasting logic (what actually ships)

For each (cluster_id, time_band):
  - **model tier** (>= 4 weeks of prior history): forecast = expanding
    mean of violation_count over all prior weeks.
  - **fallback tier** (< 4 weeks of history): same expanding-mean logic,
    just over fewer points — no separate method, for consistency.
  - Forecasted violation_count is then recombined with the zone's known
    (not forecasted) severity / time-demand / junction multipliers via
    the existing hotspot-score formula, rescaled to the same global 0–1
    bounds as the historical hotspot_scores.csv.
