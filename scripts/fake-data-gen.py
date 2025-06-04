import csv
import random
from datetime import datetime, timedelta
from faker import Faker
import pandas as pd

fake = Faker()

# Load reference CSVs
def load_reference_values(file_path):
    df = pd.read_csv(file_path)
    return df.iloc[:, 0].tolist()  # assuming ID is in the first column

# accnt_open_reasons = load_reference_values('D:/Projects/gen-ai-python/hackathon/data/GEN AI DATA/Supporting Tables/account_open_reason_data.csv')
# accnt_close_reasons = load_reference_values('D:/Projects/gen-ai-python/hackathon/data/GEN AI DATA/Supporting Tables/account_close_reasons_with_mod_user.csv')
# login_statuses = load_reference_values('D:/Projects/gen-ai-python/hackathon/data/GEN AI DATA/Supporting Tables/login_status_data.csv')
# accnt_statuses = load_reference_values('D:/Projects/gen-ai-python/hackathon/data/GEN AI DATA/Supporting Tables/accnt_status_cd.csv')
# partner_codes = load_reference_values("D:/Projects/gen-ai-python/hackathon/data/GEN AI DATA/Supporting Tables/prtnr_cd.csv")
# accnt_role_type = load_reference_values("D:/Projects/gen-ai-python/hackathon/data/GEN AI DATA/Supporting Tables/accnt_role_type_cd.csv")


accnt_open_reasons = ['Others','New Account','Replaced Card For Lost/Stolen','Product Change','Acquisition','Application','Account reopen','Re-open - bank error','Re-open - customer request','Others - No Email']
accnt_close_reasons = ['Others','Too Many Cards','Bank no longer supporting product','Annual Fee','Bank Policy','Deceased','Did Not Use','Interest Rate','Marital Status','Joint CC user remove primary request','Joint CC user remove Coapp request','Batch_close','Auto Actioned','Too Many Cards','Better Offer','Annual Fee','Deceased','Did Not Use','Interest Rate','Marital Status','Processing Error','Product Change','Terminated Employee','Unsatisfactory Service']
login_statuses = ['OK','FIRSTTIME','LOCKEDPW','LOCKEDFRAUD','TOBECHANGED','FORCERESET']
accnt_statuses = ['Valid Operating Account','Account Closed User Requested','Account Forced Closed by Juniper','Account Closed Lost/Stolen','Frozen Account','Fraudulent application','Acct Forced Closed No longer support BP product','Traded','Sold','Card is Mass Compromised']
partner_codes = ['AMAZON','FLIPKART','MYNTRA','SPICE JET','INDIGO','MAKE MY TRIP','BOOK MY SHOW','ONLY','OLA','UBER']
accnt_role_type = ['PRIMARY','AUTHORIZED','CO-APPLICANT','ACCOUNTANT','CUSTODIAN','ULMT_BNFCL_OWNR','CONTROLLER','CORPORATE_ENTITY','AUTH','BUSINESS_ADMIN']

# Track used IDs
used_accnt_ids = set()
used_party_ids = set()
used_accnt_party_ids = set()
used_login_ids = set()

# Define mappings
successful_tran_codes = {
    'successful payment': 'Payment transaction',
    'Transaction completed/Funds received from the vendor': 'Transaction',
    'Late Payment fee added to customer': 'Late Payment Fee'
}

returned_tran_codes = {
    'Payment not collected for the second return/time': 'Payment transaction',
    'Late Payment fee reversed by the bank on the customer account': 'Late Payment Fee',
    'Payment returned due to insufficient balance or account closed by the customer': 'Payment transaction',
    'transaction  failed': 'Transaction',
    'payment failed': 'Payment transaction'
}

# Helper for unique ID generation
def generate_unique_id(existing_set, digits=7):
    while True:
        val = random.randint(10**(digits-1), 10**digits - 1)
        if val not in existing_set:
            existing_set.add(val)
            return val


# Generate fake data for accnt_hdr
def generate_fake_accnt_hdr():
    accnt_id = generate_unique_id(used_accnt_ids, 7)
    open_dt = fake.date_between(start_date='-5y', end_date='today')
    close_dt = fake.date_between(start_date=open_dt, end_date='today') if random.choice([True, False]) else None

    return {
        'ACCNT_ID': accnt_id,
        'PRTNR_CD_ID': random.choice(partner_codes),
        'ACCNT_STATUS_CD_ID': random.choice(accnt_statuses),
        'LOGIN_STATUS_CD_ID': random.choice(login_statuses),
        'ACCNT_OPEN_DT': open_dt,
        'ACCNT_OPEN_REASON_CD_ID': random.choice(accnt_open_reasons),
        'ACCNT_CLOSE_DT': close_dt,
        'ACCNT_CLOSE_REASON_CD_ID': random.choice(accnt_close_reasons) if close_dt else None,
        'LAST_LOGIN_DT': fake.date_between(start_date=open_dt, end_date='today'),
        'LAST_UPDT_TS': fake.date_time_this_year(),
        'LAST_UPDT_USER': fake.user_name(),
        'INSRT_TS': fake.date_time_this_decade(),
        'INSRT_USER': fake.user_name(),
        'MOD_TS': fake.date_time_this_year(),
        'MOD_USER': fake.user_name(),
    }

