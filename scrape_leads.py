import asyncio
from playwright.async_api import async_playwright
import json
import os
import sys
import re
import requests
import io

# Force UTF-8 for Windows terminals to handle Indian characters (e.g., \u0964)
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# Always use absolute path for leads.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_FILE = os.path.join(BASE_DIR, "leads.json")

async def scrape_google_maps(query, limit=10, live=False):
    print(f"SCRAPER: Starting elite research for '{query}'...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("SCRAPER: Navigating to Google Maps...")
        await page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")

        try:
            await page.wait_for_selector('[role="feed"]', timeout=15000)
        except:
            print("SCRAPER: No results found or feed didn't load.")
            await browser.close()
            return

        leads = []
        seen_names = set()

        print("SCRAPER: Searching for 'Elite' businesses (4.0+ stars, 200+ reviews)...")

        for _ in range(8):
            await page.mouse.wheel(0, 5000)
            await asyncio.sleep(2)

            cards = await page.query_selector_all('a[href*="/maps/place/"]')

            for card in cards:
                if len(leads) >= limit:
                    break

                label = await card.get_attribute('aria-label')
                if not label:
                    continue

                name = label.split(" · ")[0] if " · " in label else label

                if name in seen_names:
                    continue
                seen_names.add(name)

                rating = 0.0
                reviews = 0

                rating_match = re.search(r'([\d.]+)\s+stars', label)
                if rating_match:
                    rating = float(rating_match.group(1))

                reviews_match = re.search(r'([\d,]+)\s+reviews', label)
                if reviews_match:
                    reviews = int(reviews_match.group(1).replace(",", ""))

                is_elite_tier = rating >= 4.0 and reviews >= 200
                if not is_elite_tier:
                    print(f"  [PROSPECT] {name} - {rating} stars ({reviews} reviews)... checking website.")

                try:
                    await card.click()
                    await asyncio.sleep(2)

                    has_website = await page.query_selector('a[aria-label*="website"]') is not None

                    phone_elem = await page.query_selector('button[aria-label*="Phone:"]')
                    phone = "Unknown"
                    if phone_elem:
                        phone_label = await phone_elem.get_attribute('aria-label')
                        phone = phone_label.replace("Phone: ", "").strip()

                    category_elem = await page.query_selector('button.DkEaL')
                    niche = await category_elem.inner_text() if category_elem else query.split(" in ")[0]

                    address_elem = await page.query_selector('button[aria-label^="Address:"]')
                    address = "Unknown"
                    if address_elem:
                        addr_label = await address_elem.get_attribute('aria-label')
                        address = addr_label.replace("Address: ", "").strip()

                    city = "Unknown"
                    if address != "Unknown":
                        parts = address.split(",")
                        city = parts[-2].strip() if len(parts) > 2 else parts[-1].strip()

                    if not has_website and phone != "Unknown":
                        status = "ELITE" if is_elite_tier else "QUALIFIED"
                        print(f"  [{status}] {name} - {rating} stars ({reviews} reviews) -> {niche}")

                        lead_data = {
                            "name": name,
                            "phone": phone,
                            "rating": rating,
                            "reviews": reviews,
                            "niche": niche,
                            "address": address,
                            "city": city,
                            "search_query": query,
                            "qualified": True
                        }

                        if live:
                            # ── FIX 1: In live mode, ONLY post to /add_lead ──
                            # Do NOT save to leads.json here — the server does it.
                            # This prevents index corruption and double-processing.
                            try:
                                resp = requests.post(
                                    "http://localhost:8000/add_lead",
                                    json=lead_data,
                                    timeout=10
                                )
                                result = resp.json()
                                if result.get("status") == "success":
                                    print(f"  [LIVE] Mission triggered for {name} (index {result.get('index')})")
                                elif result.get("status") == "exists":
                                    print(f"  [LIVE] Skipped duplicate: {name}")
                                else:
                                    print(f"  [LIVE] Server rejected {name}: {result}")
                            except Exception as e:
                                print(f"  [ERROR] Failed to trigger live mission for {name}: {e}")
                                # ── FIX 2: Fall back to local save if server unreachable ──
                                leads.append(lead_data)
                        else:
                            # Non-live mode: collect and save at end
                            leads.append(lead_data)
                    else:
                        reason = "has website" if has_website else "no phone"
                        print(f"  [SKIP] {name} - {reason}")

                except Exception:
                    continue

            if len(leads) >= limit:
                break

        await browser.close()

        # ── FIX 3: Only write leads.json in NON-live mode ─────────────────────
        # In live mode the server already wrote each lead via /add_lead.
        # Writing again here would overwrite server-managed indexes and
        # cause missions to fail with "Lead index X not found".
        if not live:
            if leads:
                print(f"SCRAPER: Successfully captured {len(leads)} elite leads.")
                existing_leads = []
                if os.path.exists(LEADS_FILE):
                    try:
                        with open(LEADS_FILE, "r", encoding="utf-8") as f:
                            existing_leads = json.load(f)
                    except Exception:
                        existing_leads = []

                existing_names = {l["name"] for l in existing_leads}
                new_unique = [l for l in leads if l["name"] not in existing_names]
                combined = existing_leads + new_unique

                with open(LEADS_FILE, "w", encoding="utf-8") as f:
                    json.dump(combined, f, indent=2)

                print(f"SCRAPER: Synchronized {len(new_unique)} new leads to database.")
            else:
                print("SCRAPER: Successfully captured 0 leads.")
        else:
            # In live mode, just report — server handled everything
            print(f"SCRAPER: Live scrape complete. All qualified leads sent to server pipeline.")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Dentists in Mumbai"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    live = "--live" in sys.argv
    asyncio.run(scrape_google_maps(query, limit, live))