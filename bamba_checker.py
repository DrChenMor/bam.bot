#!/usr/bin/env python3
"""
One‑shot Bamba Availability Checker.
– Run once (scheduled by GitHub Actions cron).
– Scrapes multiple Coles stores for Bamba.
– Sends “funny” immediate email via SMTP.
– Appends each run to history.json.
"""

import os, sys, time, random, json
from datetime import datetime
from playwright.sync_api import sync_playwright
from cryptography.fernet import Fernet
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─────────────────────────────────────────────────────────────
# 1) LOAD & DECRYPT SUBSCRIBERS
# ─────────────────────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    print("⚠️ FERNET_KEY not set; exiting.")
    sys.exit(1)
fernet = Fernet(FERNET_KEY.encode())

def load_subscribers():
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
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    path=f"{folder}/{store}_{step}_{ts}.png"
    page.screenshot(path=path); print("  📸",path)

def check_store(store):
    print(f"\n🔄 Checking {store['name']} at {datetime.now().strftime('%H:%M:%S')}…")
    result = {
        "store":     store["name"],
        "timestamp": datetime.now().isoformat(),
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

            # 3) Search “bamba”
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
# 6) MAIN
# ─────────────────────────────────────────────────────────────
def main():
    subs = load_subscribers()
    allr = []
    for store in STORES:
        res = check_store(store)
        allr.append(res)
        if res["available"]:
            for u in subs:
                if u["mode"]=="immediate":
                    subject = f"🎉 Bamba Alert: {res['store']} is stocked!"
                    body    = (
                        f"<h1>Holy Peanut! 🌰</h1>"
                        f"<p>Bamba is in stock at <b>{res['store']}</b> as of "
                        f"{res['timestamp'].split('T')[1][:8]} AWST.</p>"
                        "<p>Time to snack! 🤖</p>"
                    )
                    send_email(u["email"], subject, body)
        time.sleep(random.uniform(2,5)*60)
    append_history(allr)
    print("\n✅ Done.")

if __name__=="__main__":
    main()
