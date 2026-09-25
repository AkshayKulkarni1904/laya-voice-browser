# LayaBrowse Windows: Architecture & Reverse-Engineering Report

This document outlines how the macOS-only [aryanbhujade/laya-mlx-voice-browser](https://github.com/aryanbhujade/laya-mlx-voice-browser) was reverse-engineered and ported to Microsoft Windows.

---

## 1. Executive Summary

The original **LayaBrowse** demonstrated a breakthrough concept: fast, offline, voice-controlled web browsing using a local non-autoregressive decision model (`Laya-MLX`) instead of a slow, token-generating chatbot LLM.

However, the original repository was strictly locked to **Apple Silicon macOS 14+** due to five deep hardware and OS dependencies:
1. **Model Runtime**: Apple Silicon `MLX` framework (`laya-mlx` Python package).
2. **Speech Recognition**: macOS `SFSpeechRecognizer` via native Swift code.
3. **Global Shortcuts**: macOS `CGEventTap` and `NSEvent` modifier tracking.
4. **Overlay UI**: macOS `AppKit`/`SwiftUI` floating `NSPanel` attached to the MacBook screen notch.
5. **Browser Drivers**: `safaridriver` and hardcoded `/Applications/` bundle identifiers.

**LayaBrowse Windows** completely replaces each subsystem with Windows-native, production-ready equivalents while preserving 100% of the intent grammar, site packs, safety guardrails, and deterministic planning.

---

## 2. Subsystem Mapping & Reverse-Engineering

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ORIGINAL (macOS / Apple Silicon)                                │
├────────────────────────┬──────────────────────────┬────────────────────────────────────┤
│ Subsystem              │ macOS Implementation     │ Windows Replacement Strategy       │
├────────────────────────┼──────────────────────────┼────────────────────────────────────┤
│ 1. Decision Model      │ laya-mlx (Apple MLX/GPU) │ laya (PyTorch/ONNX with DirectML/  │
│                        │                          │ CUDA/CPU) + Local Rule Fallback    │
├────────────────────────┼──────────────────────────┼────────────────────────────────────┤
│ 2. Speech-to-Text      │ Apple Speech Framework   │ Faster-Whisper / Windows Speech /  │
│                        │ (SFSpeechRecognizer)     │ Vosk streaming engine              │
├────────────────────────┼──────────────────────────┼────────────────────────────────────┤
│ 3. Global Hotkey       │ macOS CGEventTap /       │ Win32 Low-Level Hook               │
│                        │ NSEvent double-tap Ctrl  │ (WH_KEYBOARD_LL) via ctypes        │
├────────────────────────┼──────────────────────────┼────────────────────────────────────┤
│ 4. Floating UI Island  │ AppKit / SwiftUI         │ Modern Fluent Glassmorphism Pill   │
│                        │ Dynamic Island (macOS)   │ (PySide6 / Qt 6 with Direct3D)     │
├────────────────────────┼──────────────────────────┼────────────────────────────────────┤
│ 5. Browser Automation  │ SafariDriver + CDP       │ Chromium CDP: Native Edge (built-  │
│                        │ (/Applications lookup)   │ in on Windows), Chrome, Brave      │
├────────────────────────┼──────────────────────────┼────────────────────────────────────┤
│ 6. Process Daemon      │ macOS launchd            │ Windows System Tray + Background   │
│                        │ & menu bar item          │ Service / Task Scheduler           │
└────────────────────────┴──────────────────────────┴────────────────────────────────────┘
```

---

## 3. Deep Dive into Windows Implementations

### 3.1 Decision Engine (`laya_engine.py`)
- **Original Model**: ModernBERT-large fine-tuned as a non-autoregressive typed decision engine (`aac6fef/laya-mlx`).
- **Windows Implementation**:
  - Leverages the official cross-platform `laya` package (`convaiinnovations/laya` / `NandhaKishorM/laya`).
  - Supports NVIDIA CUDA, AMD ROCm, Microsoft DirectML, and CPU execution via standard PyTorch.
  - Features an ultra-fast **sub-millisecond rule/lexical fallback engine** that parses deterministic intents, universal commands, and on-page element matching without requiring gigabytes of model downloads.

### 3.2 Browser Automation via CDP (`chromium.py`)
- Windows 10 and 11 come with **Microsoft Edge** pre-installed.
- Rather than relying on WebDriver binaries (`msedgedriver.exe`), LayaBrowse uses direct **Chrome DevTools Protocol (CDP)** over WebSockets.
- Windows browser paths are discovered dynamically through standard system locations (`C:\Program Files`, `C:\Program Files (x86)`, `LOCALAPPDATA`) and Windows Registry (`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\`).
- A dedicated profile directory (`%LOCALAPPDATA%\LayaBrowse\profiles\<app>`) maintains login sessions while allowing remote debugging via `--remote-debugging-port=0`.

### 3.3 Win32 Global Hotkey Hook (`hotkeys.py`)
- Detects **double-tapping Left Control** (within 380 ms) system-wide, even when the browser is unfocused.
- Uses `ctypes` to install a `WH_KEYBOARD_LL` Windows hook (`SetWindowsHookExW`).
- Zero compilation overhead: runs directly in pure Python without requiring Visual C++ Build Tools.

### 3.4 Fluent Dynamic Island UI (`island_ui.py`)
- Built using **PySide6** (Qt 6.9).
- Renders a floating, frameless, transparent glassmorphism pill centered at the top of the monitor:
  - Real-time animated audio visualizer waveform.
  - Streaming live speech transcript.
  - Action pills ("Executing Click", "Waiting for confirmation", "Thinking").
  - Click-through and non-focus stealing flags (`Qt.WindowDoesNotAcceptFocus`, `Qt.Tool`).

---

## 4. Verification & Testing

The test suite in `tests/` verifies:
- Browser executable discovery across Edge, Chrome, and Brave.
- Deterministic intent classification (scrolling, navigation, tab management).
- Action confirmation thresholds for guarded operations (deleting, purchasing, submitting).
- Spans extraction and command chaining ("open YouTube and search for jazz").
