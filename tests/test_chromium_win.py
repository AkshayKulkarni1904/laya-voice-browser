from __future__ import annotations

from laya_voice_browser_win.chromium import CHROMIUM_APPS, installed_apps, launch_arguments, profile_dir
from laya_voice_browser_win.browsers import default_windows_browser, resolve


def test_chromium_apps_configured():
    keys = [app.key for app in CHROMIUM_APPS]
    assert "edge" in keys
    assert "chrome" in keys
    assert "brave" in keys


def test_launch_arguments():
    edge_app = next(a for a in CHROMIUM_APPS if a.key == "edge")
    args = launch_arguments(edge_app)
    assert "--remote-debugging-port=0" in args
    assert "--no-first-run" in args
    assert any("--user-data-dir=" in arg for arg in args)


def test_resolve_default():
    resolved = resolve("auto")
    assert resolved in ["edge", "chrome", "brave", "chromium", "opera", "vivaldi"]


def test_profile_dir():
    edge_app = next(a for a in CHROMIUM_APPS if a.key == "edge")
    p = profile_dir(edge_app)
    assert "LayaBrowse" in str(p)
    assert "edge" in str(p)
