#!/usr/bin/env python3
"""
Bamba Availability Checker
– runs continuously,
– once each hour ±10 min,
– only between 07:00 and 23:00,
– takes screenshots and scrapes all your stores in turn.
"""

import time, os, random, json, sys
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# 1) Your list of stores
STORES = [
    {"name": "Dianella",   "url": "https://www.coles.com.au/find-stores/coles/wa/dianella-256"},
    {"name": "Mirrabooka", "url": "https://www.coles.com.au/find-stores/coles/wa/mirrabooka-421"},
    # …add more if you like
]

def human_delay(min_ms=500, max_ms=1500):
    """Small random pause to mimic human interaction."""
    time.sleep(random.uniform(min_ms/1000, max_ms/1000))

def take_screenshot(page, store, step):
    """
    Save a screenshot under:
      coles_screenshots/{store}_{step}_{YYYYmmdd_HHMMSS}.png
    """
    folder = "coles_screenshots"
    os.makedirs(folder, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{folder}/{store}_{step}_{ts}.png"
    page.screenshot(path=path)
    print("  📸", path)

def check_store(store):
    """
    Does the full “set location → search bamba → scrape tiles” for one store.
    Returns a dict with availability info.
    """
    print(f"\n🔄 Checking {store['name']} at {datetime.now().strftime('%H:%M:%S')}…")
    result = {"store": store["name"],
              "timestamp": datetime.now().isoformat(),
              "available": False,
              "products": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=100)
        ctx     = browser.new_context(
            viewport={"width":1280,"height":920},
            user_agent=(
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
              " AppleWebKit/537.36 (KHTML, like Gecko)"
              " Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US"
        )
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get:()=>undefined})"
        )

        try:
            # — Step 1: Open store page & set location
            page.goto(store["url"], timeout=60000)
            take_screenshot(page, store["name"], "1_store_page")

            page.wait_for_selector("text=Set location", timeout=10000)
            human_delay(500,1500)
            page.click("text=Set location")
            human_delay(1000,2000)
            take_screenshot(page, store["name"], "2_location_set")

            # — Step 2: Go to homepage & accept cookies
            page.goto("https://www.coles.com.au", timeout=60000)
            try:
                page.click("button:has-text('Accept All Cookies')", timeout=5000)
            except:
                pass
            take_screenshot(page, store["name"], "3_homepage")

            # — Step 3: Search “bamba”
            page.fill("input[placeholder*='Search']", "bamba")
            human_delay(800,1200)
            page.click("div[role='option']")
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(2000,3000)
            take_screenshot(page, store["name"], "4_results")

            # — Step 4: Scrape each product tile
            page.wait_for_selector("[data-testid='product-tiles']", timeout=15000)
            tiles = page.locator("section[data-testid='product-tile']").all()

            if not tiles:
                print("  ❓ No product tiles found!")
            else:
                for t in tiles:
                    # a) Title: try H2.product__title then fallback to H3
                    title_el = t.locator("h2.product__title, h3")
                    if title_el.count():
                        title = title_el.first.inner_text().strip()
                    else:
                        title = "Unknown Product"

                    # b) Price: cover new and old selectors
                    price_el = t.locator(
                        "span.price__value, span.price, [data-testid='product-pricing']"
                    )
                    price = price_el.first.inner_text().strip() if price_el.count() else "n/a"

                    # c) Availability flag
                    unavailable = t.locator(
                      "[data-testid='large-screen-currently-unavailable-prompt']"
                    ).count() > 0
                    available   = not unavailable
                    mark = "✅" if available else "❌"

                    # Record & print
                    result["products"].append({
                        "name":      title,
                        "price":     price,
                        "available": available
                    })
                    if available:
                        result["available"] = True
                    print(f"  {mark} {title} @ {price}")

        except Exception as e:
            print("  ⚠️ Error:", e)
            take_screenshot(page, store["name"], "error")

        finally:
            browser.close()
            print(f"  🧹 Closed browser for {store['name']}")

    return result

def run_all_checks():
    """Loop through all stores and collect results."""
    results = []
    for store in STORES:
        results.append(check_store(store))
    # Save combined JSON
    os.makedirs("bamba_results", exist_ok=True)
    out = f"bamba_results/all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {out}")
    return results

def append_to_history(run_results):
    """
    Keeps a master history.json of every run.
    run_results: list of {store,timestamp,available,products}
    """
    hist_file = "history.json"
    # Load or start fresh
    if os.path.exists(hist_file):
        history = json.load(open(hist_file))
    else:
        history = {"runs": []}

    # Append this run as one entry
    history["runs"].append(run_results)

    # (Optional) keep only the last 30 runs
    history["runs"] = history["runs"][-30:]

    # Save back out
    json.dump(history, open(hist_file, "w"), indent=2)

# Modify your main loop: after run_all_checks(), call:
if __name__=="__main__":
    while True:
        if within_hours(7,23):
            results = run_all_checks()
            append_to_history(results)
        else:
            print("⏰ Outside 07–23 AWST, skipping.")
        sleep_secs = schedule_next_run()
        time.sleep(sleep_secs)

def within_hours(start=7, end=23):
    """Return True if current local hour is between start (inclusive) and end (exclusive)."""
    h = datetime.now().hour
    return start <= h < end

def schedule_next_run():
    """
    Compute how many seconds to sleep until the next
    “top of hour ±10 minutes” check.
    """
    now      = datetime.now()
    # 1) Find the next exact hour mark
    next_hr  = (now.replace(minute=0, second=0, microsecond=0)
                   + timedelta(hours=1))
    # 2) Pick a random offset between -10 and +10 minutes
    offset   = random.uniform(-10, 10)  # in minutes
    # 3) The scheduled run time:
    run_time = next_hr + timedelta(minutes=offset)
    # 4) How many seconds until then?
    delta_s  = (run_time - now).total_seconds()
    # Guard: if something went wrong, wait 1 min
    if delta_s < 0:
        delta_s = 60
    print(f"\n⏱️ Next run scheduled at ~ {run_time.strftime('%Y-%m-%d %H:%M:%S')} "
          f"(in {delta_s/60:.1f} min)")
    return delta_s

def main():
    """
    Main loop: 
     – only checks if within 07:00–23:00 
     – else skips and still schedules the next run
    """
    while True:
        if within_hours(7,23):
            run_all_checks()
        else:
            print(f"⏰ Outside operating hours ({datetime.now().hour}:00), skipping checks.")

        # Compute & wait until next hour ±10 min
        sleep_secs = schedule_next_run()
        time.sleep(sleep_secs)

if __name__ == "__main__":
    main()
