#!/usr/bin/env python3
"""
One‑shot Bamba Availability Checker.
– Run once (scheduled by GitHub Actions cron).
– Scrapes multiple Coles stores for Bamba.
– Sends "funny" immediate email via SMTP.
– Appends each run to history.json.
"""

import os, sys, time, random, json
from datetime import datetime
import pytz
from playwright.sync_api import sync_playwright
from cryptography.fernet import Fernet
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# ─────────────────────────────────────────────────────────────
# 0) TIMEZONE & OPERATING HOURS CHECK
# ─────────────────────────────────────────────────────────────
def get_awst_time():
    """Get current time in Australian Western Standard Time (AWST)."""
    utc_now = datetime.now(pytz.utc)
    awst = pytz.timezone('Australia/Perth')  # Perth uses AWST
    return utc_now.astimezone(awst)

def is_within_operating_hours(config):
    """Check if current AWST time is within operating hours."""
    awst_now = get_awst_time()
    hour = awst_now.hour
    print(f"Current AWST time: {awst_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Operating hours: {config['operating_hours']['start']}:00-{config['operating_hours']['end']}:00")
    return config["operating_hours"]["start"] <= hour < config["operating_hours"]["end"]

# ─────────────────────────────────────────────────────────────
# 1) LOAD SUBSCRIBERS (SUPABASE VERSION)
# ─────────────────────────────────────────────────────────────
def load_subscribers():
    """Load subscribers from Supabase or fall back to local file."""
    try:
        # Try to load from Supabase first
        from supabase_client import get_subscribers
        subs = get_subscribers(mode="immediate")
        print(f"✅ Loaded {len(subs)} subscribers from Supabase")
        return subs
    except Exception as e:
        print(f"⚠️ Error loading from Supabase: {e}")
        print("Falling back to local file...")
        
        # Fall back to local file if Supabase fails
        FERNET_KEY = os.getenv("FERNET_KEY")
        if not FERNET_KEY:
            print("⚠️ FERNET_KEY not set; exiting.")
            sys.exit(1)
        fernet = Fernet(FERNET_KEY.encode())
        
        out = []
        try:
            data = json.load(open("subscribers.json"))
        except FileNotFoundError:
            return out
        for u in data.get("users", []):
            try:
                email = fernet.decrypt(u["token"].encode()).decode()
                out.append({ "email": email, "mode": u["mode"] })
            except:
                pass
        print(f"✅ Loaded {len(out)} subscribers from local file")
        return out

# ─────────────────────────────────────────────────────────────
# 2) SMTP EMAIL HELPER
# ─────────────────────────────────────────────────────────────
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
    print(f"  ✉️ Email sent to {to_email}")

# ─────────────────────────────────────────────────────────────
# 3) YOUR STORES
# ─────────────────────────────────────────────────────────────
STORES = [
    {"name":"Dianella",   "url":"https://www.coles.com.au/find-stores/coles/wa/dianella-256"},
    {"name":"Mirrabooka", "url":"https://www.coles.com.au/find-stores/coles/wa/mirrabooka-314"},
]

# ─────────────────────────────────────────────────────────────
# 4) SCRAPING HELPERS
# ─────────────────────────────────────────────────────────────
def human_delay(a=500,b=1500):
    time.sleep(random.uniform(a/1000,b/1000))

def take_screenshot(page,store,step):
    folder="coles_screenshots"; os.makedirs(folder,exist_ok=True)
    ts=get_awst_time().strftime("%Y%m%d_%H%M%S")
    path=f"{folder}/{store}_{step}_{ts}.png"
    page.screenshot(path=path); print("  📸",path)

