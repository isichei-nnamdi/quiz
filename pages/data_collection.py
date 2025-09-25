import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
import qrcode
import io
from PIL import Image

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect("audience_data.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS audience_responses (
    nickname TEXT,
    Sleep_hours REAL,
    Energy_level REAL,
    submitted_time REAL,
    PRIMARY KEY (nickname)
)
""")
conn.commit()

# ---------- HOST MODE ----------
# def host_mode():
#     st.markdown("<h1 style='text-align:center; color:#FF4B4B;'>📊 Live Audience Data Collection (Host)</h1>", unsafe_allow_html=True)
#     st.write("Manage live data collection and demonstrate Linear Regression with your audience's data.")

#     st.subheader("📲 Share with Audience")
#     base_url = st.text_input("Enter your app base URL:", "https://quizitup.streamlit.app")
#     page_name = "data_collection"

#     if st.button("🔗 Generate QR Code"):
#         link = f"{base_url}/{page_name}?mode=audience"
#         qr = qrcode.make(link)
#         buf = io.BytesIO()
#         qr.save(buf, format="PNG")
#         st.image(Image.open(buf), caption=f"Scan to Join 🎉\n{link}")

#     st.markdown("---")
#     st.subheader("📈 Live Collected Data")

#     # Add a button to fetch & show responses
#     if st.button("👀 View Live Responses"):
#         df = pd.read_sql("SELECT * FROM audience_responses", conn)

#         if not df.empty:
#             st.write(df.head(5))

#             if len(df) > 1:
#                 # Regression fit
#                 X = df["Sleep_hours"].values
#                 y = df["Energy_level"].values

#                 m, c_ = np.polyfit(X, y, 1)

#                 x_line = np.linspace(min(X), max(X), 100)
#                 y_line = m * x_line + c_

#                 # Plot
#                 fig, ax = plt.subplots()
#                 ax.scatter(X, y, color="blue", label="Audience Data")
#                 # ax.plot(x_line, y_line, color="red", label=f"y={m:.2f}x+{c_:.2f}")
#                 ax.set_xlabel("Sleep Hours")
#                 ax.set_ylabel("Energy Level")
#                 ax.set_title("Live Linear Regression from Audience Data")
#                 ax.legend()
#                 st.pyplot(fig)
            

#                 st.markdown(f"**Equation of best-fit line:**  `y = {m:.2f}x + {c_:.2f}`")
#             else:
#                 st.info("Need at least 2 responses to fit a regression line.")
#         else:
#             st.info("⏳ No audience responses yet. Waiting...")
# ---------- HOST MODE ----------
def host_mode():
    st.markdown("<h1 style='text-align:center; color:#FF4B4B;'>📊 Live Audience Data Collection (Host)</h1>", unsafe_allow_html=True)
    st.write("Manage live data collection and demonstrate Linear Regression with your audience's data.")

    st.subheader("📲 Share with Audience")
    base_url = st.text_input("Enter your app base URL:", "https://quizitup.streamlit.app")
    page_name = "data_collection"

    if st.button("🔗 Generate QR Code"):
        link = f"{base_url}/{page_name}?mode=audience"
        qr = qrcode.make(link)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        st.image(Image.open(buf), caption=f"Scan to Join 🎉\n{link}")

    st.markdown("---")
    st.subheader("📈 Live Collected Data")

    # Add a button to fetch & show responses
    if st.button("👀 View Live Responses"):
        df = pd.read_sql("SELECT * FROM audience_responses", conn)

        if not df.empty:
            st.write(df.head(5))

            # 🔽 Add download button
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="💾 Download Full Dataset as CSV",
                data=csv,
                file_name="audience_responses.csv",
                mime="text/csv"
            )

            if len(df) > 1:
                # Regression fit
                X = df["Sleep_hours"].values
                y = df["Energy_level"].values

                m, c_ = np.polyfit(X, y, 1)

                x_line = np.linspace(min(X), max(X), 100)
                y_line = m * x_line + c_

                # Plot
                fig, ax = plt.subplots()
                ax.scatter(X, y, color="blue", label="Audience Data")
                # ax.plot(x_line, y_line, color="red", label=f"y={m:.2f}x+{c_:.2f}")
                ax.set_xlabel("Sleep Hours")
                ax.set_ylabel("Energy Level")
                ax.set_title("Live Linear Regression from Audience Data")
                ax.legend()
                st.pyplot(fig)

                # st.markdown(f"**Equation of best-fit line:**  `y = {m:.2f}x + {c_:.2f}`")
            else:
                st.info("Need at least 2 responses to fit a regression line.")
        else:
            st.info("⏳ No audience responses yet. Waiting...")



# ---------- AUDIENCE MODE ----------
def audience_mode():
    st.markdown("<h1 style='text-align:center; color:#1E90FF;'>🙋 Audience Participation</h1>", unsafe_allow_html=True)
    st.write("Answer these 2 quick questions to contribute your data!")

    nickname = st.text_input("🎭 Enter your unique nickname:")

    if not nickname:
        st.info("Enter a nickname to continue.")
        return

    # Check if already submitted
    c.execute("SELECT * FROM audience_responses WHERE nickname=?", (nickname,))
    existing = c.fetchone()

    if existing:
        st.warning("⚠️ You have already submitted your response.")
        return

    # Two numeric values (example: Sleep vs Energy)
    q1, q2 = st.columns(2)
    with q1:
        x_val = st.number_input("How many hours do you usually sleep per night?", min_value=0, max_value=12, step=1)
    with q2:
        y_val = st.slider("How much energy do you feel during the day? (0–100)", min_value=0, max_value=100, step=1)

    if st.button("🚀 Submit Response"):
        now = time.time()
        c.execute("INSERT OR REPLACE INTO audience_responses VALUES (?, ?, ?, ?)", 
                  (nickname, x_val, y_val, now))
        conn.commit()
        st.balloons()
        st.success("🎉 Response submitted! Thank you for contributing.")

# ---------- MAIN APP ----------
params = st.query_params
mode = params.get("mode", "host")

if mode == "host":
    host_mode()
elif mode == "audience":
    audience_mode()
else:
    st.warning("Please choose a mode: host or audience.")