import streamlit as st
import io
import sys
import re
import textwrap
import matplotlib.pyplot as plt
import speech_recognition as sr
from query_with_model import query_account_qa

# print(query_account_qa("How many accounts are active?"))
st.set_page_config(page_title="💬 Banking GenAI Chatbot", layout="wide")

st.markdown("""
    <style>
        /* keep your existing background overrides */
        body, .stApp {
            background-color: #F7FAFC;
            color: #333333;
        }

        /* remove the page-level scrollbars */
        html, body, .main, .reportview-container, .block-container {
            max-height: 100vw; /* full viewport height */
            overflow: auto; /* prevent page-level scroll */

        }

        h1, h2, h3, h4 {
            color: #2EC4B6;
        }

        .stButton>button {
            background-color: #2EC4B6;
            color: white;
            border-radius: 5px;
            border: none;
        }

        .stButton>button:hover {
            background-color: #38B000;
        }

        #chat-container {
            overflow-y: auto !important;
            background-color: #F1F5F9;
            border: 1px solid #E2E8F0;
        }

        .user-bubble {
            background-color: #D9FBEF;
        }

        .bot-bubble {
            background-color: #F1F5F9;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize chat history and speech recognition state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "spoken_query" not in st.session_state:
    st.session_state.spoken_query = ""

# Function to record and transcribe speech
def record_and_transcribe():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Please speak clearly into your mic.")
        audio = recognizer.listen(source, timeout=10)
    try:
        text = recognizer.recognize_google(audio)
        st.success("Transcription complete!")
        st.session_state.spoken_query = text
    except sr.UnknownValueError:
        st.error("Sorry, could not understand the audio.")
    except sr.RequestError as e:
        st.error(f"Could not request results; {e}")

charts_data = {
    "How many failed login attempts happened in June?": {
        "labels": ["Successful", "Failed"],
        "values": [3550, 1450],
        "title": "Login Attempt Outcomes - June",
        "chart_type": "pie"
    },
    "Top failure reason in April 2026": {
        "labels": ["BT Amount is $0", "Other"],
        "values": [23, 10],
        "title": "Top Failure Reasons - April 2026",
        "chart_type": "bar"
    },
    "What is the success rate of credit card payments?": {
        "labels": ["Succeeded", "Failed"],
        "values": [89.5, 10.5],
        "title": "Credit Card Payment Success Rate - May 2026",
        "chart_type": "doughnut"
    },
    "How many failed payments were through ATM channel?": {
        "labels": ["Succeeded", "Failed"],
        "values": [85.5, 14.5],
        "title": "ATM Channel Payment Outcomes - Feb 2026",
        "chart_type": "pie"
    },
    "Which account status has the most users?": {
        "labels": ["Valid Operating Account", "Other Accounts"],
        "values": [775, 4225],
        "title": "Account Status Breakdown - 2025",
        "chart_type": "doughnut"
    },
    "Breakdown of account open reasons.": {
        "labels": ["Re-open - bank error", "Application", "Replaced Card For Lost/Stolen"],
        "values": [12.00, 12.00, 11.50],
        "title": "Top Reasons for Account Opening",
        "chart_type": "horizontalBar"
    },
    "Show top 3 login failure codes by volume.": {
        "labels": ["Other Error", "Invalid Password", "Timed Out"],
        "values": [75, 50, 25],
        "title": "Top Login Failure Codes - March 2023",
        "chart_type": "bar"
    },
    "What is the trend of login failures over 6 months?": {
        "labels": ["Success", "Other Error", "Invalid Password", "Timed Out"],
        "values": [25, 75, 50, 25],
        "title": "Login Status Distribution - March 2023",
        "chart_type": "line"
    },
    "Transactions in category 'Transaction'": {
        "labels": ["Total Transactions"],
        "values": [1251],
        "title": "Transaction Volume - 'Transaction' Category",
        "chart_type": "bar"
    },
    "Percentage of accounts with more than 2 months overdue.": {
        "labels": ["Overdue", "Not Overdue"],
        "values": [17, 4983],
        "title": "Overdue Accounts - May 2025",
        "chart_type": "pie"
    },
    "What are the top reasons for account closures last quarter?": {
        "labels": ["Deceased", "Too Many Cards", "Did Not Use"],
        "values": [11.88, 10.89, 10.89],
        "title": "Top 3 Reasons for Account Closure - Last Quarter",
        "chart_type": "horizontalBar"
    },
    "In May 2025, how many credit card payments failed?": {
        "labels": ["Failed", "Succeeded"],
        "values": [39, 261],  # 13% of 300 total
        "title": "Credit Card Payments - May 2025",
        "chart_type": "pie"
    },
    "In May 2026, how many credit card payments failed?": {
        "labels": ["Failed", "Succeeded"],
        "values": [13,  87],  # 13% of 100 total
        "title": "Credit Card Payments - May 2026",
        "chart_type": "doughnut"
    }
}

# Define the chart rendering function
def render_chart(question):
    if question not in charts_data:
        return None

    data = charts_data[question]
    labels = data["labels"]
    values = data["values"]
    title = data["title"]
    chart_type = data["chart_type"]

    # Choose figure size based on chart type
    # if chart_type in ["pie", "doughnut"]:
    #     fig, ax = plt.subplots(figsize=(3, 2))  # square for better visual
    # elif chart_type == "horizontalBar":
    #     fig, ax = plt.subplots(figsize=(5, 2))
    # else:
    #     fig, ax = plt.subplots(figsize=(3, 2))
    fig, ax = fig, ax = plt.subplots(figsize=(6, 3.7)) 
    if chart_type == "bar":
        ax.bar(labels, values, color='orange')
        ax.set_title(title, fontsize=6)  # Set title font size
        ax.tick_params(axis='x', labelsize=7)  # Set x-axis label font size
        ax.tick_params(axis='y', labelsize=7)  # Optional: Set y-axis label font size
        plt.xticks(rotation=45, ha='right')

    elif chart_type == "horizontalBar":
        bars = ax.barh(labels, values, color='#4682B4', edgecolor='black')  # Steel blue bars
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.5, bar.get_y() + bar.get_height() / 2,
                    f'{width}', va='center', fontsize=6, weight='bold', color='black')
        ax.set_title(title, fontsize=6, weight='bold')
        ax.tick_params(axis='y', labelsize=6)
        ax.tick_params(axis='x', labelsize=6)
        ax.xaxis.grid(True, linestyle='--', alpha=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.tight_layout(pad=1.0)

    elif chart_type == "pie":
        ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            startangle=75,
            textprops={'fontsize': 7}  # Adjust the font size as needed
        )
        ax.set_title(title, fontsize=6)  # Optional: Change title font size too
        ax.axis('equal')

    elif chart_type == "doughnut":
    # Draw pie chart with specific text properties
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            startangle=140,
            colors=['#4CAF50', '#FF5722'],  # Success: green, Fail: orange
            textprops={'fontsize': 7, 'weight': 'bold'}
        )
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        fig.gca().add_artist(centre_circle)
        ax.set_title(title, fontsize=6, weight='bold')
        ax.axis('equal')
        plt.tight_layout(pad=1.0)

    elif chart_type == "line":
        ax.plot(labels, values, marker='o', color='green', linestyle='-')
        ax.set_title(title)
        ax.set_ylabel("Value")
        plt.xticks(rotation=45, ha='right')

    else:
        plt.close(fig)
        return None

    plt.tight_layout()
    return fig
    

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("<h4 style='margin-bottom: 2px;'>📊 Dashboard</h3>", unsafe_allow_html=True)
    # st.title("📊 Data Dashboard")
    if st.session_state.messages:
        last_query = st.session_state.messages[-2]["content"] if len(st.session_state.messages) >= 2 else ""
        last_response = st.session_state.messages[-1]["content"] if st.session_state.messages else ""
        fig = render_chart(st.session_state.last_question)
        if fig:
            st.pyplot(fig)
        
    else:
        st.info("Ask a question about accounts, payments or trends to see visualizations here.")

with col2:
    st.markdown("<h4 style='margin-bottom: 2px;'>📊 Chatbot</h3>", unsafe_allow_html=True)
    if not st.session_state.messages:
        st.markdown("""
        <div style="height:330px; padding: 20px; border-radius: 10px; background-color: #f1f5f9; text-align: center; box-shadow: 2px 2px 6px rgba(0,0,0,0.05);">
            <h4 style="color: #444;">🤖 Welcome to your Banking Assistant</h4>
            <p style="color: #666; font-size: 15px;">
                Ask questions like:<br>
                <em>"What are the top reasons for account closures last quarter?"</em><br>
                <em>"Show me monthly login trends this year"</em><br>
            </p>
            <p style="color: #888; font-size: 14px;">You can also use the <strong>🎤</strong> button to ask your question via voice.</p>
        </div>
    """, unsafe_allow_html=True)
    else:
    # Scrollable chat container
        chat_html = """
            <div id="chat-container" style="height:350px; overflow-y:scroll; padding:10px; border:1px solid #ccc; border-radius:10px;">
            """

        for msg in st.session_state.messages:
            role = "You" if msg["role"] == "user" else "Bot"
            bubble_color = "#DCF8C6" if role == "You" else "#F1F0F0"
            align = "right" if role == "You" else "left"
            chat_html += f"""
            <div style='display:flex; justify-content:{"flex-end" if msg["role"] == "user" else "flex-start"}; margin-bottom:10px;'>
            <div style='max-width:80%; padding:10px; background-color:{bubble_color}; border-radius:10px; word-wrap:break-word; white-space:pre-wrap; box-shadow:1px 1px 3px rgba(0,0,0,0.1);'>
            {msg['content']}
            </div>
            </div>
            """

        chat_html += "</div>"
        chat_html += """
        <script>
            var chatContainer = document.getElementById("chat-container");
            chatContainer.scrollTop = chatContainer.scrollHeight;
        </script>
        """
        st.components.v1.html(chat_html, height=350, scrolling=False)

    # Voice + Text input side by side
    input_col1, input_col2 = st.columns([1, 7])  # Adjust ratios if needed

    with input_col1:
        st.markdown("<div style='margin-top: 0px;'></div>", unsafe_allow_html=True)
        if st.button("🎤"):
            record_and_transcribe()

        with input_col2:
            st.markdown("<div style='margin-top: 0px;'></div>", unsafe_allow_html=True)
            if st.session_state.spoken_query:
                user_prompt = st.text_input("📝", value=st.session_state.spoken_query, key="editable_prompt")
            else:
                user_prompt = st.chat_input("Ask me anything about accounts, trends, or analytics...")

            send_clicked = user_prompt is not None and user_prompt != ""


    # Handling user query
    if send_clicked and user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        st.session_state.last_question = user_prompt
        with st.spinner("Thinking..."):
            buffer = io.StringIO()
            sys_stdout_backup = sys.stdout
            sys.stdout = buffer
            try:
                query_account_qa(user_prompt)
            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                sys.stdout = sys_stdout_backup

            assistant_reply = buffer.getvalue()
            st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
            st.rerun()




    # st.title("💬 Chatbot")

    # Scrollable chat container
#     chat_html = """
#     <div style="height:400px; overflow-y:scroll; padding:10px; border:1px solid #ccc; border-radius:10px;">
#     """
#     for msg in st.session_state.messages:
#         role = "You" if msg["role"] == "user" else "Bot"
#         bubble_color = "#DCF8C6" if role == "You" else "#F1F0F0"
#         align = "right" if role == "You" else "left"
#         chat_html += f"""
#         <div style='display:flex; justify-content:{"flex-end" if msg["role"] == "user" else "flex-start"}; margin-bottom:10px;'>
#         <div style='max-width:80%; padding:10px; background-color:{bubble_color}; border-radius:10px; word-wrap:break-word; box-shadow:1px 1px 3px rgba(0,0,0,0.1);'>
#         {msg['content']}
#         </div>
#         </div>
#     """

#     chat_html += "</div>"
#     st.components.v1.html(chat_html, height=420, scrolling=False)

#     # Voice input
#     if st.button("🎤 Speak Query"):
#         record_and_transcribe()

#     spoken_query = st.session_state.spoken_query
#     if spoken_query:
#         user_prompt = st.text_input("📝 Your query:", value=spoken_query, key="editable_prompt")
#         send_clicked = user_prompt is not None
#     else:
#         user_prompt = st.chat_input("Ask me anything about accounts, trends, or analytics...")
#         send_clicked = user_prompt is not None

#     # Handling user query
#     # Add this to your message handling logic
# if send_clicked and user_prompt:
#     st.session_state.messages.append({"role": "user", "content": user_prompt})

#     # Store last question for chart rendering
#     st.session_state.last_question = user_prompt

#     with st.spinner("Thinking..."):
#         buffer = io.StringIO()
#         sys_stdout_backup = sys.stdout
#         sys.stdout = buffer
#         try:
#             query_account_qa(user_prompt)
#         except Exception as e:
#             st.error(f"❌ Error: {e}")
#         finally:
#             sys.stdout = sys_stdout_backup

#         assistant_reply = buffer.getvalue()
#         st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
#         st.rerun()



