import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from datetime import datetime

# === PATHS ===
BASE_PATH = "F:/Projects/AIModel/demo"
TRANSACTIONS_FILE = os.path.join(BASE_PATH, "data", "Main_Tables", "transaction", "transactions_updated_dates.xlsx")
TRAN_CAT_FILE = os.path.join(BASE_PATH, "data", "Supporting_Tables", "transaction", "tran_cat_cd.csv")
TRAN_CD_FILE = os.path.join(BASE_PATH, "data", "Supporting_Tables", "transaction", "Tran_cd.csv")

INDEX_PATH = os.path.join(BASE_PATH, "faiss_index", "account_index.faiss")
META_PATH = os.path.join(BASE_PATH, "faiss_index", "account_metadata.pkl")

# === LOAD DATA ===
df = pd.read_excel(TRANSACTIONS_FILE)
df_tran_cat = pd.read_csv(TRAN_CAT_FILE)
df_tran_cd = pd.read_csv(TRAN_CD_FILE)

# === COLUMN MAPS ===
cat_map = dict(zip(df_tran_cat['TRAN_CAT_CD'], df_tran_cat['Description']))
code_map = dict(zip(df_tran_cd['TRAN_CD'], df_tran_cd['Description']))

df['TRAN_CAT_DESC'] = df['TRAN_CAT_CD'].map(cat_map)
df['TRAN_TYPE_DESC'] = df['TRAN_CD'].map(code_map)

# === DATE HANDLING ===
def safe_parse_date(val):
    try:
        return pd.to_datetime(val)
    except Exception:
        return pd.NaT

df['TRAN_DATE'] = df['TRAN_DATE'].apply(safe_parse_date)
df['Month'] = df['TRAN_DATE'].dt.month
df['Year'] = df['TRAN_DATE'].dt.year
df['Month_Name'] = df['TRAN_DATE'].dt.strftime('%B')

# === MODEL ===
model = SentenceTransformer("all-MiniLM-L6-v2")

# === LOAD EXISTING FAISS INDEX ===
with open(META_PATH, "rb") as f:
    metadata = pickle.load(f)
index = faiss.read_index(INDEX_PATH)

# === SUMMARY GENERATION ===
summaries = []

total_txn = len(df)
total_amt = df['TRAN_AMT'].sum()
unique_accounts = df['ACCOUNT_ID'].nunique() if 'ACCOUNT_ID' in df.columns else None

# 1. General stats
summaries.append(f"Total transactions: {total_txn}.")
summaries.append(f"Total transaction amount: ₹{total_amt:,.2f}.")
if unique_accounts is not None:
    summaries.append(f"Unique accounts transacting: {unique_accounts}.")
summaries.append(f"Total card swipes: {total_txn}.")

# 2. Category/Type summaries
cat_sums = df.groupby('TRAN_CAT_DESC')['TRAN_AMT'].agg(['count', 'sum']).reset_index()
for _, row in cat_sums.iterrows():
    cat = str(row['TRAN_CAT_DESC'])
    summaries.append(
        f"Transactions in category '{cat}': {int(row['count'])} totaling ₹{row['sum']:.2f}."
        f" | {cat} transactions: {int(row['count'])} (alt: {cat.lower()} category)"
    )

type_sums = df.groupby('TRAN_TYPE_DESC')['TRAN_AMT'].agg(['count', 'sum']).reset_index()
for _, row in type_sums.iterrows():
    ttype = str(row['TRAN_TYPE_DESC'])
    summaries.append(
        f"Transaction type '{ttype}': {int(row['count'])} times, value ₹{row['sum']:.2f}."
        f" | {ttype} transactions: {int(row['count'])} (synonym: {ttype.lower()})"
    )

# 3. Month/Year summaries
monthly = df.groupby(['Year', 'Month', 'Month_Name'])['TRAN_AMT'].agg(['count', 'sum']).reset_index()
for _, row in monthly.iterrows():
    summaries.append(
        f"In {row['Month_Name']} {int(row['Year'])}, {int(row['count'])} transactions totaling ₹{row['sum']:.2f} occurred."
        f" | {row['count']} transactions in {row['Month_Name']} {int(row['Year'])}"
    )

yearly = df.groupby('Year')['TRAN_AMT'].agg(['count', 'sum']).reset_index()
for _, row in yearly.iterrows():
    summaries.append(
        f"In {int(row['Year'])}, {int(row['count'])} transactions with total value ₹{row['sum']:.2f}."
        f" | {row['count']} transactions in {int(row['Year'])}"
    )

# 4. Fraud summaries if available
if 'IS_FRAUD' in df.columns:
    fraud_count = df[df['IS_FRAUD'] == 1].shape[0]
    percent = (fraud_count / total_txn * 100) if total_txn else 0
    summaries.append(f"{fraud_count} transactions flagged as fraud ({percent:.2f}%).")
    fraud_month = df[df['IS_FRAUD'] == 1].groupby(['Year', 'Month_Name']).size().reset_index(name='Fraud_Count')
    for _, row in fraud_month.iterrows():
        summaries.append(
            f"In {row['Month_Name']} {int(row['Year'])}, {int(row['Fraud_Count'])} fraud transactions occurred."
        )

# 5. Merchant/City/State breakdowns if available
if 'MERCHANT_CITY' in df.columns:
    city_counts = df.groupby('MERCHANT_CITY').size().sort_values(ascending=False).head(10)
    for city, cnt in city_counts.items():
        summaries.append(f"Top merchant city: {city} ({cnt} transactions).")

if 'MERCHANT_STATE' in df.columns:
    state_counts = df.groupby('MERCHANT_STATE').size().sort_values(ascending=False).head(10)
    for state, cnt in state_counts.items():
        summaries.append(f"Top merchant state: {state} ({cnt} transactions).")

# 6. Large transactions/anomalies
if 'TRAN_AMT' in df.columns:
    high_value = df[df['TRAN_AMT'] > df['TRAN_AMT'].quantile(0.99)]
    for _, row in high_value.iterrows():
        amt = row['TRAN_AMT']
        date = row['TRAN_DATE']
        acct = row['ACCOUNT_ID'] if 'ACCOUNT_ID' in row else 'Unknown'
        summaries.append(
            f"High-value transaction: ₹{amt:,.2f} on {date.strftime('%d-%b-%Y') if pd.notna(date) else 'Unknown'}"
            f" (Account: {acct})"
        )

# 7. Example breakdowns for search coverage
summaries.append("What percent of transactions were fraud-flagged this year?")
summaries.append("Give a monthly breakdown of transaction value for 2024.")
summaries.append("Who are the top merchant cities and categories for transactions?")
summaries.append("How many online card transactions were made in March 2024?")
summaries.append("Show me high-value transactions above the 99th percentile.")

# === ENCODING AND APPEND TO INDEX ===
embeddings = model.encode(summaries, show_progress_bar=True, batch_size=32, normalize_embeddings=True)
embeddings = np.array(embeddings).astype('float32')

index.add(embeddings)
metadata.extend(summaries)

# Save back
faiss.write_index(index, INDEX_PATH)
with open(META_PATH, "wb") as f:
    pickle.dump(metadata, f)

print(f"✅ FAISS index updated with {len(summaries)} TRANSACTION summaries.")
