"""Pick and open the browser backend on Windows; "auto" follows Windows default browser."""

from __future__ import annotations

import winreg
from typing import Any

from .browser import Browser
from .chromium import CHROMIUM_APPS, ChromiumApp, ChromiumBrowser, app_path

DEFAULT_BROWSER_KEY = "edge"


def default_windows_browser() -> str:
    """Detect default browser from Windows UserChoice registry key."""
    key_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            prog_id = str(prog_id).lower()
            if "edge" in prog_id:
                return "edge"
            if "chrome" in prog_id:
                return "chrome"
            if "brave" in prog_id:
                return "brave"
            if "opera" in prog_id:
                return "opera"
            if "vivaldi" in prog_id:
                return "vivaldi"
    except (OSError, FileNotFoundError):
        pass

    # Fallback: check which browser executable is actually found on disk
    for app in CHROMIUM_APPS:
        if app_path(app):
            return app.key
    return DEFAULT_BROWSER_KEY


def resolve(choice: str | None = None) -> str:
    """Backend key for a setting: "edge", "chrome", "brave", etc."""
    choice = (choice or "auto").casefold()
    if any(app.key == choice for app in CHROMIUM_APPS):
        return choice
    detected = default_windows_browser()
    return detected


WEB_SEARCH_ENGINES = ("google", "duckduckgo", "bing", "brave")


def web_search_engine(setting: str, backend: str) -> str:
    """The search engine for a plain "search for …"."""
    if setting in WEB_SEARCH_ENGINES:
        return setting
    return "google"


def open_browser(key: str | None = None) -> Browser:
    resolved_key = resolve(key)
    app: ChromiumApp = next(
        (a for a in CHROMIUM_APPS if a.key == resolved_key),
        CHROMIUM_APPS[0],  # Default to Edge
    )
    return ChromiumBrowser(app)
