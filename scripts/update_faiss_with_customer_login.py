import os
import pandas as pd
import pickle
from sentence_transformers import SentenceTransformer
import faiss
from collections import defaultdict
from datetime import datetime

# === Paths ===
BASE_PATH = "/app"
LOGIN_CSV = os.path.join(BASE_PATH, "data", "Main_Tables", "customer-login", "customer_login.csv")
INDEX_PATH = os.path.join(BASE_PATH, "faiss_index", "account_index.faiss")
META_PATH = os.path.join(BASE_PATH, "faiss_index", "account_metadata.pkl")

# === Load Data ===
df = pd.read_csv(LOGIN_CSV)
df["LAST_LOGIN_TS"] = pd.to_datetime(df["LAST_LOGIN_TS"], errors="coerce")
df = df.dropna(subset=["LAST_LOGIN_TS"])

# === Status Code Mapping ===
status_map = {
    1: "Success",
    2: "Timed Out",
    3: "Invalid Password",
    4: "Locked due to Fraud",
    5: "Account Not Found",
    6: "Other Error"
}

# === Derived Fields ===
df["MONTH"] = df["LAST_LOGIN_TS"].dt.month
df["YEAR"] = df["LAST_LOGIN_TS"].dt.year
df["MONTH_NAME"] = df["LAST_LOGIN_TS"].dt.strftime('%B')
df["YEAR_MONTH"] = df["LAST_LOGIN_TS"].dt.strftime('%B %Y')
df["IS_FAILURE"] = df["LOGIN_STATUS_CD_ID"].isin([3, 4])

total_logins = len(df)
successful_logins = len(df[~df["IS_FAILURE"]])
failed_logins = len(df[df["IS_FAILURE"]])
failure_rate = (failed_logins / total_logins) * 100
success_rate = (successful_logins / total_logins) * 100

# === Channel Breakdown ===
channel_summary = df["SRVCG_CHNL_CD"].value_counts().to_dict()

# === Monthly Login Status ===
monthly_status_breakdown = defaultdict(lambda: defaultdict(int))
for _, row in df.iterrows():
    ym = row["YEAR_MONTH"]
    status = status_map.get(row["LOGIN_STATUS_CD_ID"], f"Status {row['LOGIN_STATUS_CD_ID']}")
    monthly_status_breakdown[ym][status] += 1

# === SentenceTransformer ===
model = SentenceTransformer('all-MiniLM-L6-v2')

# === Prepare Summaries ===
summaries = []
summaries.append(f"A total of {total_logins:,} login attempts were recorded. {successful_logins:,} were successful ({success_rate:.2f}%), and {failed_logins:,} failed ({failure_rate:.2f}%).")
summaries.append(f"{len(df.groupby('PARTY_ID')):,} unique users logged in during the observed period.")

chan_summary = ", ".join([f"{k}: {v}" for k, v in channel_summary.items()])
summaries.append(f"Login channel distribution — {chan_summary}.")

for month, statuses in sorted(monthly_status_breakdown.items()):
    status_text = ", ".join([f"{k}: {v}" for k, v in sorted(statuses.items())])
    summaries.append(f"In {month}, login status distribution — {status_text}.")

# === Load Existing Index ===
with open(META_PATH, "rb") as f:
    metadata = pickle.load(f)
index = faiss.read_index(INDEX_PATH)

# === Embed and Add ===
embeddings = model.encode(summaries)
index.add(embeddings)
metadata.extend(summaries)

# === Save Back ===
faiss.write_index(index, INDEX_PATH)
with open(META_PATH, "wb") as f:
    pickle.dump(metadata, f)

print("✅ Updated unified FAISS index with enhanced customer-login summaries.")
