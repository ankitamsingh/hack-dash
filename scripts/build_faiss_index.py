import os
import pandas as pd
import faiss
import pickle
from datetime import datetime
from sentence_transformers import SentenceTransformer
import calendar

# === PATHS ===

BASE_DIR = "/app"
ACCOUNT_MAIN = os.path.join(BASE_DIR, "data", "Main_Tables", "account")
ACCOUNT_SUPPORT = os.path.join(BASE_DIR, "data", "Supporting_Tables", "account")
FAISS_OUT_DIR = os.path.join(BASE_DIR, "faiss_index")
os.makedirs(FAISS_OUT_DIR, exist_ok=True)
print("path="+ACCOUNT_MAIN)
# === LOAD CSVs ===
accnt_hdr = pd.read_csv(os.path.join(ACCOUNT_MAIN, "account_hdr.csv"))
accnt_party = pd.read_csv(os.path.join(ACCOUNT_MAIN, "accnt_party.csv"))
accnt_role = pd.read_csv(os.path.join(ACCOUNT_SUPPORT, "accnt_role_type_cd.csv"))
accnt_status = pd.read_csv(os.path.join(ACCOUNT_SUPPORT, "accnt_status_cd.csv"))
open_reason = pd.read_csv(os.path.join(ACCOUNT_SUPPORT, "account_open_reason_data.csv"))
close_reason = pd.read_csv(os.path.join(ACCOUNT_SUPPORT, "account_close_reasons_with_mod_user.csv"))
prtnr_cd = pd.read_csv(os.path.join(ACCOUNT_SUPPORT, "prtnr_cd.csv"))

# === Format Helper ===
def format_month_date(dt_obj):
    if pd.isnull(dt_obj):
        return "Unknown date"
    return f"{calendar.month_name[dt_obj.month]} {dt_obj.year}"

# === Clean Merges ===
open_reason = open_reason[["ACCNT_OPEN_REASON_CD_ID", "ACCNT_OPEN_REASON_DESC"]]
close_reason = close_reason[["ACCNT_CLOSE_REASON_CD_ID", "ACCNT_CLOSE_REASON_DESC"]]
accnt_status = accnt_status[["ACCNT_STATUS_CD_ID", "ACCNT_STATUS_DESC"]]
prtnr_cd = prtnr_cd[["PRTNR_CD_ID", "PRTNR_NAME"]]

hdr = accnt_hdr.merge(open_reason, on="ACCNT_OPEN_REASON_CD_ID", how="left")
hdr = hdr.merge(close_reason, on="ACCNT_CLOSE_REASON_CD_ID", how="left")
hdr = hdr.merge(accnt_status, on="ACCNT_STATUS_CD_ID", how="left")
hdr = hdr.merge(prtnr_cd, on="PRTNR_CD_ID", how="left")

# === Preprocess ===
hdr["ACCNT_OPEN_DT"] = pd.to_datetime(hdr["ACCNT_OPEN_DT"], errors="coerce")
hdr["ACCNT_CLOSE_DT"] = pd.to_datetime(hdr["ACCNT_CLOSE_DT"], errors="coerce")
hdr["LAST_LOGIN_DT"] = pd.to_datetime(hdr["LAST_LOGIN_DT"], errors="coerce")

# === Calculations ===
current_year = datetime.now().year
last_year = current_year - 1
cutoff_login = datetime(current_year - 2, 1, 1)
cutoff_str = format_month_date(cutoff_login)

total_accounts = len(hdr)
active_accounts = hdr[hdr["ACCNT_STATUS_DESC"] == "Valid Operating Account"]
opened_last_year = hdr[hdr["ACCNT_OPEN_DT"].dt.year == last_year]
closed_last_year = hdr[hdr["ACCNT_CLOSE_DT"].dt.year == last_year]
dormant_accounts = hdr[hdr["LAST_LOGIN_DT"] < cutoff_login]

# Grouping logic
party_counts = accnt_party.groupby("PARTY_ID")["ACCNT_ID"].nunique()
multi_acc = (party_counts > 1).sum()
multi_pct = (multi_acc / party_counts.nunique()) * 100

