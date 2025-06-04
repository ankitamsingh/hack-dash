import os
import pandas as pd
import numpy as np
import faiss
import pickle
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# === Paths ===
BASE_PATH = "F:/Projects/AIModel/demo"
PAYMENT_DIR = os.path.join(BASE_PATH, "data", "Main_Tables", "payment")
TRANS_DIR = os.path.join(BASE_PATH, "data", "Main_Tables", "transaction")
ACCNT_DIR = os.path.join(BASE_PATH, "data", "Main_Tables", "account")
SUPPORT_DIR_ACCNT = os.path.join(BASE_PATH, "data", "Supporting_Tables", "account")
SUPPORT_DIR_TRANS = os.path.join(BASE_PATH, "data", "Supporting_Tables", "transaction")

STMT_FILE = os.path.join(PAYMENT_DIR, "stmt_dtl_updated_consistent_dates.xlsx")
ACCNT_HDR_FILE = os.path.join(ACCNT_DIR, "account_hdr.csv")
PRTNR_FILE = os.path.join(SUPPORT_DIR_ACCNT, "prtnr_cd.csv")
TRAN_FILE = os.path.join(TRANS_DIR, "transactions_updated_dates.xlsx")
TRAN_CAT_FILE = os.path.join(SUPPORT_DIR_TRANS, "tran_cat_cd.csv")
TRAN_CD_FILE = os.path.join(SUPPORT_DIR_TRANS, "Tran_cd.csv")
ACCNT_DTL_FILE = os.path.join(PAYMENT_DIR, "accnt_dtl_mapped_from_stmt_fixed.xlsx")

INDEX_PATH = os.path.join(BASE_PATH, "faiss_index", "demo_main.faiss")
META_PATH = os.path.join(BASE_PATH, "faiss_index", "demo_main.pkl")

# === Load Data ===
stmt = pd.read_excel(STMT_FILE)
accnt = pd.read_csv(ACCNT_HDR_FILE) if ACCNT_HDR_FILE.endswith('.xlsx') else pd.read_csv(ACCNT_HDR_FILE)
prtnr = pd.read_csv(PRTNR_FILE)
trans = pd.read_excel(TRAN_FILE)
tran_cat = pd.read_csv(TRAN_CAT_FILE)
tran_cd = pd.read_csv(TRAN_CD_FILE)
accnt_dtl = pd.read_excel(ACCNT_DTL_FILE)

# -- Optional: Uncomment to debug actual columns
# print("tran_cat columns:", tran_cat.columns.tolist())
# print("tran_cd columns:", tran_cd.columns.tolist())
# print("accnt_dtl columns:", accnt_dtl.columns.tolist())
# print("accnt columns:", accnt.columns.tolist())
# print("prtnr columns:", prtnr.columns.tolist())
# print("trans columns:", trans.columns.tolist())
# print("stmt columns:", stmt.columns.tolist())

# === Merge & Prepare Mappings ===
accnt_map = accnt[["ACCNT_ID", "PRTNR_CD_ID"]]
prtnr_map = prtnr[["PRTNR_CD_ID", "PRTNR_NAME"]]
tran_cd_map = tran_cd.set_index('TRAN_CD')['Description'].to_dict()
tran_cat_map = tran_cat.set_index('TRAN_CAT_CD')['Description'].to_dict()
accnt_dtl_map = accnt_dtl[[
    "CIFDB_ACCT_ID", "PAST_DUE_1_30_AMT", "PAST_DUE_31_60_AMT", "PAST_DUE_61_90_AMT",
    "PAST_DUE_91_120_AMT", "PAST_DUE_121_150_AMT", "PAST_DUE_151_180_AMT"
]]

def get_partner_name(acc_id):
    pid = accnt_map.loc[accnt_map["ACCNT_ID"] == acc_id, "PRTNR_CD_ID"]
    if len(pid) == 0: return None
    pname = prtnr_map.loc[prtnr_map["PRTNR_CD_ID"] == pid.values[0], "PRTNR_NAME"]
    return pname.values[0] if len(pname) else None

