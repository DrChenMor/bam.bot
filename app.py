import os, json
import streamlit as st
from cryptography.fernet import Fernet
from datetime import datetime

# — load Fernet key & init
FERNET_KEY = os.getenv("FERNET_KEY", "")
if not FERNET_KEY:
    st.error("⚠️ FERNET_KEY not set")
    st.stop()
f = Fernet(FERNET_KEY.encode())

# — page config
st.set_page_config(
    page_title="Bamba Tracker",
    layout="wide",
)

# — two columns for EN ↔ HE
col_en, col_he = st.columns(2)

with col_en:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Bamba-snack.jpg/480px-Bamba-snack.jpg",
        use_column_width=True
    )
    st.title("🥜 Bamba Availability Tracker Signup")
    st.markdown(
        """
        **Immediate** → Email the second Bamba pops up anywhere.  
        **Daily summary** → One friendly recap at 3 pm AWST.  
        
        We keep your address **encrypted**—that means it’s locked away where only our bot can read it. 🔐
        """
    )

with col_he:
    # Hebrew is right‑to‑left; wrap in a <div dir="rtl">
    st.markdown(
        """
        <div dir="rtl">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Bamba-snack.jpg/480px-Bamba-snack.jpg" width="100%" />
            <h1>🥜 הרשמה למעקב זמינות במבה</h1>
            <p>
            <b>מידי</b> → מקבלים אימייל ברגע שמזהים במבה בסניף.  
            <b>סיכום יומי</b> → סיכום נחמד ב–15:00.  
            </p>
            <p>האימייל שלך מוצפן (כלומר סתום במפתח 🗝️ שרק הבוט שלנו יודע).</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# — unified form (bilingual labels)
mode = st.radio(
    "Notify me when / הודיעו לי כאשר", 
    ["Immediate / מידי", "Daily summary / סיכום יומי"]
)

email = st.text_input("Your email address / כתובת המייל שלך")

if st.button("Subscribe"):
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

    st.success("🎉 You’re signed up!")

# — show the most recent check status
st.markdown("---")
try:
    history = json.load(open("history.json"))["runs"][-1]
    ts = history[0]["timestamp"].replace("T", " ")[:-7]
    st.subheader(f"Last checked: {ts} AWST")
    for s in history:
        mark = "✅" if s["available"] else "❌"
        st.write(f"{mark} **{s['store']}**")
except:
    st.info("No checks have run yet.")
