from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

key = ""
endpoint = ""

# Authenticate client
credential = AzureKeyCredential(key)
client = TextAnalyticsClient(endpoint=endpoint, credential=credential)

# Sample text analysis
documents = ["She has served very bad service."]
response = client.analyze_sentiment(documents=documents)[0]

print("Sentiment:", response.sentiment)
