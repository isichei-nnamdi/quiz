import streamlit as st
import qrcode
import sqlite3
import io
from PIL import Image
import pandas as pd
import altair as alt

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect("responses.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS responses (
                question_id TEXT,
                nickname TEXT,
                answer TEXT
            )""")
conn.commit()

# ---------- HOST MODE ----------
def host_mode():
    st.header("📊 Host Dashboard")
    question = st.text_input("Enter your question:")
    question_id = st.text_input("Question ID (unique):", "Q1")

    if st.button("Generate QR Code"):
        link = f"http://localhost:8501/?mode=audience&question_id={question_id}"
        qr = qrcode.make(link)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        st.image(Image.open(buf), caption="Scan to Join")

    # Display responses
    if st.button("Show Results"):
        df = pd.read_sql(f"SELECT answer FROM responses WHERE question_id='{question_id}'", conn)
        if not df.empty:
            chart = alt.Chart(df).mark_bar().encode(
                x='answer',
                y='count()'
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No responses yet.")

# ---------- AUDIENCE MODE ----------
def audience_mode(question_id):
    st.header("🙋 Audience Response")
    nickname = st.text_input("Enter your nickname:")
    answer = st.text_input("Your answer:")

    if st.button("Submit"):
        c.execute("INSERT INTO responses VALUES (?, ?, ?)", (question_id, nickname, answer))
        conn.commit()
        st.success("Response submitted!")

# ---------- MAIN APP ----------
params = st.query_params
mode = params.get("mode", ["host"])[0]

if mode == "host":
    host_mode()
elif mode == "audience":
    qid = params.get("question_id", ["Q1"])[0]
    audience_mode(qid)