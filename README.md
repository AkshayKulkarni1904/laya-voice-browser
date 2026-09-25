# LayaBrowse for Windows 🎙️🌐

**Voice-control Microsoft Edge, Google Chrome, Brave, or any Chromium browser on Windows using local Laya decision models and streaming speech recognition.**

Double-tap **Left Control**, speak what you want, and LayaBrowse operates your browser in real time with an animated Windows 11 Dynamic Island floating overlay.

---

![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)
![Chromium](https://img.shields.io/badge/Browsers-Edge%20%7C%20Chrome%20%7C%20Brave-4285F4)
![Local AI](https://img.shields.io/badge/AI-100%25%20Local%20%26%20Private-success)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ⚡ What is LayaBrowse Windows?

This project is a complete reverse-engineered Windows port of [aryanbhujade/laya-mlx-voice-browser](https://github.com/aryanbhujade/laya-mlx-voice-browser). While the original repository was locked to Apple Silicon Macs, **LayaBrowse Windows** brings the same lightning-fast, local, voice-driven browsing experience to all Windows users.

```
Double-tap Left Control → “open YouTube and search for Lo-Fi Beats”
                         → “open the first video”
                         → “theater mode”
                         → “in a new tab, open Wikipedia and search for Alan Turing”
                         → “scroll down”
```

---

## ✨ Features

- **🚀 100% Local Decision AI**: Powered by **Laya** non-autoregressive decision models (PyTorch / CUDA / DirectML / CPU) with an ultra-fast sub-millisecond lexical fallback engine.
- **🎨 Windows 11 Dynamic Island**: Gorgeous glassmorphic top-centered pill overlay displaying live waveform audio levels, real-time streaming transcripts, and execution badges.
- **⌨️ Global Win32 Hotkey**: Double-tap **Left Control** from any application to start/pause listening.
- **🌐 Zero Driver Setup**: Operates **Microsoft Edge** (pre-installed on all Windows systems) and **Google Chrome** via Chrome DevTools Protocol (CDP) over WebSockets.
- **🛡️ Destructive Action Safeguards**: Financial transactions, deletions, and account alterations require an explicit spoken "confirm".
- **📦 Site-Aware Control Packs**: Optimized voice controls for YouTube, GitHub, Gmail, Google, Wikipedia, Amazon, Spotify, Netflix, and more.

---

## 🛠️ Quick Installation

### 1. Clone the repository
```powershell
git clone https://github.com/your-username/laya-voice-browser-windows.git
cd laya-voice-browser-windows
```

### 2. Install dependencies
```powershell
pip install -e .
```

To install all optional extras (PyTorch GPU acceleration, Whisper STT, PySide6 GUI):
```powershell
pip install -e ".[all]"
```

### 3. Verify your environment
```powershell
layabrowse doctor
```

---

## 🚀 Usage

### Start the Voice Browser
```powershell
layabrowse start
```

Or choose a specific browser:
```powershell
layabrowse start --browser chrome
```

### Test a Command in Headless / CLI Mode
```powershell
layabrowse test "open wikipedia and search for Alan Turing"
```

---

## 🗣️ What You Can Say

| Goal | Examples |
|---|---|
| **Navigate** | *"open Wikipedia"*, *"go to github.com"* |
| **Search** | *"search for Quantum Computing"*, *"search YouTube for lo-fi beats"* |
| **Chain Actions** | *"open YouTube and search for space documentaries"* |
| **New Tabs** | *"in a new tab, open Amazon and search for mechanical keyboards"* |
| **Click Elements** | *"click the first video"*, *"click Read More"* |
| **Type Text** | *"type hello world into the search box"*, *"press enter"* |
| **Scroll** | *"scroll down a little"*, *"scroll to the bottom"*, *"scroll up"* |
| **Media Control** | *"pause"*, *"resume"*, *"skip ahead 30 seconds"*, *"mute"* |
| **Ambiguity Handling** | Say *"one"*, *"two"*, or *"the second one"* when numbered badges appear |
| **Guarded Actions** | Say *"confirm"* or *"cancel"* for sensitive actions |

---

## 🧩 Site-Aware Packs

LayaBrowse comes with specialized phrase matching for popular platforms:

- **YouTube**: *"theater mode"*, *"full screen"*, *"mini player"*, *"first video"*, *"next video"*, *"turn on captions"*
- **GitHub**: *"view code"*, *"open pull requests"*, *"open issues"*, *"read README"*, *"star repository"*
- **Gmail**: *"compose new email"*, *"reply"*, *"forward"*, *"archive"*, *"search inbox"*
- **Wikipedia**: *"random article"*, *"references"*, *"table of contents"*
- **Amazon**: *"first product"*, *"add to cart"*, *"reviews"*, *"next page"*
- **Spotify**: *"play"*, *"pause"*, *"next track"*, *"shuffle"*

---

## 🏗️ Architecture

Read the full reverse-engineering report in [ARCHITECTURE.md](ARCHITECTURE.md).

```
[ User Microphone / Hotkey ] ────► [ Windows Hook & Speech Stream ]
                                                │
                                                ▼
                                    [ Streaming Controller ]
                                                │
                      ┌─────────────────────────┴────────────────────────┐
                      ▼                                                  ▼
             [ Laya Decision Engine ]                           [ Dynamic Island UI ]
         (PyTorch / DirectML / Rule)                          (PySide6 Glassmorphic)
                      │
                      ▼
            [ Chromium CDP Client ]
             (Edge / Chrome / Brave)
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
Original inspiration and dataset structure: [aryanbhujade/laya-mlx-voice-browser](https://github.com/aryanbhujade/laya-mlx-voice-browser) and [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya).
