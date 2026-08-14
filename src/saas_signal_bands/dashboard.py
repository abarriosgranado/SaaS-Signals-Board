from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from saas_signal_bands.bands import add_signal_bands
from saas_signal_bands.landing import build_landing_page
from saas_signal_bands.plotting import plot_signal_bands


METRICS = [
    {
        "id": "mrr_growth_rate",
        "label": "MRR Growth",
        "description": "Period-over-period growth rate in monthly recurring revenue.",
        "format": "percent",
        "direction": "higher",
    },
    {
        "id": "arpu_growth_rate",
        "label": "ARPU Growth",
        "description": "Period-over-period growth rate in average revenue per active account.",
        "format": "percent",
        "direction": "higher",
    },
    {
        "id": "active_customer_growth_rate",
        "label": "Customer Growth",
        "description": "Period-over-period growth rate in active customers.",
        "format": "percent",
        "direction": "higher",
    },
    {
        "id": "customer_churn_rate",
        "label": "Customer Churn",
        "description": "Share of starting customers that churned during the period.",
        "format": "percent",
        "direction": "lower",
    },
    {
        "id": "revenue_churn_rate",
        "label": "Revenue Churn",
        "description": "Share of starting MRR lost during the period.",
        "format": "percent",
        "direction": "lower",
    },
]

PROFILES = [
    {"id": "early_signal", "label": "Early Signal", "k": 0.75},
    {"id": "normal", "label": "Normal", "k": 1.25},
    {"id": "flexible", "label": "Flexible", "k": 1.5},
]

PERIODS = [
    {"id": "all", "label": "Full period", "periods": None},
    {"id": "last_12", "label": "Last 12 months", "periods": 12},
    {"id": "custom", "label": "Custom", "periods": None},
]

FREQUENCIES = [
    {"id": "daily", "label": "Daily", "unit": "day"},
    {"id": "weekly", "label": "Weekly", "unit": "week"},
    {"id": "monthly", "label": "Monthly", "unit": "month"},
    {"id": "quarterly", "label": "Quarterly", "unit": "quarter"},
]


def _filter_period(df: pd.DataFrame, periods: int | None) -> pd.DataFrame:
    if periods is None or df.empty:
        return df.copy()
    return df.sort_values("month").tail(periods).copy()


def _build_profile_outputs(
    monthly: pd.DataFrame,
    output_dir: Path,
    window: int,
) -> dict[str, pd.DataFrame]:
    profile_data = {}
    for profile in PROFILES:
        profile_dir = output_dir / profile["id"]
        profile_dir.mkdir(parents=True, exist_ok=True)
        merged = monthly.copy()
        for metric in METRICS:
            metric_id = metric["id"]
            profiled = add_signal_bands(
                monthly,
                metric=metric_id,
                window=window,
                multiplier=profile["k"],
            )
            columns = [
                "month",
                f"{metric_id}_center_band",
                f"{metric_id}_upper_band",
                f"{metric_id}_lower_band",
                f"{metric_id}_signal",
            ]
            merged = merged.merge(profiled[columns], on="month", how="left")
            for period in PERIODS:
                period_df = _filter_period(profiled, period["periods"])
                plot_signal_bands(
                    period_df,
                    metric_id,
                    profile_dir / period["id"] / f"{metric_id}.svg",
                )
        merged.to_csv(profile_dir / "monthly_metrics_with_bands.csv", index=False)
        profile_data[profile["id"]] = merged
    return profile_data


