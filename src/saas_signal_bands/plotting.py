from __future__ import annotations

import html
from pathlib import Path

import pandas as pd


def _scale(value: float, domain_min: float, domain_max: float, range_min: float, range_max: float) -> float:
    if pd.isna(value):
        return float("nan")
    if domain_max == domain_min:
        return (range_min + range_max) / 2
    return range_min + (value - domain_min) * (range_max - range_min) / (domain_max - domain_min)


def _polyline(points: list[tuple[float, float]]) -> str:
    clean = [(x, y) for x, y in points if pd.notna(x) and pd.notna(y)]
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in clean)


def _format_value(value: float) -> str:
    if pd.isna(value):
        return ""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    if abs(value) < 1 and value != 0:
        return f"{value:.1%}"
    return f"{value:,.0f}"


def _format_metric_name(metric: str) -> str:
    known = {
        "mrr": "MRR",
        "arr": "ARR",
        "arpu": "ARPU",
        "arpu_growth_rate": "ARPU Growth",
        "ltv": "LTV",
        "mrr_growth_rate": "MRR Growth",
        "active_customers": "Active Customers",
        "active_customer_growth_rate": "Customer Growth",
        "new_customers": "New Customers",
        "net_customer_adds": "Net Customer Adds",
        "customer_churn_rate": "Customer Churn",
        "revenue_churn_rate": "Revenue Churn",
        "churned_customers": "Churned Customers",
        "churned_mrr": "Churned MRR",
    }
    return known.get(metric, metric.replace("_", " ").title())


def plot_signal_bands(
    df: pd.DataFrame,
    metric: str,
    output_path: Path,
) -> None:
    center = f"{metric}_center_band"
    upper = f"{metric}_upper_band"
    lower = f"{metric}_lower_band"
    signal = f"{metric}_signal"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_df = df.dropna(subset=["month"]).copy()
    width = 1180
    height = 720
    left = 82
    right = 42
    top = 76
    bottom = 132
    chart_width = width - left - right
    chart_height = height - top - bottom

    values = pd.concat([plot_df[metric], plot_df[upper], plot_df[lower]]).dropna()
    y_min = float(values.min())
    y_max = float(values.max())
    padding = (y_max - y_min) * 0.08 if y_max != y_min else max(abs(y_max) * 0.1, 1)
    y_min -= padding
    y_max += padding

    x_count = max(len(plot_df) - 1, 1)
    x_positions = [left + (idx / x_count) * chart_width for idx in range(len(plot_df))]

    def points_for(column: str) -> list[tuple[float, float]]:
        return [
            (
                x_positions[idx],
                _scale(value, y_min, y_max, top + chart_height, top),
            )
            for idx, value in enumerate(plot_df[column])
        ]

    metric_points = points_for(metric)
    center_points = points_for(center)
    upper_points = points_for(upper)
    lower_points = points_for(lower)
    band_points = _polyline(upper_points + list(reversed(lower_points)))

    y_ticks = []
    for idx in range(5):
        value = y_min + (idx / 4) * (y_max - y_min)
        y = _scale(value, y_min, y_max, top + chart_height, top)
        y_ticks.append((value, y))

    month_labels = []
    label_step = max(len(plot_df) // 6, 1)
    for idx, month in enumerate(plot_df["month"]):
        if idx % label_step == 0 or idx == len(plot_df) - 1:
            month_labels.append((x_positions[idx], pd.to_datetime(month).strftime("%Y-%m")))

    alert_circles = []
    for idx, row in plot_df.reset_index(drop=True).iterrows():
        if row[signal] in {"above_band", "below_band"}:
            x, y = metric_points[idx]
            label = html.escape(f"{row['month']:%Y-%m}: {row[metric]:.4g} ({row[signal]})")
            alert_circles.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.5" fill="#dc2626">'
                f"<title>{label}</title></circle>"
            )

    metric_name = _format_metric_name(metric)
    title = html.escape(f"SaaS Signals Board: {metric_name}")
    metric_label = html.escape(metric_name)
    axis_y = top + chart_height
    month_label_y = axis_y + 30
    x_axis_label_y = height - 48
    legend_y = height - 18
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{left}" y="38" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="700" fill="#111827">{title}</text>
  <text x="{left}" y="62" font-family="Inter, Arial, sans-serif" font-size="13" fill="#6b7280">Rolling average with upper and lower statistical bands</text>
  {"".join(f'<line x1="{left}" x2="{width - right}" y1="{y:.2f}" y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1"/><text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">{html.escape(_format_value(value))}</text>' for value, y in y_ticks)}
  <line x1="{left}" x2="{width - right}" y1="{axis_y:.2f}" y2="{axis_y:.2f}" stroke="#cbd5e1" stroke-width="1"/>
  <polygon points="{band_points}" fill="#bfdbfe" opacity="0.16"/>
  <polyline points="{_polyline(upper_points)}" fill="none" stroke="#f59e6b" stroke-width="1.5" opacity="0.82"/>
  <polyline points="{_polyline(lower_points)}" fill="none" stroke="#5ccfc4" stroke-width="1.5" opacity="0.82"/>
  <polyline points="{_polyline(center_points)}" fill="none" stroke="#7aa7f7" stroke-width="1.7" opacity="0.82"/>
  <polyline points="{_polyline(metric_points)}" fill="none" stroke="#111827" stroke-width="3"/>
  {"".join(alert_circles)}
  {"".join(f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{axis_y:.2f}" y2="{axis_y + 6:.2f}" stroke="#cbd5e1" stroke-width="1"/><text x="{x:.2f}" y="{month_label_y:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">{html.escape(label)}</text>' for x, label in month_labels)}
  <text x="{left + chart_width / 2:.2f}" y="{x_axis_label_y}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" font-weight="700" fill="#374151">Period (month)</text>
  <text x="{left}" y="{legend_y}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#111827">Legend:</text>
  <line x1="{left + 54}" x2="{left + 82}" y1="{legend_y - 4}" y2="{legend_y - 4}" stroke="#111827" stroke-width="3"/><text x="{left + 90}" y="{legend_y}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#374151">{metric_label}</text>
  <line x1="{left + 190}" x2="{left + 218}" y1="{legend_y - 4}" y2="{legend_y - 4}" stroke="#7aa7f7" stroke-width="1.7" opacity="0.82"/><text x="{left + 226}" y="{legend_y}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#374151">central</text>
  <line x1="{left + 290}" x2="{left + 318}" y1="{legend_y - 4}" y2="{legend_y - 4}" stroke="#f59e6b" stroke-width="1.5" opacity="0.82"/><text x="{left + 326}" y="{legend_y}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#374151">upper</text>
  <line x1="{left + 374}" x2="{left + 402}" y1="{legend_y - 4}" y2="{legend_y - 4}" stroke="#5ccfc4" stroke-width="1.5" opacity="0.82"/><text x="{left + 410}" y="{legend_y}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#374151">lower</text>
  <circle cx="{left + 472}" cy="{legend_y - 4}" r="5.5" fill="#dc2626"/><text x="{left + 486}" y="{legend_y}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#374151">signal</text>
</svg>
"""
    output_path.write_text(svg, encoding="utf-8")