top_close = hdr["ACCNT_CLOSE_REASON_DESC"].value_counts(normalize=True).head(3)
top_open = hdr["ACCNT_OPEN_REASON_DESC"].value_counts(normalize=True).head(3)
top_partners = hdr["PRTNR_NAME"].value_counts(normalize=True).head(3)
status_dist = hdr["ACCNT_STATUS_DESC"].value_counts(normalize=True).head(5)

merged_roles = accnt_party.merge(accnt_role, on="ACCNT_ROLE_TYPE_CD_ID", how="left")
role_dist = merged_roles["ACCNT_ROLE_TYPE_DESC"].value_counts(normalize=True).head(3)

# === Monthly Open/Close for 2024 ===
hdr["open_year"] = hdr["ACCNT_OPEN_DT"].dt.year
hdr["open_month"] = hdr["ACCNT_OPEN_DT"].dt.month
hdr["close_year"] = hdr["ACCNT_CLOSE_DT"].dt.year
hdr["close_month"] = hdr["ACCNT_CLOSE_DT"].dt.month

open_2024 = hdr[hdr["open_year"] == 2024]
close_2024 = hdr[hdr["close_year"] == 2024]

monthly_open_summary = open_2024.groupby("open_month").size().reindex(range(1, 13), fill_value=0)
monthly_close_summary = close_2024.groupby("close_month").size().reindex(range(1, 13), fill_value=0)

monthly_open_summaries = [
    f"In {calendar.month_name[m]} 2024, {count} new accounts were opened (monthly onboarding)." for m, count in monthly_open_summary.items()
]

monthly_close_summaries = [
    f"In {calendar.month_name[m]} 2024, {count} accounts were closed (monthly attrition)." for m, count in monthly_close_summary.items()
]

# === Final Enhanced Summaries ===
summaries = [
    f"As of {current_year}, there are {len(active_accounts)} active accounts out of {total_accounts} total accounts in the system. Active accounts (currently in use, not closed, still functioning) are those marked as 'Valid Operating Account'. This represents {len(active_accounts)/total_accounts:.2%} of all accounts.",

    f"In {last_year}, a total of {len(opened_last_year)} new accounts were opened (new customer onboarding, reactivation, first-time applications). This accounts for {len(opened_last_year)/total_accounts:.2%} of all accounts.",

    f"During {last_year}, {len(closed_last_year)} accounts were closed (account closures, terminated accounts, deactivated). This represents {len(closed_last_year)/total_accounts:.2%} of the total account base.",

    f"As of {cutoff_str}, {len(dormant_accounts)} accounts are dormant (inactive, unused, no login activity) — no login has been recorded for over two years. This is {len(dormant_accounts)/total_accounts:.2%} of all accounts.",

    "Top 3 reasons for account closure (why users close accounts, offboarding reasons, closure insights): " +
    ", ".join([f"{reason} ({pct:.2%})" for reason, pct in top_close.items()]) + ".",

    "Most common account opening reasons (why accounts are opened, entry triggers, acquisition motives): " +
    ", ".join([f"{reason} ({pct:.2%})" for reason, pct in top_open.items()]) + ".",

    "Top partner brands issuing accounts (which bank/brand issued most accounts, co-branded issuers): " +
    ", ".join([f"{partner} ({pct:.2%})" for partner, pct in top_partners.items()]) + ".",

    "Distribution of account statuses (account lifecycle stages, operational status, account types): " +
    ", ".join([f"{status} ({pct:.2%})" for status, pct in status_dist.items()]) + ".",

    f"{multi_acc} users have more than one account linked (multi-account holders, duplicate account owners, stacked accounts). That’s {multi_pct:.2f}% of all customers.",

    "Most common roles for users on accounts (account party roles, user roles, ownership types): " +
    ", ".join([f"{role} ({pct:.2%})" for role, pct in role_dist.items()]) + "."
] + monthly_open_summaries + monthly_close_summaries

# === FAISS Index Build ===
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(summaries, convert_to_numpy=True)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, os.path.join(FAISS_OUT_DIR, "account_index.faiss"))
with open(os.path.join(FAISS_OUT_DIR, "account_metadata.pkl"), "wb") as f:
    pickle.dump(summaries, f)

print("✅ FAISS index for account domain rebuilt with enhanced summaries and month-level stats.")
