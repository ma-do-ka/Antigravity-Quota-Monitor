#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#<swiftbar.title>Antigravity Quota Monitor</swiftbar.title>
#<swiftbar.version>1.7.0</swiftbar.version>
#<swiftbar.author>Madoka</swiftbar.author>
#<swiftbar.desc>Antigravity Quota & Credit Monitor (2-second refresh)</swiftbar.desc>
#<swiftbar.icon>👾</swiftbar.icon>
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
Antigravity Status Bar Script for macOS (SwiftBar Streamable Mode)
LSPログの0.1秒差分スキャンと、PythonによるローカルAPI直接フェッチ（メモリキャッシュ対応）を行い、
システム負荷を極限まで抑えながら超低レイテンシかつ滑らかなリアルタイム表示を実現します。
"""

import sys
import os
import time

# -- DEBUG: Redirect stderr to file --
sys.stderr = open('/tmp/agq_crash.log', 'w')
# ------------------------------------
import threading
import json
import socket
import datetime
import urllib.request
import urllib.error
import glob
import re
import warnings
import subprocess

# 警告出力を抑制 (urllib3のNotOpenSSLWarningなどをSwiftBarに流さないため)
warnings.filterwarnings("ignore")

# 設定情報
DAEMON_DIR = os.path.expanduser("~/.gemini/antigravity/daemon")
LOG_PATTERN = os.path.join(DAEMON_DIR, "ls_*.log")
ACTIVE_LOG_FILE = "/Users/user/Library/Logs/Antigravity/language_server.log"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
QUOTA_CACHE_FILE = os.path.expanduser("~/.gemini/antigravity/daemon/quota_cache.json")

SPINNER_FRAMES = ["✨️🤔", "💫🤔", "⭐🤔", "🌟😃"]
MOON_FRAMES = ["💬😑", "💬😐", "💬😊", "💬😃"]
VERSION = "1.7.0"
INDENT = "\u00A0\u00A0"  # SwiftBarでトリムされないクリーンなインデント (Non-Breaking Space)

# バージョンの動的取得 (package.jsonから自動連動)
try:
    package_json_path = os.path.join(os.path.dirname(SCRIPT_DIR), "package.json")
    if os.path.exists(package_json_path):
        with open(package_json_path, "r", encoding="utf-8") as f:
            package_data = json.load(f)
            if "version" in package_data:
                VERSION = package_data["version"]
except Exception:
    pass

# ユーザーの「Model Quota」ダッシュボード画面から読み取ったデフォルト初期クォータ値
DEFAULT_QUOTAS = {
    "F-Med": 100,
    "F-High": 100,
    "F-Low": 100,
    "P-Low": 100,
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
        "state_thinking": "Thinking",
        "state_pending": "Pending!",
        "state_input_req": "InputReq",
        "state_idle": "Idle",
        "state_offline": "Offline",
        "state_header": "Agent State: {state}",
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
        "about_version": f"Antigravity Quota Monitor: v{VERSION}",
        "about_website": "Website: https://note.com/us_kabu_journal/n/nb99ef3e525ce",
        "about_copyright": "Copyright © 2026 US stock journal. All rights reserved."
    },
    "ja": {
        "title_stopped": "停止中",
        "title_exhausted": "クォータ枯渇",
        "title_limit": "トークン制限",
        "title_load": "高負荷 ({req}req)",
        "title_active": "稼働中",
        "header": "🤖 Antigravity エージェント状態",
        "state_thinking": "思考中",
        "state_pending": "承認待ち",
        "state_input_req": "入力要求",
        "state_idle": "待機中",
        "state_offline": "停止中",
        "state_header": "エージェント状態: {state}",
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
        "about_version": f"Antigravity Quota Monitor: v{VERSION}",
        "about_website": "Website: https://note.com/us_kabu_journal/n/nb99ef3e525ce",
        "about_copyright": "Copyright © 2026 US stock journal. All rights reserved."
    }
}


def get_latest_log_file():
    """最新のログファイルを特定します。"""
    if os.path.exists(ACTIVE_LOG_FILE):
        return ACTIVE_LOG_FILE
        
    files = glob.glob(LOG_PATTERN)
    ide_logs = glob.glob(os.path.expanduser("~/.gemini/antigravity-ide/daemon/ls_*.log"))
    if ide_logs:
        files.extend(ide_logs)
        
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


def get_stateless_log_status(log_path=None):
    if not log_path:
        log_path = get_latest_log_file()
    status = {
        "is_thinking": False,
        "quota_exhausted": False,
        "last_error_time": None,
        "requests_last_10m": 0,
        "token_limit_exceeded": 0,
        "last_log_time": None,
        "mtime": 0
    }
    if not log_path or not os.path.exists(log_path):
        return status
        
    try:
        file_size = os.path.getsize(log_path)
        chunk_size = 64 * 1024 # 64KB
        
        with open(log_path, 'rb') as f:
            if file_size > chunk_size:
                f.seek(file_size - chunk_size)
            data = f.read().decode('utf-8', errors='ignore')
            
        lines = data.split('\n')
        now = datetime.datetime.now()
        
        import re
        log_re = re.compile(r"^([IWEF])(\d{4}) (\d{2}:\d{2}:\d{2})\.(\d{6})")
        req_count = 0
        
        file_mtime = os.path.getmtime(log_path)
        file_year = datetime.datetime.fromtimestamp(file_mtime).year
        status["mtime"] = file_mtime
        
        for line in lines:
            match = log_re.match(line)
            if not match:
                continue
            month_day, time_str = match.group(2), match.group(3)
            try:
                month, day = int(month_day[:2]), int(month_day[2:])
                hour, minute, second = map(int, time_str.split(':'))
                log_dt = datetime.datetime(file_year, month, day, hour, minute, second)
                if log_dt > now + datetime.timedelta(days=1):
                    log_dt = log_dt.replace(year=file_year - 1)
            except:
                continue
                
            status["last_log_time"] = log_dt
            
            is_request = "v1internal:streamGenerateContent" in line or "streamGenerateContent" in line
            if is_request:
                if (now - log_dt).total_seconds() <= 600:
                    req_count += 1
                if (now - log_dt).total_seconds() <= 20: # 20 seconds timeout for thinking
                    status["is_thinking"] = True
                    status["last_request_time"] = log_dt.timestamp()
                    
            if "generation exceeded max tokens limit" in line:
                if (now - log_dt).total_seconds() <= 1800:
                    status["token_limit_exceeded"] += 1
                    
            if "Resource has been exhausted" in line or "check quota" in line:
                if (now - log_dt).total_seconds() <= 300:
                    status["last_error_time"] = log_dt
                    status["quota_exhausted"] = True
                    
        status["requests_last_10m"] = req_count
        
        # 全てのconversation (transcript.jsonl) の最新1MBをスキャンし、バックグラウンドタスクが実行中か確認する
        has_active_tasks = False
        try:
            brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
            latest_t_mtime = 0
            
            if os.path.exists(brain_dir):
                import json, re
                for d in os.listdir(brain_dir):
                    t_path = os.path.join(brain_dir, d, ".system_generated", "logs", "transcript.jsonl")
                    if os.path.exists(t_path):
                        mtime = os.path.getmtime(t_path)
                        if mtime > latest_t_mtime:
                            latest_t_mtime = mtime
                            
                        # パフォーマンス対策: 過去7日間に動いたチャットのみパースする (重くならないための工夫)
                        import time
                        if mtime < time.time() - 604800:
                            continue
                            
                        # アクティブなタスクがあるかチェック
                        try:
                            with open(t_path, 'rb') as f:
                                f.seek(0, 2)
                                size = f.tell()
                                f.seek(max(0, size - 1000000))
                                data = f.read().decode('utf-8', errors='ignore')
                                
                                active_tasks = set()
                                for line in data.split('\n')[1:]:
                                    if not line.strip(): continue
                                    try:
                                        obj = json.loads(line)
                                        if obj.get('type') == 'RUN_COMMAND' and obj.get('status') == 'RUNNING':
                                            content = obj.get('content', '')
                                            m = re.search(r'task id: ([\w\-]+(?:/task-\d+)?)', content)
                                            if m: active_tasks.add(m.group(1))
                                        elif obj.get('type') == 'SYSTEM_MESSAGE':
                                            content = obj.get('content', '')
                                            if 'finished with result' in content or 'was canceled with result' in content:
                                                m = re.search(r'Task id \"([\w\-]+(?:/task-\d+)?)\" (?:finished|was canceled) with result', content)
                                                if m and m.group(1) in active_tasks:
                                                    active_tasks.remove(m.group(1))
                                    except: pass
                                
                                if len(active_tasks) > 0:
                                    has_active_tasks = True
                        except: pass

            # 全てのタスクがなく、かつ返信完了（LLM思考完了）ならThinkingを直ちに解除
            if status.get("is_thinking") and status.get("last_request_time"):
                if latest_t_mtime > status["last_request_time"] and not has_active_tasks:
                    status["is_thinking"] = False
                    
            # タスクがあるならThinkingにする
            if has_active_tasks:
                status["is_thinking"] = True

        except Exception:
            pass
                
        return status
    except Exception as e:
        with open("/tmp/agq_error.log", "a") as f:
            f.write(f"Stateless parser error: {e}\n")
        return status

def check_pending_approval():
    """最新の会話フォルダから承認待ち (requestFeedback や ask_question) があるか、transcript.jsonl の最新ログをチェックします。"""
    try:
        brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
        if not os.path.exists(brain_dir):
            return False
            
        folders = [os.path.join(brain_dir, d) for d in os.listdir(brain_dir) if os.path.isdir(os.path.join(brain_dir, d))]
        if not folders:
            return False
            
        latest_folder = max(folders, key=os.path.getmtime)
        transcript_path = os.path.join(latest_folder, ".system_generated", "logs", "transcript.jsonl")
        
        if os.path.exists(transcript_path):
            # 後ろから少しだけ読むための簡易最適化
            with open(transcript_path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                read_size = min(size, 200000)
                f.seek(size - read_size)
                lines = f.read().decode('utf-8', errors='ignore').splitlines()
                
            for line in reversed(lines):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    # ユーザーの入力があれば、承認待ちは解除されている
                    if data.get("type") == "USER_INPUT":
                        return False
                    
                    # AIのツールコールをチェック
                    if data.get("source") == "MODEL" and "tool_calls" in data:
                        for tc in data["tool_calls"]:
                            if tc.get("name") == "ask_question":
                                return True
                            
                            args = tc.get("args")
                            if isinstance(args, dict):
                                meta = args.get("ArtifactMetadata")
                                if isinstance(meta, dict) and meta.get("RequestFeedback") is True:
                                    return True
                except Exception:
                    pass
    except Exception:
        pass
    return False


def detect_agent_state(status, pending_flag=None):
    """LSPプロセス状態、ログ、会話フォルダからエージェントの状態を特定します。"""
    if not status.get("active", False):
        return "offline"
        
    # パフォーマンスのために毎ループのフォルダ走査を最適化（フラグ経由など）
    is_pending = pending_flag if pending_flag is not None else check_pending_approval()
    if is_pending:
        return "pending"
        
    if status.get("is_thinking", False):
        return "thinking"
        
    return "idle"


# LSP接続情報のメモリキャッシュ
_lsp_info_cache = None

def find_lsp_info(force=False):
    """
    実行中の language_server をすべて検索し、それぞれの CSRF トークンとポート番号のリストを返します。
    ターミナル幅によるパス切り捨てを防ぐため ps -eo を使用し、堅牢にプロセスを特定します。
    """
    global _lsp_info_cache
    if not force and _lsp_info_cache:
        return _lsp_info_cache
        
    try:
        ps_result = subprocess.run(
            "/bin/ps -eo pid,command | grep -i language_server | grep -v grep",
            shell=True, capture_output=True, text=True
        )
        if ps_result.returncode != 0 or not ps_result.stdout.strip():
            return []
            
        lines = ps_result.stdout.strip().split("\n")
        servers = []
        
        for line in lines:
            if "--csrf_token" in line:
                parts = line.split(maxsplit=1)
                if len(parts) < 2:
                    continue
                pid = int(parts[0].strip())
                cmd = parts[1]
                
                csrf_match = re.search(r"--csrf_token\s+([a-fA-F0-9-]+)", cmd)
                if not csrf_match:
                    continue
                csrf_token = csrf_match.group(1)
                
                lsof_result = subprocess.run(
                    f"/usr/sbin/lsof -a -p {pid} -i -P -n | grep LISTEN",
                    shell=True, capture_output=True, text=True, timeout=3
                )
                
                ports = []
                if lsof_result.returncode == 0:
                    lsof_lines = lsof_result.stdout.strip().split("\n")
                    for l in lsof_lines:
                        port_match = re.search(r":(\d+)\s+\(LISTEN\)", l)
                        if port_match:
                            ports.append(int(port_match.group(1)))
                
                if ports:
                    servers.append({"pid": pid, "csrf_token": csrf_token, "ports": ports})
                    
        return servers
    except Exception as e:
        with open("/tmp/agq_error.log", "a") as f:
            f.write(f"find_lsp_info ERROR: {e}\n")
    return []


def fetch_quota_from_api(port, csrf_token):
    """ローカルAPIからユーザー状態（クォータ・クレジット含む）を直接フェッチします（Node.js完全不要）。"""
    url = f"http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetUserStatus"
    body_data = json.dumps({
        "metadata": {
            "ideName": "antigravity",
            "extensionName": "antigravity",
            "locale": "en"
        }
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=body_data,
        headers={
            "Content-Type": "application/json",
            "Connect-Protocol-Version": "1",
            "X-Codeium-Csrf-Token": csrf_token
        },
        method="POST"
    )
    
    label_to_key = {
        "Gemini 3.5 Flash (Medium)": "F-Med",
        "Gemini 3.5 Flash (High)": "F-High",
        "Gemini 3.5 Flash (Low)": "F-Low",
        "Gemini 3.1 Pro (Low)": "P-Low",
        "Gemini 3.1 Pro (High)": "P-High",
        "Claude Sonnet 4.6 (Thinking)": "Sonnet",
        "Claude Opus 4.6 (Thinking)": "Opus",
        "GPT-OSS 120B (Medium)": "GPT-120"
    }
    
    try:
        # プロキシ環境変数を無視するハンドラを設定 (SwiftBar環境下での接続エラー防止)
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        with opener.open(req, timeout=3.0) as response:
            if response.status == 200:
                res_body = response.read().decode("utf-8")
                data = json.loads(res_body)
                
                if not (data and "userStatus" in data):
                    return None
                    
                user_status = data["userStatus"]
                quota_data = {}
                resets_data = {}
                
                model_config = user_status.get("cascadeModelConfigData", {})
                client_configs = model_config.get("clientModelConfigs", [])
                
                for m in client_configs:
                    label = m.get("label")
                    key = label_to_key.get(label)
                    if key:
                        quota_info = m.get("quotaInfo")
                        if quota_info:
                            rem_frac = quota_info.get("remainingFraction")
                            if rem_frac is not None:
                                quota_data[key] = round(rem_frac * 100)
                            else:
                                quota_data[key] = 0
                            
                            reset_time = quota_info.get("resetTime")
                            if reset_time:
                                resets_data[key] = reset_time
                        else:
                            quota_data[key] = 100
                            
                credits_data = {
                    "availablePrompt": 0,
                    "monthlyPrompt": 0,
                    "availableFlow": 0,
                    "monthlyFlow": 0,
                    "googleOneAi": "0"
                }
                
                plan_status = user_status.get("planStatus", {})
                if plan_status:
                    credits_data["availablePrompt"] = plan_status.get("availablePromptCredits", 0)
                    credits_data["availableFlow"] = plan_status.get("availableFlowCredits", 0)
                    
                    plan_info = plan_status.get("planInfo", {})
                    if plan_info:
                        credits_data["monthlyPrompt"] = plan_info.get("monthlyPromptCredits", 0)
                        credits_data["monthlyFlow"] = plan_info.get("monthlyFlowCredits", 0)
                        
                user_tier = user_status.get("userTier", {})
                avail_credits = user_tier.get("availableCredits", [])
                if avail_credits and len(avail_credits) > 0:
                    credits_data["googleOneAi"] = avail_credits[0].get("creditAmount", "0")
                    
                return {
                    "quota": quota_data,
                    "resets": resets_data,
                    "credits": credits_data
                }
    except Exception as e:
        with open("/tmp/agq_error.log", "a") as f:
            f.write(f"fetch_quota_from_api ERROR (port {port}): {e}\n")
    return None


def load_quota_cache_data():
    """キャッシュファイルからデータを読み込みます。"""
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
    """データをキャッシュファイルに保存します。"""
    try:
        os.makedirs(os.path.dirname(QUOTA_CACHE_FILE), exist_ok=True)
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
    """パーセンテージに応じた色付き球体絵文字を返します。"""
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
    """パーセンテージに応じたカラーコードを返します。"""
    if percentage >= 100:
        return "#a855f7"
    elif percentage >= 80:
        return "#007aff"
    elif percentage >= 60:
        return "#34c759"
    elif percentage >= 40:
        return "#ffcc00"
    elif percentage >= 20:
        return "#ff9500"
    else:
        return "#ff3b30"


def format_reset_time(iso_str, lang="en"):
    """UTCのISO 8601形式の文字列を、ローカル（日本時間）の分かりやすい表記に変換します。"""
    if not iso_str:
        return "—"
    try:
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1] + '+00:00'
        dt_utc = datetime.datetime.fromisoformat(iso_str)
        dt_local = dt_utc.astimezone()
        now = datetime.datetime.now().astimezone()
        
        if dt_local.date() == now.date():
            return f"⟳ {dt_local.strftime('%H:%M')}"
        else:
            return f"⟳ {dt_local.strftime('%m/%d %H:%M')}"
    except Exception:
        return "—"


def build_swiftbar_output(status, quotas, is_cached, credits_data, resets_data, lang, state, frame_count):
    """SwiftBar 用の標準出力を文字列として生成します。"""
    now = datetime.datetime.now()
    msg = MESSAGES[lang]
    
    prefix = "👾 "
    color_opt = ""
    
    if state == "offline":
        prefix = "⚪️"
    elif state == "pending":
        prefix = MOON_FRAMES[frame_count % len(MOON_FRAMES)]
    elif state == "thinking":
        prefix = SPINNER_FRAMES[frame_count % len(SPINNER_FRAMES)]
    else:
        prefix = "👾"

    delimiter = " ❘ "

    model_texts = []
    if quotas:
        def get_short_name(k):
            mapping = {
                "F-Med": "GF-M",
                "F-High": "GF-H",
                "F-Low": "GF-L",
                "P-Low": "GP-L",
                "P-High": "GP-H",
                "Sonnet": "Sonnet",
                "Opus": "Opus",
                "GPT-120": "GPT",
                "GPT": "GPT"
            }
            return mapping.get(k, k.split()[0][:6])

        unique_models = {}
        for key, val in quotas.items():
            display_name = get_short_name(key)
            if display_name not in unique_models or val < unique_models[display_name]:
                unique_models[display_name] = val
                
        # Preferred order
        order = {"GF-M": 1, "GF-H": 2, "GF-L": 3, "GP-L": 4, "GP-H": 5, "Sonnet": 6, "Opus": 7, "GPT": 8}
        sorted_models = sorted(unique_models.items(), key=lambda x: (order.get(x[0], 99), x[0]))
        
        for m_name, m_val in sorted_models:
            emoji = get_quota_emoji(m_val)
            model_texts.append(f"{m_name}:{emoji}")
            
    custom_delimiter = " "
    repr_str = custom_delimiter.join(model_texts)
    
    if not repr_str:
        if status["quota_exhausted"]:
            repr_str = f"AGQ: 🔴 {msg['title_exhausted']}"
        elif status["token_limit_exceeded"] > 0:
            repr_str = f"AGQ: ⚠️ {msg['title_limit']}"
        elif status["requests_last_10m"] > 10:
            repr_str = f"AGQ: 🟡 {msg['title_load'].format(req=status['requests_last_10m'])}"
        else:
            repr_str = f"AGQ: 🟢 {msg['title_active']}"

    # Remove trailing/leading space from prefix for cleaner attachment if needed
    pfx = prefix.strip()
    title = f"{pfx} {repr_str}{color_opt}"
        
    lines = [title, "---"]
    lines.append(f"{msg['header']} | font=sans-serif size=13 ")
    
    # エージェント現在の状態
    state_labels = {
        "thinking": f"🧠 {msg['state_thinking']}",
        "pending": f"⚠️ {msg['state_pending']}",
        "idle": f"✨ {msg['state_idle']}",
        "offline": f"⚪️ {msg['state_offline']}"
    }
    current_state_label = state_labels.get(state, f"✨ {msg['state_idle']}")
    state_colors = {
        "thinking": "#a855f7",
        "pending": "#ffcc00",
        "idle": "#34c759",
        "offline": "#8e8e93"
    }
    state_color = state_colors.get(state, "#34c759")
    lines.append(f"{INDENT}{msg['state_header'].format(state=current_state_label)} | color={state_color} font=sans-serif size=12")
    
    # Language Server の状態
    if status["active"]:
        elapsed = int((now - datetime.datetime.fromtimestamp(status["mtime"])).total_seconds())
        lines.append(f"{INDENT}{msg['ls_running'].format(elapsed=elapsed)} | color=#34c759 font=sans-serif size=12")
    else:
        lines.append(f"{INDENT}{msg['ls_stopped']} | color=#8e8e93 font=sans-serif size=12")
        
    # クォータ（API制限）の状態
    if status["quota_exhausted"]:
        lines.append(f"{INDENT}{msg['api_exhausted']} | color=#ff3b30 font=sans-serif size=12")
    elif status["last_error_time"]:
        err_elapsed = int((now - status["last_error_time"]).total_seconds())
        if err_elapsed < 1800:
            lines.append(f"{INDENT}{msg['api_recovering'].format(elapsed=int(err_elapsed/60))} | color=#ffcc00 font=sans-serif size=12")
        else:
            lines.append(f"{INDENT}{msg['api_normal']} | color=#34c759 font=sans-serif size=12")
    else:
        lines.append(f"{INDENT}{msg['api_normal']} | color=#34c759 font=sans-serif size=12")
        
    # モデル別クォータ詳細表示
    if quotas:
        lines.append("---")
        cache_status = msg["cached"] if is_cached else msg["realtime"]
        lines.append(f"{msg['model_header']}{cache_status} | font=sans-serif size=12 ")
        ordered_keys = ["F-Med", "F-High", "F-Low", "P-Low", "P-High", "Sonnet", "Opus", "GPT-120"]
        full_names = {
            "P-High": "Gemini 3.1 Pro (High)",
            "Sonnet": "Claude Sonnet 4.6 (Thinking)",
            "Opus": "Claude Opus 4.6 (Thinking)",
            "GPT-120": "GPT-OSS 120B (Medium)",
            "F-Med": "Gemini 3.5 Flash (Medium)",
            "F-High": "Gemini 3.5 Flash (High)",
            "F-Low": "Gemini 3.5 Flash (Low)",
            "P-Low": "Gemini 3.1 Pro (Low)"
        }
        for key in ordered_keys:
            if key in quotas:
                val = quotas[key]
                name = full_names[key]
                sphere = get_quota_sphere_emoji(val)
                color = get_quota_color(val)
                
                reset_text = "—".rjust(14)
                if resets_data and key in resets_data:
                    try:
                        reset_time = datetime.datetime.fromisoformat(resets_data[key].replace('Z', '+00:00'))
                        local_reset = reset_time.astimezone()
                        reset_text = f"↻ {local_reset.strftime('%m/%d %H:%M')}".rjust(14)
                    except Exception:
                        pass
                
                name_padded = name.ljust(35)
                val_padded = f"{val}%".rjust(4)
                
                lines.append(f"{INDENT}{sphere} {name_padded} {val_padded}   {reset_text} | font=Menlo size=12 color={color}")
        
    if credits_data:
        lines.append("---")
        lines.append(f"{msg['credit_header']} | font=sans-serif size=12 ")
        
        avail_p = credits_data.get("availablePrompt")
        month_p = credits_data.get("monthlyPrompt")
        if avail_p is not None and month_p:
            remaining_p = max(0, month_p - avail_p)
            pct = (remaining_p / month_p) * 100 if month_p > 0 else 0
            color = "#34c759" if pct >= 80 else ("#ffcc00" if pct >= 30 else "#ff3b30")
            lines.append(f"{INDENT}{msg['prompt_limit']}: {remaining_p:,} / {month_p:,} ({pct:.1f}%) | font=monospace size=12 color={color}")
        
        avail_f = credits_data.get("availableFlow")
        month_f = credits_data.get("monthlyFlow")
        if avail_f is not None and month_f:
            remaining_f = max(0, month_f - avail_f)
            pct = (remaining_f / month_f) * 100 if month_f > 0 else 0
            color = "#34c759" if pct >= 80 else ("#ffcc00" if pct >= 30 else "#ff3b30")
            lines.append(f"{INDENT}{msg['flow_credit']}: {remaining_f:,} / {month_f:,} ({pct:.1f}%) | font=monospace size=12 color={color}")
            
        g1_cred = credits_data.get("googleOneAi")
        if g1_cred is not None:
            lines.append(f"{INDENT}{msg['google_one']}: {g1_cred} | font=monospace size=12 color=#34c759")
            
    # 言語選択UI
    lines.append("---")
    script_path = os.path.realpath(__file__)
    lines.append(f"{msg['lang_header']} | font=sans-serif size=12 ")
    check_en = " [✓]" if lang == "en" else ""
    check_ja = " [✓]" if lang == "ja" else ""
    lines.append(f"{INDENT}🇺🇸 English{check_en} | terminal=false refresh=true bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--set-lang\" param3=\"en\"")
    lines.append(f"{INDENT}🇯🇵 日本語{check_ja} | terminal=false refresh=true bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--set-lang\" param3=\"ja\"")
    
    # About セクション
    lines.append("---")
    lines.append(f"{msg['about_header']} | font=sans-serif size=12 ")
    lines.append(f"{INDENT}{msg['about_version']} | font=monospace size=11 color=#8e8e93")
    lines.append(f"{INDENT}{msg['about_website']} | font=monospace size=11 href=https://note.com/us_kabu_journal/n/nb99ef3e525ce color=#007aff")
    lines.append(f"{INDENT}{msg['about_copyright']} | font=monospace size=11 color=#8e8e93")

    # 再読み込みボタン
    lines.append("---")
    lines.append(f"{msg['refresh']} | refresh=true font=sans-serif terminal=false bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--force\"")
    
    return "\n".join(lines)



def do_bg_fetch():
    try:
        servers = find_lsp_info(force=True)
        if not servers:
            return
        
        for srv in servers:
            success = False
            for port in srv["ports"]:
                data = fetch_quota_from_api(port, srv["csrf_token"])
                if data:
                    cache_data = load_quota_cache_data()
                    lang = cache_data.get("language", "en")
                    save_quota_cache_data({
                        "last_fetch_time": datetime.datetime.now().isoformat(),
                        "quota": data.get("quota"),
                        "resets": data.get("resets"),
                        "credits": data.get("credits"),
                        "language": lang
                    })
                    success = True
                    break
            if success:
                break
    except Exception as e:
        with open("/tmp/agq_error.log", "a") as f:
            f.write(f"BG fetch error: {e}\n")

def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--set-lang":
        new_lang = sys.argv[2]
        cache_data = load_quota_cache_data()
        cache_data["language"] = new_lang
        save_quota_cache_data(cache_data)
        print("Language updated to " + new_lang)
        sys.exit(0)
        
    if len(sys.argv) == 2 and sys.argv[1] == "--fetch-bg":
        do_bg_fetch()
        sys.exit(0)

    loop_start = time.time()
    
    cache_data = load_quota_cache_data()
    lang = cache_data.get("language", "en")
    if lang not in MESSAGES:
        lang = "en"
        
    quotas = cache_data.get("quota", DEFAULT_QUOTAS)
    resets_data = cache_data.get("resets", {})
    credits_data = cache_data.get("credits", {})
    
    log_status = get_stateless_log_status()
    is_pending = check_pending_approval()

    # Fast check for active LSP via cache or quick ps
    global _lsp_info_cache
    lsp_info = find_lsp_info()
    is_active = False
    
    if lsp_info and len(lsp_info) > 0:
        is_active = True
        _lsp_info_cache = lsp_info
        try:
            os.kill(lsp_info[0]["pid"], 0)
        except OSError:
            is_active = False
            _lsp_info_cache = None

    status = {
        "active": is_active,
        "quota_exhausted": log_status.get("quota_exhausted", False),
        "last_error_time": log_status.get("last_error_time"),
        "requests_last_10m": log_status.get("requests_last_10m", 0),
        "token_limit_exceeded": log_status.get("token_limit_exceeded", 0),
        "last_log_time": log_status.get("last_log_time"),
        "mtime": log_status.get("mtime", loop_start),
        "is_thinking": log_status.get("is_thinking", False)
    }
    
    state = detect_agent_state(status, pending_flag=is_pending)

    # 1 FPS Stateless Animation
    now_sec = datetime.datetime.now().second
    frame_count = now_sec

    # Check if we need to spawn background fetch
    last_fetch_str = cache_data.get("last_fetch_time", "1970-01-01T00:00:00")
    try:
        last_fetch = datetime.datetime.fromisoformat(last_fetch_str).timestamp()
    except:
        last_fetch = 0
        
    interval = 5 if state in ["thinking", "pending"] else 15
    
    # 最後のフェッチから interval + 5秒 以内であればリアルタイム同期中と判定する
    is_cached = (time.time() - last_fetch) > (interval + 5)
    
    if is_active and (time.time() - last_fetch > interval):
        # Update cache time to prevent multiple spawns
        cache_data["last_fetch_time"] = datetime.datetime.now().isoformat()
        save_quota_cache_data(cache_data)
        
        # Spawn background fetch
        subprocess.Popen(["/usr/bin/python3", os.path.realpath(__file__), "--fetch-bg"], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    output = build_swiftbar_output(
        status, quotas, is_cached, credits_data, resets_data, lang, state, frame_count
    )
    
    print(output)
    
if __name__ == "__main__":
    main()
