import streamlit as st
import qrcode
import sqlite3
import io
from PIL import Image
import pandas as pd
import altair as alt
import time


# ---------- DATABASE SETUP ----------
conn = sqlite3.connect("responses.db", check_same_thread=False)
c = conn.cursor()

# store responses
c.execute("""
CREATE TABLE IF NOT EXISTS responses (
    question_id TEXT,
    nickname TEXT,
    answer TEXT,
    start_time REAL,
    expiry_time REAL,
    PRIMARY KEY (question_id, nickname)
)
""")

# store questions
c.execute("""
CREATE TABLE IF NOT EXISTS questions (
    question_id TEXT PRIMARY KEY,
    question_text TEXT,
    duration INTEGER
)
""")

conn.commit()

# ---------- HOST MODE ----------
def host_mode():
    st.markdown("<h1 style='text-align:center; color:#FF4B4B;'>🎮 Host Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size:18px;'>Manage your questions and see live audience responses</p>", unsafe_allow_html=True)

    with st.container():
        st.subheader("📝 Create Question")
        question = st.text_input("📝 Enter your question:")
        question_id = st.text_input("🆔 Question ID (unique):", "Q1")
        duration = st.number_input("⏳ Set timer (seconds):", min_value=10, max_value=300, value=30, step=5)

        if st.button("💾 Save & Start Question"):
            c.execute("REPLACE INTO questions VALUES (?, ?, ?)", (question_id, question, duration))
            conn.commit()
            st.success(f"✅ Question '{question}' saved with {duration} seconds timer (ID: {question_id})")


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
# def audience_mode(question_id):
#     st.markdown("<h1 style='text-align:center; color:#1E90FF;'>🙋 Join the Game!</h1>", unsafe_allow_html=True)

#     # Fetch question with timer
#     c.execute("SELECT question_text, start_time, duration FROM questions WHERE question_id=?", (question_id,))
#     row = c.fetchone()

#     if not row:
#         st.error("❌ Question not found. Please wait for the host to start.")
#         return

#     question_text, start_time, duration = row
#     st.markdown(f"<h2 style='text-align:center; color:#333;'>❓ {question_text}</h2>", unsafe_allow_html=True)

#     # Timer logic
#     remaining = int((start_time + duration) - time.time())
#     if remaining <= 0:
#         st.error("⏳ Time’s up! You can’t answer this question anymore.")
#         return
#     else:
#         st.info(f"⏱ You have {remaining} seconds left!")

#     nickname = st.text_input("🎭 Enter your unique nickname:")

#     # Check if already answered
#     if nickname:
#         c.execute("SELECT * FROM responses WHERE question_id=? AND nickname=?", (question_id, nickname))
#         existing = c.fetchone()
#         if existing:
#             st.warning("⚠️ You have already answered this question.")
#             return

#     answer = st.text_input("💡 Your answer:")

#     if st.button("🚀 Submit Answer", use_container_width=True):
#         if nickname and answer:
#             try:
#                 c.execute("INSERT INTO responses VALUES (?, ?, ?)", (question_id, nickname, answer))
#                 conn.commit()
#                 st.balloons()
#                 st.success("🎉 Response submitted! Waiting for the next question...")
#             except sqlite3.IntegrityError:
#                 st.error("❌ Nickname already used for this question.")
#         else:
#             st.warning("⚠️ Please enter both nickname and answer before submitting.")
def audience_mode(question_id):
    st.markdown("<h1 style='text-align:center; color:#1E90FF;'>🙋 Join the Game!</h1>", unsafe_allow_html=True)

    # Fetch question and duration
    c.execute("SELECT question_text, duration FROM questions WHERE question_id=?", (question_id,))
    row = c.fetchone()

    if not row:
        st.error("❌ Question not found. Please wait for the host to start.")
        return

    question_text, duration = row
    st.markdown(f"<h2 style='text-align:center; color:#333;'>❓ {question_text}</h2>", unsafe_allow_html=True)

    nickname = st.text_input("🎭 Enter your unique nickname:")

    if nickname:
        # Check if already exists
        c.execute("SELECT answer, start_time, expiry_time FROM responses WHERE question_id=? AND nickname=?",
                  (question_id, nickname))
        existing = c.fetchone()

        if existing:
            answer, start_time, expiry_time = existing
            if answer:
                st.warning("⚠️ You have already answered this question.")
                return
        else:
            # First join → set start & expiry time
            start_time = time.time()
            expiry_time = start_time + duration
            c.execute("INSERT INTO responses (question_id, nickname, answer, start_time, expiry_time) VALUES (?, ?, ?, ?, ?)",
                      (question_id, nickname, None, start_time, expiry_time))
            conn.commit()

        # Countdown
        remaining = int(expiry_time - time.time())
        if remaining <= 0:
            st.error("⏳ Time’s up! You can’t answer this question anymore.")
            return
        else:
            st.info(f"⏱ You have {remaining} seconds left!")

        # Answer box
        answer = st.text_input("💡 Your answer:")

        if st.button("🚀 Submit Answer", use_container_width=True):
            if answer:
                now = time.time()
                if now <= expiry_time:
                    c.execute("UPDATE responses SET answer=? WHERE question_id=? AND nickname=?",
                              (answer, question_id, nickname))
                    conn.commit()
                    st.balloons()
                    st.success("🎉 Response submitted! Waiting for the next question...")
                else:
                    st.error("❌ Time’s up! You can’t answer anymore.")
            else:
                st.warning("⚠️ Please enter your answer before submitting.")



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
