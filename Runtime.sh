#!/bin/bash
echo "installing python packages"
pip install --no-cache-dir faiss-gpu faiss-cpu numpy pandas sentence-transformers tqdm transformers FastAPI Flask Streamlit openpyxl matplotlib SpeechRecognition

echo "Starting gen ai"
exec streamlit run main.py --server.port=8501 --server.enableCORS=false
