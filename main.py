#!/usr/bin/env python
# coding: utf-8

# In[1]:


from qalita_core.pack import Pack
import pandas as pd
import numpy as np

pack = Pack()

# --- Chargement des données (source = référence, target = actuel) ---
# Supporte database via table_or_query ou des fichiers (CSV/Parquet)
if pack.source_config.get("type") == "database":
    table_or_query = pack.source_config.get("config", {}).get("table_or_query")
    if not table_or_query:
        raise ValueError("For a 'database' type source, you must specify 'table_or_query' in the config.")
    pack.load_data("source", table_or_query=table_or_query)
else:
    pack.load_data("source")

if pack.target_config.get("type") == "database":
    table_or_query = pack.target_config.get("config", {}).get("table_or_query")
    if not table_or_query:
        raise ValueError("For a 'database' type target, you must specify 'table_or_query' in the config.")
    pack.load_data("target", table_or_query=table_or_query)
else:
    pack.load_data("target")

# Fonction utilitaire pour lire parquet si on passe un path
def _load_parquet_if_path(obj):
    try:
        if isinstance(obj, str) and obj.lower().endswith((".parquet", ".pq")):
            return pd.read_parquet(obj, engine="pyarrow")
    except Exception:
        pass
    return obj

ref_df = pack.df_source
cur_df = pack.df_target

# si pack.df_* est une liste (certains loaders renvoient une liste), on prend le premier élément
if isinstance(ref_df, list) or isinstance(cur_df, list):
    ref_df = _load_parquet_if_path(ref_df[0] if isinstance(ref_df, list) else ref_df)
    cur_df = _load_parquet_if_path(cur_df[0] if isinstance(cur_df, list) else cur_df)
else:
    ref_df = _load_parquet_if_path(ref_df)
    cur_df = _load_parquet_if_path(cur_df)

# --- Définitions des checks spécifiques au pack sales ---
# Colonnes attendues
expected_columns = ["order_id", "customer_id", "order_date", "amount", "status"]

# 1) Not-null checks sur colonnes essentielles
essential_cols = ["order_id", "customer_id", "order_date", "amount"]
for col in essential_cols:
    if col not in cur_df.columns:
        pack.metrics.data.append({
            "key": "missing_column",
            "value": f"{col} not present",
            "scope": {"perimeter": "dataset", "value": pack.target_config.get("name", "target")}
        })
        continue
    null_count = int(cur_df[col].isna().sum())
    pack.metrics.data.append({
        "key": "null_count",
        "value": str(null_count),
        "scope": {"perimeter": "column", "value": col, "parent_scope": {"perimeter": "dataset", "value": pack.target_config.get("name", "target")}}
    })

# 2) Montants positifs (amount > 0)
if "amount" in cur_df.columns:
    neg_amount_count = int((cur_df["amount"] <= 0).sum())
    pack.metrics.data.append({
        "key": "negative_amount_count",
        "value": str(neg_amount_count),
        "scope": {"perimeter": "column", "value": "amount", "parent_scope": {"perimeter": "dataset", "value": pack.target_config.get("name", "target")}}
    })

# 3) Statuts valides (Pending, Completed, Cancelled)
valid_statuses = {"Pending", "Completed", "Cancelled"}
if "status" in cur_df.columns:
    invalid_statuses = cur_df[~cur_df["status"].isin(valid_statuses)]["status"].dropna().unique().tolist()
    pack.metrics.data.append({
        "key": "invalid_status_values",
        "value": ", ".join(map(str, invalid_statuses)) if invalid_statuses else "none",
        "scope": {"perimeter": "column", "value": "status", "parent_scope": {"perimeter": "dataset", "value": pack.target_config.get("name", "target")}}
    })

# 4) Doublons sur order_id
if "order_id" in cur_df.columns:
    dup_count = int(cur_df.duplicated(subset=["order_id"]).sum())
    pack.metrics.data.append({
        "key": "duplicate_order_id_count",
        "value": str(dup_count),
        "scope": {"perimeter": "column", "value": "order_id", "parent_scope": {"perimeter": "dataset", "value": pack.target_config.get("name", "target")}}
    })

# 5) Simple "score" synthétique (exemple)
# On combine règles : si aucun null sur essential_cols, aucun montant <=0, aucun duplicat et aucun status invalide => score = 1
score_components = []
# null checks: consider passed if null_count == 0 for essential cols present
for col in essential_cols:
    if col in cur_df.columns:
        score_components.append(1.0 if int(cur_df[col].isna().sum()) == 0 else 0.0)
    else:
        score_components.append(0.0)

# amount positive
if "amount" in cur_df.columns:
    score_components.append(1.0 if (cur_df["amount"] > 0).all() else 0.0)
else:
    score_components.append(0.0)

# duplicates
if "order_id" in cur_df.columns:
    score_components.append(1.0 if dup_count == 0 else 0.0)
else:
    score_components.append(0.0)

# status
if "status" in cur_df.columns:
    score_components.append(1.0 if len(invalid_statuses) == 0 else 0.0)
else:
    score_components.append(0.0)

score = float(np.mean(score_components))
pack.metrics.data.append({
    "key": "score",
    "value": str(round(score, 2)),
    "scope": {"perimeter": "dataset", "value": pack.target_config.get("name", "target")}
})

# Sauvegarde des métriques
pack.metrics.save()


# In[ ]:




