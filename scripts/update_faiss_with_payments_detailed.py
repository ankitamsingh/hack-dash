import os
import pandas as pd
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

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

def week_of_year(date):
    try:
        dt = pd.to_datetime(date, dayfirst=True)
        return f"Week {dt.isocalendar()[1]} of {dt.year}"
    except Exception:
        return "Unknown"

def load_mapping(df, key_col, val_col):
    df = df[[key_col, val_col]].dropna()
    return dict(zip(df[key_col], df[val_col]))

# === Load Mapping Tables ===
status_map = load_mapping(pd.read_excel(STATUS_CD), "MONEY_MVMNT_STATUS_CD_ID", "MONEY_MVMNT_STATUS_DESC")
reason_map = load_mapping(pd.read_csv(STATUS_REASON), "MNY_MVMNT_STATUS_REASON_CD_ID", "MNY_MVMNT_STATUS_REASON_DESC")
subsc_map = load_mapping(pd.read_excel(SUBSC_OPTN), "MONEY_MVMNT_SUBSC_OPTN_CD_ID", "MONEY_MVMNT_SUBSC_OPTN_DESC")
type_map = load_mapping(pd.read_excel(TYPE_CD), "MONEY_MVMNT_TYPE_ID", "MONEY_MVMNT_TYPE_DESC")

# === Load Payment Data ===
df = pd.read_excel(PAYMENT_CSV)
df = df[df["AMT"].notna()]
df["STATUS_DESC"] = df["MONEY_MVMNT_STATUS_CD_ID"].map(status_map)
df["REASON_DESC"] = df["MNY_MVMNT_STATUS_REASON_CD_ID"].map(reason_map)
df["SUBSC_OPTN_DESC"] = df["MONEY_MVMNT_SUBSC_OPTN_CD_ID"].map(subsc_map)
df["TYPE_DESC"] = df["MVMNT_TYPE_CD_ID"].map(type_map)
df["MONTH"] = df["TRANS_TS"].apply(month_name_format)
df["WEEK"] = df["TRANS_TS"].apply(week_of_year)
df["DATE"] = pd.to_datetime(df["TRANS_TS"], dayfirst=True, errors="coerce")

summaries = []
today = df["DATE"].max()

# --- 1. Monthly Totals, Failures, Successes (with synonym/variant phrasing)
for month, g in df.groupby("MONTH"):
    total = g["AMT"].sum()
    success = g[g["STATUS_DESC"].str.contains("success", case=False, na=False)]
    failure = g[g["STATUS_DESC"].str.contains("fail|unsuccess|decline", case=False, na=False)]
    fail_pct = (len(failure) / len(g) * 100) if len(g) else 0
    summaries.append(f"Total payments in {month}: ₹{total:,.2f} ({len(g)} transactions).")
    summaries.append(f"In {month}, {len(success)} payments succeeded and {len(failure)} failed. Failure rate: {fail_pct:.1f}%.")
    summaries.append(f"In {month}, the number of declined or unsuccessful payments was {len(failure)} out of {len(g)} total.")

# --- 2. Trend Analysis (month-over-month changes)
months = sorted(df["MONTH"].dropna().unique(), key=lambda x: datetime.strptime(x, "%B %Y"))
for i in range(1, len(months)):
    this_month = months[i]
    last_month = months[i-1]
    this_g = df[df["MONTH"] == this_month]
    last_g = df[df["MONTH"] == last_month]
    this_fail = this_g[this_g["STATUS_DESC"].str.contains("fail|unsuccess|decline", case=False, na=False)]
    last_fail = last_g[last_g["STATUS_DESC"].str.contains("fail|unsuccess|decline", case=False, na=False)]
    change = len(this_fail) - len(last_fail)
    change_pct = (change / len(last_fail) * 100) if len(last_fail) else 0
    if change > 0:
        summaries.append(f"Failed payments increased by {change} ({change_pct:.1f}%) in {this_month} compared to {last_month}.")
    elif change < 0:
        summaries.append(f"Failed payments decreased by {abs(change)} ({abs(change_pct):.1f}%) in {this_month} compared to {last_month}.")
    else:
        summaries.append(f"Failed payments remained steady from {last_month} to {this_month}.")

# --- 3. Weekly and Daily Summaries (if data covers >1 month)
if (df["DATE"].max() - df["DATE"].min()).days > 31:
    for week, g in df.groupby("WEEK"):
        summaries.append(f"In {week}, {len(g)} payments were processed totaling ₹{g['AMT'].sum():,.2f}.")
        fails = g[g["STATUS_DESC"].str.contains("fail|unsuccess|decline", case=False, na=False)]
        summaries.append(f"{len(fails)} failed (declined) in {week}.")
    # Last-7-days
    last7 = df[df["DATE"] >= (today - timedelta(days=7))]
    if not last7.empty:
        summaries.append(f"In the last 7 days, {len(last7)} payments (₹{last7['AMT'].sum():,.2f}) processed; {len(last7[last7['STATUS_DESC'].str.contains('fail|unsuccess|decline', case=False, na=False)])} failed.")

# --- 4. Breakdown by Party/Account
for (month, accnt), g in df.groupby(["MONTH", "ACCNT_ID"]):
    summaries.append(f"In {month}, account {accnt} had {len(g)} payments totaling ₹{g['AMT'].sum():,.2f}.")

for (month, party), g in df.groupby(["MONTH", "PARTY_ID"]):
    summaries.append(f"In {month}, party {party} processed {len(g)} payments totaling ₹{g['AMT'].sum():,.2f}.")

# --- 5. Payment Type, Subscription Option, Channel breakdowns
for (month, t), g in df.groupby(["MONTH", "TYPE_DESC"]):
    summaries.append(f"In {month}, {len(g)} payments were '{t}' type (₹{g['AMT'].sum():,.2f}).")
    # Synonyms
    summaries.append(f"{len(g)} transactions classified as '{t}' in {month}.")
for (month, subsc), g in df.groupby(["MONTH", "SUBSC_OPTN_DESC"]):
    summaries.append(f"{len(g)} payments in {month} used the '{subsc}' subscription option.")
    summaries.append(f"Subscription mode '{subsc}' was selected {len(g)} times in {month}.")
for (month, chnl), g in df.groupby(["MONTH", "MONEY_MVMNT_CHNL_TYPE_CD_ID"]):
    summaries.append(f"{len(g)} payments in {month} were processed via channel code '{chnl}'.")
    summaries.append(f"Channel '{chnl}' handled {len(g)} transactions in {month}.")

# --- 6. Top Failure Reasons per Month (with alternate phrasing)
failures = df[df["STATUS_DESC"].str.contains("fail|unsuccess|decline", case=False, na=False)]
for month, g in failures.groupby("MONTH"):
    top5 = g["REASON_DESC"].value_counts().head(5)
    for reason, count in top5.items():
        summaries.append(f"In {month}, top failure reason: '{reason}' ({count} times).")
        summaries.append(f"{count} payments failed due to '{reason}' in {month}.")
        summaries.append(f"Failure reason '{reason}' was a leading cause in {month} ({count} failed).")

# --- 7. Enriched Example Summaries
for i, row in df.sample(min(30, len(df)), random_state=42).iterrows():
    s = (
        f"On {row['DATE'].strftime('%d %b %Y')}, payment of ₹{row['AMT']:.2f} (type: {row['TYPE_DESC']}, status: {row['STATUS_DESC']}, "
        f"sub: {row['SUBSC_OPTN_DESC']}, channel: {row['MONEY_MVMNT_CHNL_TYPE_CD_ID']})"
    )
    if pd.notna(row['REASON_DESC']) and "fail" in str(row['STATUS_DESC']).lower():
        s += f" failed due to '{row['REASON_DESC']}'."
    summaries.append(s)
    # Alternate
    s2 = (
        f"{row['DATE'].strftime('%B %Y')}: {row['STATUS_DESC']} payment, type '{row['TYPE_DESC']}', account {row['ACCNT_ID']}, amount ₹{row['AMT']:.2f}."
    )
    summaries.append(s2)

# === FAISS Append ===
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

print(f"✅ FAISS index updated with {len(summaries)} DETAILED and ENRICHED payment summaries.")
