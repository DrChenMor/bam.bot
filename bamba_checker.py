from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import os
import random
import json

# Store configuration - add more stores as needed
STORES = [
    {"name": "Dianella", "id": "256", "url": "https://www.coles.com.au/find-stores/coles/wa/dianella-256"},
    {"name": "Mirrabooka", "id": "421", "url": "https://www.coles.com.au/find-stores/coles/wa/mirrabooka-421"}
]

def human_delay(min_ms=500, max_ms=1500):
    time.sleep(random.uniform(min_ms/1000, max_ms/1000))

def take_screenshot(page, store_name, step):
    folder = "coles_screenshots"
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{folder}/coles_{store_name}_{step}_{timestamp}.png"
    page.screenshot(path=path)
    print(f"📸 Screenshot saved: {path}")

def check_store_bamba(store_info):
    store_name = store_info["name"]
    store_url = store_info["url"]
    
    print(f"\n🔄 Checking Bamba availability at Coles {store_name}...")
    result = {"store": store_name, "timestamp": datetime.now().isoformat(), "available": False, "products": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=150)
        context = browser.new_context(
            viewport={"width": 1280, "height": 920},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            # Step 1: Open Store Page
            print(f"🌐 Opening Coles {store_name} store page...")
            page.goto(store_url, timeout=60000)
            take_screenshot(page, store_name, "1_store_page")

            # Step 2: Click "Set location"
            print("📍 Waiting before clicking 'Set location'...")
            page.wait_for_selector("text=Set location", timeout=10000)
            human_delay(1000, 2000)
            page.locator("text=Set location").click()
            human_delay(1500, 2500)
            take_screenshot(page, store_name, "2_location_set")

            # Step 3: Navigate to Homepage
            print("🏠 Navigating to homepage...")
            page.goto("https://www.coles.com.au", timeout=60000)

            # Step 4: Cookie popup
            try:
                print("🍪 Checking for cookie popup...")
                page.locator("button:has-text('Accept All Cookies')").click(timeout=5000)
                print("✅ Cookie accepted.")
            except:
                print("ℹ️ No cookie popup found.")

            # Step 5: Wait for search bar
            print("🔍 Waiting for search bar...")
            page.wait_for_selector("input[placeholder*='Search']", timeout=20000)
            take_screenshot(page, store_name, "3_homepage")

            # Step 6: Type "bamba" into the search bar
            print("🔍 Typing 'bamba' into search...")
            search_box = page.locator("input[placeholder*='Search']").first
            search_box.fill("bamba")
            human_delay(1000, 1500)

            # Step 7: Click autocomplete suggestion (react-select fix)
            print("🖱️ Clicking first autocomplete option...")
            suggestion = page.locator("div[role='option']").first
            suggestion.wait_for(state="visible", timeout=10000)
            suggestion.click()

            # Step 8: Wait for results page
            print("⌛ Waiting for results page...")
            page.wait_for_url("**/search/products**", timeout=15000)
            human_delay(3000, 4000)
            take_screenshot(page, store_name, "4_bamba_results")

            # Step 9: Check availability
            print("🔎 Checking Bamba availability...")

            product_elements = page.locator("div.product").all()
            
            for element in product_elements:
                product_text = element.inner_text()
                if "bamba" in product_text.lower():
                    product_name = element.locator("h3").inner_text() if element.locator("h3").count() > 0 else "Unknown Bamba Product"
                    price = element.locator("span.price").inner_text() if element.locator("span.price").count() > 0 else "Price unknown"
                    unavailable = "unavailable" in product_text.lower()
                    
                    result["products"].append({
                        "name": product_name,
                        "price": price,
                        "available": not unavailable
                    })
                    
                    if not unavailable:
                        result["available"] = True
                    
                    print(f"🟦 {product_name}: {'❌ Unavailable' if unavailable else '✅ Available'}")

            if not result["products"]:
                print("❓ No Bamba products found in search results")
            elif result["available"]:
                print(f"✅ Bamba is available at Coles {store_name}!")
            else:
                print(f"❌ All Bamba products are currently unavailable at Coles {store_name}.")

        except Exception as e:
            print(f"⚠️ Error checking {store_name}: {e}")
            take_screenshot(page, store_name, "error")
            result["error"] = str(e)

        finally:
            browser.close()
            print(f"🧹 Browser for {store_name} closed")
            
    # Save result to JSON file
    results_folder = "bamba_results"
    os.makedirs(results_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"{results_folder}/{store_name.lower()}_{timestamp}.json", "w") as f:
        json.dump(result, f, indent=2)
        
    return result

def check_all_stores_separately():
    """Check each store with a delay between checks to avoid detection"""
    results = []
    
    for store in STORES:
        # Check this store
        result = check_store_bamba(store)
        results.append(result)
        
        # Random delay between store checks (2-5 minutes)
        if store != STORES[-1]:  # Don't delay after the last store
            delay_minutes = random.uniform(2, 5)
            print(f"\n⏱️ Waiting {delay_minutes:.1f} minutes before checking next store...")
            time.sleep(delay_minutes * 60)
    
    return results

# Only run checks during operating hours (7am to 11pm)
def is_within_operating_hours():
    now = datetime.now()
    hour = now.hour
    return 7 <= hour < 23

if __name__ == "__main__":
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🕒 Check started at {current_time}")
    
    if is_within_operating_hours():
        results = check_all_stores_separately()
        
        # Print summary
        print("\n📊 BAMBA AVAILABILITY SUMMARY")
        print("===========================")
        for result in results:
            status = "✅ AVAILABLE" if result.get("available") else "❌ NOT AVAILABLE"
            print(f"Coles {result['store']}: {status}")
    else:
        print("⏰ Outside of operating hours (7am-11pm). Check skipped.")
    
    print(f"\n🕒 Process completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
