import os, json, streamlit as st
from cryptography.fernet import Fernet
from datetime import datetime

# ────────────────────────────────────────────────────────────────
# PAGE CONFIG + GLOBAL CSS (Calibri font)
# ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Bamba Tracker", layout="wide")
st.markdown("""
  <style>
    * { font-family: 'Calibri', sans-serif !important; }
  </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────
# FERNET SETUP
# ────────────────────────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY", "")
if not FERNET_KEY:
    st.error("⚠️ FERNET_KEY not set")
    st.stop()
f = Fernet(FERNET_KEY.encode())

# ────────────────────────────────────────────────────────────────
# TWO‑COLUMN BILINGUAL HEADER
# ────────────────────────────────────────────────────────────────
col_en, col_he = st.columns(2)

with col_en:
    # exactly the same calls in English
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Bamba-snack.jpg/480px-Bamba-snack.jpg",
        use_container_width=True
    )
    st.header("🥜 Bam.Bot WA Availability Tracker Signup")
    st.markdown("""
    **Immediate** - Email the second Bamba pops up in Coles Dianella or Coles Mirrabooka.  
    **Daily summary** - One friendly recap at 15:00 AWST.  

    We keep your address **encrypted**—that means it’s locked away so only our bot can read it. 🔐
    """)

with col_he:
    # same calls, Hebrew text, wrapped in RTL container
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Bamba-snack.jpg/480px-Bamba-snack.jpg",
        use_container_width=True
    )
    st.markdown("<h2 dir='rtl'>🥜 הרשמה למעקב במבה – במבוט WA</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <div dir="rtl">
        <p><b>במיידי</b> – שלח דחוף אימייל ברגע שאתה מזהה שיש במבה בסניף דיאנלה או מיררבוקה למה אני זקוק למנת בוטנים.</p>
        <p><b>סיכום יומי</b> – סיכום פעם ביום שנייה לפני שאוספים את הילדים ב–15:00.</p>

        האימייל שלך **מוצפן** - הגנה מפני אנטישמיים מובטחת אלא אם הבוט שלנו יתאסלם.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ────────────────────────────────────────────────────────────────
# SUBSCRIPTION FORM
# ────────────────────────────────────────────────────────────────
mode = st.radio(
    "Notify me when / הודיעו לי כאשר:",
    ["Immediate / במיידי", "Daily summary / סיכום פעם ביום"]
)

email = st.text_input("Email:")

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

    st.success("🎉 You’re signed up! Check your inbox soon.")

st.markdown("---")

# ────────────────────────────────────────────────────────────────
# LATEST STATUS
# ────────────────────────────────────────────────────────────────
try:
    history = json.load(open("history.json"))["runs"]
    latest  = history[-1]
    ts      = latest[0]["timestamp"].replace("T", " ").split(".")[0]
    st.subheader(f"Last checked at {ts} AWST")
    for s in latest:
        mark = "✅" if s["available"] else "❌"
        st.write(f"{mark} **{s['store']}**")
except:
    st.info("No checks have run yet.")
