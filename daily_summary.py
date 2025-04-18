import os, json
from datetime import date
import pytz
from datetime import datetime
from cryptography.fernet import Fernet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─── SETUP ───────────────────────────────────────────────────
def get_awst_time():
    """Get current time in Australian Western Standard Time (AWST)."""
    utc_now = datetime.now(pytz.utc)
    awst = pytz.timezone('Australia/Perth')  # Perth uses AWST
    return utc_now.astimezone(awst)

# Try to use Supabase first, fall back to local file if not available
try:
    from supabase_client import get_subscribers
    use_supabase = True
    print("Using Supabase for subscribers")
except ImportError:
    use_supabase = False
    print("Supabase not available, using local file")
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
today = get_awst_time().date().isoformat()
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
if use_supabase:
    # Get subscribers from Supabase
    daily_subscribers = get_subscribers(mode="daily")
    for sub in daily_subscribers:
        subject = "🌰 Your Bamba Daily Roundup is here!"
        send_email(sub["email"], subject, html)
else:
    # Fall back to local file
    subs = json.load(open("subscribers.json"))["users"]
    for u in subs:
        if u["mode"]=="daily":
            try:
                email = f.decrypt(u["token"].encode()).decode()
            except:
                continue
            subject = "🌰 Your Bamba Daily Roundup is here!"
            send_email(email, subject, html)
