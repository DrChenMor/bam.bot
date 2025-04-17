#!/usr/bin/env python3
"""
Bamba Availability Checker
– runs once an hour ±10 minutes,
– only between 07:00–23:00 AWST,
– takes screenshots & scrapes each store,
– sends a *funny* immediate email when Bamba appears.
"""

import time, os, random, json, sys
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# 1) YOUR STORES
STORES = [
    {"name": "Dianella",   "url": "https://www.coles.com.au/find-stores/coles/wa/dianella-256"},
    {"name": "Mirrabooka", "url": "https://www.coles.com.au/find-stores/coles/wa/mirrabooka-421"},
]

# 2) LOAD SUBSCRIBERS
#    subscribers.json holds {"users":[{"email":..,"mode":"immediate"|"daily"},...]}
def load_subscribers():
    return json.load(open("subscribers.json"))["users"]

# 3) SENDGRID EMAIL HELPER
def notify_email(to_email, subject, html_content):
    """Send an email via SendGrid."""
    msg = Mail(
        from_email="noreply@bambabot.com",
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    sg.send(msg)
    print(f"  ✉️ Email to {to_email}: {subject}")

# 4) TIME UTILS
def within_hours(start=7, end=23):
    h = datetime.now().hour
    return start <= h < end

def schedule_next_run():
    now     = datetime.now()
    next_hr = (now.replace(minute=0, second=0, microsecond=0)
                  + timedelta(hours=1))
    offset  = random.uniform(-10, 10)  # ±10 min
    run_at  = next_hr + timedelta(minutes=offset)
    delta   = (run_at - now).total_seconds()
    if delta < 0: delta = 60
    print(f"\n⏱️ Next run ≈ {run_at.strftime('%H:%M:%S')} (in {delta/60:.1f} min)")
    return delta

def human_delay(a=500, b=1500):
    time.sleep(random.uniform(a/1000, b/1000))

def take_screenshot(page, store, step):
    folder = "coles_screenshots"; os.makedirs(folder, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{folder}/{store}_{step}_{ts}.png"
    page.screenshot(path=path)
    print("  📸", path)

# 5) SCRAPE ONE STORE
def check_store(store):
    print(f"\n🔄 Checking {store['name']} at {datetime.now().strftime('%H:%M:%S')}…")
    result = {
        "store": store["name"],
        "timestamp": datetime.now().isoformat(),
        "available": False,
        "products": []
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=100)
        ctx     = browser.new_context(
            viewport={"width":1280,"height":920},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:() => undefined})")

        try:
            # 1) Store page → set location
            page.goto(store["url"], timeout=60000)
            take_screenshot(page, store["name"], "1_store")
            page.wait_for_selector("text=Set location", timeout=10000)
            human_delay(); page.click("text=Set location")
            human_delay(); take_screenshot(page, store["name"], "2_loc")

            # 2) Homepage → accept cookies
            page.goto("https://www.coles.com.au", timeout=60000)
            try: page.click("button:has-text('Accept All Cookies')", timeout=5000)
            except: pass
            take_screenshot(page, store["name"], "3_home")

            # 3) Search “bamba”
            page.fill("input[placeholder*='Search']", "bamba")
            human_delay()
            page.click("div[role='option']")
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(); take_screenshot(page, store["name"], "4_res")

            # 4) Scrape tiles
            page.wait_for_selector("[data-testid='product-tiles']", timeout=15000)
            tiles = page.locator("section[data-testid='product-tile']").all()
            if not tiles:
                print("  ❓ No tiles!")
            else:
                for t in tiles:
                    # title: H2 or H3
                    te = t.locator("h2.product__title, h3")
                    title = te.first.inner_text().strip() if te.count() else "Unknown"

                    # price: new or old selector
                    pe = t.locator("span.price__value, span.price, [data-testid='product-pricing']")
                    price = pe.first.inner_text().strip() if pe.count() else "n/a"

                    # availability
                    un = t.locator("[data-testid='large-screen-currently-unavailable-prompt']").count()>0
                    ok = not un
                    mark = "✅" if ok else "❌"
                    result["products"].append({"name":title,"price":price,"available":ok})
                    if ok: result["available"]=True

                    print(f"  {mark} {title} @ {price}")

        except Exception as e:
            print("  ⚠️ Error:", e)
            take_screenshot(page, store["name"], "error")

        finally:
            browser.close()
            print(f"  🧹 Closed {store['name']}")

    return result

# 6) HISTORY & IMMEDIATE NOTIFICATIONS
def append_history(run_res):
    hist = {"runs": []}
    if os.path.exists("history.json"):
        hist = json.load(open("history.json"))
    hist["runs"].append(run_res)
    hist["runs"] = hist["runs"][-30:]  # keep last 30 runs
    json.dump(hist, open("history.json","w"), indent=2)

def main():
    while True:
        if within_hours(7,23):
            subs    = load_subscribers()
            results = []
            for store in STORES:
                r = check_store(store)
                results.append(r)
                # immediate‑mode emails
                if r["available"]:
                    for u in subs:
                        if u["mode"]=="immediate":
                            # —— CUSTOMIZE YOUR FUNNY EMAIL HERE ——
                            subj = f"🎉 Bamba Alert: {r['store']} is snack‑time heaven!"
                            body = (
                              f"<h1>Holy Peanut! 🌰</h1>"
                              f"<p>Our midnight snack radar just pinged:</p>"
                              f"<strong>{r['store']} has Bamba!</strong><br>"
                              f"Checked at {r['timestamp']} AWST. Go grab it!</p>"
                              f"<p>– Yours, your Friendly Bamba Bot 🤖</p>"
                            )
                            notify_email(u["email"], subj, body)
                time.sleep(random.uniform(2,5)*60)  # 2–5 min between stores

            append_history(results)
        else:
            print(f"⏰ Now {datetime.now().hour}:00 — outside 07–23 AWST, skipping.")

        time.sleep(schedule_next_run())

if __name__=="__main__":
    main()
