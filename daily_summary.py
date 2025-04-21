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

# First try to get runs from today
runs = [r for r in hist["runs"] if r and r[0]["timestamp"].startswith(today)]

# If no runs today, use the most recent runs instead
if not runs and hist["runs"]:
    # Use the most recent run date
    latest_run = hist["runs"][-1]
    latest_date = latest_run[0]["timestamp"].split("T")[0]
    runs = [r for r in hist["runs"] if r and r[0]["timestamp"].startswith(latest_date)]

if not runs:
    print("No runs found in history."); exit(0)

html = "<h2>🥜 Bamba Daily Chuckle & Check</h2>"
for run in runs:
    ts = run[0]["timestamp"].split("T")[1][:8]
    html += f"<h3>🔍 Checked at {ts} AWST</h3>"
    
    for store_data in run:
        store_name = store_data["store"]
        mark = "✅" if store_data["available"] else "❌"
        html += f"<h4>{mark} {store_name}</h4>"
        
        if not store_data["products"]:
            html += "<p>No Bamba products found at this store.</p>"
            continue
        
        html += "<ul>"
        for product in store_data["products"]:
            # Extract size from product name if available
            size = "Unknown size"
            if "|" in product["name"]:
                product_name = product["name"].split("|")[0].strip()
                size = product["name"].split("|")[1].strip()
            else:
                product_name = product["name"]
                
            status = "✅ Available" if product["available"] else "❌ Currently Unavailable"
            html += f"<li><strong>{product_name}</strong> ({size}) - {status}<br>Price: {product['price']}</li>"
        html += "</ul>"
    html += "<hr>"

# Add the closing message
html += "<p>That's all for today! Keep it nutty 🤪</p>"

# Add unsubscribe link
if use_supabase:
    try:
        # For each subscriber, generate a unique unsubscribe token
        for sub in daily_subscribers:
            from supabase_client import generate_unsubscribe_token
            unsubscribe_token = generate_unsubscribe_token(sub["email"])
            # Use the URL of your Streamlit app
            app_url = "https://bambot.streamlit.app/"
            sub_html = html + f'<p style="color: #777; font-size: 0.8em; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 10px;">Don\'t want these emails? <a href="{app_url}?token={unsubscribe_token}">Unsubscribe</a></p>'
            
            # Send the email with the unsubscribe link
            subject = "🌰 Your Bamba Daily Roundup is here!"
            send_email(sub["email"], subject, sub_html)
    except Exception as e:
        print(f"Error generating unsubscribe link: {e}")
