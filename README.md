# SaaS Signals Board

SaaS Signals Board applies technical-analysis ideas to SaaS operating metrics and turns them into narrative business signals. The framework uses Bollinger-style bands to detect range breaks, momentum to measure directional change, persistence to measure signal duration, and baseline shift to detect when the normal level itself may be changing. The board also supports known business-event annotations, including optional rebase events that restart rolling-band calculations from a business change.

The first version is built for the Kaggle dataset:

https://www.kaggle.com/datasets/rivalytics/saas-subscription-and-churn-analytics-dataset

## Metrics

- MRR growth rate
- ARPU growth rate
- Active customer growth rate
- Customer churn rate
- Revenue churn rate

The MVP focuses on five KPIs that are both important and directly supported by the Kaggle subscription and churn data. Raw MRR and active customer counts are kept as context, but the signal board focuses on rates and relative changes because high-growth SaaS metrics often trend upward rather than oscillating around a stable mean. CAC is not estimated because the dataset does not provide acquisition or marketing spend. LTV is kept out of the signal board because monthly churn can make it jump sharply, but the CSV includes raw and smoothed LTV for reference.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Download the Kaggle dataset and place the CSV files in:

```text
data/raw/
```

Expected files:

```text
ravenstack_accounts.csv
ravenstack_subscriptions.csv
ravenstack_churn_events.csv
ravenstack_feature_usage.csv
ravenstack_support_tickets.csv
```

Only `ravenstack_subscriptions.csv` and `ravenstack_churn_events.csv` are needed for the first metrics pipeline.

## Run

Build the SaaS Signals Board:

```bash
python -m saas_signal_bands.cli --dashboard
```

Outputs:

```text
outputs/dashboard.html
outputs/index.html
outputs/monthly_metrics.csv
outputs/early_signal/all/*.svg
outputs/early_signal/last_12/*.svg
outputs/normal/all/*.svg
outputs/flexible/all/*.svg
```

Build one chart:

```bash
python -m saas_signal_bands.cli --metric mrr_growth_rate
```

Outputs:

```text
outputs/monthly_metrics.csv
outputs/mrr_growth_rate_signal_bands.svg
```

Try another metric:

```bash
python -m saas_signal_bands.cli --metric customer_churn_rate
python -m saas_signal_bands.cli --metric revenue_churn_rate
python -m saas_signal_bands.cli --metric mrr_growth_rate
```

## How The Signals Work

The board is designed around four questions and an executive summary layer:

- Did the metric break its expected range?
- Is the metric improving or deteriorating versus the previous period and the same period last year?
- Has the abnormal movement repeated across consecutive periods?
- Has the baseline itself possibly moved to a new level?
- What does that combination mean in business language for this specific metric?

### Bollinger Bands

Bollinger Bands are the range signal. For each metric:


```text
central_band = rolling average over N periods
upper_band = rolling average + k * rolling standard deviation
lower_band = rolling average - k * rolling standard deviation
```

```text
range_signal = actual value outside upper_band or lower_band
```

The default window follows the selected data frequency: `N = 365` for daily data, `N = 52` for weekly data, `N = 12` for monthly data, and `N = 4` for quarterly data. The default sensitivity is `k = 1.25`.

The board includes a data-frequency setting so the user can declare whether each CSV record represents a day, week, month, or quarter. The current Kaggle dataset is modeled monthly, so the default rolling window is 12 periods.

`k` is the tolerance margin. It is not a percentage value or a currency amount; it is a multiplier of the metric's rolling standard deviation.

```text
higher k = wider bands = fewer alerts
lower k = tighter bands = more alerts
```

The SaaS Signals Board starts with three suggested sensitivity scenarios, but the user can change both the number of scenarios and each scenario's `k` value:

```text
Early Signal = k 0.75
Normal = k 1.25
Flexible = k 1.5
```

### Momentum

Momentum is the directional change signal.

```text
previous_period_momentum = current period value - previous period value
seasonal_momentum = current period value - same period last year value
```

The first line shows short-term movement. The second line adds seasonal context, so a normal post-season decline does not automatically look like deterioration. For metrics where higher is better, positive momentum is usually good. For metrics where lower is better, such as churn, positive momentum can be a risk. The dashboard translates these comparisons into a `Momentum read` instead of only showing the numbers.

### Persistence

Persistence separates one-off noise from repeated abnormal movement.

```text
signal_duration = consecutive periods outside the normal range
```

The word `period` depends on the selected data frequency: consecutive days for daily data, consecutive weeks for weekly data, consecutive months for monthly data, or consecutive quarters for quarterly data.

The dashboard translates this into a `Persistence read`: fresh break, repeated signal, or persistent operating issue.

### Baseline Shift

Baseline Shift compares the recent average with the previous baseline.

```text
recent_average = average of last 3 periods
previous_baseline = average of previous 12 periods
baseline_shift = recent_average - previous_baseline
```

Range Signal detects abnormal points. Baseline Shift detects whether the normal level itself may be changing.

In the interactive chart, Baseline Shift is shown as two lines: recent 3-period average and previous 12-period average. The area between the lines is shaded green when the shift is favorable and red when it is unfavorable, using the business direction of the metric. For growth metrics, higher is favorable; for churn metrics, lower is favorable.

### Known Events

Known events let the user annotate business context, such as a price increase, large enterprise deal, campaign launch, or product change. Events can be saved as visual notes or marked as rebase events. A rebase event restarts rolling-band calculations from that date, mirroring the analyst logic of saying that post-event performance should not be compared with the old baseline.
