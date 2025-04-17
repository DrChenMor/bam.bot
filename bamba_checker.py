#!/usr/bin/env python3
"""
bamba_checker.py

– Runs once each hour ±10 minutes  
– Only between 07:00–23:00 AWST  
– Scrapes multiple Coles stores for Bamba availability  
– Sends a funny immediate email to encrypted-subscriber emails  
– Appends each run to history.json for daily summaries
"""

import os
import sys
import time
import random
import json
from datetime import datetime, timedelta

from playwright.sync_api import sync_playwright
from cryptography.fernet import Fernet
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ─────────────────────────────────────────────────────────────
# 1) SETUP ENCRYPTION FOR SUBSCRIBERS
# ─────────────────────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    print("⚠️ FERNET_KEY not set. Exiting.")
    sys.exit(1)

fernet = Fernet(FERNET_KEY.encode())

def load_subscribers():
    """Load and decrypt subscribers from subscribers.json."""
    subs = []
    try:
        data = json.load(open("subscribers.json"))
    except FileNotFoundError:
        return subs
    for u in data.get("users", []):
        try:
            email = fernet.decrypt(u["token"].encode()).decode()
            subs.append({"email": email, "mode": u["mode"]})
        except Exception as e:
            print(f"⚠️ Failed to decrypt subscriber token: {e}")
    return subs

