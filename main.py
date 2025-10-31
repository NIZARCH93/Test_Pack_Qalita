#!/usr/bin/env python3
# coding: utf-8
"""Pack QALITA : contrôles qualité simples sur des données de ventes."""

from __future__ import annotations

from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd
from qalita_core.pack import Pack

EXPECTED_COLUMNS: Iterable[str] = [
    "order_id",
    "customer_id",
    "order_date",
    "amount",
    "status",
]
ESSENTIAL_COLUMNS: Iterable[str] = ["order_id", "customer_id", "order_date", "amount"]
VALID_STATUSES = {"Pending", "Completed", "Cancelled"}

pack = Pack()


def _normalise_dataframe(data: Any) -> pd.DataFrame:
    """Transforme la donnée renvoyée par QALITA en DataFrame pandas."""
    if isinstance(data, list) and data:
        data = data[0]

    if isinstance(data, str):
        lower = data.lower()
        if lower.endswith((".parquet", ".pq")):
            return pd.read_parquet(data, engine="pyarrow")
        if lower.endswith(".csv"):
            return pd.read_csv(data)

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if data is None:
        return pd.DataFrame()

    try:
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def _load_dataframe(role: str) -> pd.DataFrame:
    """Charge un DataFrame via l'API Pack de QALITA."""
    config: Dict[str, Any] = getattr(pack, f"{role}_config", None) or {}
    if not config:
        return pd.DataFrame()

    if config.get("type") == "database":
        table_or_query = config.get("config", {}).get("table_or_query")
        if not table_or_query:
            raise ValueError(
                f"For a 'database' type {role}, you must specify 'table_or_query' in the config."
            )
        pack.load_data(role, table_or_query=table_or_query)
    else:
        pack.load_data(role)

    return _normalise_dataframe(getattr(pack, f"df_{role}"))


def _dataset_scope(dataset_name: str) -> Dict[str, Any]:
    return {"perimeter": "dataset", "value": dataset_name}


def _column_scope(dataset_name: str, column: str) -> Dict[str, Any]:
    return {
        "perimeter": "column",
        "value": column,
        "parent_scope": _dataset_scope(dataset_name),
    }


def _add_metric(key: str, value: str, scope: Dict[str, Any]) -> None:
    pack.metrics.data.append({"key": key, "value": value, "scope": scope})


reference_df = _load_dataframe("source")
current_df = _load_dataframe("target")

# Normalise également si QALITA a directement fourni les dataframes
reference_df = _normalise_dataframe(reference_df)
current_df = _normalise_dataframe(current_df)

target_name = (pack.target_config or {}).get("name", "target")
dataset_scope = _dataset_scope(target_name)

_add_metric("row_count", str(len(current_df)), dataset_scope)

expected_missing = sorted(set(EXPECTED_COLUMNS) - set(current_df.columns))
_add_metric(
    "missing_expected_columns",
    ", ".join(expected_missing) if expected_missing else "none",
    dataset_scope,
)

for column in ESSENTIAL_COLUMNS:
    if column not in current_df.columns:
        _add_metric(
            "missing_column",
            f"{column} not present",
            dataset_scope,
        )
        continue

    null_count = int(current_df[column].isna().sum())
    _add_metric("null_count", str(null_count), _column_scope(target_name, column))

neg_amount_count = 0
if "amount" in current_df.columns:
    neg_amount_count = int((current_df["amount"] <= 0).sum())
    _add_metric(
        "non_positive_amount_count",
        str(neg_amount_count),
        _column_scope(target_name, "amount"),
    )

invalid_statuses: Iterable[str] = []
if "status" in current_df.columns:
    invalid = current_df.loc[~current_df["status"].isin(VALID_STATUSES), "status"].dropna().unique()
    invalid_statuses = sorted(map(str, invalid))
    _add_metric(
        "invalid_status_values",
        ", ".join(invalid_statuses) if invalid_statuses else "none",
        _column_scope(target_name, "status"),
    )

duplicate_order_count = 0
if "order_id" in current_df.columns:
    duplicate_order_count = int(current_df.duplicated(subset=["order_id"]).sum())
    _add_metric(
        "duplicate_order_id_count",
        str(duplicate_order_count),
        _column_scope(target_name, "order_id"),
    )

if not reference_df.empty:
    _add_metric(
        "row_count_delta_vs_reference",
        str(len(current_df) - len(reference_df)),
        dataset_scope,
    )

    if "order_id" in current_df.columns and "order_id" in reference_df.columns:
        current_ids = set(current_df["order_id"].dropna().astype(str))
        reference_ids = set(reference_df["order_id"].dropna().astype(str))
        new_orders = sorted(current_ids - reference_ids)
        missing_orders = sorted(reference_ids - current_ids)
        _add_metric(
            "new_order_ids",
            ", ".join(new_orders) if new_orders else "none",
            dataset_scope,
        )
        _add_metric(
            "missing_order_ids",
            ", ".join(missing_orders) if missing_orders else "none",
            dataset_scope,
        )

score_components = []
for column in ESSENTIAL_COLUMNS:
    if column in current_df.columns:
        score_components.append(1.0 if int(current_df[column].isna().sum()) == 0 else 0.0)
    else:
        score_components.append(0.0)

if "amount" in current_df.columns:
    score_components.append(1.0 if (current_df["amount"] > 0).all() else 0.0)
else:
    score_components.append(0.0)

if "order_id" in current_df.columns:
    score_components.append(1.0 if duplicate_order_count == 0 else 0.0)
else:
    score_components.append(0.0)

if "status" in current_df.columns:
    score_components.append(1.0 if not invalid_statuses else 0.0)
else:
    score_components.append(0.0)

score = float(np.mean(score_components)) if score_components else 0.0
_add_metric("score", str(round(score, 2)), dataset_scope)

pack.metrics.save()
