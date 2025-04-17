from playwright.sync_api import sync_playwright
import time, os, random, json
from datetime import datetime

# 1) List your stores here
STORES = [
    {
      "name": "Dianella",
      "url":  "https://www.coles.com.au/find-stores/coles/wa/dianella-256"
    },
    {
      "name": "Mirrabooka",
      "url":  "https://www.coles.com.au/find-stores/coles/wa/mirrabooka-314"
    },
    # add more stores as you like
]

# tiny human‑style random delay
def human_delay(min_ms=500, max_ms=1500):
    """Small random delay to mimic human behavior."""
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
    Run the “set location → search bamba → scrape” flow for one store.
    Returns a dict: {store, timestamp, available, products: [...]}
    """
    print(f"\n🔄 Checking {store['name']}…")
    result = {
        "store":     store["name"],
        "timestamp": datetime.now().isoformat(),
        "available": False,
        "products":  []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=100)
        ctx     = browser.new_context(
            viewport={"width": 1280, "height": 920},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US"
        )
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        try:
            # — Step 1: Open store page + set location
            page.goto(store["url"], timeout=60000)
            take_screenshot(page, store["name"], "1_store_page")

            page.wait_for_selector("text=Set location", timeout=10000)
            human_delay(500, 1500)
            page.click("text=Set location")
            human_delay(1000, 2000)
            take_screenshot(page, store["name"], "2_location_set")

            # — Step 2: Go to homepage + accept cookies
            page.goto("https://www.coles.com.au", timeout=60000)
            try:
                page.click("button:has-text('Accept All Cookies')", timeout=5000)
            except:
                pass
            take_screenshot(page, store["name"], "3_homepage")

            # — Step 3: Search “bamba”
            page.fill("input[placeholder*='Search']", "bamba")
            human_delay(800, 1200)
            page.click("div[role='option']")  # first autocomplete suggestion
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(2000, 3000)
            take_screenshot(page, store["name"], "4_results")

            # — Step 4: Wait for & scrape product cards
            page.wait_for_selector(
                "li[data-testid='product-card'], div[data-testid='product-card']",
                timeout=15000
            )
            cards = page.locator(
                "li[data-testid='product-card'], div[data-testid='product-card']"
            ).all()

            if not cards:
                print("  ❓ No Bamba products found.")
            else:
                for c in cards:
                    # grab title
                    title = c.locator("h3, [data-testid='product-name']").inner_text().strip()
                    # grab price
                    price = c.locator("span.price, [data-testid='price']").inner_text().strip()
                    # detect availability flag
                    unavailable = c.locator("text=Currently unavailable").count() > 0

                    result["products"].append({
                        "name":      title,
                        "price":     price,
                        "available": not unavailable
                    })
                    if not unavailable:
                        result["available"] = True

                    mark = "✅" if not unavailable else "❌"
                    print(f"  {mark} {title} @ {price}")

        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            take_screenshot(page, store["name"], "error")

        finally:
            browser.close()
            print(f"  🧹 Closed browser for {store['name']}")

    return result

def main():
    all_results = []
    for store in STORES:
        res = check_store(store)
        all_results.append(res)

        # Optional: wait 2–5 minutes before the next store
        if store is not STORES[-1]:
            mins = random.uniform(2,5)
            print(f"⏱️ Sleeping {mins:.1f} min before next store…")
            time.sleep(mins * 60)

    # Save a combined JSON of all runs
    os.makedirs("bamba_results", exist_ok=True)
    out_path = f"bamba_results/all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n💾 Results written to {out_path}")

if __name__ == "__main__":
    main()
