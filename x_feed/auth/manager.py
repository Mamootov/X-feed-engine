from playwright.async_api import async_playwright, BrowserContext
from loguru import logger

class AuthManager:
    def __init__(self, config: dict):
        self.state_path = config["paths"]["storage_state"]
        self.proxy = config.get("proxy")
        self.playwright = None
        self.browser = None

    async def get_context(self) -> BrowserContext:
        if not self.state_path.exists():
            raise FileNotFoundError(
                f"Session file missing at '{self.state_path}'. "
                f"Please run authentication first."
            )

        self.playwright = await async_playwright().start()
        
        logger.info("Launching headless browser with persistent session...")
        if self.proxy:
            logger.info(f"Using proxy: {self.proxy['server']}")

        self.browser = await self.playwright.chromium.launch(
            headless=True,
            proxy=self.proxy,
            args=[
                "--disable-http2",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--blink-settings=imagesEnabled=false",
            ]
        )
        
        context_args = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        logger.info(f"Injecting cookies from: {self.state_path}")
        context = await self.browser.new_context(storage_state=self.state_path, **context_args)
        return context

    async def verify_login(self, page) -> bool:
        """
        Confirms the loaded storage_state actually represents a logged-in
        session, instead of assuming the file's existence means it's valid.
        Placeholder/expired/revoked cookies will load into the context fine
        but won't pass X's auth check, so this catches that case up front
        rather than letting every target account time out individually.
        """
        try:
            await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(
                'a[data-testid="AppTabBar_Home_Link"]',
                timeout=10000
            )
            logger.success("Session verified: logged in.")
            return True
        except Exception:
            logger.error(
                "Session check failed: not logged in. "
                "'data/storage_state.json' likely has missing/placeholder/expired "
                "cookies. Re-run and choose option 1 (Automated Login) or "
                "option 2 (Manual Login) to regenerate a real session."
            )
            return False

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()