# === Summaries List ===
summaries = []

### 1. What if late payment fees will be reduced by 8$ (or any X$)
late_payment = trans[
    (trans['TRAN_CAT_CD'] == 7) & (trans['TRAN_CD'] == 402)
]
late_payment_sum = late_payment.groupby("ACCNT_ID")["TRAN_AMT"].sum()
total_accounts = late_payment_sum.count()
orig_fee = late_payment_sum.sum()
new_fee = total_accounts * 8
loss = orig_fee - new_fee
summaries.append(
    f"[domain:what_if][tag:late_fee_reduction] If late payment fees are reduced to $8/account, for {total_accounts} accounts, "
    f"the old total was {orig_fee:.2f}, new would be {new_fee:.2f}, so revenue loss is {loss:.2f}."
)

### 2. What if one partner left—impact on late payment fees
late_payment_part = late_payment.merge(accnt_map, left_on='ACCNT_ID', right_on='ACCNT_ID')
late_payment_part = late_payment_part.merge(prtnr_map, left_on='PRTNR_CD_ID', right_on='PRTNR_CD_ID')
for partner, group in late_payment_part.groupby('PRTNR_NAME'):
    part_fee = group['TRAN_AMT'].sum()
    left_fee = orig_fee - part_fee
    summaries.append(
    f"[domain:what_if][tag:partner_leave] If partner '{partner}' leaves, the business will LOSE late fee revenue of ${part_fee:,.2f}. "
    f"Total late fee revenue will drop from ${orig_fee:,.2f} to ${left_fee:,.2f}."
)


### 3. Partner-wise transactions and payment
trans_p = trans.merge(accnt_map, left_on="ACCNT_ID", right_on="ACCNT_ID").merge(prtnr_map, left_on="PRTNR_CD_ID", right_on="PRTNR_CD_ID")
for partner, group in trans_p.groupby('PRTNR_NAME'):
    txn_count = group.shape[0]
    txn_amt = group["TRAN_AMT"].sum()
    summaries.append(
        f"[domain:partner][tag:partner_txn] Partner '{partner}': {txn_count} transactions, total value {txn_amt:.2f}."
    )

### 4. Statement balance from stmt_dtl_c partner-wise & total
stmt_part = stmt.merge(accnt_map, left_on='CIFDB_ACCT_ID', right_on='ACCNT_ID').merge(prtnr_map, left_on='PRTNR_CD_ID', right_on='PRTNR_CD_ID')
for partner, group in stmt_part.groupby('PRTNR_NAME'):
    total_bal = group['BAL_CURR_AMT'].sum()
    total_min_due = group['PAYMT_MIN_STMT_AMT'].sum()
    summaries.append(
        f"[domain:statement][tag:partner_stmt] Partner '{partner}': Statement balance {total_bal:.2f}, min due {total_min_due:.2f}."
    )
# Total
total_bal = stmt_part['BAL_CURR_AMT'].sum()
total_min_due = stmt_part['PAYMT_MIN_STMT_AMT'].sum()
summaries.append(
    f"[domain:statement][tag:total_stmt] All partners: Statement balance {total_bal:.2f}, min due {total_min_due:.2f}."
)

### 5. Partner-wise and total auto pay subscriptions and trends
if 'AUTO_PAY_SUBS' in accnt.columns:
    auto_pay_part = accnt.merge(prtnr_map, left_on='PRTNR_CD_ID', right_on='PRTNR_CD_ID')
    for partner, group in auto_pay_part.groupby('PRTNR_NAME'):
        auto_count = group['AUTO_PAY_SUBS'].sum()
        summaries.append(
            f"[domain:autopay][tag:partner_autopay] Partner '{partner}': {auto_count} auto-pay subscriptions."
        )
    summaries.append(
        f"[domain:autopay][tag:total_autopay] All partners: {auto_pay_part['AUTO_PAY_SUBS'].sum()} auto-pay subscriptions."
    )