# ─────────────────────────────────────────────────────────────
# 2) SENDGRID EMAIL HELPER
# ─────────────────────────────────────────────────────────────
def notify_email(to_email, subject, html_content):
    """Send an email via SendGrid."""
    msg = Mail(
        from_email="noreply@bambabot.com",
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    response = sg.send(msg)
    print(f"  ✉️ Sent ({response.status_code}) to {to_email}")

# ─────────────────────────────────────────────────────────────
# 3) CONFIGURE YOUR STORES
# ─────────────────────────────────────────────────────────────
STORES = [
    {"name": "Dianella",   "url": "https://www.coles.com.au/find-stores/coles/wa/dianella-256"},
    {"name": "Mirrabooka", "url": "https://www.coles.com.au/find-stores/coles/wa/mirrabooka-314"},
    # add more stores here if you like
]

# ─────────────────────────────────────────────────────────────
# 4) TIME & SCHEDULING UTILS
# ─────────────────────────────────────────────────────────────
def within_hours(start=7, end=23):
    """Return True if current hour is between start (inclusive) and end (exclusive)."""
    h = datetime.now().hour
    return start <= h < end

def schedule_next_run():
    """
    Compute seconds until the next "hour ±10 min" run.
    E.g. if it's 07:25, schedule between 08:00 ±10 min.
    """
    now    = datetime.now()
    next_hr = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    offset  = random.uniform(-10, 10)  # ±10 minutes
    run_at  = next_hr + timedelta(minutes=offset)
    delta   = (run_at - now).total_seconds()
    if delta < 0:
        delta = 60
    print(f"\n⏱️ Next run at ~{run_at.strftime('%H:%M:%S')} (in {delta/60:.1f} min)")
    return delta

# ─────────────────────────────────────────────────────────────
# 5) BROWSER / SCRAPE HELPERS
# ─────────────────────────────────────────────────────────────
def human_delay(min_ms=500, max_ms=1500):
    """Small random pause to mimic a human user."""
    time.sleep(random.uniform(min_ms/1000, max_ms/1000))

def take_screenshot(page, store, step):
    """Save a screenshot under coles_screenshots/{store}_{step}_{timestamp}.png."""
    folder = "coles_screenshots"
    os.makedirs(folder, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{folder}/{store}_{step}_{ts}.png"
    page.screenshot(path=path)
    print(f"  📸 {path}")

def check_store(store):
    """
    Open a headless browser, set the store location, search 'bamba',
    scrape each product tile, and return a dict of results.
    """
    print(f"\n🔄 Checking {store['name']} at {datetime.now().strftime('%H:%M:%S')}…")
    result = {
        "store":     store["name"],
        "timestamp": datetime.now().isoformat(),
        "available": False,
        "products":  []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=100)
        ctx = browser.new_context(
            viewport={"width":1280,"height":920},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        try:
            # Step 1: Open store page & click 'Set location'
            page.goto(store["url"], timeout=60000)
            take_screenshot(page, store["name"], "1_store_page")
            page.wait_for_selector("text=Set location", timeout=10000)
            human_delay(); page.click("text=Set location")
            human_delay(); take_screenshot(page, store["name"], "2_location_set")

            # Step 2: Go to homepage & accept cookies
            page.goto("https://www.coles.com.au", timeout=60000)
            try:
                page.click("button:has-text('Accept All Cookies')", timeout=5000)
            except:
                pass
            take_screenshot(page, store["name"], "3_homepage")

            # Step 3: Search for 'bamba'
            page.fill("input[placeholder*='Search']", "bamba")
            human_delay()
            page.click("div[role='option']")
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(); take_screenshot(page, store["name"], "4_results")

            # Step 4: Scrape each product tile
            page.wait_for_selector("[data-testid='product-tiles']", timeout=15000)
            tiles = page.locator("section[data-testid='product-tile']").all()

            if not tiles:
                print("  ❓ No product tiles found!")
            else:
                for tile in tiles:
                    # a) Title: try H2.product__title, then fallback to H3
                    te = tile.locator("h2.product__title, h3")
                    title = te.first.inner_text().strip() if te.count() else "Unknown Product"

                    # b) Price: new or old selector
                    pe = tile.locator("span.price__value, span.price, [data-testid='product-pricing']")
                    price = pe.first.inner_text().strip() if pe.count() else "n/a"

                    # c) Availability: look for 'Currently unavailable'
                    unavailable = tile.locator(
                        "[data-testid='large-screen-currently-unavailable-prompt']"
                    ).count() > 0
                    available = not unavailable
                    mark = "✅" if available else "❌"

                    result["products"].append({
                        "name":      title,
                        "price":     price,
                        "available": available
                    })
                    if available:
                        result["available"] = True

                    print(f"  {mark} {title} @ {price}")

        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            take_screenshot(page, store["name"], "error")

        finally:
            browser.close()
            print(f"  🧹 Closed browser for {store['name']}")

    return result

# ─────────────────────────────────────────────────────────────
# 6) APPEND TO HISTORY
# ─────────────────────────────────────────────────────────────
def append_history(results):
    """Append this run's results to history.json, keeping last 30 runs."""
    hist_file = "history.json"
    if os.path.exists(hist_file):
        history = json.load(open(hist_file))
    else:
        history = {"runs": []}
    history["runs"].append(results)
    history["runs"] = history["runs"][-30:]
    json.dump(history, open(hist_file, "w"), indent=2)

# ─────────────────────────────────────────────────────────────
# 7) MAIN LOOP
# ─────────────────────────────────────────────────────────────
def main():
    while True:
        # Only scrape during operating hours
        if within_hours(7,23):
            subscribers = load_subscribers()
            run_results = []
            for store in STORES:
                res = check_store(store)
                run_results.append(res)
                # Send immediate emails for available stores
                if res["available"]:
                    for u in subscribers:
                        if u["mode"] == "immediate":
                            # —— FUNNY EMAIL CONTENT ——  
                            subject = f"🎉 Bamba Alert: {res['store']} is snack-time heaven!"
                            body    = (
                                f"<h1>Holy Peanut! 🌰</h1>"
                                f"<p>Bamba is IN STOCK at <b>{res['store']}</b> as of "
                                f"{res['timestamp'].split('T')[1][:8]} AWST.</p>"
                                f"<p>Ready… set… snack! 🤖</p>"
                            )
                            notify_email(u["email"], subject, body)
                # Delay 2–5 min before next store
                time.sleep(random.uniform(2,5) * 60)

            # Record history for daily summary
            append_history(run_results)

        else:
            print(f"⏰ Now {datetime.now().hour}:00 — outside 07–23 AWST, skipping.")

        # Sleep until next hour ±10 min
        time.sleep(schedule_next_run())

if __name__ == "__main__":
    main()
