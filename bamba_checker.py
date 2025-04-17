#!/usr/bin/env python3
"""
Hourly Bamba Checker with SMTP‑email notifications.

– Scrapes each store once/hour ±10 min between 07–23 AWST
– Sends immediate “funny” email via SMTP to encrypted subscribers
– Appends each run to history.json
"""

import os, sys, time, random, json
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from cryptography.fernet import Fernet
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ────────────────────────────────────────────────────────────
# 1) LOAD & DECRYPT SUBSCRIBERS
# ────────────────────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    print("⚠️ FERNET_KEY not set. Exiting."); sys.exit(1)
f = Fernet(FERNET_KEY.encode())

def load_subscribers():
    out = []
    try:
        data = json.load(open("subscribers.json"))
    except FileNotFoundError:
        return out
    for u in data.get("users", []):
        try:
            email = f.decrypt(u["token"].encode()).decode()
            out.append({"email": email, "mode": u["mode"]})
        except:
            pass
    return out

# ────────────────────────────────────────────────────────────
# 2) SMTP HELPER
# ────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────
# 3) STORES & SCHEDULING
# ────────────────────────────────────────────────────────────
STORES = [
    {"name":"Dianella",   "url":"https://www.coles.com.au/find-stores/coles/wa/dianella-256"},
    {"name":"Mirrabooka", "url":"https://www.coles.com.au/find-stores/coles/wa/mirrabooka-421"},
]

def within_hours(start=7, end=23):
    h = datetime.now().hour
    return start <= h < end

def next_sleep():
    now    = datetime.now()
    next_h = now.replace(minute=0,second=0,microsecond=0) + timedelta(hours=1)
    off    = random.uniform(-10,10)  # ±10 min
    run_at = next_h + timedelta(minutes=off)
    secs   = (run_at-now).total_seconds()
    if secs<0: secs=60
    print(f"\n⏱️ Next run ~{run_at.strftime('%H:%M:%S')} (in {secs/60:.1f} min)")
    return secs

# ────────────────────────────────────────────────────────────
# 4) SCRAPING HELPERS
# ────────────────────────────────────────────────────────────
def human_delay(a=500,b=1500):
    time.sleep(random.uniform(a/1000,b/1000))

def take_screenshot(page,store,step):
    d="coles_screenshots"; os.makedirs(d,exist_ok=True)
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    path=f"{d}/{store}_{step}_{ts}.png"
    page.screenshot(path=path); print("  📸",path)

def check_store(store):
    print(f"\n🔄 Checking {store['name']} at {datetime.now().strftime('%H:%M:%S')}…")
    res={"store":store["name"],
         "timestamp":datetime.now().isoformat(),
         "available":False,
         "products":[]}

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
            # 1) Store → set location
            page.goto(store["url"],timeout=60000)
            take_screenshot(page,store["name"],"1_store")
            page.wait_for_selector("text=Set location",timeout=10000)
            human_delay(); page.click("text=Set location")
            human_delay(); take_screenshot(page,store["name"],"2_loc")

            # 2) Homepage → accept cookies
            page.goto("https://www.coles.com.au",timeout=60000)
            try: page.click("button:has-text('Accept All Cookies')",timeout=5000)
            except: pass
            take_screenshot(page,store["name"],"3_home")

            # 3) Search “bamba”
            page.fill("input[placeholder*='Search']","bamba")
            human_delay(); page.click("div[role='option']")
            page.wait_for_url("**/search/products**",timeout=15000)
            human_delay(); take_screenshot(page,store["name"],"4_res")

            # 4) Scrape tiles
            page.wait_for_selector("[data-testid='product-tiles']",timeout=15000)
            tiles=page.locator("section[data-testid='product-tile']").all()
            if not tiles:
                print("  ❓ No tiles!")
            else:
                for t in tiles:
                    te=t.locator("h2.product__title, h3")
                    title=te.first.inner_text().strip() if te.count() else "Unknown"
                    pe=t.locator("span.price__value, span.price, [data-testid='product-pricing']")
                    price=pe.first.inner_text().strip() if pe.count() else "n/a"
                    un=t.locator("[data-testid='large-screen-currently-unavailable-prompt']").count()>0
                    ok=not un
                    mark="✅" if ok else "❌"
                    res["products"].append({"name":title,"price":price,"available":ok})
                    if ok: res["available"]=True
                    print(f"  {mark} {title} @ {price}")

        except Exception as e:
            print("  ⚠️ Error:",e)
            take_screenshot(page,store["name"],"error")
        finally:
            browser.close()
            print(f"  🧹 Closed {store['name']}")

    return res

# ────────────────────────────────────────────────────────────
# 5) HISTORY
# ────────────────────────────────────────────────────────────
def append_history(runs):
    hf="history.json"
    hist={"runs":[]}
    if os.path.exists(hf):
        hist=json.load(open(hf))
    hist["runs"].append(runs)
    hist["runs"]=hist["runs"][-30:]
    json.dump(hist,open(hf,"w"),indent=2)

# ────────────────────────────────────────────────────────────
# 6) MAIN LOOP
# ────────────────────────────────────────────────────────────
def main():
    while True:
        if within_hours(7,23):
            subs=load_subscribers()
            allr=[]
            for s in STORES:
                r=check_store(s); allr.append(r)
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
                time.sleep(random.uniform(2,5)*60)
            append_history(allr)
        else:
            print(f"⏰ {datetime.now().hour}:00 — outside 07–23 AWST, skipping.")
        time.sleep(next_sleep())

if __name__=="__main__":
    main()
