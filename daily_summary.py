import os, json
from datetime import date
import pytz
from datetime import datetime
from cryptography.fernet import Fernet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random

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

# ─── BUILD OPTIMIZED SUMMARY ─────────────────────────────────
def build_daily_summary():
    """Build optimized daily summary to avoid Gmail clipping."""
    hist = json.load(open("history.json"))
    today = get_awst_time().date().isoformat()
    
    # Try to get runs from today first
    runs = [r for r in hist["runs"] if r and r[0]["timestamp"].startswith(today)]
    
    # If no runs today, use the most recent runs instead
    if not runs and hist["runs"]:
        latest_run = hist["runs"][-1]
        latest_date = latest_run[0]["timestamp"].split("T")[0]
        runs = [r for r in hist["runs"] if r and r[0]["timestamp"].startswith(latest_date)]
    
    if not runs:
        print("No runs found in history."); exit(0)
    
    # Only use the latest run to reduce email size
    latest_run = runs[-1]
    
    # Define CSS once to reduce email size
    css = """
    <style>
    .bamba-email{font-family:Arial,sans-serif;max-width:600px;margin:0 auto}
    .bamba-header{font-size:20px;font-weight:bold;margin:10px 0}
    .bamba-subheader{font-size:16px;margin:5px 0}
    .bamba-store{padding:5px 0;margin:5px 0}
    .bamba-product{margin:4px 0}
    .available{color:green}
    .unavailable{color:#d9534f}
    .bamba-fact{background-color:#f8f9fa;padding:8px;border-left:4px solid #ffc107;margin:8px 0}
    </style>
    """
    
    # Build email HTML with minimal tags and whitespace
    html = f"{css}<div class='bamba-email'><h2 class='bamba-header'>🥜 Bamba Daily Chuckle & Check</h2>"
    
    # Add timestamp
    ts = latest_run[0]["timestamp"].split("T")[1][:8]
    date_str = latest_run[0]["timestamp"].split("T")[0]
    html += f"<p>📅 {date_str} | 🕒 Latest check at {ts} AWST</p>"
    
    # Add store data compactly
    for store_data in latest_run:
        store_name = store_data["store"]
        available_mark = "✅" if store_data["available"] else "❌"
        
        html += f"<div class='bamba-store'><h3 class='bamba-subheader'>{available_mark} {store_name}</h3>"
        
        if not store_data["products"]:
            html += "<p>No products found</p></div>"
            continue
        
        # Display products compactly
        html += "<ul style='margin:0;padding-left:20px'>"
        for product in store_data["products"]:
            # Get size and product name
            if "|" in product["name"]:
                product_name, size = product["name"].split("|", 1)
                product_name = product_name.strip()
                size = size.strip()
            else:
                product_name = product["name"]
                size = "Unknown size"
            
            # Set status with appropriate style
            status_class = "available" if product["available"] else "unavailable"
            status_icon = "✅" if product["available"] else "❌"
            
            html += f"<li class='bamba-product'><span class='{status_class}'>{status_icon} <b>{product_name}</b> ({size})</span><br>Price: {product['price']}</li>"
        
        html += "</ul></div>"
    
    # Add closing message and simple footer
    html += "<p>That's all for today! Keep it nutty 🤪</p>"
    html += "<p style='color:#777;margin-top:10px;font-size:14px'>Your BamBot WA</p>"
    
    return html

# ─── MAIN EXECUTION ───────────────────────────────────────────
# Build optimized email content
main_html = build_daily_summary()

# Send emails to subscribers
if use_supabase:
    # Get daily subscribers
    daily_subscribers = get_subscribers(mode="daily")
    
    # Send to each subscriber with customizations
    for sub in daily_subscribers:
        try:
            email_parts = []
            
            # Add Bamba fact if subscribed (before main content for better visibility)
            if sub.get("include_facts", False):
                fact = get_random_bamba_fact()
                email_parts.append(f"<div class='bamba-fact'><h3>🌟 Bamba Fact of the Day</h3><p>{fact}</p></div>")
            
            # Add main content
            email_parts.append(main_html)
            
            # Add unsubscribe link
            try:
                unsubscribe_token = generate_unsubscribe_token(sub["email"])
                app_url = "https://bambot.streamlit.app/"
                email_parts.append(f"<p style='color:#777;font-size:12px;margin-top:10px'>Don't want these emails? <a href='{app_url}?token={unsubscribe_token}'>Unsubscribe</a></p>")
            except Exception as e:
                print(f"Error generating unsubscribe link: {e}")
            
            # Send complete email
            complete_html = "".join(email_parts)
            send_email(sub["email"], "🌰 Your Bamba Daily Roundup is here!", complete_html)
        except Exception as e:
            print(f"Error sending email to {sub.get('email', 'unknown')}: {e}")
else:
    # Fall back to local file approach
    subfile = "subscribers.json"
    if os.path.exists(subfile):
        data = json.load(open(subfile))
        for user in data.get("users", []):
            if user.get("mode") == "daily":
                try:
                    email = f.decrypt(user["token"].encode()).decode()
                    send_email(email, "🌰 Your Bamba Daily Roundup is here!", main_html)
                except Exception as e:
                    print(f"Error sending to subscriber: {e}")
    else:
        print("No subscribers.json file found.")
