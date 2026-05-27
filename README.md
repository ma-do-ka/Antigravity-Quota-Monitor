# 👾 Antigravity Quota Monitor (AQM)

![Antigravity Quota Monitor Banner](banner.png)

[![Open VSX Version](https://img.shields.io/open-vsx/v/ma-do-ka/antigravity-quota)](https://open-vsx.org/extension/ma-do-ka/antigravity-quota)
[![Open VSX Downloads](https://img.shields.io/open-vsx/dt/ma-do-ka/antigravity-quota?color=green)](https://open-vsx.org/extension/ma-do-ka/antigravity-quota)
[![GitHub Stars](https://img.shields.io/github/stars/ma-do-ka/Antigravity-Quota-Monitor?style=flat&color=yellow)](https://github.com/ma-do-ka/Antigravity-Quota-Monitor)
[![GitHub Issues](https://img.shields.io/github/issues/ma-do-ka/Antigravity-Quota-Monitor)](https://github.com/ma-do-ka/Antigravity-Quota-Monitor/issues)
[![License](https://img.shields.io/github/license/ma-do-ka/Antigravity-Quota-Monitor)](https://github.com/ma-do-ka/Antigravity-Quota-Monitor/blob/main/LICENSE)

🇯🇵 **[日本語バージョンはこちら (Jump to Japanese Version)](#-日本語バージョン)**

---

**Antigravity Quota Monitor (AQM)** is a premium macOS menu bar utility (SwiftBar / xbar plugin) designed to monitor real-time API quotas, reset times, and monthly credits for your LLMs (Flash, Pro, Sonnet, Opus, etc.) under the Antigravity agent system.

With an ultra-fast, zero-ui-interference local API collector, it helps you keep track of your active model quotas without interrupting your workspace flow.

---

## ✨ Features

*   **📊 Real-Time Multi-Model Status Board**: Monitor current remaining percentage quotas for Flash (Med/High/Low), Pro (Low/High), Sonnet 4.6, Opus 4.6, and GPT-OSS 120B in a beautiful menu bar ribbon.
*   **🔋 Pure Stealth & Zero-Configuration**: 100% background fetching. No popup windows or browser session hijacking. It automatically hooks into your local Language Server daemon over localhost and fetches directly via the Connect protocol.
*   **💳 Monthly Credit Tracker**: Calculates your precise remaining Monthly Prompt Credits and Flow Credits, displaying them with status colors depending on usage (Green for safe, Yellow for warnings, Red for exhausted).
*   **⏱️ Smart UTC-to-Local Reset Times**: Detects the precise moment when your exhausted quota recovers and displays it translated to your local timezone.
*   **🌐 In-Menu Translation (EN / JA)**: Toggle display languages between English and Japanese with a single click.
*   **👾 Stealth & Pro Design**: Custom built-in interactive `About` section. The default debug menu items ("Run in Terminal", "Disable Plugin", standard About box) are hidden to keep the menu pristine. (Hold `Option (Alt)` while clicking to reveal them!).

---

## 🔴 Model Quota Status Table

The status bar represents current remaining quotas using a premium 6-tier color-coded system with dynamic percentage indicators. 

| Status | Dropdown Color | Percentage Range | Visual Representation & Meaning |
| :---: | :--- | :---: | :--- |
| 🟣 | **Purple** | `100%` | **Full capacity** — Completely safe and ready to generate content. |
| 🔵 | **Blue** | `80% - 99%` | **Highly stable** — Securely active with plenty of quota remaining. |
| 🟢 | **Green** | `60% - 79%` | **Safe state** — Normal operation mode with stable capacity. |
| 🟡 | **Yellow** | `40% - 59%` | **Caution mode** — Approaching limits. Displays the reset timer (e.g., `⟳ 15:16`). |
| 🟠 | **Orange** | `20% - 39%` | **Low capacity** — Quota running thin. Recovery timer displayed. |
| 🔴 | **Red** | `0% - 19%` | **Exhausted** — Crucial recovery state. Displays local reset time to indicate recovery. |

![AQM Menu Screenshot](menu_screenshot.png)

---

## 🚀 Installation & Setup

Installation is highly streamlined. Please follow the steps below.

### 1. Install via VS Code Extension (Recommended)

The easiest way to get started is to install the bridge extension directly from your IDE's marketplace.

1. Open the **Extensions Panel** in your VS Code compatible IDE (VS Code, Cursor, etc.).
2. Search for **`AQM`** or `Antigravity Quota`.
3. Install **Antigravity Quota Monitor** published by **ma-do-ka**.

* 📦 *Open VSX: [ma-do-ka/antigravity-quota](https://open-vsx.org/extension/ma-do-ka/antigravity-quota)*
* 💻 *GitHub: [ma-do-ka/Antigravity-Quota-Monitor](https://github.com/ma-do-ka/Antigravity-Quota-Monitor)*

> [!NOTE]
> **SwiftBar Integration**
> Installing this IDE extension will automatically deploy the required SwiftBar plugin scripts to your macOS system in the background.  
> *Note: The SwiftBar application itself is not bundled. If it is not installed on your system, the extension will display a prompt with a direct link to download it.*

### 2. Prepare SwiftBar (macOS)

To display the monitor in your menu bar, you need the native macOS application **SwiftBar**.

1. Download and install the latest release from the [SwiftBar Official GitHub](https://github.com/swiftbar/SwiftBar) (or run `brew install swiftbar` if you use Homebrew).
2. Launch the SwiftBar app. It will automatically detect the AQM plugin deployed by the IDE and display your quotas in the menu bar!

---

## 🏗️ Technical Architecture

This plugin is optimized for high-performance, low-overhead execution:

*   **`antigravity_status.py`** (The Orchestrator): Parses local agent diagnostic logs, performs high-efficiency caching, manages localized menu renders, and acts as the SwiftBar entry point.
*   **`get_quota.js`** (The Connect Crawler): An ultra-fast script executing Node.js native sockets. It identifies the target Language Server PID via `/bin/ps`, scans target sockets restricted strictly to that PID, and securely makes direct HTTP POST calls to the Connect server in **under 0.04 seconds**.

---

## 🛡️ Privacy & Security

*   **No Third-Party Siphoning**: 100% of network traffic travels strictly over `127.0.0.1` (localhost). Your credentials never touch public endpoints or secondary logging systems.
*   **No Stored Keys**: The system utilizes temporary session tokens dynamically loaded from running daemons. There are no API keys saved in plaintext files.

---

### 🌟 Support the Project
If you find this project helpful, please consider giving it a ⭐ on [GitHub](https://github.com/ma-do-ka/Antigravity-Quota-Monitor)! Your support keeps the development active and motivated.

---

# 🇯🇵 日本語バージョン

**Antigravity Quota Monitor (AQM)** は、macOS のメニューバー（システムバー）および VS Code に、Antigravity（Gemini）エージェント環境下の各種モデル（Flash、Pro、Sonnet、Opusなど）のリアルタイム利用クォータ残量、リセット時間、および月間プロンプト/フロークレジット制限枠を**美しく可視化するプレミアムユーティリティ**です。

ローカル起動している Language Server から暗号セッショントークンを動的に自動検出し、 Connect API エンドポイントを直接フェッチする超高速バックグラウンド動作のため、開発中のエージェントワークスペースの流れを一切阻害しません。

---

## ✨ 主な特長と機能

*   **📊 リアルタイム・マルチモデルステータスボード**: Flash (Med/High/Low), Pro (Low/High), Sonnet 4.6, Opus 4.6, GPT-OSS 120B などの主要モデルのクォータ残量をメニューバーに一括横並びで表示。
*   **🔋 ユーザー干渉ゼロのサイレントスキャン**: ブラウザ操作の乗っ取りや、邪魔な設定ポップアップウィンドウは **100% 発生しません**。ローカルで常駐する Language Server デーモンから通信ポートとCSRFトークンを自動的に検出し、直接通信を行います。
*   **💳 月間利用クレジット枠の可視化**: 月間のプロンプト制限、フロークレジット枠、Google One AIクレジットの残量をパーセンテージ付きで美しく表示。クォータ残量に応じてカラーが自動変化（🟢安全、🟡警告、🔴枯渇）します。
*   **⏱️ インテリジェントな回復時間（日本時間）自動変換**: クォータが枯渇した際、いつ制限が解除されるかをローカルタイムゾーン（JST）にスマートに自動変換して表示。
*   **🌐 言語切り替えUI (日/英)**: 詳細メニューからワンクリックで表示言語を英語・日本語に動的にトグル切り替え可能。
*   **👾 ステルス＆プロ仕様のクリーンデザイン**: SwiftBarのデフォルトデバッグ項目を隠し、完全にデザインされた About セクションを統合した極上のメニューに仕上げています（`Option (Alt)` キーを押しながらクリックすると通常のデバッグメニューが表示されます）。

---

## 🔴 モデルクォータ表示ステータス一覧

メニューバー上の各モデルの残りクォータは、プレミアムな6色のカラーコードシステムと動的パーセンテージインジケータによって視覚的に美しく分類されます。

| 状態 | ドロップダウン色 | パーセント閾値 | 視覚表現とステータスの意味 |
| :---: | :--- | :---: | :--- |
| 🟣 | **紫 (Purple)** | `100%` | **満タン稼働中** — クォータは完全に安全で、すぐにフル生成が可能です。 |
| 🔵 | **青 (Blue)** | `80% - 99%` | **極めて安定** — 十分な容量を維持して安全に稼働中。 |
| 🟢 | **緑 (Green)** | `60% - 79%` | **通常動作状態** — 安定した残量があり、平常通り生成可能です。 |
| 🟡 | **黄 (Yellow)** | `40% - 59%` | **注意モード** — 残量がやや低下。回復時間が動的に表示されます（例: `⟳ 15:16`）。 |
| 🟠 | **橙 (Orange)** | `20% - 39%` | **残量僅少** — 回復時間（日本時間）を表示。生成を抑えて回復を待つことを推奨。 |
| 🔴 | **赤 (Red)** | `0% - 19%` | **制限・枯渇** — API制限回復待ち。回復タイムスタンプを表示。 |

---

## 🚀 導入・セットアップ手順

導入は非常に簡単です。以下の手順に従ってください。

### 1. VS Code 拡張機能のインストール（推奨）

最も簡単な方法は、お使いのIDE（VS Code、Cursorなど）の拡張機能マーケットプレイスから直接インストールすることです。

1. IDEの **拡張機能パネル**（Extensions）を開きます。
2. 検索バーに **`AQM`** または `Antigravity Quota` と入力します。
3. **ma-do-ka** がパブリッシュしている **Antigravity Quota Monitor (AQM)** を選択して「インストール」をクリックします。

* 📦 *Open VSX 公式: [ma-do-ka/antigravity-quota](https://open-vsx.org/extension/ma-do-ka/antigravity-quota)*
* 💻 *GitHub ソース: [ma-do-ka/Antigravity-Quota-Monitor](https://github.com/ma-do-ka/Antigravity-Quota-Monitor)*

> [!NOTE]
> **SwiftBar との自動ブリッジ配置**
> IDEに拡張機能をインストールすると、バックグラウンドで自動的に macOS の SwiftBar 用スクリプトが適切な場所に配置・連携されます。
> *※注意: SwiftBar アプリ本体自体は同梱されていません。未インストールの場合は、拡張機能からダウンロード用のダイレクトリンクを案内するプロンプトが表示されます。*

### 2. Prepare SwiftBar (macOS)

メニューバーにクォータを表示するためには、macOS 用のネイティブアプリである **SwiftBar** が必要です。

1. [SwiftBar 公式 GitHub](https://github.com/swiftbar/SwiftBar) から最新リリースをダウンロードしてインストールします（Homebrew ユーザーは `brew install swiftbar` でもインストール可能です）。
2. SwiftBar を起動します。IDE拡張機能が配置した AQM プラグインを自動検出して、メニューバーにリアルタイムなクォータ情報が即時に表示されます！

---

## 🏗️ 技術アーキテクチャ

本ツールは極めて軽量かつシステム負荷を最小限に抑えるよう設計されています：

*   **`antigravity_status.py`**（司令塔）: ローカルエージェントのログ監視、高効率なファイルキャッシュ制御、SwiftBar 向けの美麗なマルチ言語メニューのレンダリングを司ります。
*   **`get_quota.js`**（超高速クローラ）: Node.js ネイティブソケット処理による超軽量スクリプト。`/bin/ps` から Language Server の PID を特定後、その PID に制限されたリスニングソケットを瞬間スキャンし、暗号トークンを用いてわずか **0.04 秒未満** でクォータ情報を取得します。

---

## 🛡️ プライバシーとセキュリティ

*   **完全ローカル通信**: 全てのネットワーク通信はローカルホスト（`127.0.0.1`）でのみ完結します。お客様の認証情報やクォータデータが外部の第三者サーバーやログ収集サービスへ送信されることは一切ありません。
*   **セッショントークンの安全な運用**: 起動中のプロセスから一時的なセッショントークンを動的にロードして使用するため、APIキーなどをプレーンテキストでファイルに保存するリスクを完全に排除しています。

---

### 🌟 プロジェクト支援のお願い
もしこのプロジェクトが役に立ったと感じられたら、ぜひ [GitHub](https://github.com/ma-do-ka/Antigravity-Quota-Monitor) で ⭐ (Star) を押していただけると嬉しいです！皆様の支援が開発の大きなモチベーションになります。

---

*🇯🇵 For Japanese Users: 詳細な使い方やセットアップガイドについては、[こちらの公式Note記事](https://note.com/us_kabu_journal/n/nb99ef3e525ce) をご覧ください。*
