import asyncio
from playwright.async_api import async_playwright
import json
import os
import sys
import re

async def scrape_google_maps(query, limit=10):
    print(f"SCRAPER: Starting elite research for '{query}'...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Go to Google Maps
        print(f"SCRAPER: Navigating to Google Maps...")
        await page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
        
        try:
            # Wait for results
            await page.wait_for_selector('[role="feed"]', timeout=15000)
        except:
            print("SCRAPER: No results found or feed didn't load.")
            await browser.close()
            return

        leads = []
        seen_names = set()
        
        print("SCRAPER: Searching for 'Elite' businesses (4.0+ stars, 200+ reviews)...")
        
        # Scroll and collect
        for _ in range(8): # Scroll more for better coverage
            await page.mouse.wheel(0, 5000)
            await asyncio.sleep(2)
            
            # Find all business card elements
            cards = await page.query_selector_all('a[href*="/maps/place/"]')
            
            for card in cards:
                if len(leads) >= limit:
                    break
                    
                label = await card.get_attribute('aria-label')
                if not label:
                    continue
                
                # Parse Rich Aria Label
                # Example: "Name · 4.5 stars · 1,234 reviews · Dentist"
                name = label.split(" · ")[0] if " · " in label else label
                
                if name in seen_names:
                    continue
                seen_names.add(name)

                # Extract Rating and Reviews
                rating = 0.0
                reviews = 0
                
                rating_match = re.search(r'([\d.]+)\s+stars', label)
                if rating_match:
                    rating = float(rating_match.group(1))
                
                reviews_match = re.search(r'([\d,]+)\s+reviews', label)
                if reviews_match:
                    reviews_str = reviews_match.group(1).replace(",", "")
                    reviews = int(reviews_str)

                # Pre-Qualify: We prioritize Elite but allow anything without a website
                is_elite_tier = rating >= 4.0 and reviews >= 200
                if not is_elite_tier:
                    print(f"  [PROSPECT] {name} - {rating} stars ({reviews} reviews)... checking website.")

                # Now click to check website and phone
                try:
                    await card.click()
                    await asyncio.sleep(2)
                    
                    # Check for Website
                    has_website = await page.query_selector('a[aria-label*="website"]') is not None
                    
                    # Check for Phone
                    phone_elem = await page.query_selector('button[aria-label*="Phone:"]')
                    phone = "Unknown"
                    if phone_elem:
                        phone = await phone_elem.get_attribute('aria-label')
                        phone = phone.replace("Phone: ", "").strip()
                    
                    # NEW: Extract Category (Niche)
                    category_elem = await page.query_selector('button.DkEaL')
                    niche = await category_elem.inner_text() if category_elem else query.split(" in ")[0]
                    
                    # NEW: Extract Address
                    address_elem = await page.query_selector('button[aria-label^="Address:"]')
                    address = "Unknown"
                    if address_elem:
                        address = await address_elem.get_attribute('aria-label')
                        address = address.replace("Address: ", "").strip()
                    
                    # NEW: Extract City from Address
                    city = "Unknown"
                    if address != "Unknown":
                        # Simple heuristic: last component before state/pin or comma-separated
                        parts = address.split(",")
                        if len(parts) >= 2:
                            city = parts[-2].strip() if len(parts) > 2 else parts[-1].strip()
                    
                    # FINAL Qualification: No Website + Has Phone
                    if not has_website and phone != "Unknown":
                        status = "ELITE" if is_elite_tier else "QUALIFIED"
                        print(f"  [{status}] {name} - {rating} stars ({reviews} reviews) -> {niche}")
                        leads.append({
                            "name": name,
                            "phone": phone,
                            "rating": rating,
                            "reviews": reviews,
                            "niche": niche,
                            "address": address,
                            "city": city,
                            "search_query": query,
                            "qualified": True
                        })
                    else:
                        reason = "has website" if has_website else "no phone"
                        print(f"  [SKIP] {name} - {reason}")
                        
                except Exception as e:
                    continue
            
            if len(leads) >= limit:
                break

        await browser.close()
        
        # Save to leads.json
        if leads:
            print(f"SCRAPER: Successfully captured {len(leads)} elite leads.")
            existing_leads = []
            if os.path.exists("leads.json"):
                with open("leads.json", "r") as f:
                    try:
                        existing_leads = json.load(f)
                    except:
                        pass
            
            # Merge
            existing_names = {l['name'] for l in existing_leads}
            new_unique_leads = [l for l in leads if l['name'] not in existing_names]
            
            combined_leads = existing_leads + new_unique_leads
            with open("leads.json", "w") as f:
                json.dump(combined_leads, f, indent=2)
            
            print(f"SCRAPER: Synchronized {len(new_unique_leads)} new leads to database.")
        else:
            print(f"SCRAPER: Successfully captured {len(leads)} leads.")

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Dentists in Mumbai"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    asyncio.run(scrape_google_maps(query, limit))
