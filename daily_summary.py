import os, json
from datetime import date
from cryptography.fernet import Fernet
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ────────────────────────────────────────────────────────────
# SETUP
# ────────────────────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    print("⚠️ FERNET_KEY not set. Exiting."); exit(1)
f = Fernet(FERNET_KEY.encode())

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
FROM_EMAIL  = os.getenv("FROM_EMAIL", SMTP_USER)

def send_email(to_email, subject, html_content):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = FROM_EMAIL
    msg["To"]      = to_email
    msg.attach(MIMEText(html_content, "html"))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(FROM_EMAIL, to_email, msg.as_string())
    print("✉️ Summary to", to_email)

# ────────────────────────────────────────────────────────────
# DAILY SUMMARY LOGIC
# ────────────────────────────────────────────────────────────
hist = json.load(open("history.json"))
today = date.today().isoformat()
runs  = [r for r in hist["runs"] if r and r[0]["timestamp"].startswith(today)]
if not runs:
    print("No runs today; skipping."); exit(0)

html = "<h2>🥜 Bamba Daily Roundup</h2>"
for run in runs:
    ts = run[0]["timestamp"].split("T")[1][:8]
    html += f"<h3>Checked at {ts} AWST</h3><ul>"
    for s in run:
        mark = "✅" if s["available"] else "❌"
        html += f"<li>{mark} {s['store']}</li>"
    html += "</ul>"
html += "<p>Stay nutty! 🤪</p>"

subs = json.load(open("subscribers.json"))["users"]
for u in subs:
    if u["mode"]=="daily":
        try:
            email = f.decrypt(u["token"].encode()).decode()
        except:
            continue
        send_email(email,
                   "🌰 Your Bamba Daily Report",
                   html)
