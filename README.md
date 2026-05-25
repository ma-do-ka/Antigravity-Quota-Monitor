# 👾 Antigravity Quota Monitor
<img width="1983" height="793" alt="ChatGPT Image 2026年5月26日 08_50_09" src="https://github.com/user-attachments/assets/0d1e4e6a-6188-433f-9bef-b5f1937b7cff" />

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)](#)
[![SwiftBar](https://img.shields.io/badge/Compatible-SwiftBar%20%2F%20xbar-orange.svg)](#)

A premium macOS menu bar utility (SwiftBar / xbar plugin) to monitor real-time API quotas, reset times, and monthly credits for your LLMs under the Antigravity agent system.

With an ultra-fast, zero-ui-interference local API collector, it helps you keep track of your active model quotas without interrupting your workspace flow.


---

## ✨ Features

*   **📊 Real-Time Multi-Model Status Board**: Monitor current remaining percentage quotas for Flash (Med/High/Low), Pro (Low/High), Sonnet 4.6, Opus 4.6, and GPT-OSS 120B in a beautiful menu bar ribbon.
*   **🔌 Zero-Interference API Crawling**: Pure background fetching. No popup windows or browser session hijacking. It automatically hooks into your local Language Server daemon, locates the active LISTEN port, extracts the CSRF token, and fetches directly via the Connect protocol.
*   **💳 Monthly Credit Tracker**: Calculates your precise remaining Monthly Prompt Credits and Flow Credits, displaying them with status colors depending on usage (Green for safe, Yellow for warnings, Red for exhausted).
*   **⏱️ Smart UTC-to-Local Reset Times**: Detects the precise moment when your exhausted quota recovers and displays it translated to your local timezone.
*   **🌐 In-Menu Translation (EN / JA)**: Toggle display languages between English and Japanese with a single click.
*   **👾 Stealth & Pro Design**: Custom built-in interactive `About` section. The default debug menu items ("Run in Terminal", "Disable Plugin", standard About box) are hidden to keep the menu pristine. (Hold `Option (Alt)` while clicking to reveal them!).

<img width="926" height="751" alt="image" src="https://github.com/user-attachments/assets/8462c7f6-e49d-4075-8a93-91192f793f40" />


---

## 🛠️ Requirements

*   **macOS** (compatible with Apple Silicon and Intel)
*   **Python 3.x**
*   **Node.js** (Standard runtime, no external npm packages required)
*   **SwiftBar** (Recommended) or **xbar** installed on macOS

---

## 🚀 Installation & Setup

### Step 1: Clone the Repository
Clone this repository to your preferred local workspace (e.g., your Desktop or Projects folder):
```bash
git clone https://github.com/yourusername/AntigravityQuarterViewer.git
cd AntigravityQuarterViewer
```

### Step 2: Establish the SwiftBar Symbolic Link
SwiftBar executes plugins placed in its plugins directory. Create a symbolic link pointing to the executable Python coordinator in the `app` subdirectory:

```bash
# 1. Ensure the executable permission is set
chmod +x app/antigravity_status.py

# 2. Link the script to the SwiftBar plugins folder
ln -sf "$(pwd)/app/antigravity_status.py" ~/Library/Application\ Support/SwiftBar/plugins/antigravity_status.py
```

### Step 3: Refresh SwiftBar
Open SwiftBar, or refresh all active plugins by running the following command:
```bash
open -g "swiftbar://refreshall"
```
The monitor will instantly appear in your menu bar.

---

## 🏗️ Technical Architecture

This plugin is optimized for high-performance, low-overhead execution:

*   **`app/antigravity_status.py`** (The Orchestrator): Parses local agent diagnostic logs, performs high-efficiency caching, manages localized menu renders, and acts as the SwiftBar entry point.
*   **`app/get_quota.js`** (The Connect Crawler): An ultra-fast script executing Node.js native sockets. It identifies the target Language Server PID via `/bin/ps`, scans target sockets using `/usr/sbin/lsof` restricted strictly to that PID, and securely makes direct HTTP POST calls to the Connect server (`GetUserStatus` endpoint) in **under 0.04 seconds**.

---

## 🛡️ Privacy & Security

*   **No Third-Party Siphoning**: 100% of network traffic travels strictly over `127.0.0.1` (localhost). Your credentials never touch public endpoints or secondary logging systems.
*   **No Stored Keys**: The system utilizes temporary session tokens dynamically loaded from running daemons. There are no API keys saved in plaintext files.

---

## 📄 License

This project is licensed under the **Apache License 2.0**.

```text
Copyright 2026 Madoka (US Stock Journal Editorial Director)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