# Generate accnt_party entry
def generate_fake_accnt_party(accnt_id, party_id):
    accnt_party_id = generate_unique_id(used_accnt_party_ids, 9)
    now = datetime.now()
    return {
        'ACCNT_PARTY_ID': accnt_party_id,
        'ACCNT_ID': accnt_id,
        'PARTY_ID': party_id,
        'ACCNT_ROLE_TYPE_CD_ID': random.choice(accnt_role_type),
        'ACCNT_NICK_NM': fake.first_name(),
        'INSRT_USER': fake.user_name(),
        'INSRT_TS': now,
        'UPDT_USER': fake.user_name(),
        'UPDT_TS': now
    }

# Generate sec_login entry
def generate_fake_sec_login(party_id):
    login_id = generate_unique_id(used_login_ids, 9)
    now = datetime.now()
    return {
        'LOGIN_ID': login_id,
        'PARTY_ID': party_id,
        'USER_ID_TX': fake.user_name(),
        'LAST_LOGIN_TS': fake.date_time_this_year(),
        'LOGIN_STATUS_CD_ID': random.choice(login_statuses),
        'RGSTR_TS': now,
        'INSRT_TS': now,
        'INSRT_USER': fake.user_name(),
        'MOD_TS': now,
        'MOD_USER': fake.user_name(),
        'PSWD': fake.sha256(),  # mock password, raw binary field
        'SRVCG_CHNL_CD': fake.random_element(elements=['WEB', 'MOB', 'API'])
    }


def generate_fake_transaction(accnt_id):
    now = datetime.now()
    three_months_ago = now - timedelta(days=90)
    one_year_ago = now - timedelta(days=365)
    tran_date = fake.date_between(start_date=one_year_ago, end_date=three_months_ago)
    tran_post_dt = tran_date + timedelta(days=random.randint(2, 10))
    status =  status = random.choice(['Successful', 'Returned'])
    tran_cd = ''
    tran_cat_cd = ''
    if status == 'Successful':
        tran_cd = random.choice(list(successful_tran_codes.keys()))
        tran_cat_cd = successful_tran_codes[tran_cd]
    elif status == 'Returned':
        tran_cd = random.choice(list(returned_tran_codes.keys()))
        tran_cat_cd = returned_tran_codes[tran_cd]

    return {
        'ACCT_ID': accnt_id,
        'MRCHNT_DBA_NM': fake.company(),
        'MRCHNT_CITY_NM': fake.city(),
        'MRCHNT_STATE_CD': fake.state_abbr(),
        'TRAN_POST_DT': tran_post_dt,
        'TRAN_DATE': tran_date,
        'TRAN_CD': tran_cd,
        'TRAN_CAT_CD': tran_cat_cd,
        'TRAN_DSPTE_FLAG': random.choice(['Y', 'N']),
        'TRAN_FRAUD_FLAG': random.choice(['Y', 'N']),
        'TRAN_AMT': round(random.uniform(1.0, 10000.0), 3),
        'INCHG_FEE': round(random.uniform(0.1, 50.0), 3),
        'DBR_CD_ID': random.choice(['D', 'C']),
        'Status': status,
        'Description': fake.sentence(nb_words=5),
        'ELECTRNC_PYMT_VALUE': random.choice(['Y', 'N'])
    }



# Write data to CSV
def write_to_csv(filename, data, fieldnames):
    with open(filename, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

# Main function
def generate_all_data(num_accounts):
    accnt_hdr_data = []
    accnt_party_data = []
    sec_login_data = []
    tran_dtl_data = []

    for _ in range(num_accounts):
        accnt = generate_fake_accnt_hdr()
        accnt_hdr_data.append(accnt)

        party_id = generate_unique_id(used_party_ids, 9)
        accnt_party_data.append(generate_fake_accnt_party(accnt['ACCNT_ID'], party_id))
        sec_login_data.append(generate_fake_sec_login(party_id))
        for _ in range(5):
            tran_dtl_data.append(generate_fake_transaction(accnt['ACCNT_ID']))

    write_to_csv('accnt_hdr_fake_data.csv', accnt_hdr_data, accnt_hdr_data[0].keys())
    write_to_csv('accnt_party_fake_data.csv', accnt_party_data, accnt_party_data[0].keys())
    write_to_csv('sec_login_fake_data.csv', sec_login_data, sec_login_data[0].keys())
    write_to_csv('tran_dtl_data_fake.csv', tran_dtl_data, tran_dtl_data[0].keys())

# Run generation
generate_all_data(20000)