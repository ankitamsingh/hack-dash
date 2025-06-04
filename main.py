# main.py
import subprocess

scripts = [
    "scripts/build_faiss_index.py",
    "scripts/update_faiss_with_customer_login.py",
    "scripts/update_faiss_with_payments.py",
    "scripts/update_faiss_with_payments_detailed.py",
    "scripts/query_with_model.py"
]

for script in scripts:
    print(f"Running {script}...")
    subprocess.run(["python", script], check=True)
