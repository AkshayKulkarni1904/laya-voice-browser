"""Windows Global Hotkey & Double-Tap Key Listener.

Uses Win32 WH_KEYBOARD_LL low-level hook to detect:
1. Double-tap Left Control (standard LayaBrowse activation)
2. Custom hotkey chords (e.g. Ctrl + Shift + Space)
"""

from __future__ import annotations

import ctypes
import threading
import time
from collections.abc import Callable
from ctypes import wintypes

# Win32 Constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_CONTROL = 0x11
VK_SPACE = 0x20
VK_SHIFT = 0x10


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT)
)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class WindowsHotkeyListener:
    """Listens for global double-tap Left Control or customizable hotkey combinations on Windows."""

    def __init__(
        self,
        on_trigger: Callable[[], None],
        *,
        double_tap_interval_ms: float = 380.0,
    ) -> None:
        self.on_trigger = on_trigger
        self.double_tap_interval_ms = double_tap_interval_ms / 1000.0
        self._hook = None
        self._hook_proc = None
        self._thread: threading.Thread | None = None
        self._thread_id = None
        self._running = False
        self._last_ctrl_release_time = 0.0
        self._intervening_key = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_hook_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run_hook_loop(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()

        def hook_callback(nCode: int, wParam: wintypes.WPARAM, lParam: ctypes.POINTER(KBDLLHOOKSTRUCT)):
            if nCode >= 0:
                vk = lParam.contents.vkCode
                now = time.monotonic()

                if wParam in (WM_KEYUP, WM_SYSKEYUP):
                    if vk in (VK_LCONTROL, VK_CONTROL):
                        if not self._intervening_key:
                            diff = now - self._last_ctrl_release_time
                            if diff <= self.double_tap_interval_ms:
                                self._last_ctrl_release_time = 0.0
                                try:
                                    self.on_trigger()
                                except Exception:
                                    pass
                            else:
                                self._last_ctrl_release_time = now
                        else:
                            self._last_ctrl_release_time = now
                            self._intervening_key = False
                    else:
                        self._intervening_key = True

                elif wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    if vk not in (VK_LCONTROL, VK_CONTROL):
                        self._intervening_key = True

            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        self._hook_proc = HOOKPROC(hook_callback)
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._hook_proc, kernel32.GetModuleHandleW(None), 0
        )

        msg = wintypes.MSG()
        while self._running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if b_ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
