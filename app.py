import os, json, streamlit as st
from cryptography.fernet import Fernet
from datetime import datetime

# ─── PAGE CONFIG & FONT ──────────────────────────────────────
st.set_page_config(
    page_title="Bam.Bot - Bamba Tracker",
    layout="wide",
    page_icon="bamlogo.png"  # or "assets/bamlogo.png"
)
st.markdown("""
  <style>
    * { font-family: 'Calibri', sans-serif !important; }
  </style>
""", unsafe_allow_html=True)

# ─── FERNET SETUP ────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY", "")
if not FERNET_KEY:
    st.error("⚠️ FERNET_KEY not set"); st.stop()
f = Fernet(FERNET_KEY.encode())

# ─── ONE IMAGE AT TOP ────────────────────────────────────────
st.markdown("""
<div style='text-align: center;'>
  <img src='https://raw.githubusercontent.com/DrChenMor/bam.bot/main/bamlogo.png' width='300'/>
</div>
""", unsafe_allow_html=True)

# ─── TWO‑COLUMN BILINGUAL HEADER ────────────────────────────
col_en, col_he = st.columns(2)

with col_en:
    st.header("🥜 Bam.Bot WA Availability Tracker Signup")
    st.markdown("""
    **Immediate** – Email the second Bamba pops up in Coles Dianella or Mirrabooka.  
    **Daily summary** – One friendly recap at 15:00 AWST.  

    🔐 We keep your address **encrypted**— only our bot can read it.
    """)

with col_he:
    st.markdown("<h2 dir='rtl'>🥜 הרשמה למעקב במבה – במבוט WA</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <div dir="rtl">
        <p><b>במיידי</b> – שלח דחוף אימייל ברגע שאתה מזהה שיש במבה בסניף דיאנלה או מיררבוקה למה אני זקוק למנת בוטנים.</p>
        <p><b>סיכום יומי</b> – סיכום פעם ביום שנייה לפני שאוספים את הילדים ב–15:00.</p>
        <p> 🔐 האימייל שלך <b>מוצפן</b> – הגנה מפני אנטישמיים מובטחת, אלא אם הבוט שלנו יתאסלם.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─── SUBSCRIPTION FORM ───────────────────────────────────────
with st.container():
    # Use columns to center the form
    left_col, center_col, right_col = st.columns([1, 2, 1])
    with center_col:
        st.markdown("""
            <div style="
                padding: 25px;
                border: 1px solid #ccc;
                border-radius: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                background-color: #fdfdfd;
                margin-bottom: 40px;
            ">
            """, unsafe_allow_html=True)

        mode = st.radio(
            "Notify me when / הודיעו לי כאשר:",
            ["Immediate / במיידי", "Daily summary / סיכום פעם ביום"]
        )

        email = st.text_input("Your email / כתובת המייל שלך")

        if st.button("Subscribe"):
            token = f.encrypt(email.encode()).decode()
            subfile = "subscribers.json"
            data = json.load(open(subfile)) if os.path.exists(subfile) else {"users": []}
            data["users"].append({
                "token": token,
                "mode": "immediate" if mode.startswith("Immediate") else "daily"
            })
            with open(subfile, "w") as fp:
                json.dump(data, fp, indent=2)
            st.success("🎉 You’re signed up! Check your inbox soon.")

        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")


# ─── LATEST STATUS ───────────────────────────────────────────
try:
    hist   = json.load(open("history.json"))["runs"]
    latest = hist[-1]
    ts     = latest[0]["timestamp"].replace("T"," ").split(".")[0]
    st.subheader(f"Last checked at {ts} AWST")
    for s in latest:
        mark = "✅" if s["available"] else "❌"
        st.write(f"{mark} **{s['store']}**")
except:
    st.info("No checks have run yet.")
