from __future__ import annotations

import numpy as np
import pandas as pd

from saas_signal_bands.data import find_column


def _month_start(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.to_period("M").dt.to_timestamp()


def build_monthly_metrics(
    subscriptions: pd.DataFrame,
    churn_events: pd.DataFrame,
    gross_margin: float = 0.80,
) -> pd.DataFrame:
    subscription_id = find_column(
        subscriptions, ["subscription_id", "id", "sub_id"]
    )
    account_id = find_column(
        subscriptions, ["account_id", "customer_id", "account", "tenant_id"]
    )
    start_date = find_column(
        subscriptions, ["start_date", "subscription_start", "created_at", "signup_date"]
    )
    mrr = find_column(
        subscriptions,
        ["mrr", "mrr_amount", "monthly_recurring_revenue", "monthly_fee", "price"],
    )

    subs = subscriptions.copy()
    subs["_start_month"] = _month_start(subs[start_date])
    subs["_mrr"] = pd.to_numeric(subs[mrr], errors="coerce").fillna(0.0)
    if "end_date" in subs.columns:
        subs["_end_month"] = _month_start(subs["end_date"])
    else:
        subs["_end_month"] = pd.NaT

    churn = churn_events.copy()
    churn_subscription_col = None
    for candidate in ["subscription_id", "sub_id"]:
        if candidate in churn.columns:
            churn_subscription_col = candidate
            break

    churn_account_col = None
    for candidate in ["account_id", "customer_id", "account", "tenant_id"]:
        if candidate in churn.columns:
            churn_account_col = candidate
            break

    churn_date = find_column(
        churn, ["churn_date", "cancelled_at", "canceled_at", "event_date", "date"]
    )
    churn["_churn_month"] = _month_start(churn[churn_date])

    if churn_subscription_col:
        churn_keys = churn[[churn_subscription_col, "_churn_month"]].rename(
            columns={churn_subscription_col: subscription_id}
        )
        subs = subs.merge(churn_keys, on=subscription_id, how="left")
    elif churn_account_col:
        churn_keys = churn[[churn_account_col, "_churn_month"]].rename(
            columns={churn_account_col: account_id}
        )
        subs = subs.merge(churn_keys, on=account_id, how="left")
    else:
        subs["_churn_month"] = pd.NaT

    subs["_inactive_month"] = subs["_churn_month"].combine_first(subs["_end_month"])

    first_month = subs["_start_month"].min()
    last_month = max(
        subs["_start_month"].max(),
        subs["_inactive_month"].dropna().max()
        if subs["_inactive_month"].notna().any()
        else subs["_start_month"].max(),
    )
    months = pd.date_range(first_month, last_month, freq="MS")

    rows = []
    for month in months:
        active_mask = (subs["_start_month"] <= month) & (
            subs["_inactive_month"].isna() | (subs["_inactive_month"] > month)
        )
        starting_mask = (subs["_start_month"] < month) & (
            subs["_inactive_month"].isna() | (subs["_inactive_month"] >= month)
        )
        churned_mask = subs["_inactive_month"] == month

        active = subs.loc[active_mask]
        starting = subs.loc[starting_mask]
        churned = subs.loc[churned_mask]

        active_customers = active[account_id].nunique()
        starting_customers = starting[account_id].nunique()
        churned_customers = churned[account_id].nunique()
        new_customers = subs.loc[subs["_start_month"] == month, account_id].nunique()
        mrr_value = active["_mrr"].sum()
        starting_mrr = starting["_mrr"].sum()
        churned_mrr = churned["_mrr"].sum()

        customer_churn_rate = (
            churned_customers / starting_customers if starting_customers else np.nan
        )
        revenue_churn_rate = churned_mrr / starting_mrr if starting_mrr else np.nan
        arpu = mrr_value / active_customers if active_customers else np.nan
        ltv_raw = (
            arpu * gross_margin / customer_churn_rate
            if customer_churn_rate and customer_churn_rate > 0
            else np.nan
        )

        rows.append(
            {
                "month": month,
                "mrr": mrr_value,
                "arr": mrr_value * 12,
                "active_customers": active_customers,
                "starting_customers": starting_customers,
                "new_customers": new_customers,
                "net_customer_adds": new_customers - churned_customers,
                "arpu": arpu,
                "customer_churn_rate": customer_churn_rate,
                "revenue_churn_rate": revenue_churn_rate,
                "ltv_raw": ltv_raw,
                "churned_customers": churned_customers,
                "starting_mrr": starting_mrr,
                "churned_mrr": churned_mrr,
            }
        )

    metrics = pd.DataFrame(rows)
    metrics["mrr_growth_rate"] = metrics["mrr"].pct_change()
    metrics["arpu_growth_rate"] = metrics["arpu"].pct_change()
    metrics["active_customer_growth_rate"] = metrics["active_customers"].pct_change()
    metrics["customer_churn_caution"] = metrics["starting_customers"].fillna(0) < 20
    metrics["revenue_churn_caution"] = (
        (metrics["starting_mrr"].fillna(0) < 10_000)
        | (metrics["revenue_churn_rate"] > 1)
    )
    churn_smooth = metrics["customer_churn_rate"].rolling(window=6, min_periods=3).mean()
    metrics["customer_churn_rate_smoothed_6p"] = churn_smooth
    metrics["ltv"] = np.where(
        churn_smooth > 0,
        metrics["arpu"] * gross_margin / churn_smooth,
        np.nan,
    )
    metrics["ltv_caution"] = metrics["customer_churn_caution"] | churn_smooth.isna()
    metrics = metrics.replace([np.inf, -np.inf], np.nan)
    return metrics
