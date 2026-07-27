import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Union
from loguru import logger
from playwright.async_api import Page


async def scrape_user_profile(
    page: Page, 
    username: str, 
    max_age_hours: Union[int, float, dict] = 24
) -> List[Dict[str, Any]]:
    """
    پروفایل کاربر مورد نظر را به صورت Async اسکرپ کرده و توئیت‌های محدوده زمانی تعیین‌شده را استخراج می‌کند.
    """
    if isinstance(max_age_hours, dict):
        max_age_hours = max_age_hours.get("max_age_hours", max_age_hours.get("hours", 24))
    
    try:
        max_age_hours = int(max_age_hours)
    except (ValueError, TypeError):
        max_age_hours = 24

    logger.info(f"Starting scrape for @{username}...")
    
    try:
        await page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=20000)
    except Exception as e:
        logger.warning(f"No tweets found or page load timeout for @{username}: {e}")
        return []

    scraped_tweets: List[Dict[str, Any]] = []
    seen_tweet_urls = set()
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    
    scroll_attempts = 0
    max_scroll_attempts = 5
    old_tweets_streak = 0
    MAX_OLD_STREAK = 3

    while scroll_attempts < max_scroll_attempts:
        tweet_elements = await page.locator('article[data-testid="tweet"]').all()
        new_tweets_in_batch = 0

        for tweet in tweet_elements:
            try:
                # ۱. استخراج و بررسی زمان انتشار (Timestamp)
                time_element = tweet.locator('time').first
                if await time_element.count() == 0:
                    continue
                
                datetime_str = await time_element.get_attribute('datetime')
                if not datetime_str:
                    continue

                # ۲. استخراج لینک یکتا (جلوگیری از بررسی مجدد المان‌های تکراری در اسکرول)
                status_link = await time_element.evaluate("el => el.closest('a')?.href")
                if not status_link or status_link in seen_tweet_urls:
                    continue

                seen_tweet_urls.add(status_link)
                tweet_dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))

                # ۳. بررسی سنجاق‌شده (Pinned) بودن توئیت
                social_context = tweet.locator('div[data-testid="socialContext"]')
                is_pinned = False
                if await social_context.count() > 0:
                    context_text = (await social_context.first.text_content() or "").lower()
                    if any(kw in context_text for kw in ["pinned", "سنجاق", "pin"]):
                        is_pinned = True

                # ۴. بررسی محدوده زمانی با الگوریتم Streak
                if tweet_dt < cutoff_time:
                    if is_pinned:
                        logger.info(f"Skipping old pinned tweet for @{username}.")
                        continue
                    
                    old_tweets_streak += 1
                    logger.debug(
                        f"Tweet older than {max_age_hours}h for @{username} "
                        f"({tweet_dt.strftime('%Y-%m-%d %H:%M')}). Streak: {old_tweets_streak}/{MAX_OLD_STREAK}"
                    )
                    
                    if old_tweets_streak >= MAX_OLD_STREAK:
                        logger.info(f"Reached {MAX_OLD_STREAK} consecutive old tweets for @{username}. Stopping.")
                        return scraped_tweets
                    continue
                else:
                    old_tweets_streak = 0  # با دیدن هر توئیت جدید، شمارنده ریست می‌شود

                # ۵. استخراج متن توئیت
                text_elements = await tweet.locator('div[data-testid="tweetText"]').all_text_contents()
                content_text = text_elements[0].strip() if text_elements else ""
                quoted_text = text_elements[1].strip() if len(text_elements) > 1 else None

                full_text = content_text
                if quoted_text:
                    full_text += f"\n\n[Quoted Tweet]: {quoted_text}"

                new_tweets_in_batch += 1

                # ۶. ساخت دیکشنری خروجی (با تمام نام‌گذاری‌های استاندارد برای جلوگیری از KeyError)
                tweet_data = {
                    "user": username,
                    "username": username,
                    "target_account": username,
                    "tweet_url": status_link,
                    "text": full_text,
                    "content_text": content_text,
                    "quoted_text": quoted_text,
                    "timestamp": datetime_str,
                    "is_pinned": is_pinned,
                    "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                }
                
                scraped_tweets.append(tweet_data)

            except Exception as e:
                logger.debug(f"Parsing exception: {e}")
                continue

        # اسکرول به پایین جهت دریافت داده‌های جدید
        await page.evaluate("window.scrollBy(0, 1000)")
        await asyncio.sleep(1.5)

        if new_tweets_in_batch == 0:
            scroll_attempts += 1
        else:
            scroll_attempts = 0

    return scraped_tweets