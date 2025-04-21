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

# Collection of Bamba facts for the enhanced subscription
BAMBA_FACTS = [
    "Bamba was first produced in Israel in 1964 by the Osem company.",
    "Bamba is made from peanut butter-flavored puffed corn and contains 50% peanuts.",
    "Studies suggest early exposure to peanut products like Bamba may help prevent peanut allergies in children.",
    "Bamba is the best-selling snack in Israel, with 90% of Israeli families buying it regularly.",
    "The Bamba Baby, the brand's mascot since 1992, is a diapered baby with red hair.",
    "Bamba contains no preservatives, food coloring, or artificial flavors.",
    "The original Bamba factory is located in Holon, Israel.",
    "Over 1 million bags of Bamba are produced daily.",
    "Sweet Bamba varieties include strawberry, halva, and nougat flavors.",
    "In Israel, Bamba is often a baby's first solid food."
]

def get_random_bamba_fact():
    """Return a random fact about Bamba."""
    import random
    return random.choice(BAMBA_FACTS)

# Try to use Supabase first, fall back to local file if not available
try:
    from supabase_client import get_subscribers, generate_unsubscribe_token
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

# Add footer
html += """
<div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;">
    <p style="color: #777;">Your BamBot WA</p>
</div>
"""

# ─── EMAIL DAILY SUBSCRIBERS ─────────────────────────────────
if use_supabase:
    # Get subscribers from Supabase
    daily_subscribers = get_subscribers(mode="daily")
    
    # Send to each subscriber with unique unsubscribe link
    for sub in daily_subscribers:
        try:
            # Add a Bamba fact if subscribed
            fact_section = ""
            if sub.get("include_facts", False):
                fact = get_random_bamba_fact()
                fact_section = f"""
                <div style='background-color: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #ffc107;'>
                <h3>🌟 Bamba Fact of the Day</h3>
                <p>{fact}</p>
                </div>
                """
            
            # Add unsubscribe link
            try:
                unsubscribe_token = generate_unsubscribe_token(sub["email"])
                # Use the URL of your Streamlit app
                app_url = "https://bambot.streamlit.app/"
                unsubscribe_section = f'<p style="color: #777; font-size: 0.8em; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 10px;">Don\'t want these emails? <a href="{app_url}?token={unsubscribe_token}">Unsubscribe</a></p>'
            except Exception as e:
                print(f"Error generating unsubscribe link: {e}")
                unsubscribe_section = ""
            
            # Complete email with all sections
            complete_html = fact_section + html + unsubscribe_section
            
            # Send the email with customized content based on preferences
            subject = "🌰 Your Bamba Daily Roundup is here!"
            send_email(sub["email"], subject, complete_html)
        except Exception as e:
            print(f"Error sending email to {sub.get('email', 'unknown')}: {e}")
else:
    # Fall back to local file subscribers approach
    subfile = "subscribers.json"
    if os.path.exists(subfile):
        data = json.load(open(subfile))
        for user in data.get("users", []):
            if user.get("mode") == "daily":
                try:
                    email = f.decrypt(user["token"].encode()).decode()
                    send_email(email, "🌰 Your Bamba Daily Roundup is here!", html)
                except Exception as e:
                    print(f"Error sending to subscriber: {e}")
    else:
        print("No subscribers.json file found.")
