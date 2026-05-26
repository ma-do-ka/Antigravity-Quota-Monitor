#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#<swiftbar.title>Antigravity Quota Monitor</swiftbar.title>
#<swiftbar.version>1.2</swiftbar.version>
#<swiftbar.author>Madoka</swiftbar.author>
#<swiftbar.desc>Antigravity Quota & Credit Monitor</swiftbar.desc>
#<swiftbar.icon>👾</swiftbar.icon>
#<swiftbar.hideAbout>true</swiftbar.hideAbout>
#<swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
#<swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
#
# Copyright 2026 Madoka (US Stock Journal Editorial Director)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Antigravity Status Bar Script for macOS (SwiftBar / xbar compatible)
Antigravity（Gemini）のLanguage Serverログ監視と、ローカルAPI直接フェッチによるモデル別クォータ横並び表示（キャッシュ対応）を行います。
"""

import os
import sys
import glob
import re
import datetime
import subprocess
import json

# 設定情報
DAEMON_DIR = os.path.expanduser("~/.gemini/antigravity/daemon")
LOG_PATTERN = os.path.join(DAEMON_DIR, "ls_*.log")
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
GET_QUOTA_JS = os.path.join(SCRIPT_DIR, "get_quota.js")
QUOTA_CACHE_FILE = os.path.expanduser("~/.gemini/antigravity/quota_cache.json")

# ユーザーの「Model Quota」ダッシュボード画面から読み取ったデフォルト初期クォータ値
DEFAULT_QUOTAS = {
    "F-Med": 100,
    "F-High": 100,
    "F-Low": 100,  # 新モデル
    "P-Low": 40,  # 40% remaining
    "P-High": 100,
    "Sonnet": 100,
    "Opus": 100,
    "GPT-120": 100
}

MESSAGES = {
    "en": {
        "title_stopped": "Stopped",
        "title_exhausted": "QuotaExhausted",
        "title_limit": "TokenLimit",
        "title_load": "HighLoad ({req}req)",
        "title_active": "Active",
        "header": "🤖 Antigravity Agent Status",
        "ls_running": "Language Server: 🟢 Running ({elapsed}s ago)",
        "ls_stopped": "Language Server: ⚪️ Stopped",
        "api_exhausted": "API Status: 🔴 Quota Exhausted (Waiting)",
        "api_recovering": "API Status: 🟡 Recovering ({elapsed}m ago)",
        "api_normal": "API Status: 🟢 Normal (Safe)",
        "model_header": "⚡️ Model Quotas",
        "cached": " (cached)",
        "realtime": " (realtime)",
        "reset": "reset",
        "credit_header": "💳 Monthly Credit Limits",
        "prompt_limit": "Prompt Limit",
        "flow_credit": "Flow Credit",
        "google_one": "Google One AI Credit",
        "refresh": "🔄 Refresh",
        "lang_header": "🌐 Language",
        "about_header": "ℹ️ About",
        "about_version": "  ・Antigravity Quota Monitor: v1.2",
        "about_website": "  ・Website: https://note.com/us_kabu_journal/n/nb99ef3e525ce",
        "about_copyright": "  ・Copyright © 2026 US stock journal. All rights reserved."
    },
    "ja": {
        "title_stopped": "停止中",
        "title_exhausted": "クォータ枯渇",
        "title_limit": "トークン制限",
        "title_load": "高負荷 ({req}req)",
        "title_active": "稼働中",
        "header": "🤖 Antigravity エージェント状態",
        "ls_running": "Language Server: 🟢 稼働中 ({elapsed}秒前に更新)",
        "ls_stopped": "Language Server: ⚪️ 停止中",
        "api_exhausted": "API制限状況: 🔴 クォータ枯渇中 (回復待ち)",
        "api_recovering": "API制限状況: 🟡 制限回復中 ({elapsed}分前にエラー)",
        "api_normal": "API制限状況: 🟢 正常 (安全)",
        "model_header": "⚡️ 各モデルのクォータ現状",
        "cached": "（キャッシュ表示中）",
        "realtime": "（リアルタイム同期中）",
        "reset": "リセット",
        "credit_header": "💳 月間利用クレジット枠",
        "prompt_limit": "プロンプト制限",
        "flow_credit": "フロークレジット",
        "google_one": "Google One AI クレジット",
        "refresh": "🔄 再読み込み",
        "lang_header": "🌐 言語設定 (Language)",
        "about_header": "ℹ️ About",
        "about_version": "  ・Antigravity Quota Monitor: v1.2",
        "about_website": "  ・Website: https://note.com/us_kabu_journal/n/nb99ef3e525ce",
        "about_copyright": "  ・Copyright © 2026 US stock journal. All rights reserved."
    }
}

def get_latest_log_file():
    """最新のログファイルを特定します。"""
    files = glob.glob(LOG_PATTERN)
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def parse_log_time(month_day_str, time_str, file_mtime):
    """ログのタイムスタンプ文字列をdatetimeオブジェクトに変換します。"""
    file_year = datetime.datetime.fromtimestamp(file_mtime).year
    try:
        month = int(month_day_str[:2])
        day = int(month_day_str[2:])
        hour, minute, second = map(int, time_str.split(':'))
        
        log_dt = datetime.datetime(file_year, month, day, hour, minute, second)
        
        file_dt = datetime.datetime.fromtimestamp(file_mtime)
        if log_dt > file_dt + datetime.timedelta(days=1):
            log_dt = log_dt.replace(year=file_year - 1)
            
        return log_dt
    except Exception:
        return None

def analyze_logs(log_file):
    """ログファイルを読み込み、利用統計およびエラー状況を解析します。"""
    if not log_file or not os.path.exists(log_file):
        return {
            "active": False,
            "quota_exhausted": False,
            "last_error_time": None,
            "requests_last_10m": 0,
            "token_limit_exceeded": 0,
            "last_log_time": None,
            "mtime": 0
        }
    
    file_mtime = os.path.getmtime(log_file)
    
    max_read_bytes = 1024 * 512  # 512KB
    file_size = os.path.getsize(log_file)
    
    lines = []
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        if file_size > max_read_bytes:
            f.seek(file_size - max_read_bytes)
            f.readline()
        lines = f.readlines()
        
    now = datetime.datetime.now()
    quota_exhausted = False
    last_error_time = None
    requests_last_10m = 0
    token_limit_exceeded = 0
    last_log_time = None
    
    log_re = re.compile(r"^([IWEF])(\d{4}) (\d{2}:\d{2}:\d{2})\.(\d{6})")
    
    for line in reversed(lines):
        match = log_re.match(line)
        if not match:
            continue
        
        log_level, month_day, time_str, _ = match.groups()
        log_dt = parse_log_time(month_day, time_str, file_mtime)
        if not log_dt:
            continue
            
        if last_log_time is None:
            last_log_time = log_dt
            
        is_request = "v1internal:streamGenerateContent" in line or "streamGenerateContent" in line
        if is_request:
            if (now - log_dt).total_seconds() <= 600:
                requests_last_10m += 1
                
        if "generation exceeded max tokens limit" in line:
            if (now - log_dt).total_seconds() <= 1800:
                token_limit_exceeded += 1
                
        if "Resource has been exhausted" in line or "check quota" in line:
            if last_error_time is None:
                last_error_time = log_dt
                if (now - log_dt).total_seconds() <= 300:
                    quota_exhausted = True
                    
    is_active = (now - datetime.datetime.fromtimestamp(file_mtime)).total_seconds() <= 120
    
    return {
        "active": is_active,
        "quota_exhausted": quota_exhausted,
        "last_error_time": last_error_time,
        "requests_last_10m": requests_last_10m,
        "token_limit_exceeded": token_limit_exceeded,
        "last_log_time": last_log_time,
        "mtime": file_mtime
    }

def get_node_path():
    """nodeコマンドの絶対パスを自動検出します。"""
    paths = [
        "/opt/homebrew/bin/node",
        "/usr/local/bin/node",
        "/usr/bin/node"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "node" # フォールバック

def get_realtime_model_quotas():
    """LSPからリアルタイムのモデル別クォータおよびクレジット情報を取得します。"""
    if not os.path.exists(GET_QUOTA_JS):
        return None
    try:
        node_path = get_node_path()
        result = subprocess.run(
            [node_path, GET_QUOTA_JS],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            if data.get("success"):
                return {
                    "quota": data.get("quota"),
                    "resets": data.get("resets"),
                    "credits": data.get("credits")
                }
    except Exception:
        pass
    return None

CACHE_LIFETIME_SECONDS = 0  # キャッシュ保持時間 (Connect APIは超軽量のため、毎回リアルタイム取得します)

def load_quota_cache_data():
    """キャッシュファイルから最終取得日時を含むデータを読み込みます。"""
    default_credits = {
        "availablePrompt": 0,
        "monthlyPrompt": 0,
        "availableFlow": 0,
        "monthlyFlow": 0,
        "googleOneAi": "0"
    }
    if os.path.exists(QUOTA_CACHE_FILE):
        try:
            with open(QUOTA_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "quota" in data:
                    if "credits" not in data:
                        data["credits"] = default_credits
                    if "resets" not in data:
                        data["resets"] = {}
                    if "language" not in data:
                        data["language"] = "en"
                    return data
        except Exception:
            pass
    
    # 存在しない場合の初期データ
    initial_data = {
        "last_fetch_time": "1970-01-01T00:00:00",
        "quota": DEFAULT_QUOTAS,
        "resets": {},
        "credits": default_credits,
        "language": "en"
    }
    save_quota_cache_data(initial_data)
    return initial_data

def save_quota_cache_data(cache_data):
    """クォータ情報を最終取得日時とともにキャッシュファイルに保存します。"""
    try:
        with open(QUOTA_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_quota_emoji(percentage):
    """パーセンテージに応じた色付き絵文字を返します。"""
    if percentage >= 100:
        return f"🟣{percentage}%"
    elif percentage >= 80:
        return f"🔵{percentage}%"
    elif percentage >= 60:
        return f"🟢{percentage}%"
    elif percentage >= 40:
        return f"🟡{percentage}%"
    elif percentage >= 20:
        return f"🟠{percentage}%"
    else:
        return f"🔴{percentage}%"

def get_quota_sphere_emoji(percentage):
    """パーセンテージに応じた色付き球体絵文字単体を返します。"""
    if percentage >= 100:
        return "🟣"
    elif percentage >= 80:
        return "🔵"
    elif percentage >= 60:
        return "🟢"
    elif percentage >= 40:
        return "🟡"
    elif percentage >= 20:
        return "🟠"
    else:
        return "🔴"

def get_quota_color(percentage):
    """パーセンテージに応じたプレミアムなカラー（Hexコード）を返します。"""
    if percentage >= 100:
        return "#a855f7"  # 紫 (🟣)
    elif percentage >= 80:
        return "#007aff"  # 青 (🔵)
    elif percentage >= 60:
        return "#34c759"  # 緑 (🟢)
    elif percentage >= 40:
        return "#ffcc00"  # 黄 (🟡)
    elif percentage >= 20:
        return "#ff9500"  # 橙 (🟠)
    else:
        return "#ff3b30"  # 赤 (🔴)

def format_reset_time(iso_str, lang="en"):
    """UTCのISO 8601形式の文字列を、ローカル（日本時間）の分かりやすい表記に変換します。"""
    if not iso_str:
        return "—"
    try:
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1] + '+00:00'
        dt_utc = datetime.datetime.fromisoformat(iso_str)
        
        # 実行マシンのローカルタイムゾーン（日本時間）に動的変換
        dt_local = dt_utc.astimezone()
        now = datetime.datetime.now().astimezone()
        
        # 今日中か明日以降かで表示フォーマットをスマートに判定
        if dt_local.date() == now.date():
            return f"⟳ {dt_local.strftime('%H:%M')}"
        else:
            return f"⟳ {dt_local.strftime('%m/%d %H:%M')}"
    except Exception:
        return "—"

def print_swiftbar_format(status, log_file, quotas, is_cached=False, credits_data=None, resets_data=None, lang="en"):
    """SwiftBar / xbar 用の標準出力を生成します。"""
    now = datetime.datetime.now()
    msg = MESSAGES[lang]
    
    # 1. メニューバー表示タイトル
    title_parts = []
    if quotas:
        # モデル順を指定して横並びテキストを構築
        model_order = [
            ("F-Med", "F-Med"),
            ("F-High", "F-High"),
            ("F-Low", "F-Low"),
            ("P-Low", "P-Low"),
            ("P-High", "P-High"),
            ("Sonnet", "Sonnet"),
            ("Opus", "Opus"),
            ("GPT-120", "GPT")
        ]
        for key, label in model_order:
            if key in quotas:
                emoji = get_quota_emoji(quotas[key])
                title_parts.append(f"{label}:{emoji}")
        
        if title_parts:
            # キャッシュ表示の場合は控えめなマークを付加
            prefix = "👾 "
            title = prefix + "  •  ".join(title_parts)
        else:
            title = f"👾 AGY: 🟢 {msg['title_active']}"
    else:
        if not status["active"]:
            title = f"👾 AGY: ⚪️ {msg['title_stopped']}"
        elif status["quota_exhausted"]:
            title = f"👾 AGY: 🔴 {msg['title_exhausted']}"
        elif status["token_limit_exceeded"] > 0:
            title = f"👾 AGY: ⚠️ {msg['title_limit']}"
        elif status["requests_last_10m"] > 10:
            title = f"👾 AGY: 🟡 {msg['title_load'].format(req=status['requests_last_10m'])}"
        else:
            title = f"👾 AGY: 🟢 {msg['title_active']}"
        
    print(title)
    
    # 2. ドロップダウンメニュー
    print("---")
    print(f"{msg['header']} | font=sans-serif size=13 bold=true")
    
    # Language Server の状態
    if status["active"]:
        elapsed = int((now - datetime.datetime.fromtimestamp(status["mtime"])).total_seconds())
        print(f"{msg['ls_running'].format(elapsed=elapsed)} | color=#34c759 font=sans-serif")
    else:
        print(f"{msg['ls_stopped']} | color=#8e8e93 font=sans-serif")
        
    # クォータ（API制限）の状態
    if status["quota_exhausted"]:
        print(f"{msg['api_exhausted']} | color=#ff3b30 font=sans-serif")
    elif status["last_error_time"]:
        err_elapsed = int((now - status["last_error_time"]).total_seconds())
        if err_elapsed < 1800:
            print(f"{msg['api_recovering'].format(elapsed=int(err_elapsed/60))} | color=#ffcc00 font=sans-serif")
        else:
            print(f"{msg['api_normal']} | color=#34c759 font=sans-serif")
    else:
        print(f"{msg['api_normal']} | color=#34c759 font=sans-serif")
        
    # モデル別クォータ詳細表示 (取得できている場合)
    if quotas:
        print("---")
        cache_status = msg["cached"] if is_cached else msg["realtime"]
        print(f"{msg['model_header']}{cache_status} | font=sans-serif size=12 bold=true")
        full_names = {
            "F-Med": "Gemini 3.5 Flash (Med)",
            "F-High": "Gemini 3.5 Flash (High)",
            "F-Low": "Gemini 3.5 Flash (Low)",
            "P-Low": "Gemini 3.1 Pro (Low)",
            "P-High": "Gemini 3.1 Pro (High)",
            "Sonnet": "Claude Sonnet 4.6",
            "Opus": "Claude Opus 4.6",
            "GPT-120": "GPT-OSS 120B"
        }
        for key, name in full_names.items():
            if key in quotas:
                val = quotas[key]
                sphere = get_quota_sphere_emoji(val)
                color = get_quota_color(val)
                
                # 回復時間の表記
                reset_text = "—"
                if val < 100 and resets_data and key in resets_data:
                    reset_text = format_reset_time(resets_data[key], lang)
                
                # アライメント位置合わせのための等幅パディング
                name_padded = name.ljust(26)
                val_padded = f"{val}%".rjust(4)
                reset_padded = reset_text.rjust(14)
                
                print(f"  {sphere} {name_padded} {val_padded}   {reset_padded} | font=Menlo size=12 color={color}")
        
    if credits_data:
        print("---")
        print(f"{msg['credit_header']} | font=sans-serif size=12 bold=true")
        
        # プロンプトクレジット
        avail_p = credits_data.get("availablePrompt")
        month_p = credits_data.get("monthlyPrompt")
        if avail_p is not None and month_p:
            remaining_p = max(0, month_p - avail_p)
            pct = (remaining_p / month_p) * 100 if month_p > 0 else 0
            color = "#34c759" if pct >= 80 else ("#ffcc00" if pct >= 30 else "#ff3b30")
            print(f"  ・{msg['prompt_limit']}: {remaining_p:,} / {month_p:,} ({pct:.1f}%) | font=monospace size=12 color={color}")
        
        # フロークレジット
        avail_f = credits_data.get("availableFlow")
        month_f = credits_data.get("monthlyFlow")
        if avail_f is not None and month_f:
            remaining_f = max(0, month_f - avail_f)
            pct = (remaining_f / month_f) * 100 if month_f > 0 else 0
            color = "#34c759" if pct >= 80 else ("#ffcc00" if pct >= 30 else "#ff3b30")
            print(f"  ・{msg['flow_credit']}: {remaining_f:,} / {month_f:,} ({pct:.1f}%) | font=monospace size=12 color={color}")
            
        # Google One AI
        g1_cred = credits_data.get("googleOneAi")
        if g1_cred is not None:
            print(f"  ・{msg['google_one']}: {g1_cred} | font=monospace size=12 color=#34c759")
            
    # 3. 言語選択UI
    print("---")
    script_path = os.path.realpath(__file__)
    print(f"{msg['lang_header']} | font=sans-serif size=12 bold=true")
    check_en = " [✓]" if lang == "en" else ""
    check_ja = " [✓]" if lang == "ja" else ""
    print(f"  ・🇺🇸 English{check_en} | terminal=false refresh=true bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--set-lang\" param3=\"en\"")
    print(f"  ・🇯🇵 日本語{check_ja} | terminal=false refresh=true bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--set-lang\" param3=\"ja\"")
    
    # 4. 独自 About セクション
    print("---")
    print(f"{msg['about_header']} | font=sans-serif size=12 bold=true")
    print(f"{msg['about_version']} | font=monospace size=11 color=#8e8e93")
    print(f"{msg['about_website']} | font=monospace size=11 href=https://note.com/us_kabu_journal/n/nb99ef3e525ce color=#007aff")
    print(f"{msg['about_copyright']} | font=monospace size=11 color=#8e8e93")

    # 5. 再読み込みボタン
    print("---")
    print(f"{msg['refresh']} | refresh=true font=sans-serif terminal=false bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--force\"")

def main():
    # 言語設定の変更コマンド処理 (--set-lang en|ja)
    if "--set-lang" in sys.argv:
        try:
            idx = sys.argv.index("--set-lang")
            lang = sys.argv[idx + 1]
            if lang in ["en", "ja"]:
                cache_data = load_quota_cache_data()
                cache_data["language"] = lang
                save_quota_cache_data(cache_data)
        except Exception:
            pass
        sys.exit(0)
    
    latest_log = get_latest_log_file()
    status = analyze_logs(latest_log)
    
    # 引数判定
    is_json = "--json" in sys.argv
    force_fetch = "--force" in sys.argv
    
    # キャッシュを読み込む
    cache_data = load_quota_cache_data()
    quotas = cache_data["quota"]
    resets_data = cache_data.get("resets", {})
    credits_data = cache_data.get("credits")
    lang = cache_data.get("language", "en")
    is_cached = True
    
    # 前回の取得時刻からの経過時間を判定
    last_fetch_str = cache_data.get("last_fetch_time", "1970-01-01T00:00:00")
    try:
        last_fetch = datetime.datetime.fromisoformat(last_fetch_str)
    except Exception:
        last_fetch = datetime.datetime(1970, 1, 1)
        
    seconds_since_last_fetch = (datetime.datetime.now() - last_fetch).total_seconds()
    
    # 15分経過しているか、あるいは--force引数が指定された場合のみ、リアルタイム取得を実行
    should_fetch = force_fetch or (seconds_since_last_fetch >= CACHE_LIFETIME_SECONDS)
    
    if should_fetch:
        res_data = get_realtime_model_quotas()
        if res_data:
            quotas = res_data.get("quota")
            resets_data = res_data.get("resets")
            credits_data = res_data.get("credits")
            is_cached = False
            # API通信が成功したため稼働状態を強制アクティブに上書き
            status["active"] = True
            status["mtime"] = datetime.datetime.now().timestamp()
            # 最新のデータをキャッシュに保存（言語設定も維持）
            save_quota_cache_data({
                "last_fetch_time": datetime.datetime.now().isoformat(),
                "quota": quotas,
                "resets": resets_data,
                "credits": credits_data,
                "language": lang
            })
            
    # Language Serverプロセスの生存状況を ps コマンドで動的に判定 (ログ非出力環境への対応)
    try:
        lsp_check = subprocess.run("ps aux | grep -i language_server | grep -v grep", shell=True, capture_output=True, text=True)
        if lsp_check.returncode == 0 and "language_server" in lsp_check.stdout:
            status["active"] = True
            status["mtime"] = datetime.datetime.now().timestamp()
        else:
            status["active"] = False
    except Exception:
        status["active"] = False
            
    if is_json:
        print(json.dumps({
            "status": status,
            "quotas": quotas,
            "resets": resets_data,
            "credits": credits_data,
            "is_cached": is_cached,
            "log_file": latest_log,
            "seconds_since_last_fetch": seconds_since_last_fetch,
            "last_fetch_time": last_fetch_str,
            "language": lang
        }, default=lambda x: x.isoformat() if isinstance(x, datetime.datetime) else str(x), indent=2, ensure_ascii=False))
    else:
        print_swiftbar_format(status, latest_log, quotas, is_cached, credits_data, resets_data, lang)

if __name__ == "__main__":
    main()
