import pandas as pd
import openai
from openai import OpenAI

# Load your CSV
df = pd.read_csv("C:/gen ai/test-csv.csv")

# Convert the DataFrame to a string (small preview only)
data_preview = df.head(10).to_string(index=False)

# Question to ask
user_question = "What is the average monthly charge?"

# Build prompt
prompt = f"""
You are a data analyst. Here's the dataset:

{data_preview}

Now answer this question: {user_question}
"""

# Call OpenAI (use your API key or Azure OpenAI endpoint)
# openai.api_key = ""
# response = openai.ChatCompletion.create(
#   model="gpt-4",
#   messages=[{"role": "user", "content": prompt}]
# )

client = OpenAI(api_key="")

response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # or "gpt-3.5-turbo"
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": "What is the average monthly charge?"}
    ]
)

print(response.choices[0].message.content)
