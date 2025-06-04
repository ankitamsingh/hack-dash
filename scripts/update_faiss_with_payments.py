import os
import pandas as pd
import faiss
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime

# === Paths ===
BASE_PATH = "F:/Projects/AIModel/demo"
PAYMENT_CSV = os.path.join(BASE_PATH, "data", "Main_Tables", "payment", "Internal-payment", "payment_movement_5000_full_records.xlsx")
STATUS_CD = os.path.join(BASE_PATH, "data", "Supporting_Tables", "payment", "Internal-payment", "money_mvmnt_status_cd.xlsx")
STATUS_REASON = os.path.join(BASE_PATH, "data", "Supporting_Tables", "payment", "Internal-payment", "money_mvmnt_status_reason_full.csv")
SUBSC_OPTN = os.path.join(BASE_PATH, "data", "Supporting_Tables", "payment", "Internal-payment", "money_mvmnt_subsc_optn_cd.xlsx")
TYPE_CD = os.path.join(BASE_PATH, "data", "Supporting_Tables", "payment", "Internal-payment", "money_mvmnt_type.xlsx")
INDEX_PATH = os.path.join(BASE_PATH, "faiss_index", "account_index.faiss")
META_PATH = os.path.join(BASE_PATH, "faiss_index", "account_metadata.pkl")

def month_name_format(date):
    try:
        dt = pd.to_datetime(date, dayfirst=True)
        return dt.strftime("%B %Y")
    except Exception:
        return "Unknown"

def load_mapping(df, key_col, val_col):
    df = df[[key_col, val_col]].dropna()
    return dict(zip(df[key_col], df[val_col]))

# Load mapping files
status_map = load_mapping(pd.read_excel(STATUS_CD), "MONEY_MVMNT_STATUS_CD_ID", "MONEY_MVMNT_STATUS_DESC")
reason_map = load_mapping(pd.read_csv(STATUS_REASON), "MNY_MVMNT_STATUS_REASON_CD_ID", "MNY_MVMNT_STATUS_REASON_DESC")
subsc_map = load_mapping(pd.read_excel(SUBSC_OPTN), "MONEY_MVMNT_SUBSC_OPTN_CD_ID", "MONEY_MVMNT_SUBSC_OPTN_DESC")
type_map = load_mapping(pd.read_excel(TYPE_CD), "MONEY_MVMNT_TYPE_ID", "MONEY_MVMNT_TYPE_DESC")

# Load and map payments data
df = pd.read_excel(PAYMENT_CSV)
df = df[df["AMT"].notna()]
df["STATUS_DESC"] = df["MONEY_MVMNT_STATUS_CD_ID"].map(status_map)
df["REASON_DESC"] = df["MNY_MVMNT_STATUS_REASON_CD_ID"].map(reason_map)
df["SUBSC_OPTN_DESC"] = df["MONEY_MVMNT_SUBSC_OPTN_CD_ID"].map(subsc_map)
df["TYPE_DESC"] = df["MVMNT_TYPE_CD_ID"].map(type_map)
df["MONTH"] = df["TRANS_TS"].apply(month_name_format)

summaries = []

# 1. Monthly total amounts
for month, g in df.groupby("MONTH"):
    amt = g["AMT"].sum()
    summaries.append(f"Total payments in {month}: ₹{amt:,.2f}.")

# 2. Type breakdown
for month, g in df.groupby("MONTH"):
    for t, tg in g.groupby("TYPE_DESC"):
        summaries.append(f"In {month}, {len(tg)} '{t}' payments were made, totaling ₹{tg['AMT'].sum():,.2f}.")

# 3. Status (success/failure) breakdown
for month, g in df.groupby("MONTH"):
    for status, sg in g.groupby("STATUS_DESC"):
        pct = len(sg) / len(g) * 100
        summaries.append(f"In {month}, there were {len(sg)} payments with status '{status}' ({pct:.1f}% of the month's total).")

# 4. Top 5 failure reasons
failures = df[df["STATUS_DESC"].str.contains("fail|unsuccess", case=False, na=False)]
for month, g in failures.groupby("MONTH"):
    reasons = g["REASON_DESC"].value_counts().head(5)
    for reason, count in reasons.items():
        summaries.append(f"Top failure reason in {month}: '{reason}' occurred {count} times.")

# 5. Subscription option breakdown
for month, g in df.groupby("MONTH"):
    for subsc, sg in g.groupby("SUBSC_OPTN_DESC"):
        summaries.append(f"{len(sg)} payments in {month} used subscription option '{subsc}'.")

# 6. Channel breakdown
for month, g in df.groupby("MONTH"):
    for chnl, cg in g.groupby("MONEY_MVMNT_CHNL_TYPE_CD_ID"):
        summaries.append(f"{len(cg)} payments in {month} were through channel code '{chnl}'.")

# 7. Enriched examples for search
for i, row in df.sample(min(25, len(df))).iterrows():
    summaries.append(
        f"In {row['MONTH']}, payment of ₹{row['AMT']:.2f} (type: {row['TYPE_DESC']}, status: {row['STATUS_DESC']}, sub: {row['SUBSC_OPTN_DESC']})"
        + (f" failed due to '{row['REASON_DESC']}'." if pd.notna(row['REASON_DESC']) and "fail" in str(row['STATUS_DESC']).lower() else "")
    )

# Append to FAISS
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(summaries, show_progress_bar=True)

index = faiss.read_index(INDEX_PATH)
with open(META_PATH, "rb") as f:
    metadata = pickle.load(f)

index.add(np.array(embeddings).astype("float32"))
metadata.extend(summaries)

faiss.write_index(index, INDEX_PATH)
with open(META_PATH, "wb") as f:
    pickle.dump(metadata, f)

print(f"✅ FAISS index updated with {len(summaries)} detailed payment summaries.")
