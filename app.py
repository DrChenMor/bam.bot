import os
import json
import streamlit as st
from cryptography.fernet import Fernet
from datetime import datetime

# ────────────────────────────────────────────────────────────────
# 0) CSS to set Calibri (with fallback) and remove deprecation notice
# ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Bamba Tracker", layout="wide")
st.markdown("""
    <style>
      * { font-family: 'Calibri', sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────
# 1) Load + init Fernet
# ────────────────────────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY", "")
if not FERNET_KEY:
    st.error("⚠️ FERNET_KEY not set in environment")
    st.stop()
f = Fernet(FERNET_KEY.encode())

# ────────────────────────────────────────────────────────────────
# 2) Page header & two‑column bilingual intro
# ────────────────────────────────────────────────────────────────
col_en, col_he = st.columns(2)

with col_en:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Bamba-snack.jpg/480px-Bamba-snack.jpg",
        use_container_width=True
    )
    st.title("🥜 Bamba Availability Tracker Signup")
    st.markdown(
        """
        **Immediate** → Email the second Bamba pops up anywhere.  
        **Daily summary** → One friendly recap at 3 pm AWST.  
        
        We keep your address **encrypted**—that means it’s locked away so only our bot can read it. 🔐
        """
    )

with col_he:
    st.markdown(
        """
        <div dir="rtl">
          <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Bamba-snack.jpg/480px-Bamba-snack.jpg" width="100%" />
          <h1>🥜 הרשמה למעקב זמינות במבה</h1>
          <p>
            <b>מידי</b> → אימייל ברגע שמזהים במבה בסניף.  
            <b>סיכום יומי</b> → סיכום נחמד בכל יום ב–15:00.  
          </p>
          <p>האימייל שלך מוצפן (סתום במפתח 🗝️ שרק הבוט שלנו יודע).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ────────────────────────────────────────────────────────────────
# 3) Notification mode & email input
# ────────────────────────────────────────────────────────────────
mode = st.radio(
    "Notify me when / הודיעו לי כאשר:",
    ["Immediate / מידי", "Daily summary / סיכום יומי"],
    index=0,
)

email = st.text_input("Your email address / כתובת המייל שלך")

if st.button("Subscribe"):
    # Encrypt the email address
    token = f.encrypt(email.encode()).decode()
    subfile = "subscribers.json"
    if os.path.exists(subfile):
        data = json.load(open(subfile))
    else:
        data = {"users": []}

    data["users"].append({
        "token": token,
        "mode":  "immediate" if mode.startswith("Immediate") else "daily"
    })

    with open(subfile, "w") as fp:
        json.dump(data, fp, indent=2)

    st.success("🎉 You’re signed up! Check your inbox soon.")

st.markdown("---")

# ────────────────────────────────────────────────────────────────
# 4) Show latest availability status
# ────────────────────────────────────────────────────────────────
try:
    history = json.load(open("history.json"))["runs"]
    latest  = history[-1]
    ts      = latest[0]["timestamp"].replace("T", " ").split(".")[0]
    st.subheader(f"Last checked at {ts} AWST")
    for store in latest:
        mark = "✅" if store["available"] else "❌"
        st.write(f"{mark} **{store['store']}**")
except:
    st.info("No checks have run yet.")
