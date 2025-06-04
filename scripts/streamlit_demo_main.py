import os
import streamlit as st
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import pandas as pd

# === Paths ===
BASE_PATH = "F:/Projects/AIModel/demo"
INDEX_PATH = os.path.join(BASE_PATH, "faiss_index", "demo_main.faiss")
META_PATH = os.path.join(BASE_PATH, "faiss_index", "demo_main.pkl")

# === Load model, index, and metadata ===
@st.cache_resource
def load_index_and_metadata():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)
    return model, index, metadata

model, index, metadata = load_index_and_metadata()

# === Extract domains and tags for filtering ===
def parse_domain_tag(summary):
    domain = "unknown"
    tag = "unknown"
    if summary.startswith("[domain:"):
        parts = summary.split("]", 2)
        if len(parts) >= 2:
            domain_part = parts[0].split(":")[-1]
            tag_part = parts[1].split(":")[-1]
            domain = domain_part.replace("[domain:", "").replace("]", "").strip()
            tag = tag_part.replace("[tag:", "").replace("]", "").strip()
    return domain, tag

domains, tags = zip(*[parse_domain_tag(s) for s in metadata])
unique_domains = sorted(set(domains))
unique_tags = sorted(set(tags))

# === Streamlit UI ===
st.title("Demo Main FAISS Q&A Dashboard")
st.write("Ask questions related to payments, partners, statements, and more.")

query = st.text_input("Enter your business/statistics question:")

# Domain/Tag filtering
col1, col2 = st.columns(2)
domain_filter = col1.selectbox("Filter by domain", ["All"] + unique_domains)
tag_filter = col2.selectbox("Filter by tag", ["All"] + unique_tags)

top_k = st.slider("Number of top matches to show", min_value=1, max_value=10, value=5)

def extract_partner_breakdowns(summaries):
    """Return a list of (partner, value) if present in the summary string."""
    breakdowns = []
    for summary in summaries:
        # Example pattern: Partner 'X': 100 transactions, total value 10000.00.
        if "Partner '" in summary:
            try:
                parts = summary.split("Partner '")
                for p in parts[1:]:
                    pname = p.split("'")[0]
                    stats = p.split("': ", 1)[1].split(".")[0]
                    breakdowns.append((pname, stats))
            except Exception:
                continue
    return breakdowns

if query:
    # Encode and search
    qvec = model.encode([query])
    scores, idxs = index.search(qvec, top_k)
    matches = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx < 0 or idx >= len(metadata): continue
        summary = metadata[idx]
        domain, tag = parse_domain_tag(summary)
        if (domain_filter == "All" or domain == domain_filter) and (tag_filter == "All" or tag == tag_filter):
            matches.append((score, summary, domain, tag))
    st.markdown("### Top Results")
    if matches:
        for i, (score, summary, domain, tag) in enumerate(matches):
            st.write(f"**{i+1}. [Domain: `{domain}` | Tag: `{tag}` | Score: `{score:.2f}`]**")
            st.info(summary)
        # Partner breakdowns (if present)
        st.markdown("---")
        st.subheader("Partner Breakdowns")
        breakdowns = extract_partner_breakdowns([m[1] for m in matches])
        if breakdowns:
            bd_df = pd.DataFrame(breakdowns, columns=["Partner", "Details"])
            st.dataframe(bd_df)
        else:
            st.write("No partner breakdowns found in the current results.")
    else:
        st.warning("No matches found for this query/filters.")

    # Export option
    if matches:
        if st.button("Export results as CSV"):
            df_export = pd.DataFrame([{
                "score": s, "summary": sm, "domain": d, "tag": t
            } for (s, sm, d, t) in matches])
            st.download_button("Download CSV", df_export.to_csv(index=False), file_name="faiss_matches.csv")
else:
    st.info("Enter a query above to search business summaries.")
