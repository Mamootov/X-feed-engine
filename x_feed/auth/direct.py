import asyncio
from playwright.async_api import async_playwright
from loguru import logger

async def automated_login(config: dict) -> bool:
    creds = config["credentials"]
    state_path = config["paths"]["storage_state"]
    state_path.parent.mkdir(parents=True, exist_ok=True)

    if not creds.get("user") or not creds.get("password"):
        logger.error("Missing X_USER or X_PASS credentials in .env file.")
        return False

    proxy = config.get("proxy")

    async with async_playwright() as p:
        logger.info("Launching browser for automated authentication flow...")
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
        
        try:
            logger.info("Navigating to X login page...")
            await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=45000)
            
            # Step 1: Input Username
            username_selector = 'input[autocomplete="username"], input[name="text"]'
            await page.wait_for_selector(username_selector, timeout=30000)
            await page.fill(username_selector, creds["user"])
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)

            # Step 2: Verification step if prompted
            email_challenge = await page.locator('input[data-testid="ocfEnterTextTextInput"]').count()
            if email_challenge > 0:
                if creds.get("email"):
                    logger.warning("Secondary verification required. Entering email...")
                    await page.fill('input[data-testid="ocfEnterTextTextInput"]', creds["email"])
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(3)
                else:
                    logger.error("Email challenge presented, but X_EMAIL is not set.")
                    return False

            # Step 3: Input Password
            await page.wait_for_selector('input[name="password"]', timeout=30000)
            await page.fill('input[name="password"]', creds["password"])
            await page.click('button[data-testid="LoginForm_Login_Button"]')
            
            # Step 4: Verify
            await page.wait_for_selector('a[data-testid="AppTabBar_Home_Link"]', timeout=45000)
            await context.storage_state(path=state_path)
            logger.success(f"Authentication successful! Saved state to: {state_path}")
            return True

        except Exception as e:
            logger.error(f"Automated login failed: {e}")
            return False
        finally:
            await browser.close()