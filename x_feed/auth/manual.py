import asyncio
from playwright.async_api import async_playwright
from loguru import logger

async def manual_login(config: dict):
    state_path = config["paths"]["storage_state"]
    state_path.parent.mkdir(parents=True, exist_ok=True)

    proxy = config.get("proxy")

    async with async_playwright() as p:
        logger.info("Launching browser for manual authentication setup...")
        if proxy:
            logger.info(f"Using proxy: {proxy['server']}")
        browser = await p.chromium.launch(
            headless=False,
            proxy=proxy,
            args=["--disable-http2"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto("https://x.com/i/flow/login")
        
        print("\n" + "="*70)
        print("1. Log in to your X account in the opened browser window.")
        print("2. Once you reach the Home feed, return here and press ENTER.")
        print("="*70 + "\n")
        
        input("--> Press ENTER after successful login: ")
        
        await context.storage_state(path=state_path)
        logger.success(f"Session state successfully exported to:\n{state_path}")
        await browser.close()