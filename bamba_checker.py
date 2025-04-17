from playwright.sync_api import sync_playwright
import time, os, random, json
from datetime import datetime

# 1) List your stores here
STORES = [
    {
      "name": "Mirrabooka",
      "url":  "https://www.coles.com.au/find-stores/coles/wa/mirrabooka-314"
    },
    # add more stores as you like
]

# tiny human‑style random delay

def human_delay(min_ms=500, max_ms=1500):
    """Tiny random pause to look more human."""
    time.sleep(random.uniform(min_ms/1000, max_ms/1000))

def take_screenshot(page, store, step):
    """Save screenshots in coles_screenshots/{store}_{step}_{timestamp}.png."""
    os.makedirs("coles_screenshots", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"coles_screenshots/{store}_{step}_{ts}.png"
    page.screenshot(path=path)
    print("  📸", path)

def check_store(store):
    """Runs the ‘set location → search bamba → scrape tiles’ flow for 1 store."""
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
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
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

            # — Step 2: Go home & accept cookies
            page.goto("https://www.coles.com.au", timeout=60000)
            try:
                page.click("button:has-text('Accept All Cookies')", timeout=5000)
            except:
                pass
            take_screenshot(page, store["name"], "3_homepage")

            # — Step 3: Search “bamba”
            page.fill("input[placeholder*='Search']", "bamba")
            human_delay(800,1200)
            page.click("div[role='option']")   # pick first suggestion
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(2000,3000)
            take_screenshot(page, store["name"], "4_results")

            # — Step 4: Wait for the tile container, then scrape each tile
            page.wait_for_selector("[data-testid='product-tiles']", timeout=15000)
            tiles = page.locator("section[data-testid='product-tile']").all()

            if not tiles:
                print("  ❓ No product tiles found!")
            else:
                for t in tiles:
                    # — a) Get the name, try H2.product__title first, then H3
                    title_el = t.locator("h2.product__title, h3")
                    if title_el.count():
                        title = title_el.first.inner_text().strip()
                    else:
                        title = "Unknown Product"

                    # — b) Get the price
                    if t.locator("span.price").count():
                        price = t.locator("span.price").first.inner_text().strip()
                    else:
                        price = "n/a"

                    # — c) Detect “Currently unavailable”
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

def main():
    all_results = []
    for store in STORES:
        res = check_store(store)
        all_results.append(res)

        # optional pause between stores
        if store is not STORES[-1]:
            mins = random.uniform(2,5)
            print(f"⏱️ Sleeping {mins:.1f} min before next store…")
            time.sleep(mins*60)

    # Save combined results
    os.makedirs("bamba_results", exist_ok=True)
    out = f"bamba_results/all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out,"w") as f:
        json.dump(all_results, f, indent=2)
    print("\n💾 Results written to", out)

if __name__=="__main__":
    main()
