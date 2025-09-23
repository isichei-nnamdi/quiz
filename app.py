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

# store responses
c.execute("""
CREATE TABLE IF NOT EXISTS responses (
    question_id TEXT,
    nickname TEXT,
    answer TEXT,
    PRIMARY KEY (question_id, nickname)
)
""")

# store questions
c.execute("""
CREATE TABLE IF NOT EXISTS questions (
    question_id TEXT PRIMARY KEY,
    question_text TEXT
)
""")

conn.commit()


def host_mode():
    st.markdown("<h1 style='text-align:center; color:#FF4B4B;'>🎮 Host Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size:18px;'>Manage your questions and see live audience responses</p>", unsafe_allow_html=True)

    with st.container():
        st.subheader("📝 Create Question")
        question = st.text_input("Enter your question:")
        question_id = st.text_input("Question ID (unique):", "Q1")

        if st.button("💾 Save Question"):
            c.execute("REPLACE INTO questions VALUES (?, ?)", (question_id, question))
            conn.commit()
            st.success(f"✅ Question '{question}' saved with ID {question_id}")

    st.markdown("---")
    st.subheader("📲 Share with Audience")
    base_url = st.text_input("Enter your app base URL:", "https://quizitup.streamlit.app/")

    if st.button("🔗 Generate QR Code"):
        link = f"{base_url}/?mode=audience&question_id={question_id}"
        qr = qrcode.make(link)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        st.image(Image.open(buf), caption=f"Scan to Join 🎉\n{link}")

    st.markdown("---")
    st.subheader("📊 Live Results")
    # if st.button("👀 Show Results"):
    #     df = pd.read_sql(f"SELECT answer FROM responses WHERE question_id='{question_id}'", conn)
    #     if not df.empty:
    #         chart = alt.Chart(df).mark_bar(color="#FF4B4B").encode(
    #             x='answer',
    #             y='count()'
    #         ).properties(title="Live Audience Responses")
    #         st.altair_chart(chart, use_container_width=True)
    #     else:
    #         st.info("⏳ Waiting for audience responses...")
    if st.button("👀 Show Results"):
        df = pd.read_sql(f"SELECT nickname, answer FROM responses WHERE question_id='{question_id}'", conn)
        if not df.empty:
            chart = alt.Chart(df).mark_bar().encode(
                x=alt.X('answer:N', title="Answers"),
                y=alt.Y('count():Q', title="Number of Responses"),
                color=alt.Color('nickname:N', legend=alt.Legend(title="Participants"))
            ).properties(
                title="Live Audience Responses",
                width=600,
                height=400
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("⏳ Waiting for audience responses...")




# ---------- AUDIENCE MODE ----------
def audience_mode(question_id):
    st.markdown("<h1 style='text-align:center; color:#1E90FF;'>🙋 Join the Game!</h1>", unsafe_allow_html=True)

    # Fetch question text
    c.execute("SELECT question_text FROM questions WHERE question_id=?", (question_id,))
    row = c.fetchone()

    if row:
        question_text = row[0]
        st.markdown(f"<h2 style='text-align:center; color:#333;'>❓ {question_text}</h2>", unsafe_allow_html=True)
    else:
        st.error("❌ Question not found. Please wait for the host to start.")
        return

    st.markdown("---")
    nickname = st.text_input("🎭 Enter your unique nickname:")

    # Check if nickname already answered this question
    if nickname:
        c.execute("SELECT * FROM responses WHERE question_id=? AND nickname=?", (question_id, nickname))
        existing = c.fetchone()
        if existing:
            st.warning("⚠️ You have already answered this question. Wait for the next one!")
            return  # stop showing answer box

    # Only show answer input if nickname is available
    answer = st.text_input("💡 Your answer:")

    if st.button("🚀 Submit Answer", use_container_width=True):
        if nickname and answer:
            try:
                c.execute("INSERT INTO responses VALUES (?, ?, ?)", (question_id, nickname, answer))
                conn.commit()
                st.balloons()  # 🎈 Confetti
                st.success("🎉 Response submitted! Waiting for the next question...")
            except sqlite3.IntegrityError:
                st.error("❌ Nickname already taken for this question. Choose another nickname or wait.")
        else:
            st.warning("⚠️ Please enter both nickname and answer before submitting.")



# ---------- MAIN APP ----------
params = st.query_params

mode = params.get("mode", "host")   # returns a string
qid = params.get("question_id", "Q1")

if mode == "host":
    host_mode()
elif mode == "audience":
    if qid:
        audience_mode(qid)
    else:
        st.error("❌ No question selected. Please scan a valid QR code.")
else:
    st.warning("Please choose a mode: host or audience.")
