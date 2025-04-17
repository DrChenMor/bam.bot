import os, json
from datetime import date
from cryptography.fernet import Fernet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─── SETUP ───────────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    print("⚠️ FERNET_KEY missing"); exit(1)
f = Fernet(FERNET_KEY.encode())

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
FROM_EMAIL  = os.getenv("FROM_EMAIL", SMTP_USER)

def send_email(to, subj, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subj
    msg["From"]    = FROM_EMAIL
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(FROM_EMAIL, to, msg.as_string())
    print("✉️ Sent to", to)

# ─── BUILD SUMMARY ───────────────────────────────────────────
hist = json.load(open("history.json"))
today = date.today().isoformat()
runs  = [r for r in hist["runs"] if r and r[0]["timestamp"].startswith(today)]
if not runs:
    print("No runs today."); exit(0)

html = "<h2>🥜 Bamba Daily Chuckle & Check</h2>"
for run in runs:
    ts = run[0]["timestamp"].split("T")[1][:8]
    html += f"<h3>🔍 Checked at {ts} AWST</h3><ul>"
    for s in run:
        mark = "✅" if s["available"] else "❌"
        html += f"<li>{mark} {s['store']} — saw {len(s['products'])} products</li>"
    html += "</ul>"
html += "<p>That's all for today! Keep it nutty 🤪</p>"

# ─── EMAIL DAILY SUBSCRIBERS ─────────────────────────────────
subs = json.load(open("subscribers.json"))["users"]
for u in subs:
    if u["mode"]=="daily":
        try:
            email = f.decrypt(u["token"].encode()).decode()
        except:
            continue
        subject = "🌰 Your Bamba Daily Roundup is here!"
        send_email(email, subject, html)
