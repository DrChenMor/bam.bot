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
      "url":  "https://www.coles.com.au/find-stores/coles/wa/mirrabooka-421"
    },
    # add more stores as you like
]

# tiny human‑style random delay
def human_delay(min_ms=500, max_ms=1500):
    time.sleep(random.uniform(min_ms/1000, max_ms/1000))

# save nicely named screenshots
def take_screenshot(page, store, step):
    folder = "coles_screenshots"
    os.makedirs(folder, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{folder}/{store}_{step}_{ts}.png"
    page.screenshot(path=path)
    print("  📸", path)

def check_store(store):
    """
    Runs the full Coles → set location → search bamba → scrape flow
    for one store, returns a dict with {"store","timestamp","available",…}
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
            viewport={"width":1280,"height":920},
            user_agent=(
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
              " AppleWebKit/537.36 (KHTML, like Gecko)"
              " Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US"
        )
        page = ctx.new_page()
        # hide webdriver flag
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get:()=>undefined})")

        try:
            # ————————————————
            # 1) Open store page + set location
            # ————————————————
            page.goto(store["url"], timeout=60000)
            take_screenshot(page, store["name"], "1_store_page")

            page.wait_for_selector("text=Set location", timeout=10000)
            human_delay(500,1500)
            page.click("text=Set location")
            human_delay(1000,2000)
            take_screenshot(page, store["name"], "2_location_set")

            # ————————————————
            # 2) Go home + accept cookies if needed
            # ————————————————
            page.goto("https://www.coles.com.au", timeout=60000)
            try:
                page.click("button:has-text('Accept All Cookies')", timeout=5000)
            except: pass
            take_screenshot(page, store["name"], "3_homepage")

            # ————————————————
            # 3) Search “bamba”
            # ————————————————
            page.fill("input[placeholder*='Search']", "bamba")
            human_delay(800,1200)
            page.click("div[role=option]")  # first autocomplete
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(2000,3000)
            take_screenshot(page, store["name"], "4_results")

            # ————————————————
            # 4) Scrape product cards
            # ————————————————
            cards = page.locator("div.product, li[data-testid=product-card]").all()
            for c in cards:
                txt = c.inner_text().lower()
                if "bamba" in txt:
                    name = c.locator("h3, .product-name").all_text_contents()
                    price= c.locator(".price, [data-testid=price]").all_text_contents()
                    available = "currently unavailable" not in txt
                    result["products"].append({
                        "name":      name[0] if name else "Bamba",
                        "price":     price[0] if price else "n/a",
                        "available": available
                    })
                    if available:
                        result["available"] = True

            if not result["products"]:
                print("  ❓ No Bamba products found.")
            else:
                for p in result["products"]:
                    mark = "✅" if p["available"] else "❌"
                    print(f"  {mark} {p['name']} @ {p['price']}")

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

        # optional: wait a few minutes between stores
        if store is not STORES[-1]:
            delay = random.uniform(2,5)*60
            print(f"⏱️ Sleeping {delay/60:.1f} min before next store…")
            time.sleep(delay)

    # save everything as one JSON
    os.makedirs("bamba_results", exist_ok=True)
    path = f"bamba_results/all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(path,"w") as f:
        json.dump(all_results, f, indent=2)
    print("\n💾 Results written to", path)

if __name__=="__main__":
    main()
