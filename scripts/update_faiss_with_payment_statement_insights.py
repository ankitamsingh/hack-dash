import os
import pandas as pd
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from datetime import datetime

# === Paths ===
BASE_PATH = "/app"
PAYMENT_CSV = os.path.join(BASE_PATH, "data", "Main_Tables", "payment", "internal-payment", "payment_movement_5000_full_records.xlsx")
STATEMENT_XLSX = os.path.join(BASE_PATH, "data", "Main_Tables", "payment", "stmt_dtl_updated_consistent_dates.xlsx")
ACCT_XLSX = os.path.join(BASE_PATH, "data", "Main_Tables", "payment", "accnt_dtl_mapped_from_stmt_fixed.xlsx")
INDEX_PATH = os.path.join(BASE_PATH, "faiss_index", "account_index.faiss")
META_PATH = os.path.join(BASE_PATH, "faiss_index", "account_metadata.pkl")

def month_name_format(date):
    try:
        dt = pd.to_datetime(date, dayfirst=True)
        return dt.strftime("%B %Y")
    except Exception:
        return "Unknown"

# 1. Load data
payments = pd.read_excel(PAYMENT_CSV)
statements = pd.read_excel(STATEMENT_XLSX)
accts = pd.read_excel(ACCT_XLSX)

# 2. Standardize and merge keys
payments["CIFDB_ACCT_ID"] = payments["ACCNT_ID"]
# statements and accts already have CIFDB_ACCT_ID
statements["STMT_MONTH"] = statements["STMT_CLOS_DT"].apply(month_name_format)
payments["MONTH"] = payments["TRANS_TS"].apply(month_name_format)

# 3. Merge for cross-domain analysis
# payments + statements (join on account + closest previous statement by date)
statements["STMT_CLOS_DT"] = pd.to_datetime(statements["STMT_CLOS_DT"], errors="coerce")
payments["TRANS_TS"] = pd.to_datetime(payments["TRANS_TS"], errors="coerce")
merged = pd.merge(payments, statements, on="CIFDB_ACCT_ID", suffixes=('', '_STMT'))

# Filter only payments that happened before or on the statement close date (per cycle)
merged = merged[merged["TRANS_TS"] <= merged["STMT_CLOS_DT"]]
# For each payment, keep only the latest statement close date before the payment
merged = merged.sort_values(["ACCNT_ID", "TRANS_TS", "STMT_CLOS_DT"])
merged = merged.groupby(["ACCNT_ID", "TRANS_TS"]).tail(1)

# Now join with account detail (accnt_dtl_mapped_from_stmt_fixed.xlsx)
merged = pd.merge(merged, accts, on="CIFDB_ACCT_ID", suffixes=('', '_ACCT'))

summaries = []
# --- 1. Overdue insights ---
for month, g in merged.groupby("STMT_MONTH"):
    overdue_accts = g[g.get("TOT_PAST_DUE_AMT", 0) > 0]["ACCNT_ID"].unique()
    overdue_count = len(overdue_accts)
    overdue_amt = g[g.get("TOT_PAST_DUE_AMT", 0) > 0]["TOT_PAST_DUE_AMT"].sum()
    paid_down = g[(g.get("TOT_PAST_DUE_AMT", 0) > 0) & (g["AMT"] >= g.get("TOT_PAST_DUE_AMT", 0))]
    paid_down_count = paid_down["ACCNT_ID"].nunique()
    summaries.append(f"In {month}, {overdue_count} accounts were overdue, total overdue amount ₹{overdue_amt:,.2f}.")
    summaries.append(f"In {month}, {paid_down_count} overdue accounts made a payment covering their total overdue.")
    summaries.append(f"{overdue_count - paid_down_count} accounts with overdue did not pay full overdue in {month}.")

# --- 2. Minimum due coverage ---
for month, g in merged.groupby("STMT_MONTH"):
    met_min_due = g[g["AMT"] >= g["PAYMT_MIN_STMT_AMT"]]
    pct_met_min_due = len(met_min_due) / len(g) * 100 if len(g) else 0
    summaries.append(f"In {month}, {len(met_min_due)} out of {len(g)} payments ({pct_met_min_due:.1f}%) covered at least the statement minimum due.")

# --- 3. Delinquency trends (consecutive missed) ---
delinquent = merged[(merged.get("CNSCTV_DAYS_PAST_DUE_CNT", 0) >= 30)]
for month, g in delinquent.groupby("STMT_MONTH"):
    summaries.append(f"In {month}, {len(g['ACCNT_ID'].unique())} accounts were delinquent for 30+ consecutive days.")

# --- 4. Behavior (good/on-time) ---
on_time = merged[merged.get("TOT_PAST_DUE_AMT", 0) == 0]
for month, g in on_time.groupby("STMT_MONTH"):
    summaries.append(f"In {month}, {len(g['ACCNT_ID'].unique())} accounts had no overdue and always paid on time.")

# --- 5. Channel/type impact on overdue ---
for (month, channel), g in merged.groupby(["STMT_MONTH", "MONEY_MVMNT_CHNL_TYPE_CD_ID"]):
    overdue_via_channel = g[g.get("TOT_PAST_DUE_AMT", 0) > 0]
    summaries.append(
        f"In {month}, channel '{channel}' processed {len(g)} payments; {len(overdue_via_channel)} were for overdue accounts."
    )

# --- 6. Accounts closed after failing to pay min due ---
closed = merged[merged.get("CHARGEOFF_DT", "").notnull()]
failed_to_pay = closed[closed["AMT"] < closed["PAYMT_MIN_STMT_AMT"]]
for month, g in failed_to_pay.groupby("STMT_MONTH"):
    summaries.append(
        f"In {month}, {len(g['ACCNT_ID'].unique())} accounts were charged off after failing to pay their minimum due."
    )

# --- 7. Example phrases / synonyms for search variety ---
for i, row in merged.sample(min(25, len(merged)), random_state=42).iterrows():
    s = (
        f"On {row['TRANS_TS'].strftime('%d %b %Y')}, account {row['ACCNT_ID']} paid ₹{row['AMT']:.2f} "
        f"(statement min due: ₹{row['PAYMT_MIN_STMT_AMT']:.2f}, overdue: ₹{row.get('TOT_PAST_DUE_AMT', 0):.2f})."
    )
    if row.get('TOT_PAST_DUE_AMT', 0) > 0:
        s += " Payment was towards overdue."
    if row['AMT'] >= row['PAYMT_MIN_STMT_AMT']:
        s += " Payment covered minimum due."
    else:
        s += " Payment did not cover minimum due."
    summaries.append(s)
    # Variant
    summaries.append(
        f"Account {row['ACCNT_ID']} paid on {row['TRANS_TS'].strftime('%d-%m-%Y')}. Was overdue: {row.get('TOT_PAST_DUE_AMT', 0) > 0}, Paid at least min due: {row['AMT'] >= row['PAYMT_MIN_STMT_AMT']}."
    )

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

print(f"✅ FAISS index updated with {len(summaries)} payment+statement+account insights.")
