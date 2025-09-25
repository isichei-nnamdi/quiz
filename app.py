import streamlit as st
import qrcode
import sqlite3
import io
from PIL import Image
import pandas as pd
import altair as alt
import time


# ---------- DATABASE SETUP (fixed) ----------
conn = sqlite3.connect("responses.db", check_same_thread=False)
c = conn.cursor()

# create responses table (per-user timer stored here)
c.execute("""
CREATE TABLE IF NOT EXISTS responses (
    question_id TEXT,
    nickname TEXT,
    answer TEXT,
    start_time REAL,
    expiry_time REAL,
    submitted_time REAL,
    PRIMARY KEY (question_id, nickname)
)
""")

# create questions table (host sets duration but NOT start_time)
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
        # st.subheader("📝 Create Question")
        question = st.text_input("📝 Enter your question:")
        q1, q2 = st.columns(2)
        with q1:
            question_id = st.text_input("🆔 Question ID (unique):", "Q1")
        with q2:
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
        df = pd.read_sql(f"""
            SELECT nickname, answer, start_time, submitted_time 
            FROM responses 
            WHERE question_id='{question_id}'
        """, conn)

        if not df.empty:
            # compute duration in seconds
            df["duration"] = (df["submitted_time"] - df["start_time"]).round().astype("Int64")

            # nickname label with duration
            df["nickname_label"] = df["nickname"] + " (" + df["duration"].astype(str) + "s)"

            chart = alt.Chart(df).mark_bar().encode(
                x=alt.X('answer:N', title="Answers"),
                y=alt.Y('count():Q', title="Number of Responses"),
                color=alt.Color('nickname_label:N', legend=alt.Legend(title="Participants (time taken)"))
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

    # Fetch question and duration
    c.execute("SELECT question_text, duration FROM questions WHERE question_id=?", (question_id,))
    row = c.fetchone()

    if not row:
        st.error("❌ Question not found. Please wait for the host to start.")
        return

    question_text, duration = row[0], row[1]
    st.markdown(f"<h2 style='text-align:center; color:#333;'>❓ {question_text}</h2>", unsafe_allow_html=True)

    # Ask for nickname first — we only start personal timer once a nickname is provided
    nickname = st.text_input("🎭 Enter your unique nickname:")

    if not nickname:
        st.info("Enter a unique nickname to start your personal timer.")
        return

    # Check if this user already has a responses row for this question
    c.execute(
        "SELECT answer, start_time, expiry_time FROM responses WHERE question_id=? AND nickname=?",
        (question_id, nickname)
    )
    existing = c.fetchone()

    # If first time they join, insert a row with start_time & expiry_time (start timer now)
    if existing is None:
        start_time = time.time()
        expiry_time = start_time + int(duration)
        try:
            c.execute(
                "INSERT INTO responses (question_id, nickname, answer, start_time, expiry_time) VALUES (?, ?, ?, ?, ?)",
                (question_id, nickname, None, start_time, expiry_time)
            )
            conn.commit()
            # fetch back the inserted values
            c.execute(
                "SELECT answer, start_time, expiry_time FROM responses WHERE question_id=? AND nickname=?",
                (question_id, nickname)
            )
            existing = c.fetchone()
        except sqlite3.IntegrityError:
            # Very unlikely race: someone inserted same nickname at same time — re-fetch
            c.execute(
                "SELECT answer, start_time, expiry_time FROM responses WHERE question_id=? AND nickname=?",
                (question_id, nickname)
            )
            existing = c.fetchone()

    # Now existing contains (answer, start_time, expiry_time)
    answer_db, start_time, expiry_time = existing

    # If they already submitted an answer
    if answer_db:
        st.warning("⚠️ You have already answered this question.")
        return

    # Remaining time
    remaining = int(expiry_time - time.time())
    if remaining <= 0:
        st.error("⏳ Time’s up! You can’t answer this question anymore.")
        return
    else:
        st.info(f"⏱ You have {remaining} seconds left!")

    # Show answer input (use keys to avoid collisions if multiple users in same session)
    answer_input = st.text_input("💡 Your answer:", key=f"answer_{question_id}_{nickname}")

    if st.button("🚀 Submit Answer", key=f"submit_{question_id}_{nickname}", use_container_width=True):
        now = time.time()
        if now > expiry_time:
            st.error("❌ Time’s up! You can’t answer anymore.")
            return
        if not answer_input:
            st.warning("⚠️ Please enter your answer before submitting.")
            return

        # Save response
        now = time.time()
        c.execute(
            "UPDATE responses SET answer=?, submitted_time=? WHERE question_id=? AND nickname=?",
            (answer_input, now, question_id, nickname)
        )
        conn.commit()
        st.balloons()
        st.success("🎉 Response submitted! Waiting for the next question...")



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