def check_store(store):
    awst_now = get_awst_time()
    print(f"\n🔄 Checking {store['name']} at {awst_now.strftime('%H:%M:%S AWST')}…")
    result = {
        "store":     store["name"],
        "timestamp": awst_now.isoformat(),
        "available": False,
        "products":  []
    }
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,slow_mo=100)
        ctx=browser.new_context(
            viewport={"width":1280,"height":920},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page=ctx.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        try:
            # 1) Open store & Set location
            page.goto(store["url"], timeout=60000)
            take_screenshot(page, store["name"], "1_store")
            page.wait_for_selector("text=Set location", timeout=10000)
            human_delay(); page.click("text=Set location")
            human_delay(); take_screenshot(page, store["name"], "2_loc")

            # 2) Home & cookies
            page.goto("https://www.coles.com.au", timeout=60000)
            try: page.click("button:has-text('Accept All Cookies')", timeout=5000)
            except: pass
            take_screenshot(page, store["name"], "3_home")

            # 3) Search "bamba"
            page.fill("input[placeholder*='Search']", "bamba")
            human_delay(); page.click("div[role='option']")
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(); take_screenshot(page, store["name"], "4_res")

            # 4) Scrape each tile
            page.wait_for_selector("[data-testid='product-tiles']", timeout=15000)
            tiles = page.locator("section[data-testid='product-tile']").all()
            if not tiles:
                print("  ❓ No product tiles found!")
            else:
                for t in tiles:
                    title_el = t.locator("h2.product__title, h3")
                    title    = title_el.first.inner_text().strip() if title_el.count() else "Unknown"
                    price_el = t.locator("span.price__value, span.price, [data-testid='product-pricing']")
                    price    = price_el.first.inner_text().strip() if price_el.count() else "n/a"
                    unavailable = t.locator("[data-testid='large-screen-currently-unavailable-prompt']").count()>0
                    available   = not unavailable
                    mark        = "✅" if available else "❌"
                    result["products"].append({"name":title,"price":price,"available":available})
                    if available: result["available"] = True
                    print(f"  {mark} {title} @ {price}")
        except Exception as e:
            print("  ⚠️ Error:",e)
            take_screenshot(page, store["name"], "error")
        finally:
            browser.close()
            print(f"  🧹 Closed browser for {store['name']}")
    return result

# ─────────────────────────────────────────────────────────────
# 5) APPEND TO HISTORY
# ─────────────────────────────────────────────────────────────
def append_history(run_results):
    hf = "history.json"
    history = {"runs": []}
    if os.path.exists(hf):
        history = json.load(open(hf))
    history["runs"].append(run_results)
    history["runs"] = history["runs"][-30:]
    with open(hf,"w") as f:
        json.dump(history, f, indent=2)

# ─────────────────────────────────────────────────────────────
# 6) CHANGE DETECTION
# ─────────────────────────────────────────────────────────────
def detect_changes(current_results, history):
    """Detect changes in product availability between current and previous check.
    
    Returns:
        Dictionary of changes per store and product
    """
    changes = {}
    
    # If no history yet, consider everything as new
    if not history["runs"]:
        for store_data in current_results:
            store_name = store_data["store"]
            changes[store_name] = []
            
            for product in store_data["products"]:
                changes[store_name].append({
                    "product": product["name"],
                    "change_type": "new" if product["available"] else "unavailable",
                    "price": product["price"],
                    "available": product["available"]
                })
        return changes
    
    # Get the most recent previous check
    prev_check = history["runs"][-1]
    
    # Create a lookup for easier comparison
    prev_status = {}
    for store_data in prev_check:
        store_name = store_data["store"]
        prev_status[store_name] = {}
        
        for product in store_data["products"]:
            prev_status[store_name][product["name"]] = {
                "available": product["available"],
                "price": product["price"]
            }
    
    # Now compare current results with previous
    for store_data in current_results:
        store_name = store_data["store"]
        changes[store_name] = []
        
        for product in store_data["products"]:
            product_name = product["name"]
            
            # If product existed before
            if store_name in prev_status and product_name in prev_status[store_name]:
                # Check if availability changed
                prev_available = prev_status[store_name][product_name]["available"]
                curr_available = product["available"]
                
                if prev_available != curr_available:
                    change_type = "now_available" if curr_available else "now_unavailable"
                    changes[store_name].append({
                        "product": product_name,
                        "change_type": change_type,
                        "price": product["price"],
                        "available": curr_available
                    })
            else:
                # New product
                changes[store_name].append({
                    "product": product_name,
                    "change_type": "new" if product["available"] else "unavailable",
                    "price": product["price"],
                    "available": product["available"]
                })
    
    return changes

# ─────────────────────────────────────────────────────────────
# 7) CONSOLIDATED EMAIL NOTIFICATIONS
# ─────────────────────────────────────────────────────────────
def send_notifications(store_results, subscribers):
    """Send notifications to subscribers based on their preferences."""
    
    # Load history to detect changes
    history = {"runs": []}
    if os.path.exists("history.json"):
        history = json.load(open("history.json"))
    
    # Detect changes since last check
    changes = detect_changes(store_results, history)
    
    # Build a consolidated notification for each subscriber
    for subscriber in subscribers:
        # Skip subscribers who want change notifications if nothing changed
        if subscriber.get("notify_on_change_only", True):  # Default is now TRUE
            has_relevant_changes = False
            for store_name, store_changes in changes.items():
                if store_changes and (subscriber.get("store_preference", "both") == "both" or 
                                     subscriber.get("store_preference", "both") == store_name.lower()):
                    has_relevant_changes = True
                    break
            
            if not has_relevant_changes:
                continue
        
        # Create consolidated email content
        subject = "🥜 Bamba Status Update"
        
        # Start building the email
        body = "<h1>Bamba Status Update</h1>"
        
        # Add a Bamba fact if subscribed
        if subscriber.get("include_facts", False):
            fact = get_random_bamba_fact()
            body += f"<div style='background-color: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #ffc107;'>"
            body += f"<h3>🌟 Bamba Fact of the Day</h3>"
            body += f"<p>{fact}</p>"
            body += "</div>"
        
        any_available = False
        
        # Add store sections based on preferences
        for store_data in store_results:
            store_name = store_data["store"]
            
            # Skip if not interested in this store
            if subscriber.get("store_preference", "both") != "both" and subscriber.get("store_preference", "both") != store_name.lower():
                continue
            
            # Get timestamp in AWST
            ts = store_data["timestamp"].split("T")[1][:8]
            
            body += f"<h2>{store_name} (Checked at {ts} AWST)</h2>"
            
            if not store_data["products"]:
                body += "<p>No Bamba products found at this store.</p>"
                continue
            
            body += "<ul>"
            
            for product in store_data["products"]:
                # Extract size from product name
                size = "Unknown"
                if "|" in product["name"]:
                    size = product["name"].split("|")[1].strip()
                
                product_name = product["name"].split("|")[0].strip() if "|" in product["name"] else product["name"]
                
                # Skip if not interested in this size
                size_pref = subscriber.get("product_size_preference", "both")
                if size_pref != "both":
                    if size_pref == "25g" and "25g" not in size:
                        continue
                    if size_pref == "100g" and "100g" not in size:
                        continue
                
                status = "✅ Available" if product["available"] else "❌ Currently Unavailable"
                
                # Highlight changes if notify_on_change_only is True
                highlight = ""
                for change in changes.get(store_name, []):
                    if change["product"] == product["name"]:
                        if change["change_type"] in ["now_available", "new"] and product["available"]:
                            highlight = " - <strong style='color: green;'>JUST BECAME AVAILABLE!</strong>"
                            any_available = True
                        elif change["change_type"] == "now_unavailable":
                            highlight = " - <strong style='color: red;'>JUST SOLD OUT!</strong>"
                
                body += f"<li><strong>{product_name}</strong> ({size}) - {status}{highlight}<br>Price: {product['price']}</li>"
            
            body += "</ul>"
        
        # Update subject line if anything is available
        if any_available:
            subject = "🎉 Bamba Alert: Now Available!"
        
        body += "<p>Happy snacking! 🤖</p>"
        
        # Add unsubscribe link
        try:
            from supabase_client import generate_unsubscribe_token
            unsubscribe_token = generate_unsubscribe_token(subscriber["email"])
            # Use the URL of your Streamlit app
            app_url = "https://bambot.streamlit.app/"
            body += f'<p style="color: #777; font-size: 0.8em; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 10px;">Don\'t want these emails? <a href="{app_url}?token={unsubscribe_token}">Unsubscribe</a></p>'
        except Exception as e:
            print(f"Error generating unsubscribe link: {e}")
        
        # Send the email
        send_email(subscriber["email"], subject, body)
        print(f"  ✉️ Consolidated email sent to {subscriber['email']}")
        
# ─────────────────────────────────────────────────────────────
# 8) MAIN
# ─────────────────────────────────────────────────────────────
def main():
    # Load config and check operating hours
    config = json.load(open("config.json"))
    
    # Check if we're within operating hours
    if not is_within_operating_hours(config):
        print(f"⏰ Outside operating hours. Current AWST time: {get_awst_time().strftime('%H:%M')}. Exiting.")
        sys.exit(0)  # Exit gracefully, not as an error
    
    # Load subscribers
    subs = load_subscribers()
    
    # Check stores
    allr = []
    for store in STORES:
        res = check_store(store)
        allr.append(res)
        time.sleep(random.uniform(2,5))  # Short delay for testing
    
    # Send consolidated notifications based on subscriber preferences
    send_notifications(allr, subs)
    
    # Save results to history
    append_history(allr)
    print("\n✅ Done.")

if __name__=="__main__":
    main()
