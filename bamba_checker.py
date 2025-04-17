#!/usr/bin/env python3
"""
One‑shot Bamba Availability Checker.
– Run once, then exit.
– Scheduled by GitHub Actions cron.
"""

import os, sys, time, random, json
from datetime import datetime
from playwright.sync_api import sync_playwright
from cryptography.fernet import Fernet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 1) Load & decrypt subscribers
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    print("⚠️ FERNET_KEY not set"); sys.exit(1)
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
            out.append({"email": email, "mode": u["mode"]})
        except:
            pass
    return out

# 2) SMTP helper
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
    print(f"✉️ Sent to {to}")

# 3) Stores
STORES = [
    {"name":"Dianella",   "url":"https://www.coles.com.au/find-stores/coles/wa/dianella-256"},
    {"name":"Mirrabooka", "url":"https://www.coles.com.au/find-stores/coles/wa/mirrabooka-314"},
]

# 4) Scrape one store
def human_delay(a=500,b=1500):
    time.sleep(random.uniform(a/1000,b/1000))

def take_screenshot(page, store, step):
    folder = "coles_screenshots"
    os.makedirs(folder, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{folder}/{store}_{step}_{ts}.png"
    page.screenshot(path=path)
    print("📸", path)

def check_store(store):
    print(f"\n🔄 Checking {store['name']}…")
    res = {"store":store["name"],
           "timestamp":datetime.now().isoformat(),
           "available":False,
           "products":[]}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        try:
            # 1) Set location
            page.goto(store["url"], timeout=60000)
            take_screenshot(page, store["name"], "1_store")
            page.wait_for_selector("text=Set location", timeout=10000)
            human_delay(); page.click("text=Set location")
            human_delay(); take_screenshot(page, store["name"], "2_loc")

            # 2) Homepage + cookies
            page.goto("https://www.coles.com.au", timeout=60000)
            try: page.click("button:has-text('Accept All Cookies')", timeout=5000)
            except: pass
            take_screenshot(page, store["name"], "3_home")

            # 3) Search “bamba”
            page.fill("input[placeholder*='Search']", "bamba")
            human_delay(); page.click("div[role='option']")
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(); take_screenshot(page, store["name"], "4_res")

            # 4) Scrape tiles
            tiles = page.locator("section[data-testid='product-tile']").all()
            if not tiles:
                print("❓ No tiles")
            else:
                for t in tiles:
                    te = t.locator("h2.product__title, h3")
                    title = te.first.inner_text().strip() if te.count() else "Unknown"
                    pe = t.locator("span.price__value, span.price, [data-testid='product-pricing']")
                    price = pe.first.inner_text().strip() if pe.count() else "n/a"
                    unavailable = t.locator(
                        "[data-testid='large-screen-currently-unavailable-prompt']"
                    ).count() > 0
                    ok = not unavailable
                    mark = "✅" if ok else "❌"
                    res["products"].append({"name":title,"price":price,"available":ok})
                    if ok: 
                        res["available"] = True
                    print(f"{mark} {title} @ {price}")
        except Exception as e:
            print("⚠️", e)
            take_screenshot(page, store["name"], "error")
        finally:
            browser.close()

    return res

# 5) Append history
def append_history(runs):
    hf = "history.json"
    hist = {"runs": []}
    if os.path.exists(hf):
        hist = json.load(open(hf))
    hist["runs"].append(runs)
    hist["runs"] = hist["runs"][-30:]
    json.dump(hist, open(hf,"w"), indent=2)

# 6) Main
def main():
    # optional jitter 0–5 min so your runs aren’t always exactly on the hour
    time.sleep(random.uniform(0,300))

    subs = load_subscribers()
    allr = []
    for store in STORES:
        r = check_store(store)
        allr.append(r)
         if r["available"]:
             for u in subs:
                  if u["mode"]=="immediate":
                         # Funny email
                         sub=f"🎉 Bamba Alert: {r['store']} has snacks!"
                         body=(
                           f"<h1>Holy Peanut! 🌰</h1>"
                           f"<p>Bamba is in stock at <b>{r['store']}</b> "
                           f"as of {r['timestamp'].split('T')[1][:8]} AWST.</p>"
                           "<p>From your neighborhood BamBot</p>"
                         )
                         send_email(u["email"], sub, body)
        time.sleep(random.uniform(120,300))  # 2–5 min between stores
    append_history(allr)
    print("✅ Done – exiting.")

if __name__=="__main__":
    main()
