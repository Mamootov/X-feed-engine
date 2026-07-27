import asyncio
import sys
from loguru import logger

from x_feed.config import load_config
from x_feed.database import reset_and_init_db, save_tweets_to_db
from x_feed.auth.direct import automated_login
from x_feed.auth.manual import manual_login
from x_feed.auth.manager import AuthManager
from x_feed.scraper.feed import scrape_user_profile

async def select_authentication_method(config: dict) -> bool:
    state_path = config["paths"]["storage_state"]

    print("\n" + "=" * 65)
    print("                X ENGINE - AUTHENTICATION MENU              ")
    print("=" * 65)
    print(" 1. Automated Login  (Uses X_USER, X_PASS, X_EMAIL from .env)")
    print(" 2. Manual Login     (Opens browser for interactive login)")
    print(" 3. Existing Session (Use existing storage_state.json directly)")
    print(" 4. Exit")
    print("=" * 65)

    choice = input("Select an option (1-4): ").strip()

    if choice == "1":
        return await automated_login(config)

    elif choice == "2":
        await manual_login(config)
        return state_path.exists()

    elif choice == "3":
        if not state_path.exists():
            logger.error(f"No existing session found at '{state_path}'. Please select option 1 or 2.")
            return await select_authentication_method(config)
        return True

    elif choice == "4":
        logger.info("Exiting application.")
        sys.exit(0)

    else:
        logger.warning("Invalid option. Enter 1, 2, 3, or 4.")
        return await select_authentication_method(config)

async def run_engine(config: dict):
    # Freshly initialize database on every run
    reset_and_init_db(config["paths"]["db_path"])

    auth_manager = AuthManager(config)
    try:
        context = await auth_manager.get_context()
        page = await context.new_page()

        if not await auth_manager.verify_login(page):
            logger.error("Aborting run: session is not authenticated.")
            return

        target_users = config["scraper"].get("target_users", [])
        if not target_users:
            logger.warning("No target users defined in config.json under 'scraper.target_users'.")
            return

        all_collected_tweets = []

        for username in target_users:
            tweets = await scrape_user_profile(page, username, config)
            all_collected_tweets.extend(tweets)
            await asyncio.sleep(2)  # Delay between target account navigations

        # Save all results to database
        save_tweets_to_db(config["paths"]["db_path"], all_collected_tweets)

    except Exception as e:
        logger.error(f"Engine execution failure: {e}")
    finally:
        await auth_manager.close()

async def main():
    config = load_config()
    authenticated = await select_authentication_method(config)

    if authenticated:
        await run_engine(config)
    else:
        logger.error("Authentication failed. Aborting pipeline.")

if __name__ == "__main__":
    asyncio.run(main())