def build_dashboard(
    monthly: pd.DataFrame,
    output_dir: Path,
    window: int = 12,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(output_dir / "monthly_metrics.csv", index=False)
    profile_data = _build_profile_outputs(monthly, output_dir, window)
    build_landing_page(monthly, output_dir)

    default_profile = "normal"
    metric_options = "\n".join(
        f'<button class="metric-tab{" active" if index == 0 else ""}" data-metric="{metric["id"]}">{html.escape(metric["label"])}</button>'
        for index, metric in enumerate(METRICS)
    )
    profile_options = "\n".join(
        f'<button class="profile-tab{" active" if profile["id"] == default_profile else ""}" data-profile="{profile["id"]}">{html.escape(profile["label"])} <span>k={profile["k"]}</span></button>'
        for profile in PROFILES
    )
    default_period = "all"
    period_options = "\n".join(
        f'<button class="period-tab{" active" if period["id"] == default_period else ""}" data-period="{period["id"]}">{html.escape(period["label"])}</button>'
        for period in PERIODS
    )
    default_frequency = "monthly"
    frequency_options = "\n".join(
        f'<button class="frequency-tab{" active" if frequency["id"] == default_frequency else ""}" data-frequency="{frequency["id"]}">{html.escape(frequency["label"])}</button>'
        for frequency in FREQUENCIES
    )
    start_month = monthly["month"].min().strftime("%b %Y")
    end_month = monthly["month"].max().strftime("%b %Y")
    monthly_records = monthly.copy()
    monthly_records["month"] = monthly_records["month"].dt.strftime("%Y-%m-%d")
    monthly_json = json.dumps(monthly_records.to_dict(orient="records"))
    metric_meta = json.dumps(
        {
            metric["id"]: {
                "label": metric["label"],
                "format": metric["format"],
                "direction": metric["direction"],
            }
            for metric in METRICS
        }
    )
    metric_labels = json.dumps({metric["id"]: metric["label"] for metric in METRICS})
    profile_k = json.dumps({profile["id"]: profile["k"] for profile in PROFILES})
    profile_labels = json.dumps({profile["id"]: profile["label"] for profile in PROFILES})
    period_labels = json.dumps({period["id"]: period["label"] for period in PERIODS})
    period_lengths = json.dumps({period["id"]: period["periods"] for period in PERIODS})
    frequency_labels = json.dumps(
        {frequency["id"]: frequency["label"] for frequency in FREQUENCIES}
    )
    frequency_units = json.dumps(
        {frequency["id"]: frequency["unit"] for frequency in FREQUENCIES}
    )
    initial_scenarios = json.dumps(PROFILES)
    default_metric = METRICS[0]["id"]

    dashboard = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SaaS Signals Board</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #151922;
      --muted: #667085;
      --line: #d9dee8;
      --soft: #f5f7fb;
      --panel: #ffffff;
      --blue: #2563eb;
      --teal: #0f9f8f;
      --orange: #e56b1f;
      --red: #c62828;
      --green: #16794c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #eef2f7;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    .wrap {{
      width: min(1240px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .topbar {{
      min-height: 128px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 4.5rem);
      line-height: 0.95;
      letter-spacing: 0;
    }}
    .subtitle {{
      max-width: 720px;
      margin: 0;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.5;
    }}
    .back-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      padding: 12px 18px;
      border: 1px solid var(--blue);
      border-radius: 8px;
      background: var(--blue);
      color: #fff;
      font-size: .95rem;
      font-weight: 800;
      text-decoration: none;
    }}
    .back-link:hover {{ background: #1d4ed8; border-color: #1d4ed8; }}
    main {{ padding: 24px 0 40px; }}
    .controls {{
      display: grid;
      grid-template-columns: 1.1fr .8fr .85fr .85fr;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .control-panel, .chart-panel, .metric-summary, .event-panel {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .control-panel {{
      padding: 14px;
    }}
    .scenario-panel {{
      padding: 14px;
      margin-bottom: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .event-panel {{
      padding: 14px;
      margin-bottom: 16px;
    }}
    .event-form {{
      display: grid;
      grid-template-columns: 160px minmax(220px, 1fr) 120px;
      gap: 10px;
      align-items: end;
    }}
    .event-form label {{
      display: grid;
      gap: 6px;
    }}
    .event-form span {{
      color: var(--muted);
      font-size: .72rem;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .event-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .event-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 32px;
      padding: 6px 8px 6px 10px;
      border: 1px solid #fed7aa;
      border-radius: 999px;
      background: #fff7ed;
      color: #9a3412;
      font-size: .78rem;
      font-weight: 750;
    }}
    .event-chip button {{
      min-height: 22px;
      width: 22px;
      padding: 0;
      border-radius: 999px;
      border-color: #fdba74;
      color: #9a3412;
      background: #ffedd5;
      line-height: 1;
    }}
    .scenario-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 12px;
    }}
    .scenario-head p {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: .86rem;
      line-height: 1.45;
    }}
    .scenario-count {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: .86rem;
      font-weight: 700;
      white-space: nowrap;
    }}
    .scenario-count input {{
      width: 74px;
    }}
    .scenario-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
    }}
    .scenario-row {{
      display: grid;
      grid-template-columns: 1fr 96px;
      gap: 8px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
    }}
    .scenario-field {{
      display: grid;
      gap: 5px;
    }}
    .scenario-field span {{
      color: var(--muted);
      font-size: .7rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    input {{
      min-height: 36px;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--ink);
      background: #fff;
      font: inherit;
      padding: 7px 9px;
    }}
    .apply-row {{
      display: flex;
      justify-content: flex-end;
      margin-top: 10px;
    }}
    .label {{
      display: block;
      color: var(--muted);
      font-size: .78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 10px;
    }}
    .tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    button {{
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      padding: 8px 12px;
    }}
    button:hover {{ border-color: #9aa6bd; }}
    button.active {{
      border-color: var(--blue);
      background: #edf4ff;
      color: #174ea6;
    }}
    button span {{
      color: var(--muted);
      font-weight: 600;
      margin-left: 4px;
    }}
    .custom-period {{
      display: grid;
      grid-template-columns: minmax(220px, 320px) 92px;
      gap: 10px;
      align-items: end;
    }}
    .custom-period-panel {{
      padding: 14px;
      margin-bottom: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .custom-period span {{
      display: block;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: .72rem;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .custom-period input {{
      min-height: 38px;
    }}
    .custom-period button {{
      min-height: 38px;
    }}
    .signal-caution {{
      display: block !important;
      margin-top: 8px !important;
      color: #9a3412 !important;
      font-weight: 700 !important;
    }}
    .chart-tooltip .warning {{
      justify-content: flex-start;
      margin-top: 7px;
      padding-top: 7px;
      border-top: 1px solid #fed7aa;
      color: #9a3412;
      font-weight: 750;
      white-space: normal;
    }}
    .chart-panel {{
      overflow: hidden;
      margin-bottom: 16px;
    }}
    .metric-summary {{
      padding: 18px;
    }}
    .metric-summary h2 {{
      margin: 0 0 14px;
      font-size: 1.35rem;
      line-height: 1.15;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
    }}
    .summary-card {{
      display: grid;
      gap: 10px;
      min-height: 190px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
    }}
    .summary-card h3 {{
      margin: 0;
      font-size: 1rem;
      line-height: 1.15;
    }}
    .summary-value {{
      margin: 0;
      color: var(--ink);
      font-size: 1.35rem;
      font-weight: 850;
      line-height: 1;
    }}
    .summary-card p {{
      margin: 0;
      color: var(--muted);
      font-size: .82rem;
      line-height: 1.38;
    }}
    .summary-status {{
      display: inline-flex;
      width: fit-content;
      align-items: center;
      min-height: 24px;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: .72rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .summary-status.risk {{ background: #fdecec; color: var(--red); }}
    .summary-status.opportunity {{ background: #eaf7f0; color: var(--green); }}
    .summary-status.normal {{ background: #edf4ff; color: #174ea6; }}
    .summary-section {{
      display: grid;
      gap: 5px;
      padding-top: 8px;
      border-top: 1px solid var(--line);
    }}
    .summary-section h4 {{
      margin: 0;
      color: var(--ink);
      font-size: .78rem;
      font-weight: 850;
      text-transform: uppercase;
      letter-spacing: .06em;
    }}
    .chart-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
    }}
    .chart-head h2 {{
      margin: 0;
      font-size: 1.65rem;
      line-height: 1.15;
    }}
    .chart-head p {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: .86rem;
    }}
    .chart-canvas {{
      position: relative;
      display: block;
      width: 100%;
      min-height: 1020px;
      background: #fff;
    }}
    .chart-canvas svg {{ display: block; width: 100%; height: auto; }}
    .chart-tooltip {{
      position: absolute;
      z-index: 5;
      width: max-content;
      max-width: 280px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, .97);
      box-shadow: 0 12px 30px rgba(15, 23, 42, .14);
      color: var(--ink);
      font-size: .78rem;
      line-height: 1.35;
      pointer-events: none;
      transform: translate(12px, 12px);
      opacity: 0;
      transition: opacity .08s ease;
    }}
    .chart-tooltip.visible {{ opacity: 1; }}
    .chart-tooltip strong {{
      display: block;
      margin-bottom: 6px;
      font-size: .82rem;
    }}
    .chart-tooltip span {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .chart-tooltip b {{
      color: var(--ink);
      font-weight: 750;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: .78rem;
      font-weight: 750;
    }}
    .pill.risk {{ background: #fdecec; color: var(--red); }}
    .pill.opportunity {{ background: #eaf7f0; color: var(--green); }}
    .pill.normal, .pill.neutral {{ background: #edf4ff; color: #174ea6; }}
    .note {{
      margin-top: 14px;
      color: var(--muted);
      font-size: .83rem;
      line-height: 1.45;
    }}
    @media (max-width: 900px) {{
      .topbar, .chart-head {{ align-items: flex-start; flex-direction: column; }}
      .controls {{ grid-template-columns: 1fr; }}
      .event-form {{ grid-template-columns: 1fr 1fr; }}
      .scenario-head {{ flex-direction: column; }}
      .scenario-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 560px) {{
      .summary-grid {{ grid-template-columns: 1fr; }}
      .scenario-grid {{ grid-template-columns: 1fr; }}
      .event-form {{ grid-template-columns: 1fr; }}
      .custom-period {{ grid-template-columns: 1fr; }}
      .wrap {{ width: min(100% - 20px, 1240px); }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div>
        <h1>SaaS Signals Board</h1>
      </div>
      <a class="back-link" href="index.html">Back to project theory</a>
    </div>
  </header>
  <main class="wrap">
    <section class="controls">
      <div class="control-panel">
        <span class="label">Metric</span>
        <div class="tabs" id="metric-tabs">{metric_options}</div>
      </div>
      <div class="control-panel">
        <span class="label">Scenario</span>
        <div class="tabs" id="profile-tabs">{profile_options}</div>
      </div>
      <div class="control-panel">
        <span class="label">Period</span>
        <div class="tabs" id="period-tabs">{period_options}</div>
      </div>
      <div class="control-panel">
        <span class="label">Data frequency</span>
        <div class="tabs" id="frequency-tabs">{frequency_options}</div>
      </div>
    </section>
    <section class="custom-period-panel">
      <span class="label">Custom period</span>
      <div class="custom-period">
        <label><span>Months to analyze</span><input id="custom-period-count" type="number" min="1" max="120" step="1" value="18"></label>
        <button id="apply-period" type="button">Apply</button>
      </div>
    </section>
    <section class="scenario-panel">
      <div class="scenario-head">
        <div>
          <span class="label">Configure sensitivity scenarios</span>
        </div>
        <label class="scenario-count">Number of scenarios <input id="scenario-count" type="number" min="1" max="8" step="1" value="{len(PROFILES)}"></label>
      </div>
      <div class="scenario-grid" id="scenario-inputs"></div>
      <div class="apply-row"><button id="apply-scenarios" type="button">Apply scenarios</button></div>
    </section>
    <section class="event-panel">
      <span class="label">Known event annotations</span>
      <div class="event-form">
        <label><span>Period</span><input id="event-month" type="month" min="{monthly["month"].min().strftime("%Y-%m")}" max="{monthly["month"].max().strftime("%Y-%m")}" value="{monthly["month"].max().strftime("%Y-%m")}"></label>
        <label><span>Event label</span><input id="event-label" type="text" placeholder="Price increase, enterprise deal, campaign..."></label>
        <button id="add-event" type="button">Add event</button>
      </div>
      <div class="event-list" id="event-list"></div>
    </section>
    <section class="chart-panel">
      <div class="chart-head">
        <div>
          <h2 id="chart-title">SaaS Signals Board</h2>
        </div>
      </div>
      <div id="chart-frame" class="chart-canvas" role="img" aria-label="Signal bands chart"></div>
    </section>
    <section class="metric-summary" aria-label="Metric signal summary">
      <h2>Metric signal summary</h2>
      <div class="summary-grid" id="metric-summary-grid"></div>
    </section>
  </main>
  <script>
    const metricLabels = {metric_labels};
    const metricMeta = {metric_meta};
    const monthlyData = {monthly_json};
    const profileK = {profile_k};
    const profileLabels = {profile_labels};
    const periodLabels = {period_labels};
    const periodLengths = {period_lengths};
    const frequencyLabels = {frequency_labels};
    const frequencyUnits = {frequency_units};
    const initialScenarios = {initial_scenarios};
    const windowSize = "{window}";
    const rollingWindows = {{
      daily: 365,
      weekly: 52,
      monthly: 12,
      quarterly: 4
    }};
    const metricTabs = document.querySelectorAll(".metric-tab");
    const periodTabs = document.querySelectorAll(".period-tab");
    const frequencyTabs = document.querySelectorAll(".frequency-tab");
    const customPeriodCount = document.getElementById("custom-period-count");
    const applyPeriod = document.getElementById("apply-period");
    const frame = document.getElementById("chart-frame");
    const title = document.getElementById("chart-title");
    const metricSummaryGrid = document.getElementById("metric-summary-grid");
    const profileTabsContainer = document.getElementById("profile-tabs");
    const scenarioCount = document.getElementById("scenario-count");
    const scenarioInputs = document.getElementById("scenario-inputs");
    const applyScenarios = document.getElementById("apply-scenarios");
    const eventMonth = document.getElementById("event-month");
    const eventLabel = document.getElementById("event-label");
    const addEvent = document.getElementById("add-event");
    const eventList = document.getElementById("event-list");
    let metric = "{default_metric}";
    let profile = "{default_profile}";
    let period = "{default_period}";
    let frequency = "{default_frequency}";
    let scenarios = initialScenarios.map((item) => ({{ ...item }}));
    let events = loadEvents();

    function loadEvents() {{
      try {{
        const saved = JSON.parse(localStorage.getItem("saasSignalsEvents") || "[]");
        return Array.isArray(saved) ? saved : [];
      }} catch (error) {{
        return [];
      }}
    }}

    function saveEvents() {{
      localStorage.setItem("saasSignalsEvents", JSON.stringify(events));
    }}

    function normalizeEventMonth(value) {{
      return value ? `${{value.slice(0, 7)}}-01` : "";
    }}

    function monthDistance(fromMonth, toMonth) {{
      const from = new Date(fromMonth);
      const to = new Date(toMonth);
      return (to.getFullYear() - from.getFullYear()) * 12 + (to.getMonth() - from.getMonth());
    }}

    function eventForRow(row) {{
      if (!row) return null;
      return events
        .filter((event) => event.month <= row.month)
        .sort((a, b) => a.month.localeCompare(b.month))
        .at(-1) || null;
    }}

    function explanatoryEvent(row) {{
      const event = eventForRow(row);
      if (!event) return null;
      const distance = monthDistance(event.month, row.month);
      return distance >= 0 && distance <= 3 ? event : null;
    }}

    function renderEvents() {{
      const sorted = events.slice().sort((a, b) => a.month.localeCompare(b.month));
      eventList.innerHTML = sorted.length
        ? sorted.map((event) => `<span class="event-chip">${{event.month.slice(0, 7)}} · ${{escapeHtml(event.label)}} <button type="button" aria-label="Remove event" data-event-id="${{event.id}}">x</button></span>`).join("")
        : `<span class="note">No known events annotated yet.</span>`;
      eventList.querySelectorAll("[data-event-id]").forEach((button) => {{
        button.addEventListener("click", () => {{
          events = events.filter((event) => event.id !== button.dataset.eventId);
          saveEvents();
          renderEvents();
          updateChart();
        }});
      }});
    }}

    function slugify(value) {{
      return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "scenario";
    }}

    function escapeHtml(value) {{
      return String(value).replace(/[&<>"']/g, (char) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }}[char]));
    }}

    function truncateText(value, maxLength) {{
      const text = String(value || "").trim();
      return text.length > maxLength ? `${{text.slice(0, maxLength - 1)}}...` : text;
    }}

    function wrapEventLabel(value) {{
      const words = String(value || "").trim().split(/\\s+/).filter(Boolean);
      const lines = [""];
      words.forEach((word) => {{
        const current = lines[lines.length - 1];
        const next = current ? `${{current}} ${{word}}` : word;
        if (next.length <= 26 || !current) {{
          lines[lines.length - 1] = next;
        }} else if (lines.length < 2) {{
          lines.push(word);
        }} else {{
          lines[1] = `${{lines[1]}} ${{word}}`;
        }}
      }});
      return lines.slice(0, 2).map((line) => truncateText(line, 28));
    }}

    function formatValue(value, valueFormat) {{
      if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
      if (valueFormat === "currency") return `$${{Math.round(value).toLocaleString("en-US")}}`;
      if (valueFormat === "percent") return `${{(value * 100).toFixed(1)}}%`;
      if (valueFormat === "integer") return Math.round(value).toLocaleString("en-US");
      return Number(value).toFixed(2);
    }}

    function signalLabel(value) {{
      if (!value) return "n/a";
      return value.replace("_", " ");
    }}

    function formatAxis(value) {{
      if (value === null || value === undefined || Number.isNaN(value)) return "";
      const abs = Math.abs(value);
      if (abs >= 1000000) return `${{(value / 1000000).toFixed(1)}}M`;
      if (abs >= 1000) return `${{(value / 1000).toFixed(1)}}K`;
      if (abs < 1 && value !== 0) return `${{(value * 100).toFixed(1)}}%`;
      return Math.round(value).toLocaleString("en-US");
    }}

    function mean(values) {{
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }}

    function sampleStd(values, avg) {{
      if (values.length < 2) return 0;
      const variance = values.reduce((sum, value) => sum + Math.pow(value - avg, 2), 0) / (values.length - 1);
      return Math.sqrt(variance);
    }}

    function rollingWindow() {{
      return rollingWindows[frequency] || Number(windowSize);
    }}

    function withBandsForMetric(metricId, k) {{
      const currentWindow = rollingWindow();
      const minPeriods = Math.max(3, Math.min(Math.floor(currentWindow / 2), currentWindow));
      return monthlyData.map((row, index) => {{
        const start = Math.max(0, index - currentWindow + 1);
        const windowRows = monthlyData.slice(start, index + 1)
          .map((item) => Number(item[metricId]))
          .filter((value) => Number.isFinite(value));
        const next = {{ ...row }};
        if (windowRows.length >= minPeriods) {{
          const avg = mean(windowRows);
          const std = sampleStd(windowRows, avg);
          next.center = avg;
          next.upper = avg + k * std;
          next.lower = avg - k * std;
          if (Number(row[metricId]) > next.upper) next.signal = "above_band";
          else if (Number(row[metricId]) < next.lower) next.signal = "below_band";
          else next.signal = "normal";
        }} else {{
          next.center = null;
          next.upper = null;
          next.lower = null;
          next.signal = "warming_up";
        }}
        return next;
      }});
    }}

    function withBands(k) {{
      return withBandsForMetric(metric, k);
    }}

    function filterPeriod(rows) {{
      const length = period === "custom"
        ? customPeriodLength()
        : periodLengths[period];
      if (!length) return rows;
      return rows.slice(-length);
    }}

    function customPeriodLength() {{
      return Math.max(1, Number(customPeriodCount.value) || 18);
    }}

    function updateCustomPeriodLabel() {{
      const customTab = document.querySelector('[data-period="custom"]');
      if (customTab) customTab.textContent = `Last ${{customPeriodLength()}} months`;
    }}

    function scale(value, domainMin, domainMax, rangeMin, rangeMax) {{
      if (value === null || value === undefined || Number.isNaN(value)) return null;
      if (domainMax === domainMin) return (rangeMin + rangeMax) / 2;
      return rangeMin + ((value - domainMin) * (rangeMax - rangeMin)) / (domainMax - domainMin);
    }}

    function polyline(points) {{
      return points.filter((point) => point[0] !== null && point[1] !== null).map((point) => `${{point[0].toFixed(2)}},${{point[1].toFixed(2)}}`).join(" ");
    }}

    function activeScenario() {{
      return scenarios.find((item) => item.id === profile) || scenarios[0];
    }}

    function businessTone(signal, direction) {{
      if (signal === "warming_up" || signal === "normal") return "normal";
      if (direction === "lower") return signal === "above_band" ? "risk" : "opportunity";
      return signal === "above_band" ? "opportunity" : "risk";
    }}

    function changeTone(change, direction) {{
      if (change === 0) return "normal";
      if (direction === "lower") return change > 0 ? "risk" : "opportunity";
      return change > 0 ? "opportunity" : "risk";
    }}

    function annualOffset() {{
      if (frequency === "daily") return 365;
      if (frequency === "weekly") return 52;
      if (frequency === "quarterly") return 4;
      return 12;
    }}

    function signedChange(value, valueFormat) {{
      const sign = value > 0 ? "+" : value < 0 ? "-" : "";
      if (valueFormat === "percent") return `${{sign}}${{(Math.abs(value) * 100).toFixed(1)}}%`;
      return `${{sign}}${{formatValue(Math.abs(value), valueFormat)}}`;
    }}

    function toneLabel(tone) {{
      if (tone === "risk") return "Risk";
      if (tone === "opportunity") return "Opportunity";
      return "Normal";
    }}

    function momentumToneFromChanges(previousChange, seasonalChange, direction) {{
      const tones = [previousChange, seasonalChange]
        .filter((value) => value !== null && value !== undefined && Number.isFinite(value))
        .map((value) => changeTone(value, direction));
      if (tones.includes("risk")) return "risk";
      if (tones.includes("opportunity")) return "opportunity";
      return "normal";
    }}

    function earlySignalLabel(tone) {{
      if (tone === "risk") return "Early risk";
      if (tone === "opportunity") return "Early opportunity";
      return "No early signal";
    }}

    function durationTone(streak, rangeTone) {{
      if (streak === 0) return "normal";
      return rangeTone;
    }}

    function durationLabel(streak) {{
      if (streak === 0) return "No repeated signal";
      if (streak === 1) return "Single-period signal";
      return "Repeated signal";
    }}

    function baselineShiftMeaning(metricId, shift, recentAverage, baselineAverage) {{
      const meta = metricMeta[metricId];
      if (![shift, recentAverage, baselineAverage].every((value) => Number.isFinite(Number(value)))) {{
        return "There is not enough history yet to compare the recent baseline with the previous one.";
      }}
      const recentText = formatValue(recentAverage, meta.format);
      const baselineText = formatValue(baselineAverage, meta.format);
      const shiftText = signedChange(shift, meta.format);
      const lower = shift < 0;

      if (Math.abs(shift) <= Math.max(Math.abs(baselineAverage) * 0.01, 0.0001)) {{
        return `Recent ${{meta.label}} is broadly in line with its previous baseline: ${{recentText}} recently vs ${{baselineText}} before. No clear change in the normal level yet.`;
      }}

      const messages = {{
        mrr_growth_rate: lower
          ? `MRR growth has slowed materially: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} in the previous baseline. The business is still growing, but at a much weaker pace (${{shiftText}}).`
          : `MRR growth has accelerated: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. This suggests the revenue growth baseline may have moved up (${{shiftText}}).`,
        arpu_growth_rate: lower
          ? `ARPU growth has weakened: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. Pricing, mix or expansion revenue may be losing momentum (${{shiftText}}).`
          : `ARPU growth has improved: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. Pricing, mix or expansion revenue may be contributing more than usual (${{shiftText}}).`,
        active_customer_growth_rate: lower
          ? `Customer growth has slowed: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. Acquisition or retention may be losing speed (${{shiftText}}).`
          : `Customer growth has accelerated: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. Acquisition or retention may be performing above the previous baseline (${{shiftText}}).`,
        customer_churn_rate: lower
          ? `Customer churn is running below its previous baseline: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. Fewer customers are leaving than usual, which is a positive shift (${{shiftText}}).`
          : `Customer churn is running above its previous baseline: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. More customers are leaving than usual, so this deserves investigation (${{shiftText}}).`,
        revenue_churn_rate: lower
          ? `Revenue churn is running below its previous baseline: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. Less recurring revenue is being lost than usual, which is a positive shift (${{shiftText}}).`
          : `Revenue churn is running above its previous baseline: the last 3 periods averaged ${{recentText}} vs ${{baselineText}} before. More recurring revenue is being lost than usual, so this deserves investigation (${{shiftText}}).`
      }};

      return messages[metricId] || `Recent ${{meta.label}} averaged ${{recentText}} vs ${{baselineText}} in the previous baseline. The normal level may have changed by ${{shiftText}}.`;
    }}

    function baselineShiftForRows(historyRows, metricId) {{
      const cleanRows = historyRows.filter((row) => Number.isFinite(Number(row[metricId])));
      if (cleanRows.length < 15) {{
        return {{
          tone: "normal",
          title: "Not enough history",
          copy: "Needs 3 recent periods and 12 previous baseline periods.",
          shift: null,
          recentAverage: null,
          baselineAverage: null
        }};
      }}
      const recentRows = cleanRows.slice(-3);
      const baselineRows = cleanRows.slice(-15, -3);
      const recentValues = recentRows.map((row) => Number(row[metricId]));
      const baselineValues = baselineRows.map((row) => Number(row[metricId]));
      const recentAverage = mean(recentValues);
      const baselineAverage = mean(baselineValues);
      const baselineStd = sampleStd(baselineValues, baselineAverage);
      const shift = recentAverage - baselineAverage;
      const threshold = Math.max(baselineStd * 1.5, Math.abs(baselineAverage) * 0.05, 0.0001);
      const meta = metricMeta[metricId];
      if (Math.abs(shift) <= threshold) {{
        return {{
          tone: "normal",
          title: "No structural shift",
          copy: baselineShiftMeaning(metricId, shift, recentAverage, baselineAverage),
          shift,
          recentAverage,
          baselineAverage
        }};
      }}
      const tone = changeTone(shift, meta.direction);
      const directionText = tone === "opportunity" ? "positive" : "negative";
      return {{
        tone,
        title: `Possible ${{directionText}} baseline shift`,
        copy: baselineShiftMeaning(metricId, shift, recentAverage, baselineAverage),
        shift,
        recentAverage,
        baselineAverage
      }};
    }}

    function dataCaution(row, metricId) {{
      if (!row) return "";
      if (metricId === "customer_churn_rate" && row.customer_churn_caution) {{
        return "Data warning: small starting customer base; interpret churn cautiously.";
      }}
      if (metricId === "revenue_churn_rate" && row.revenue_churn_caution) {{
        return "Data warning: small starting MRR or churn above 100%; interpret cautiously.";
      }}
      return "";
    }}

    function periodDataCaution(rows, metricId) {{
      const cautionedRows = rows.filter((row) => dataCaution(row, metricId));
      if (!cautionedRows.length) return "";
      const first = cautionedRows[0].month.slice(0, 7);
      const last = cautionedRows[cautionedRows.length - 1].month.slice(0, 7);
      const periodText = cautionedRows.length === 1 ? first : `${{first}}-${{last}}`;
      if (metricId === "customer_churn_rate") {{
        return `Data warning: ${{cautionedRows.length}} visible period${{cautionedRows.length === 1 ? "" : "s"}} have a small starting customer base (${{periodText}}).`;
      }}
      if (metricId === "revenue_churn_rate") {{
        return `Data warning: ${{cautionedRows.length}} visible period${{cautionedRows.length === 1 ? "" : "s"}} have small starting MRR or churn above 100% (${{periodText}}).`;
      }}
      return "";
    }}

    function metricStorySubject(metricId) {{
      return {{
        mrr_growth_rate: "MRR growth",
        arpu_growth_rate: "ARPU growth",
        active_customer_growth_rate: "customer growth",
        customer_churn_rate: "customer churn",
        revenue_churn_rate: "revenue churn"
      }}[metricId] || metricLabels[metricId].toLowerCase();
    }}

    function rangeStory(metricId, latest, rangeTone) {{
      const meta = metricMeta[metricId];
      const value = Number(latest[metricId]);
      const valueText = formatValue(value, meta.format);
      if (latest.signal === "warming_up") {{
        return `There is not enough history yet to decide whether ${{metricStorySubject(metricId)}} is behaving normally.`;
      }}
      if (latest.signal === "normal") {{
        return `At ${{valueText}}, ${{metricStorySubject(metricId)}} is still inside its normal operating range. There is no current range break, so the latest movement looks contained.`;
      }}

      const stories = {{
        mrr_growth_rate: {{
          risk: value < 0
            ? `MRR is contracting this period (${{valueText}}), and the contraction is outside the normal range. This is a revenue-growth warning, not just a slower month.`
            : `MRR is still growing (${{valueText}}), but growth is below its normal range. The business is expanding at an unusually weak pace.`,
          opportunity: `MRR growth is unusually strong at ${{valueText}}. Revenue expansion is running above its recent normal range.`
        }},
        arpu_growth_rate: {{
          risk: value < 0
            ? `ARPU is declining (${{valueText}}), and the move is outside the normal range. Revenue per account is under unusual pressure.`
            : `ARPU is growing at ${{valueText}}, but below its normal range. Pricing, mix or expansion revenue may be softer than usual.`,
          opportunity: `ARPU growth is unusually strong at ${{valueText}}. Pricing, customer mix or expansion revenue may be outperforming the recent baseline.`
        }},
        active_customer_growth_rate: {{
          risk: value < 0
            ? `The active customer base is shrinking (${{valueText}}), and the move is outside the normal range. Acquisition and retention should be reviewed together.`
            : `Customer growth is positive at ${{valueText}}, but below its normal range. The customer base is expanding more slowly than expected.`,
          opportunity: `Customer growth is unusually strong at ${{valueText}}. Acquisition and/or retention are performing above the recent pattern.`
        }},
        customer_churn_rate: {{
          risk: `Customer churn is unusually high at ${{valueText}}. More customers are leaving than the recent range would normally suggest.`,
          opportunity: `Customer churn is unusually low at ${{valueText}}. Fewer customers are leaving than normal, which is a retention upside signal.`
        }},
        revenue_churn_rate: {{
          risk: `Revenue churn is unusually high at ${{valueText}}. The business is losing more recurring revenue than its recent range would normally suggest.`,
          opportunity: `Revenue churn is unusually low at ${{valueText}}. Less recurring revenue is being lost than normal, which supports net revenue retention.`
        }}
      }};

      return stories[metricId]?.[rangeTone] || `At ${{valueText}}, ${{metricStorySubject(metricId)}} is outside its normal range and deserves investigation.`;
    }}

    function momentumStory(metricId, previousChange, seasonalChange) {{
      const meta = metricMeta[metricId];
      const previousTone = Number.isFinite(previousChange) ? changeTone(previousChange, meta.direction) : null;
      const seasonalTone = Number.isFinite(seasonalChange) ? changeTone(seasonalChange, meta.direction) : null;
      const previousText = Number.isFinite(previousChange) ? signedChange(previousChange, meta.format) : "n/a";
      const seasonalText = Number.isFinite(seasonalChange) ? signedChange(seasonalChange, meta.format) : "n/a";
      const subject = metricStorySubject(metricId);

      if (!previousTone && !seasonalTone) {{
        return `There is not enough history yet to compare ${{subject}} against the previous period or the same period last year.`;
      }}
      if (previousTone === "risk" && seasonalTone === "risk") {{
        return `The signal is weakening on both comparisons: ${{previousText}} versus the previous period and ${{seasonalText}} versus the same period last year. This points to broad deterioration, not just a seasonal effect.`;
      }}
      if (previousTone === "opportunity" && seasonalTone === "opportunity") {{
        return `Momentum is positive on both comparisons: ${{previousText}} versus the previous period and ${{seasonalText}} versus the same period last year. The improvement is both recent and seasonally stronger.`;
      }}
      if (previousTone === "risk" && seasonalTone === "opportunity") {{
        return `The latest movement is weaker than last period (${{previousText}}), but still better than the same period last year (${{seasonalText}}). This looks like short-term cooling, not necessarily a year-over-year deterioration.`;
      }}
      if (previousTone === "opportunity" && seasonalTone === "risk") {{
        return `The metric improved versus last period (${{previousText}}), but remains worse than the same period last year (${{seasonalText}}). The short-term bounce has not recovered the seasonal gap yet.`;
      }}
      if (previousTone === "risk") {{
        return `The latest period moved in the wrong direction versus the previous period (${{previousText}}). Same-period history is not available, so treat this as an early short-term warning.`;
      }}
      if (previousTone === "opportunity") {{
        return `The latest period improved versus the previous period (${{previousText}}). Same-period history is not available, so the seasonal read is still incomplete.`;
      }}
      if (seasonalTone === "risk") {{
        return `Compared with the same period last year, ${{subject}} is worse by ${{seasonalText}}. This suggests the movement is not just normal seasonality.`;
      }}
      return `Compared with the same period last year, ${{subject}} is better by ${{seasonalText}}. The seasonal comparison is favorable.`;
    }}

    function durationStory(streak, rangeTone) {{
      if (streak === 0) {{
        return "There is no active range break. The latest movement is not repeating outside the expected range.";
      }}
      if (streak === 1) {{
        return rangeTone === "risk"
          ? "This is a fresh break outside the range. Investigate the driver now before treating it as a new trend."
          : "This is a fresh favorable break outside the range. Check whether it comes from a repeatable driver or a one-off event.";
      }}
      return rangeTone === "risk"
        ? `The break has lasted ${{streak}} consecutive periods. This is becoming persistent and should be treated as an operating issue, not noise.`
        : `The favorable break has lasted ${{streak}} consecutive periods. This may indicate a real improvement rather than a one-off spike.`;
    }}

    function renderMetricSummary(k) {{
      metricSummaryGrid.innerHTML = Object.keys(metricLabels).map((metricId) => {{
        const metricRows = withBandsForMetric(metricId, k);
        const visibleRows = filterPeriod(metricRows).filter((row) => Number.isFinite(Number(row[metricId])));
        const historyRows = metricRows.filter((row) => Number.isFinite(Number(row[metricId])));
        const latest = visibleRows[visibleRows.length - 1];
        const previous = visibleRows[visibleRows.length - 2];
        const meta = metricMeta[metricId];
        if (!latest) {{
          return `<article class="summary-card"><h3>${{metricLabels[metricId]}}</h3><p>No data available for the selected period.</p></article>`;
        }}

        const latestHistoryIndex = historyRows.findLastIndex((row) => row.month === latest.month);
        const rangeTone = businessTone(latest.signal, meta.direction);
        const previousChange = previous ? Number(latest[metricId]) - Number(previous[metricId]) : null;
        const seasonalRow = latestHistoryIndex >= annualOffset()
          ? historyRows[latestHistoryIndex - annualOffset()]
          : null;
        const seasonalChange = seasonalRow ? Number(latest[metricId]) - Number(seasonalRow[metricId]) : null;
        let streak = 0;
        for (let index = visibleRows.length - 1; index >= 0; index -= 1) {{
          if (["above_band", "below_band"].includes(visibleRows[index].signal)) streak += 1;
          else break;
        }}

        const earlyTone = momentumToneFromChanges(previousChange, seasonalChange, meta.direction);
        const durationSignalTone = durationTone(streak, rangeTone);
        const baselineShift = baselineShiftForRows(historyRows.slice(0, latestHistoryIndex + 1), metricId);
        const currentStory = rangeStory(metricId, latest, rangeTone);
        const earlyStory = momentumStory(metricId, previousChange, seasonalChange);
        const persistenceStory = durationStory(streak, rangeTone);
        const cautionText = dataCaution(latest, metricId) || periodDataCaution(visibleRows, metricId);
        const cautionHtml = cautionText ? `<p class="signal-caution">${{cautionText}}</p>` : "";

        return `<article class="summary-card">
          <h3>${{metricLabels[metricId]}}</h3>
          <p class="summary-value">${{formatValue(Number(latest[metricId]), meta.format)}}</p>
          <span class="summary-status ${{rangeTone}}">${{toneLabel(rangeTone)}}</span>
          <p>${{currentStory}}</p>
          ${{cautionHtml}}
          <div class="summary-section">
            <h4>Momentum read</h4>
            <span class="summary-status ${{earlyTone}}">${{earlySignalLabel(earlyTone)}}</span>
            <p>${{earlyStory}}</p>
          </div>
          <div class="summary-section">
            <h4>Persistence read</h4>
            <span class="summary-status ${{durationSignalTone}}">${{durationLabel(streak)}}</span>
            <p>${{persistenceStory}}</p>
          </div>
          <div class="summary-section">
            <h4>Baseline shift</h4>
            <span class="summary-status ${{baselineShift.tone}}">${{baselineShift.title}}</span>
            <p>${{baselineShift.copy}}</p>
          </div>
        </article>`;
      }}).join("");
    }}

    function updateChart() {{
      const scenario = activeScenario();
      if (!scenario) return;
      const k = Number(scenario.k);
      const allRows = withBands(k);
      const rows = filterPeriod(allRows);
      const historyRows = allRows.filter((row) => Number.isFinite(Number(row[metric])));
      const width = 1180;
      const height = 1370;
      const left = 82;
      const right = 42;
      const top = 64;
      const chartWidth = width - left - right;
      const chartHeight = 390;
      const momentumTop = top + chartHeight + 240;
      const momentumHeight = 150;
      const baselineTop = momentumTop + momentumHeight + 260;
      const baselineHeight = 150;
      const values = rows.flatMap((row) => [Number(row[metric]), row.upper, row.lower]).filter((value) => Number.isFinite(value));
      let yMin = Math.min(...values);
      let yMax = Math.max(...values);
      const padding = yMax !== yMin ? (yMax - yMin) * 0.08 : Math.max(Math.abs(yMax) * 0.1, 1);
      yMin -= padding;
      yMax += padding;
      const xCount = Math.max(rows.length - 1, 1);
      const pointsFor = (field) => rows.map((row, index) => {{
        const x = left + (index / xCount) * chartWidth;
        const rawValue = field === "metric" ? Number(row[metric]) : row[field];
        return [x, scale(rawValue, yMin, yMax, top + chartHeight, top)];
      }});
      const metricPoints = pointsFor("metric");
      const centerPoints = pointsFor("center");
      const upperPoints = pointsFor("upper");
      const lowerPoints = pointsFor("lower");
      const bandPoints = polyline([...upperPoints, ...lowerPoints.slice().reverse()]);
      const yTicks = Array.from({{ length: 5 }}, (_, index) => {{
        const value = yMin + (index / 4) * (yMax - yMin);
        const y = scale(value, yMin, yMax, top + chartHeight, top);
        return `<line x1="${{left}}" x2="${{width - right}}" y1="${{y.toFixed(2)}}" y2="${{y.toFixed(2)}}" stroke="#e5e7eb" stroke-width="1"/><text x="${{left - 12}}" y="${{(y + 4).toFixed(2)}}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">${{formatAxis(value)}}</text>`;
      }}).join("");
      const labelStep = Math.max(Math.floor(rows.length / 6), 1);
      const xAxisLabels = (axisY, labelY) => rows.map((row, index) => {{
        if (index % labelStep !== 0 && index !== rows.length - 1) return "";
        const x = left + (index / xCount) * chartWidth;
        const label = row.month.slice(0, 7);
        return `<line x1="${{x.toFixed(2)}}" x2="${{x.toFixed(2)}}" y1="${{axisY.toFixed(2)}}" y2="${{(axisY + 6).toFixed(2)}}" stroke="#cbd5e1" stroke-width="1"/><text x="${{x.toFixed(2)}}" y="${{labelY.toFixed(2)}}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">${{label}}</text>`;
      }}).join("");
      const visibleEvents = events.filter((event) => rows.some((row) => row.month.slice(0, 7) === event.month.slice(0, 7)));
      const eventMarkers = visibleEvents.map((event) => {{
        const index = rows.findIndex((row) => row.month.slice(0, 7) === event.month.slice(0, 7));
        if (index < 0) return "";
        const x = left + (index / xCount) * chartWidth;
        const labelLines = wrapEventLabel(event.label);
        const labelWidth = 236;
        const labelHeight = labelLines.length > 1 ? 44 : 30;
        const labelX = Math.max(left + 8, Math.min(x + 8, width - right - labelWidth));
        const labelY = top + 12;
        const textX = labelX + 12;
        const textY = labelLines.length > 1 ? labelY + 15 : labelY + 20;
        const textLines = labelLines.map((line, lineIndex) =>
          `<tspan x="${{textX.toFixed(2)}}" dy="${{lineIndex === 0 ? 0 : 15}}">${{escapeHtml(line)}}</tspan>`
        ).join("");
        return `<line x1="${{x.toFixed(2)}}" x2="${{x.toFixed(2)}}" y1="${{top}}" y2="${{(baselineTop + baselineHeight).toFixed(2)}}" stroke="#f97316" stroke-width="1.5" stroke-dasharray="5 5" opacity="0.75"/>
          <rect x="${{labelX.toFixed(2)}}" y="${{labelY.toFixed(2)}}" width="${{labelWidth}}" height="${{labelHeight}}" rx="7" fill="#fff7ed" stroke="#fed7aa"/>
          <text x="${{textX.toFixed(2)}}" y="${{textY.toFixed(2)}}" font-family="Inter, Arial, sans-serif" font-size="11" font-weight="750" fill="#9a3412"><title>${{escapeHtml(event.label)}}</title>${{textLines}}</text>`;
      }}).join("");
      const alerts = rows.map((row, index) => {{
        if (!["above_band", "below_band"].includes(row.signal)) return "";
        const point = metricPoints[index];
        const explained = explanatoryEvent(row);
        return `<circle cx="${{point[0].toFixed(2)}}" cy="${{point[1].toFixed(2)}}" r="5.5" fill="${{explained ? "#f97316" : "#dc2626"}}"/>`;
      }}).join("");
      const momentumRows = rows.map((row, index) => {{
        const historyIndex = historyRows.findIndex((item) => item.month === row.month);
        const currentValue = Number(row[metric]);
        const previousChange = historyIndex > 0
          ? currentValue - Number(historyRows[historyIndex - 1][metric])
          : null;
        const seasonalChange = historyIndex >= annualOffset()
          ? currentValue - Number(historyRows[historyIndex - annualOffset()][metric])
          : null;
        const x = left + (index / xCount) * chartWidth;
        return {{ x, previousChange, seasonalChange, month: row.month }};
      }});
      const baselineRows = rows.map((row, index) => {{
        const historyIndex = historyRows.findIndex((item) => item.month === row.month);
        const baseline = historyIndex >= 0
          ? baselineShiftForRows(historyRows.slice(0, historyIndex + 1), metric)
          : {{ shift: null, recentAverage: null, baselineAverage: null, tone: "normal", title: "Not enough history", copy: "" }};
        const x = left + (index / xCount) * chartWidth;
        return {{ x, month: row.month, ...baseline }};
      }});
      const momentumValues = momentumRows
        .flatMap((row) => [row.previousChange, row.seasonalChange])
        .filter((value) => Number.isFinite(value));
      const maxMomentum = Math.max(...momentumValues.map((value) => Math.abs(value)), 1);
      const momentumZero = momentumTop + momentumHeight / 2;
      const momentumBarWidth = Math.min(22, Math.max(8, chartWidth / Math.max(rows.length, 1) * 0.34));
      const signalColor = (value) => {{
        const isPositiveForBusiness = metricMeta[metric].direction === "lower" ? value < 0 : value > 0;
        return isPositiveForBusiness ? "#16a34a" : "#dc2626";
      }};
      const momentumBar = (x, value, offset, label) => {{
        if (!Number.isFinite(value)) return "";
        const y = scale(value, -maxMomentum, maxMomentum, momentumTop + momentumHeight, momentumTop);
        const rectY = Math.min(y, momentumZero);
        const rectHeight = Math.max(Math.abs(y - momentumZero), 1);
        return `<rect x="${{(x + offset).toFixed(2)}}" y="${{rectY.toFixed(2)}}" width="${{momentumBarWidth.toFixed(2)}}" height="${{rectHeight.toFixed(2)}}" rx="3" fill="${{signalColor(value)}}" opacity="0.82"/>`;
      }};
      const rowLabel = (value) => signedChange(value, metricMeta[metric].format);
      const momentumBars = momentumRows.map((row) => {{
        const previous = momentumBar(row.x, row.previousChange, -momentumBarWidth - 1, `${{row.month.slice(0, 7)}} previous period`);
        const seasonal = momentumBar(row.x, row.seasonalChange, 1, `${{row.month.slice(0, 7)}} same period last year`);
        return previous + seasonal;
      }}).join("");
      const baselineValues = baselineRows
        .flatMap((row) => [row.recentAverage, row.baselineAverage])
        .filter((value) => Number.isFinite(value));
      let baselineMin = Math.min(...baselineValues);
      let baselineMax = Math.max(...baselineValues);
      const baselinePadding = baselineMax !== baselineMin ? (baselineMax - baselineMin) * 0.12 : Math.max(Math.abs(baselineMax) * 0.1, 0.01);
      baselineMin -= baselinePadding;
      baselineMax += baselinePadding;
      const baselinePoint = (row, field) => [
        row.x,
        scale(row[field], baselineMin, baselineMax, baselineTop + baselineHeight, baselineTop)
      ];
      const baselineRecentPoints = baselineRows.map((row) => baselinePoint(row, "recentAverage"));
      const baselinePriorPoints = baselineRows.map((row) => baselinePoint(row, "baselineAverage"));
      const baselineAreas = baselineRows.slice(1).map((row, index) => {{
        const previous = baselineRows[index];
        if (![previous.shift, row.shift].every((value) => Number.isFinite(value))) return "";
        const previousRecent = baselinePoint(previous, "recentAverage");
        const currentRecent = baselinePoint(row, "recentAverage");
        const currentBaseline = baselinePoint(row, "baselineAverage");
        const previousBaseline = baselinePoint(previous, "baselineAverage");
        if ([previousRecent, currentRecent, currentBaseline, previousBaseline].some((point) => point[1] === null)) return "";
        const averageShift = (previous.shift + row.shift) / 2;
        const color = signalColor(averageShift);
        const points = [previousRecent, currentRecent, currentBaseline, previousBaseline]
          .map((point) => `${{point[0].toFixed(2)}},${{point[1].toFixed(2)}}`)
          .join(" ");
        return `<polygon points="${{points}}" fill="${{color}}" opacity="0.14"/>`;
      }}).join("");
      const baselineSignals = baselineRows.map((row) => {{
        if (!Number.isFinite(row.shift) || row.tone === "normal") return "";
        const point = baselinePoint(row, "recentAverage");
        return `<circle cx="${{point[0].toFixed(2)}}" cy="${{point[1].toFixed(2)}}" r="5" fill="${{signalColor(row.shift)}}"/>`;
      }}).join("");
      const firstBaselineIndex = baselineRows.findIndex((row) => Number.isFinite(row.shift));
      const baselineWarmup = firstBaselineIndex > 0
        ? (() => {{
            const endX = left + ((firstBaselineIndex - 0.5) / xCount) * chartWidth;
            const widthWarmup = Math.max(0, endX - left);
            return `<rect x="${{left}}" y="${{baselineTop}}" width="${{widthWarmup.toFixed(2)}}" height="${{baselineHeight}}" fill="#f8fafc" opacity="0.72"/>
              <text x="${{(left + 12).toFixed(2)}}" y="${{(baselineTop + 24).toFixed(2)}}" font-family="Inter, Arial, sans-serif" font-size="11" font-weight="700" fill="#64748b">Warm-up: needs 3 recent + 12 previous periods</text>`;
          }})()
        : "";
      const hoverSlotWidth = chartWidth / Math.max(rows.length, 1);
      const rangeHoverTargets = rows.map((row, index) => {{
        const point = metricPoints[index];
        const x = Math.max(left, Math.min(width - right - hoverSlotWidth, point[0] - hoverSlotWidth / 2));
        return `<rect data-hover="range" data-index="${{index}}" x="${{x.toFixed(2)}}" y="${{top}}" width="${{hoverSlotWidth.toFixed(2)}}" height="${{chartHeight.toFixed(2)}}" fill="#ffffff" opacity="0" pointer-events="all"/>`;
      }}).join("");
      const momentumHoverTargets = rows.map((row, index) => {{
        const point = metricPoints[index];
        const x = Math.max(left, Math.min(width - right - hoverSlotWidth, point[0] - hoverSlotWidth / 2));
        return `<rect data-hover="momentum" data-index="${{index}}" x="${{x.toFixed(2)}}" y="${{momentumTop}}" width="${{hoverSlotWidth.toFixed(2)}}" height="${{momentumHeight}}" fill="#ffffff" opacity="0" pointer-events="all"/>`;
      }}).join("");
      const baselineHoverTargets = rows.map((row, index) => {{
        const point = metricPoints[index];
        const x = Math.max(left, Math.min(width - right - hoverSlotWidth, point[0] - hoverSlotWidth / 2));
        return `<rect data-hover="baseline" data-index="${{index}}" x="${{x.toFixed(2)}}" y="${{baselineTop}}" width="${{hoverSlotWidth.toFixed(2)}}" height="${{baselineHeight}}" fill="#ffffff" opacity="0" pointer-events="all"/>`;
      }}).join("");
      frame.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="${{width}}" height="${{height}}" viewBox="0 0 ${{width}} ${{height}}">
        <rect width="100%" height="100%" fill="#ffffff"/>
        <text x="${{left}}" y="38" font-family="Inter, Arial, sans-serif" font-size="20" font-weight="700" fill="#111827">${{metricLabels[metric]}} Range Signal</text>
        <g aria-label="Range chart legend">
          <line x1="${{width - right - 520}}" x2="${{width - right - 490}}" y1="34" y2="34" stroke="#111827" stroke-width="3.4"/><text x="${{width - right - 480}}" y="39" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">actual value</text>
          <line x1="${{width - right - 380}}" x2="${{width - right - 350}}" y1="34" y2="34" stroke="#7aa7f7" stroke-width="2" opacity="0.82"/><text x="${{width - right - 340}}" y="39" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">central</text>
          <line x1="${{width - right - 272}}" x2="${{width - right - 242}}" y1="34" y2="34" stroke="#f59e6b" stroke-width="1.8" opacity="0.82"/><text x="${{width - right - 232}}" y="39" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">upper</text>
          <line x1="${{width - right - 174}}" x2="${{width - right - 144}}" y1="34" y2="34" stroke="#5ccfc4" stroke-width="1.8" opacity="0.82"/><text x="${{width - right - 134}}" y="39" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">lower</text>
          <circle cx="${{width - right - 76}}" cy="34" r="6.5" fill="#dc2626"/><text x="${{width - right - 60}}" y="39" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">signal</text>
        </g>
        ${{yTicks}}
        <line x1="${{left}}" x2="${{width - right}}" y1="${{top + chartHeight}}" y2="${{top + chartHeight}}" stroke="#cbd5e1" stroke-width="1"/>
        <polygon points="${{bandPoints}}" fill="#bfdbfe" opacity="0.16"/>
        ${{eventMarkers}}
        <polyline points="${{polyline(upperPoints)}}" fill="none" stroke="#f59e6b" stroke-width="1.5" opacity="0.82"/>
        <polyline points="${{polyline(lowerPoints)}}" fill="none" stroke="#5ccfc4" stroke-width="1.5" opacity="0.82"/>
        <polyline points="${{polyline(centerPoints)}}" fill="none" stroke="#7aa7f7" stroke-width="1.7" opacity="0.82"/>
        <polyline points="${{polyline(metricPoints)}}" fill="none" stroke="#111827" stroke-width="3"/>
        ${{alerts}}
        ${{xAxisLabels(top + chartHeight, top + chartHeight + 30)}}
        <text x="${{left + chartWidth / 2}}" y="${{(top + chartHeight + 54).toFixed(2)}}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" font-weight="700" fill="#374151">Period (${{frequencyUnits[frequency]}})</text>
        <text x="${{left}}" y="${{(momentumTop - 26).toFixed(2)}}" font-family="Inter, Arial, sans-serif" font-size="20" font-weight="700" fill="#111827">${{metricLabels[metric]}} Momentum</text>
        <g aria-label="Momentum chart legend">
          <rect x="${{width - right - 304}}" y="${{(momentumTop - 41).toFixed(2)}}" width="16" height="12" rx="2" fill="#16a34a" opacity="0.82"/><text x="${{width - right - 280}}" y="${{(momentumTop - 30).toFixed(2)}}" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">favorable</text>
          <rect x="${{width - right - 158}}" y="${{(momentumTop - 41).toFixed(2)}}" width="16" height="12" rx="2" fill="#dc2626" opacity="0.82"/><text x="${{width - right - 134}}" y="${{(momentumTop - 30).toFixed(2)}}" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">unfavorable</text>
        </g>
        <line x1="${{left}}" x2="${{width - right}}" y1="${{momentumZero.toFixed(2)}}" y2="${{momentumZero.toFixed(2)}}" stroke="#cbd5e1" stroke-width="1"/>
        <line x1="${{left}}" x2="${{width - right}}" y1="${{momentumTop}}" y2="${{momentumTop}}" stroke="#eef2f7" stroke-width="1"/>
        <line x1="${{left}}" x2="${{width - right}}" y1="${{momentumTop + momentumHeight}}" y2="${{momentumTop + momentumHeight}}" stroke="#eef2f7" stroke-width="1"/>
        <text x="${{left - 12}}" y="${{(momentumTop + 4).toFixed(2)}}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="11" fill="#6b7280">+${{formatAxis(maxMomentum)}}</text>
        <text x="${{left - 12}}" y="${{(momentumZero + 4).toFixed(2)}}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="11" fill="#6b7280">0</text>
        <text x="${{left - 12}}" y="${{(momentumTop + momentumHeight + 4).toFixed(2)}}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="11" fill="#6b7280">-${{formatAxis(maxMomentum)}}</text>
        ${{momentumBars}}
        <line x1="${{left}}" x2="${{width - right}}" y1="${{momentumTop + momentumHeight}}" y2="${{momentumTop + momentumHeight}}" stroke="#cbd5e1" stroke-width="1"/>
        ${{xAxisLabels(momentumTop + momentumHeight, momentumTop + momentumHeight + 30)}}
        <text x="${{left + chartWidth / 2}}" y="${{(momentumTop + momentumHeight + 54).toFixed(2)}}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" font-weight="700" fill="#374151">Period (${{frequencyUnits[frequency]}})</text>
        <text x="${{left}}" y="${{(baselineTop - 28).toFixed(2)}}" font-family="Inter, Arial, sans-serif" font-size="20" font-weight="700" fill="#111827">${{metricLabels[metric]}} Baseline Shift</text>
        <g aria-label="Baseline shift chart legend">
          <line x1="${{width - right - 396}}" x2="${{width - right - 366}}" y1="${{(baselineTop - 36).toFixed(2)}}" y2="${{(baselineTop - 36).toFixed(2)}}" stroke="#2563eb" stroke-width="2.5"/><text x="${{width - right - 356}}" y="${{(baselineTop - 31).toFixed(2)}}" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">recent 3-period avg</text>
          <line x1="${{width - right - 176}}" x2="${{width - right - 146}}" y1="${{(baselineTop - 36).toFixed(2)}}" y2="${{(baselineTop - 36).toFixed(2)}}" stroke="#f59e6b" stroke-width="2.2"/><text x="${{width - right - 136}}" y="${{(baselineTop - 31).toFixed(2)}}" font-family="Inter, Arial, sans-serif" font-size="14" fill="#374151">previous 12-period avg</text>
        </g>
        <line x1="${{left}}" x2="${{width - right}}" y1="${{baselineTop}}" y2="${{baselineTop}}" stroke="#eef2f7" stroke-width="1"/>
        <line x1="${{left}}" x2="${{width - right}}" y1="${{(baselineTop + baselineHeight / 2).toFixed(2)}}" y2="${{(baselineTop + baselineHeight / 2).toFixed(2)}}" stroke="#eef2f7" stroke-width="1"/>
        <line x1="${{left}}" x2="${{width - right}}" y1="${{baselineTop + baselineHeight}}" y2="${{baselineTop + baselineHeight}}" stroke="#eef2f7" stroke-width="1"/>
        <text x="${{left - 12}}" y="${{(baselineTop + 4).toFixed(2)}}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="11" fill="#6b7280">${{formatAxis(baselineMax)}}</text>
        <text x="${{left - 12}}" y="${{(baselineTop + baselineHeight + 4).toFixed(2)}}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="11" fill="#6b7280">${{formatAxis(baselineMin)}}</text>
        ${{baselineWarmup}}
        ${{baselineAreas}}
        <polyline points="${{polyline(baselinePriorPoints)}}" fill="none" stroke="#f59e6b" stroke-width="2.2" opacity="0.9"/>
        <polyline points="${{polyline(baselineRecentPoints)}}" fill="none" stroke="#2563eb" stroke-width="2.7"/>
        ${{baselineSignals}}
        <line x1="${{left}}" x2="${{width - right}}" y1="${{baselineTop + baselineHeight}}" y2="${{baselineTop + baselineHeight}}" stroke="#cbd5e1" stroke-width="1"/>
        ${{xAxisLabels(baselineTop + baselineHeight, baselineTop + baselineHeight + 30)}}
        <text x="${{left + chartWidth / 2}}" y="${{(baselineTop + baselineHeight + 54).toFixed(2)}}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" font-weight="700" fill="#374151">Period (${{frequencyUnits[frequency]}})</text>
        ${{rangeHoverTargets}}
        ${{momentumHoverTargets}}
        ${{baselineHoverTargets}}
      </svg>`;
      const tooltipNode = document.createElement("div");
      tooltipNode.className = "chart-tooltip";
      frame.appendChild(tooltipNode);
      const hideTooltip = () => tooltipNode.classList.remove("visible");
      const moveTooltip = (event) => {{
        const frameRect = frame.getBoundingClientRect();
        const tooltipRect = tooltipNode.getBoundingClientRect();
        const nextLeft = Math.min(event.clientX - frameRect.left + 14, frameRect.width - tooltipRect.width - 18);
        const nextTop = Math.min(event.clientY - frameRect.top + 14, frameRect.height - tooltipRect.height - 18);
        tooltipNode.style.left = `${{Math.max(12, nextLeft)}}px`;
        tooltipNode.style.top = `${{Math.max(12, nextTop)}}px`;
      }};
      const renderTooltip = (target) => {{
        const index = Number(target.dataset.index);
        const type = target.dataset.hover;
        const row = rows[index];
        const momentumRow = momentumRows[index];
        const baselineRow = baselineRows[index];
        if (!row) return "";
        if (type === "momentum") {{
          const previousMomentum = Number.isFinite(momentumRow.previousChange)
            ? rowLabel(momentumRow.previousChange)
            : "n/a";
          const yoyMomentum = Number.isFinite(momentumRow.seasonalChange)
            ? rowLabel(momentumRow.seasonalChange)
            : "n/a";
          return `<strong>${{row.month.slice(0, 7)}} · Momentum</strong>
            <span>Previous period <b>${{previousMomentum}}</b></span>
            <span>Same period last year <b>${{yoyMomentum}}</b></span>`;
        }}
        if (type === "baseline") {{
          if (!baselineRow || !Number.isFinite(baselineRow.shift)) {{
            return `<strong>${{row.month.slice(0, 7)}} · Baseline Shift</strong>
              <span>Status <b>Not enough history</b></span>`;
          }}
          return `<strong>${{row.month.slice(0, 7)}} · Baseline Shift</strong>
            <span>Recent 3-period avg <b>${{formatValue(baselineRow.recentAverage, metricMeta[metric].format)}}</b></span>
            <span>Previous 12-period avg <b>${{formatValue(baselineRow.baselineAverage, metricMeta[metric].format)}}</b></span>
            <span>Shift <b>${{signedChange(baselineRow.shift, metricMeta[metric].format)}}</b></span>
            <span>Status <b>${{baselineRow.title}}</b></span>`;
        }}
        const cautionText = dataCaution(row, metric);
        const knownEvent = eventForRow(row);
        const explanation = explanatoryEvent(row);
        return `<strong>${{row.month.slice(0, 7)}} · Range signal</strong>
          <span>${{metricLabels[metric]}} <b>${{formatValue(Number(row[metric]), metricMeta[metric].format)}}</b></span>
          <span>Central band <b>${{formatValue(row.center, metricMeta[metric].format)}}</b></span>
          <span>Upper band <b>${{formatValue(row.upper, metricMeta[metric].format)}}</b></span>
          <span>Lower band <b>${{formatValue(row.lower, metricMeta[metric].format)}}</b></span>
          <span>Signal <b>${{signalLabel(row.signal)}}</b></span>
          ${{knownEvent ? `<span>Latest event <b>${{escapeHtml(knownEvent.label)}}</b></span>` : ""}}
          ${{explanation && ["above_band", "below_band"].includes(row.signal) ? `<span class="warning">Explained by known event window.</span>` : ""}}
          ${{cautionText ? `<span class="warning">${{cautionText}}</span>` : ""}}`;
      }};
      frame.querySelectorAll("[data-hover]").forEach((target) => {{
        target.addEventListener("pointerenter", (event) => {{
          tooltipNode.innerHTML = renderTooltip(target);
          tooltipNode.classList.add("visible");
          moveTooltip(event);
        }});
        target.addEventListener("pointermove", (event) => {{
          tooltipNode.innerHTML = renderTooltip(target);
          moveTooltip(event);
        }});
        target.addEventListener("pointerleave", hideTooltip);
      }});
      title.textContent = "SaaS Signals Board";
      renderMetricSummary(k);
      renderScenarioTabs();
    }}

    function renderScenarioTabs() {{
      profileTabsContainer.innerHTML = scenarios.map((scenario) => (
        `<button class="profile-tab${{scenario.id === profile ? " active" : ""}}" data-profile="${{scenario.id}}">${{scenario.label}} <span>k=${{scenario.k}}</span></button>`
      )).join("");
      profileTabsContainer.querySelectorAll(".profile-tab").forEach((tab) => {{
        tab.addEventListener("click", () => {{
          profile = tab.dataset.profile;
          updateChart();
        }});
      }});
    }}

    function renderScenarioInputs() {{
      const count = Math.max(1, Math.min(8, Number(scenarioCount.value) || scenarios.length));
      while (scenarios.length < count) {{
        const next = scenarios.length + 1;
        scenarios.push({{ id: `scenario_${{next}}`, label: `Scenario ${{next}}`, k: 1.25 }});
      }}
      scenarios = scenarios.slice(0, count);
      scenarioInputs.innerHTML = scenarios.map((scenario, index) => (
        `<div class="scenario-row">
          <label class="scenario-field"><span>Scenario name</span><input aria-label="Scenario ${{index + 1}} label" data-scenario-label="${{index}}" value="${{scenario.label}}"></label>
          <label class="scenario-field"><span>k value</span><input aria-label="Scenario ${{index + 1}} k value" data-scenario-k="${{index}}" type="number" min="0.1" max="5" step="0.05" value="${{scenario.k}}"></label>
        </div>`
      )).join("");
    }}

    metricTabs.forEach((tab) => {{
      tab.addEventListener("click", () => {{
        metricTabs.forEach((item) => item.classList.remove("active"));
        tab.classList.add("active");
        metric = tab.dataset.metric;
        updateChart();
      }});
    }});

    periodTabs.forEach((tab) => {{
      tab.addEventListener("click", () => {{
        periodTabs.forEach((item) => item.classList.remove("active"));
        tab.classList.add("active");
        period = tab.dataset.period;
        updateChart();
      }});
    }});

    applyPeriod.addEventListener("click", () => {{
      periodTabs.forEach((item) => item.classList.remove("active"));
      const customTab = document.querySelector('[data-period="custom"]');
      updateCustomPeriodLabel();
      if (customTab) customTab.classList.add("active");
      period = "custom";
      updateChart();
    }});

    customPeriodCount.addEventListener("keydown", (event) => {{
      if (event.key === "Enter") {{
        event.preventDefault();
        applyPeriod.click();
      }}
    }});

    frequencyTabs.forEach((tab) => {{
      tab.addEventListener("click", () => {{
        frequencyTabs.forEach((item) => item.classList.remove("active"));
        tab.classList.add("active");
        frequency = tab.dataset.frequency;
        updateChart();
      }});
    }});

    scenarioCount.addEventListener("change", renderScenarioInputs);
    applyScenarios.addEventListener("click", () => {{
      const labels = scenarioInputs.querySelectorAll("[data-scenario-label]");
      const values = scenarioInputs.querySelectorAll("[data-scenario-k]");
      scenarios = Array.from(labels).map((labelInput, index) => {{
        const label = labelInput.value.trim() || `Scenario ${{index + 1}}`;
        const kValue = Math.max(0.1, Number(values[index].value) || 1.25);
        return {{ id: `${{slugify(label)}}_${{index}}`, label, k: Number(kValue.toFixed(2)) }};
      }});
      profile = scenarios[0].id;
      updateChart();
    }});

    addEvent.addEventListener("click", () => {{
      const month = normalizeEventMonth(eventMonth.value);
      const label = eventLabel.value.trim();
      if (!month || !label) return;
      events.push({{
        id: `${{month}}_${{Date.now()}}`,
        month,
        label
      }});
      events = events.sort((a, b) => a.month.localeCompare(b.month));
      eventLabel.value = "";
      saveEvents();
      renderEvents();
      updateChart();
    }});

    eventLabel.addEventListener("keydown", (event) => {{
      if (event.key === "Enter") {{
        event.preventDefault();
        addEvent.click();
      }}
    }});

    renderScenarioInputs();
    renderEvents();
    updateChart();
  </script>
</body>
</html>
"""

    dashboard_path = output_dir / "dashboard.html"
    dashboard_path.write_text(dashboard, encoding="utf-8")
    return dashboard_path
