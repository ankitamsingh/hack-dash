import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

# === CONFIG ===
DEBUG = True
USE_FLAN_CLEANING = True  # Toggle this to turn FLAN rephrasing on/off

# === PATHS ===
BASE_DIR = "/app"
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "faiss_index", "account_index.faiss")
FAISS_META_PATH = os.path.join(BASE_DIR, "faiss_index", "account_metadata.pkl")

# === LOAD MODELS ===
print("🔁 Loading SentenceTransformer...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

if USE_FLAN_CLEANING:
    print("✨ Loading FLAN-T5 for optional answer rephrasing...")
    flan_model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")
    flan_tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
    flan_pipeline = pipeline("text2text-generation", model=flan_model, tokenizer=flan_tokenizer)

# === LOAD FAISS INDEX & METADATA ===
print("📦 Loading FAISS index...")
index = faiss.read_index(FAISS_INDEX_PATH)
with open(FAISS_META_PATH, "rb") as f:
    summaries = pickle.load(f)

def query_account_qa(user_query: str, top_k: int = 5):
    embedding = embed_model.encode([user_query])
    D, I = index.search(np.array(embedding), top_k)
    results = []
    for idx, dist in zip(I[0], D[0]):
        results.append({
            "match_score": float(dist),
            "summary": summaries[idx]
        })
    top_result = results[0]["summary"]
    if USE_FLAN_CLEANING:
        prompt = f"Rephrase clearly and professionally without changing the meaning: {top_result}"
        rephrased = flan_pipeline(prompt, max_length=128, do_sample=False)[0]["generated_text"]
        results[0]["summary"] = rephrased.strip()
    return {
        "original_query": user_query,
        "top_matches": results
    }

# === DEBUG TEST QUERIES ===
if DEBUG:
    test_queries = [
        # Account & General
        "How many accounts are active?",
        "How many users opened an account last year?",
        "What are the top reasons accounts are closed?",
        "Which partner issued the most accounts?",
        "How many accounts are dormant?",
        "What are the most common account statuses?",
        "How many people have multiple accounts?",
        "When did most users last log in?",
        "What are the most common roles for parties on accounts?",
        "How many accounts were closed in 2024?",

        # Customer-login insights
        "What is the overall login success rate?",
        "How many first-time logins occurred?",
        "How many users failed to login due to wrong password?",
        "Which login channel is used most?",
        "How many logins happened in January 2024?",
        "What is the login trend over 2024?",
        "Did login activity increase after March 2024?",
        "Are mobile logins more frequent than web?",
        "Was there any login failure recorded?",

        # Payments + Statements + Account detail (cross-domain)
        "How many accounts were overdue last month?",
        "How much was the total overdue amount in June 2024?",
        "How many overdue accounts made a payment last month?",
        "How many payments covered at least the minimum due on statement?",
        "What percent of payments covered the minimum due in July 2024?",
        "How many accounts were delinquent for more than 30 days in June 2024?",
        "How many accounts paid on time every cycle in 2024?",
        "Which payment channel had the most overdue settlements?",
        "How many accounts were charged off after failing to pay their minimum due?",
        "Give an example of a payment that did not cover the minimum due.",
        "Which accounts regularly pay less than the minimum due?",
        "Which accounts recovered from overdue in the last quarter?",
        "Which payment type is most common for overdue settlements?",
        "Are payments more likely to cover the minimum due via API or MOB channels?",
        "How many accounts became active after payment in the last quarter?",
        "How often do customers pay late versus on time?",
        "Did failed payments increase compared to last month?",

        # Transaction analytics
        "What is the total transaction amount for March 2025?",
        "Which transaction category is most common in 2024?",
        "How many transactions were completed via API in May 2025?",
        "List top 5 transaction categories by volume in 2024.",
        "What percent of all transactions were failed in June 2024?",
        "Which accounts had the highest transaction value last quarter?",
        "How many unique parties made transactions in April 2025?",
        "What was the average transaction size last month?",
        "Which transaction type had the most failures this year?",
        "Are WEB transactions increasing month over month?",
        "List all accounts with transactions above ₹10,000 in February 2025.",
    ]

    print("\n🔍 Running test queries across all domains:")
    for query in test_queries:
        result = query_account_qa(query)
        print("\n===================================")
        print("🔸 Original Query:", result["original_query"])
        for i, r in enumerate(result["top_matches"]):
            domain = r.get("domain", "N/A")
            print(f"\n🔹 Match {i+1} (Score: {r['match_score']:.2f}) [Domain: {domain}]:")
            print(r["summary"])


# === CLI MODE ===
if not DEBUG:
    while True:
        user_input = input("💬 Enter your query (or type 'exit'): ")
        if user_input.lower() in ["exit", "quit"]:
            break
        result = query_account_qa(user_input)
        print("\n🔸 Original Query:", result["original_query"])
        for i, r in enumerate(result["top_matches"]):
            print(f"\n🔹 Match {i+1} (Score: {r['match_score']:.2f}):")
            print(r["summary"])