### 6. Partner-wise and total overdue amount (accnt_dtl)
accnt_dtl_p = accnt_dtl.merge(accnt_map, left_on='CIFDB_ACCT_ID', right_on='ACCNT_ID').merge(prtnr_map, left_on='PRTNR_CD_ID', right_on='PRTNR_CD_ID')
for partner, group in accnt_dtl_p.groupby('PRTNR_NAME'):
    cols = [
        'PAST_DUE_1_30_AMT',
        'PAST_DUE_31_60_AMT',
        'PAST_DUE_61_90_AMT',
        'PAST_DUE_91_120_AMT',
        'PAST_DUE_121_150_AMT',
        'PAST_DUE_151_180_AMT'
    ]
    overdue = group[cols].sum().sum()
    summaries.append(
        f"[domain:overdue][tag:partner_overdue] Partner '{partner}': total overdue amount {overdue:.2f}."
    )
# Total
overdue = (
    accnt_dtl_p['PAST_DUE_1_30_AMT'].sum() +
    accnt_dtl_p['PAST_DUE_31_60_AMT'].sum() +
    accnt_dtl_p['PAST_DUE_61_90_AMT'].sum() +
    accnt_dtl_p['PAST_DUE_91_120_AMT'].sum() +
    accnt_dtl_p['PAST_DUE_121_150_AMT'].sum() +
    accnt_dtl_p['PAST_DUE_151_180_AMT'].sum()
)
summaries.append(
    f"[domain:overdue][tag:total_overdue] All partners: total overdue amount {overdue:.2f}."
)

### 7. Late payment fee revenue (with mapping)
latefee_txn = trans[
    (trans['TRAN_CAT_CD'] == 7) & (trans['TRAN_CD'] == 402)
].merge(accnt_map, left_on='ACCNT_ID', right_on='ACCNT_ID').merge(prtnr_map, left_on='PRTNR_CD_ID', right_on='PRTNR_CD_ID')
for partner, group in latefee_txn.groupby('PRTNR_NAME'):
    latefee_sum = group["TRAN_AMT"].sum()
    summaries.append(
        f"[domain:latefee][tag:latefee_rev] Partner '{partner}': late payment fee revenue {latefee_sum:.2f}."
    )
# Total
latefee_sum = latefee_txn["TRAN_AMT"].sum()
summaries.append(
    f"[domain:latefee][tag:total_latefee_rev] All partners: late payment fee revenue {latefee_sum:.2f}."
)
latefee_stats = {
    "total_accounts": int(total_accounts),
    "orig_fee": float(orig_fee),
    # Add partner breakdowns if needed
}
with open(os.path.join(BASE_PATH, "faiss_index", "latefee_stats.json"), "w") as f:
    import json
    json.dump(latefee_stats, f)
partner_fees = (
    late_payment_part.groupby('PRTNR_NAME')['TRAN_AMT']
    .sum()
    .sort_values(ascending=False)
    .to_dict()
)

latefee_stats = {
    "total_accounts": int(total_accounts),
    "orig_fee": float(orig_fee),
    "partner_fees": {k: float(v) for k, v in partner_fees.items()}
}

import json
with open(os.path.join(BASE_PATH, "faiss_index", "latefee_stats.json"), "w") as f:
    json.dump(latefee_stats, f, indent=2)    
# === Show example summaries ===
print("\nSample summaries:")
for s in summaries[:10]:
    print(s)

# === FAISS Embedding + Indexing ===
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(summaries, show_progress_bar=True)
dim = embeddings.shape[1]

if os.path.exists(INDEX_PATH):
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)
else:
    index = faiss.IndexFlatL2(dim)
    metadata = []

index.add(embeddings)
metadata.extend(summaries)

faiss.write_index(index, INDEX_PATH)
with open(META_PATH, "wb") as f:
    pickle.dump(metadata, f)

print(f"\n✅ {len(summaries)} business summaries added to: {INDEX_PATH}")
print(f"✅ Metadata saved to: {META_PATH}")
