import json
from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"

class Config:
    def __init__():
        pass

def _resolve_proxy(config_data: dict):
    """
    Builds a Playwright-compatible proxy dict from the "proxy" section of
    config.json, or returns None if no proxy should be used.

    This is intentionally opt-in: if "proxy" is missing, disabled, or has
    no server set, the browser launches with a normal direct connection.
    Anyone cloning the repo works out of the box with no proxy required;
    people who need one just fill in their own config.json locally
    (which stays out of git — see .gitignore).
    """
    proxy_cfg = config_data.get("proxy", {}) or {}

    if not proxy_cfg.get("enabled", False):
        return None

    server = (proxy_cfg.get("server") or "").strip()
    if not server:
        return None

    proxy = {"server": server}

    username = proxy_cfg.get("username")
    password = proxy_cfg.get("password")
    if username:
        proxy["username"] = username
    if password:
        proxy["password"] = password

    return proxy

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
        
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    # Resolve paths relative to project root
    paths = config_data.get("paths", {})
    env_path = BASE_DIR / paths.get("env_file", ".env")
    storage_state_path = BASE_DIR / paths.get("storage_state", "data/storage_state.json")
    db_path = BASE_DIR / paths.get("db_path", "data/tweets.db")

    # Load environment variables
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    return {
        "paths": {
            "env_file": env_path,
            "storage_state": storage_state_path,
            "db_path": db_path
        },
        "scraper": config_data.get("scraper", {
            "mode": "time",
            "max_tweets": 50,
            "time_window_hours": 12
        }),
        "credentials": {
            "user": os.getenv("X_USER", ""),
            "password": os.getenv("X_PASS", ""),
            "email": os.getenv("X_EMAIL", "")
        },
        "proxy": _resolve_proxy(config_data)
    }