import os
import pandas as pd

BASE_PATH = "F:/Projects/AIModel/demo"
TRANS_DIR = os.path.join(BASE_PATH, "data", "Main_Tables", "transaction")
TRAN_FILE = os.path.join(TRANS_DIR, "transactions_updated_dates.xlsx")

# Load transaction data
trans = pd.read_excel(TRAN_FILE)

print("\n=== ALL COLUMNS IN TRANSACTION FILE ===")
print(list(trans.columns))

# Show unique values (in case of leading/trailing spaces or type mismatches)
print("\n=== UNIQUE VALUES: TRAN_CAT_CD ===")
print(trans['TRAN_CAT_CD'].unique())
print("=== UNIQUE VALUES: TRAN_CD ===")
print(trans['TRAN_CD'].unique())

# Try converting to numeric just in case
trans['TRAN_CAT_CD'] = pd.to_numeric(trans['TRAN_CAT_CD'], errors='coerce')
trans['TRAN_CD'] = pd.to_numeric(trans['TRAN_CD'], errors='coerce')

# Print how many rows are not NaN after conversion
print("\nCount non-null TRAN_CAT_CD:", trans['TRAN_CAT_CD'].notnull().sum())
print("Count non-null TRAN_CD:", trans['TRAN_CD'].notnull().sum())

# Filter for late payment fee transactions
late_payment = trans[(trans['TRAN_CAT_CD'] == 402) & (trans['TRAN_CD'] == 7)]

print(f"\n=== FOUND {len(late_payment)} LATE PAYMENT TRANSACTIONS ===")
if not late_payment.empty:
    print(late_payment[['ACCNT_ID', 'TRAN_CAT_CD', 'TRAN_CD', 'TRAN_AMT']].head(10))
else:
    print("No rows match TRAN_CAT_CD == 402 and TRAN_CD == 7")

# Extra: Show all unique pairs if you want to see what combinations really exist
print("\n=== UNIQUE (TRAN_CAT_CD, TRAN_CD) PAIRS ===")
print(trans[['TRAN_CAT_CD', 'TRAN_CD']].drop_duplicates().values.tolist())
