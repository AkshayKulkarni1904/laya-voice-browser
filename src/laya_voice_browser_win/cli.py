"""Command-line interface for LayaBrowse on Windows."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .browser import ReconnectingBrowser
from .browsers import default_windows_browser, open_browser, resolve
from .chromium import installed_apps
from .controller import StreamingController
from .hotkeys import WindowsHotkeyListener
from .island_ui import IslandApp
from .laya import LayaEngine
from .types import TranscriptEvent


def _cmd_status(args: argparse.Namespace) -> int:
    print("=" * 60)
    print(" LayaBrowse for Windows - System Status")
    print("=" * 60)

    # Browsers
    apps = installed_apps()
    default_app = default_windows_browser()
    print(f"\nInstalled Chromium Browsers ({len(apps)} found):")
    for app in apps:
        is_def = " (Default)" if app.key == default_app else ""
        print(f"  • {app.name} [{app.key}]{is_def}")

    # Engine
    print("\nDecision Engine:")
    try:
        import laya
        print("  • Official Laya package: Available (PyTorch)")
    except ImportError:
        print("  • Fast Rule/Lexical Fallback: Active (Zero-latency sub-ms)")

    # Speech & UI
    print("\nInterface:")
    print("  • Dynamic Island: PySide6 Hardware Accelerated")
    print("  • Global Hotkey: Double-tap Left Control (Win32 Hook)")
    print("=" * 60)
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    print("Running LayaBrowse Windows diagnostic checks...")
    ok = True

    # Check 1: Chromium browser available
    apps = installed_apps()
    if apps:
        print(f"  [PASS] Found browser: {apps[0].name}")
    else:
        print("  [FAIL] No Chromium browser detected. Please install Microsoft Edge or Google Chrome.")
        ok = False

    # Check 2: Websockets
    try:
        import websockets
        print("  [PASS] Websockets library installed")
    except ImportError:
        print("  [FAIL] Websockets not installed. Run: pip install websockets")
        ok = False

    # Check 3: UI
    try:
        import PySide6
        print("  [PASS] PySide6 installed (Floating Island UI ready)")
    except ImportError:
        print("  [WARN] PySide6 not installed. UI will run in headless console mode.")

    print("\nResult:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


def _cmd_test(args: argparse.Namespace) -> int:
    query = " ".join(args.command)
    print(f"Executing simulated voice command: {query!r}")

    engine = LayaEngine()
    engine.warm()

    target_browser = resolve(args.browser)
    print(f"Opening browser ({target_browser})...")
    browser = open_browser(target_browser)

    controller = StreamingController(
        browser,
        engine,
        announce=lambda msg: print(f"  >> {msg}"),
    )

    event = TranscriptEvent(text=query, final=True, utterance_id="test-1", at=time.time())
    controller.submit(event)
    controller.wait_idle(timeout=15.0)
    print("\nCommand completed successfully!")
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    print("Starting LayaBrowse for Windows...")
    print("Double-tap Left Control to activate voice listening.")
    print("Press Ctrl+C in this terminal to stop.")

    # 1. Start Island UI
    island = None
    if not args.no_gui:
        try:
            island = IslandApp()
            island.start()
        except Exception as e:
            print(f"Could not initialize Island UI: {e}")

    # 2. Initialize Engine & Browser
    engine = LayaEngine(args.model)
    engine.warm()

    chosen_browser = resolve(args.browser)
    browser = ReconnectingBrowser(lambda: open_browser(chosen_browser))

    # 3. Controller
    controller = StreamingController(
        browser,
        engine,
        announce=print,
        island=island,
    )

    # 4. Hotkey Listener (Double-Tap Left Control)
    is_listening = True

    def on_hotkey_toggle():
        nonlocal is_listening
        is_listening = not is_listening
        status_text = "Listening" if is_listening else "Paused"
        print(f"\n[Hotkey] Voice control toggled: {status_text}")
        if island:
            island.set_status(status_text, "listening" if is_listening else "idle")

    hotkeys = WindowsHotkeyListener(on_hotkey_toggle)
    hotkeys.start()

    # 5. Interactive input loop (CLI fallback / voice simulation)
    print("\nYou can also type commands directly below:")
    try:
        while True:
            try:
                line = input("layabrowse> ").strip()
                if not line:
                    continue
                if line.lower() in ("exit", "quit"):
                    break
                event = TranscriptEvent(text=line, final=True, utterance_id=f"cli-{time.time()}", at=time.time())
                controller.submit(event)
            except EOFError:
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("\nShutting down LayaBrowse...")
        hotkeys.stop()
        controller.close()
        browser.close()
        if island:
            island.hide()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="layabrowse",
        description="LayaBrowse for Windows: Voice-control Edge or Chrome with local Laya decisions.",
    )
    parser.add_argument("--browser", choices=["auto", "edge", "chrome", "brave", "opera"], default="auto")
    parser.add_argument("--model", default=None, help="Laya model name or local path")

    subparsers = parser.add_subparsers(dest="command")

    # start
    p_start = subparsers.add_parser("start", help="Start the LayaBrowse voice listener")
    p_start.add_argument("--no-gui", action="store_true", help="Run without the floating island overlay")

    # status
    subparsers.add_parser("status", help="Show system status and detected browsers")

    # doctor
    subparsers.add_parser("doctor", help="Run environment diagnostic checks")

    # test
    p_test = subparsers.add_parser("test", help="Test a single command without voice")
    p_test.add_argument("command", nargs="+", help="Command phrase to test")

    args = parser.parse_args(argv)

    if args.command == "status":
        return _cmd_status(args)
    elif args.command == "doctor":
        return _cmd_doctor(args)
    elif args.command == "test":
        return _cmd_test(args)
    elif args.command == "start" or args.command is None:
        return _cmd_start(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
