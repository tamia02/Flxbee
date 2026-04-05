import asyncio
from playwright.async_api import async_playwright

async def debug_labels(query):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
        await page.wait_for_selector('[role="feed"]', timeout=15000)
        
        cards = await page.query_selector_all('a[href*="/maps/place/"]')
        print(f"DEBUG: Found {len(cards)} cards.")
        for card in cards:
            label = await card.get_attribute('aria-label')
            print(f"LABEL: {label}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_labels("Dentists in Mumbai"))
