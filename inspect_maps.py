import asyncio
from playwright.async_api import async_playwright

async def inspect_maps(query="Dentist in Mumbai"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
        await page.wait_for_selector('[role="feed"]', timeout=10000)
        
        # Take a screenshot of the first card's HTML
        cards = await page.query_selector_all('a[href*="/maps/place/"]')
        if cards:
            card = cards[0]
            await card.click()
            await asyncio.sleep(3)
            # Find rating and reviews
            content = await page.content()
            with open("maps_debug.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved maps_debug.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_maps())
