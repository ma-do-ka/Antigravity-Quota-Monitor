#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#<swiftbar.title>Antigravity Quota Monitor</swiftbar.title>
#<swiftbar.version>2.6.1</swiftbar.version>
#<swiftbar.author>Madoka</swiftbar.author>
#<swiftbar.desc>Antigravity Quota & Credit Monitor (10-second refresh)</swiftbar.desc>
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

# -- DEBUG: Redirect stderr to user-specific daemon directory --
DAEMON_DIR = os.path.expanduser("~/.gemini/antigravity/daemon")
try:
    os.makedirs(DAEMON_DIR, exist_ok=True)
    sys.stderr = open(os.path.join(DAEMON_DIR, "agq_crash.log"), "w")
except:
    pass
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

# Pillow (PIL) の動的画像生成用インポート試行
try:
    from PIL import Image, ImageDraw, ImageFont
    import io
    import base64
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# 警告出力を抑制 (urllib3のNotOpenSSLWarningなどをSwiftBarに流さないため)
warnings.filterwarnings("ignore")

# 設定情報
DAEMON_DIR = os.path.expanduser("~/.gemini/antigravity/daemon")
LOG_PATTERN = os.path.join(DAEMON_DIR, "ls_*.log")
ACTIVE_LOG_FILE = os.path.expanduser("~/Library/Logs/Antigravity/language_server.log")
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
QUOTA_CACHE_FILE = os.path.expanduser("~/.gemini/antigravity/daemon/quota_cache.json")

# 1 FPS Stateless Animation
# メニューバーのアニメーション用フレーム (10秒周期更新なので、インデックスの切り替え用)
SPINNER_FRAMES = ["✨️🤔", "💫🤔", "⭐🤔", "🌟😃"]
MOON_FRAMES = ["💬😑", "💬😐", "💬😊", "💬😃"]
VERSION = "2.6.0"
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

def write_error_log(msg):
    """エラーログを書き込みます。サイズが100KBを超えた場合は切り詰めてローテーションします。"""
    log_file = os.path.join(DAEMON_DIR, "agq_error.log")
    try:
        if os.path.exists(log_file) and os.path.getsize(log_file) > 100 * 1024:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"--- Log rotated at {datetime.datetime.now()} ---\n")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")
    except:
        pass


# ユーザーの「Model Quota」ダッシュボード画面から読み取ったデフォルト初期クォータ値
DEFAULT_QUOTAS = {
    "Gemini": 100,
    "Claude_GPT": 100
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
        
        # 最新の数件の conversation (transcript.jsonl) のみをスキャンし、バックグラウンドタスクが実行中か確認する
        has_active_tasks = False
        try:
            brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
            latest_t_mtime = 0
            
            if os.path.exists(brain_dir):
                import json, re, time
                # 1. すべての会話ディレクトリを取得して、更新日時でソートし、最新の5件に絞る (ディスクI/O負荷を激減させる)
                subdirs = []
                with os.scandir(brain_dir) as it:
                    for entry in it:
                        if entry.is_dir():
                            try:
                                subdirs.append((entry.path, entry.stat().st_mtime))
                            except OSError:
                                pass
                
                subdirs.sort(key=lambda x: x[1], reverse=True)
                active_subdirs = [x[0] for x in subdirs[:5]]
                
                for d_path in active_subdirs:
                    t_path = os.path.join(d_path, ".system_generated", "logs", "transcript.jsonl")
                    if os.path.exists(t_path):
                        mtime = os.path.getmtime(t_path)
                        if mtime > latest_t_mtime:
                            latest_t_mtime = mtime
                            
                        # パフォーマンス対策: 過去1時間以内に動いたチャットのみパースする (重くならないための工夫)
                        if mtime < time.time() - 3600:
                            continue
                            
                        # スタック防止: 最終更新から15分(900秒)以上経過しているタスクはゾンビと見なして無視する
                        if time.time() - mtime > 900:
                            continue
                            
                        # アクティブなタスクがあるかチェック
                        try:
                            with open(t_path, 'rb') as f:
                                f.seek(0, 2)
                                size = f.tell()
                                # パフォーマンス対策: 読み込みバッファを1MBから50KBに縮小しJSONパース負荷を下げる
                                f.seek(max(0, size - 50000))
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
                                    
                                # 2. 最新ログの状態とmtimeによる「Working」の動的検知
                                # 会話ログが直近 120 秒以内に更新されている場合
                                if time.time() - mtime <= 120:
                                    lines = [l for l in data.split('\n') if l.strip()]
                                    if lines:
                                        last_line = lines[-1]
                                        try:
                                            last_obj = json.loads(last_line)
                                            last_type = last_obj.get("type")
                                            last_source = last_obj.get("source")
                                            
                                            # 最後の行がモデルの応答であり、かつ tool_calls を含まない場合は「返答完了」とみなす
                                            is_final_reply = False
                                            if last_source == "MODEL" and last_type == "PLANNER_RESPONSE":
                                                t_calls = last_obj.get("tool_calls")
                                                if not t_calls or len(t_calls) == 0:
                                                    is_final_reply = True
                                                    
                                            # 最終返答を返していない（＝まだ自律動作が続いている）場合は、タスク実行中とみなす
                                            if not is_final_reply:
                                                has_active_tasks = True
                                        except:
                                            pass
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
        write_error_log(f"Stateless parser error: {e}")
        return status

def check_pending_approval():
    """最新の会話フォルダ群から承認待ち (requestFeedback や run_command 等) があるか、transcript.jsonl の最新ログをチェックします。"""
    try:
        brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
        if not os.path.exists(brain_dir):
            return False
            
        folders = []
        with os.scandir(brain_dir) as it:
            for entry in it:
                if entry.is_dir():
                    try:
                        folders.append((entry.path, entry.stat().st_mtime))
                    except OSError:
                        pass
        if not folders:
            return False
            
        # 最新の5つのフォルダに絞って走査する (I/O負荷軽減と複数セッション監視の並立)
        folders.sort(key=lambda x: x[1], reverse=True)
        active_folders = [x[0] for x in folders[:5]]
        
        # 承認が必要なツールとそれに対応する実行結果のログ type の対応マップ
        REQUIRED_APPROVAL_TOOLS = {
            "run_command": "RUN_COMMAND",
            "write_to_file": "WRITE_FILE",
            "replace_file_content": "REPLACE_FILE_CONTENT",
            "multi_replace_file_content": "MULTI_REPLACE_FILE_CONTENT",
            "ask_permission": "ASK_PERMISSION",
            "generate_image": "GENERATE_IMAGE",
            "ask_question": "ASK_QUESTION"
        }
        
        for folder_path in active_folders:
            transcript_path = os.path.join(folder_path, ".system_generated", "logs", "transcript.jsonl")
            if not os.path.exists(transcript_path):
                continue
                
            try:
                with open(transcript_path, "rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    # 読み込みサイズを200KBに制限してパフォーマンス確保
                    read_size = min(size, 200000)
                    f.seek(size - read_size)
                    lines = f.read().decode('utf-8', errors='ignore').splitlines()
                
                executed_types = set()
                
                for line in reversed(lines):
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        # ユーザーの入力があれば、このセッションは承認待ちは解除されているため次のフォルダへ
                        if data.get("type") == "USER_INPUT":
                            break
                        
                        line_type = data.get("type")
                        if line_type in REQUIRED_APPROVAL_TOOLS.values():
                            status_val = data.get("status")
                            if status_val in ("BLOCKED", "PENDING", "WAITING"):
                                return True
                            else:
                                executed_types.add(line_type)
                        # "CODE_ACTION" が検出された場合、ファイル編集系は実行済みとしてマーク
                        if line_type == "CODE_ACTION":
                            executed_types.add("WRITE_FILE")
                            executed_types.add("REPLACE_FILE_CONTENT")
                            executed_types.add("MULTI_REPLACE_FILE_CONTENT")
                        
                        # AIのツールコールをチェック
                        if data.get("source") == "MODEL" and data.get("type") == "PLANNER_RESPONSE":
                            tool_calls = data.get("tool_calls")
                            if isinstance(tool_calls, list):
                                for tc in tool_calls:
                                    name = tc.get("name")
                                    
                                    # 承認が必要なツールであり、かつ逆順でまだ実行された形跡がない場合
                                    if name in REQUIRED_APPROVAL_TOOLS:
                                        target_type = REQUIRED_APPROVAL_TOOLS[name]
                                        if target_type not in executed_types:
                                            return True
                                            
                                    # ArtifactのRequestFeedbackのチェックも残す
                                    args = tc.get("args")
                                    if isinstance(args, dict):
                                        meta = args.get("ArtifactMetadata")
                                        if isinstance(meta, dict) and meta.get("RequestFeedback") is True:
                                            return True
                            
                            # 最新のPLANNER_RESPONSEに到達し、承認待ちが無いと判断されたらこのフォルダの探索終了
                            break
                    except Exception:
                        pass
            except Exception:
                pass
            
    except Exception:
        pass
    return False


def detect_agent_state(status, pending_flag=None):
    """LSPプロセス状態、ログ、会話フォルダからエージェントの状態を特定します。"""
    # 承認待ち、または思考中(タスク実行中)の場合は、LSPがアクティブでなくても稼働中と判定する
    is_pending = pending_flag if pending_flag is not None else check_pending_approval()
    if is_pending:
        return "pending"
        
    if status.get("is_thinking", False):
        return "thinking"
        
    if not status.get("active", False):
        return "offline"
        
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
        write_error_log(f"find_lsp_info ERROR: {e}")
    return []


def fetch_quota_from_api(port, csrf_token):
    """ローカルAPI(Language Server)からクォータ情報を取得します。"""
    # 完全に環境変数のプロキシを無効化する
    import os
    for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
        if k in os.environ:
            del os.environ[k]
    os.environ['no_proxy'] = '*'

    # 127.0.0.1 で Errno 8 が出ることがあるため localhost に変更
    url = f"http://localhost:{port}/exa.language_server_pb.LanguageServerService/GetUserStatus"
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
    
    try:
        # プロキシ環境変数を無視するハンドラを設定 (SwiftBar環境下での接続エラー防止)
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        with opener.open(req, timeout=3.0) as response:
            res_body = response.read().decode('utf-8')
            
            # --- DEBUG DUMP ---
            try:
                import os
                dump_path = os.path.expanduser("~/.gemini/antigravity/daemon/api_dump.json")
                with open(dump_path, "w") as f:
                    f.write(res_body)
            except:
                pass
            # ------------------

            if response.status == 200:
                data = json.loads(res_body)
                
                if not (data and "userStatus" in data):
                    return None
                    
                user_status = data["userStatus"]
                quota_data = {"Gemini": 100, "Claude_GPT": 100}
                resets_data = {"Gemini": None, "Claude_GPT": None}
                
                model_config = user_status.get("cascadeModelConfigData", {})
                client_configs = model_config.get("clientModelConfigs", [])
                
                for m in client_configs:
                    label = m.get("label", "")
                    
                    if "Gemini" in label:
                        group_key = "Gemini"
                    elif "Claude" in label or "GPT" in label:
                        group_key = "Claude_GPT"
                    else:
                        continue
                    
                    quota_info = m.get("quotaInfo")
                    if quota_info:
                        rem_frac = quota_info.get("remainingFraction")
                        pct = round(rem_frac * 100) if rem_frac is not None else 0
                        reset_time = quota_info.get("resetTime")
                        
                        if pct < quota_data[group_key] or resets_data[group_key] is None:
                            quota_data[group_key] = pct
                            if reset_time:
                                resets_data[group_key] = reset_time
                                
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
        write_error_log(f"fetch_quota_from_api ERROR (port {port}): {e}")
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
                    
                    # もし2.6.0の個別キーが含まれている場合は、キャッシュを初期化して差し戻す
                    q = data["quota"]
                    if "Gemini_5h" in q or "Claude_GPT_5h" in q:
                        data["quota"] = DEFAULT_QUOTAS.copy()
                        data["resets"] = {}
                        save_quota_cache_data(data)
                    return data
        except Exception as e:
            write_error_log(f"load_quota_cache_data migration error: {e}")
            
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
    """データをキャッシュファイルにアトミックに保存します。"""
    try:
        dest_dir = os.path.dirname(QUOTA_CACHE_FILE)
        os.makedirs(dest_dir, exist_ok=True)
        import tempfile
        # 同一ファイルシステム内に一時ファイルを作成
        with tempfile.NamedTemporaryFile("w", dir=dest_dir, delete=False, encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
            temp_name = f.name
        # アトミックに置換 (POSIX上では不可分操作)
        os.replace(temp_name, QUOTA_CACHE_FILE)
    except Exception as e:
        write_error_log(f"save_quota_cache_data ERROR: {e}")


def update_quota_cache_data(new_data):
    """APIからフェッチした新規データでキャッシュを更新・アトミック保存します。"""
    try:
        cache_data = load_quota_cache_data()
        
        cache_data["quota"] = new_data.get("quota", DEFAULT_QUOTAS)
        cache_data["resets"] = new_data.get("resets", {})
        cache_data["credits"] = new_data.get("credits", cache_data.get("credits", {}))
        cache_data["last_fetch_time"] = datetime.datetime.now().isoformat()
        
        save_quota_cache_data(cache_data)
    except Exception as e:
        write_error_log(f"update_quota_cache_data ERROR: {e}")


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


_FONT_CACHE = {}

def get_cached_font(font_path, size, index=0):
    """フォントオブジェクトをキャッシュから取得します (ファイルI/O削減)。"""
    key = (font_path, size, index)
    if key not in _FONT_CACHE:
        try:
            if index > 0:
                _FONT_CACHE[key] = ImageFont.truetype(font_path, size, index=index)
            else:
                _FONT_CACHE[key] = ImageFont.truetype(font_path, size)
        except Exception:
            try:
                # フォールバックフォント
                fallback_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
                _FONT_CACHE[key] = ImageFont.truetype(fallback_path, size)
            except Exception:
                _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def generate_circular_progress_base64(percentage, display_name, reset_text):
    """円形プログレスリングと右側のテキスト（モデル名・回復時間）を2倍サイズ(DPI 144)で合成してRetina対応で返します。"""
    if not HAS_PILLOW:
        return None
    try:
        # 横長(720x128)の画像を作成（2xサイズ、透過背景）
        width = 720
        height = 128
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 1. 左端に円形リングを描画
        size = 128
        margin = 12
        box = [margin, margin, size - margin, size - margin]
        color_code = get_quota_color(percentage)
        
        # 背景のグレーのリング (太さ 12px)
        draw.arc(box, start=0, end=360, fill=(60, 60, 60, 255), width=12)
        
        # 進捗のカラーリング (上部-90度から時計回り, 太さ 12px)
        angle = int((percentage / 100.0) * 360)
        if angle > 0:
            draw.arc(box, start=-90, end=-90 + angle, fill=color_code, width=12)
            
        # リング中央のパーセンテージ数値 (フォントサイズ 32)
        pct_text = f"{percentage}%"
        pct_font = get_cached_font("/System/Library/Fonts/Helvetica.ttc", 32, index=2)
                
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), pct_text, font=pct_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        else:
            text_w, text_h = draw.textsize(pct_text, font=pct_font) if hasattr(draw, "textsize") else (48, 28)
            
        text_x = (size - text_w) // 2
        text_y = (size - text_h) // 2 - 2
        
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            draw.text((text_x + dx, text_y + dy), pct_text, fill=(255, 255, 255, 255), font=pct_font)
            
        # 2. 右側にテキスト（モデル名とリセット時間）を描画
        # フォント読み込み (フォントサイズ 30, 26)
        font_title = get_cached_font("/System/Library/Fonts/Helvetica.ttc", 30, index=2)
        font_sub = get_cached_font("/System/Library/Fonts/Helvetica.ttc", 26, index=2)
                
        # 描画開始位置 (X=150px)
        text_start_x = 150
        
        # 1行目: モデルグループ名 (太字補強のため重ね描き)
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            draw.text((text_start_x + dx, 24 + dy), display_name, fill=color_code, font=font_title)
            
        # 2行目: 回復時間
        sub_text = f"(Reset: {reset_text})"
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            draw.text((text_start_x + dx, 68 + dy), sub_text, fill=color_code, font=font_sub)
            
        # Base64への変換 (DPIを144に設定してRetina対応にする)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", dpi=(144, 144))
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return img_str
    except Exception:
        return None

def determine_quota_type(iso_str):
    """
    リセット時間のISO 8601形式文字列から、制限タイプを判定します。
    - 残り時間が 24時間以内の場合: "5h"
    - 残り時間が 24時間より長い場合: "W"
    - 判定できないか None の場合: None
    """
    if not iso_str:
        return None
    try:
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1] + '+00:00'
        dt_utc = datetime.datetime.fromisoformat(iso_str)
        dt_local = dt_utc.astimezone()
        now = datetime.datetime.now().astimezone()
        diff = (dt_local - now).total_seconds()
        
        if diff <= 86400: # 24時間以内
            return "5h"
        else:
            return "W"
    except Exception:
        return None

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

    repr_str = ""
    if quotas:
        gemini_val = quotas.get("Gemini", quotas.get("F-Med", 100))
        claude_val = quotas.get("Claude_GPT", quotas.get("Sonnet", 100))
        
        def make_bar(val):
            filled = max(0, min(10, round(val / 10)))
            if val >= 100:
                dot = "🟣"
            elif val >= 80:
                dot = "🔵"
            elif val >= 60:
                dot = "🟢"
            elif val >= 40:
                dot = "🟡"
            elif val >= 20:
                dot = "🟠"
            else:
                dot = "🔴"
            return dot * filled + "⚫" * (10 - filled)

        gemini_bar = make_bar(gemini_val)
        claude_bar = make_bar(claude_val)
        
        gemini_type = None
        if gemini_val < 100 and resets_data:
            r_val = resets_data.get("Gemini", resets_data.get("F-Med"))
            gemini_type = determine_quota_type(r_val)
        gemini_suffix = f"({gemini_type})" if gemini_type else ""
        
        claude_type = None
        if claude_val < 100 and resets_data:
            r_val = resets_data.get("Claude_GPT", resets_data.get("Sonnet"))
            claude_type = determine_quota_type(r_val)
        claude_suffix = f"({claude_type})" if claude_type else ""
        
        repr_str = f"Gemini {gemini_bar} {gemini_val}%{gemini_suffix}  ❘  Claude & GPT {claude_bar} {claude_val}%{claude_suffix}"
            
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
    lines.append(f"{msg['header']} | font=\"Helvetica-Bold\" size=13 color=#ffffff")
    
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
        
    # モデル別クォータ詳細表示 (グループ化 & 円形プログレスリング & 週制限オミット)
    if quotas:
        lines.append("---")
        cache_status = msg["cached"] if is_cached else msg["realtime"]
        lines.append(f"⚡️ Model Quotas {cache_status} | font=\"Helvetica-Bold\" size=12 color=#ffffff")
        
        # 代表値グループ定義 (旧形式に戻す)
        groups = []
        if "Gemini" in quotas:
            groups.append(("Gemini", "Gemini Models", "Gemini"))
        elif "F-Med" in quotas:
            groups.append(("F-Med", "Gemini Models", "F-Med"))
            
        if "Claude_GPT" in quotas:
            groups.append(("Claude_GPT", "Claude & GPT Models", "Claude_GPT"))
        elif "Sonnet" in quotas:
            groups.append(("Sonnet", "Claude & GPT Models", "Sonnet"))
        
        for key, display_name, reset_key in groups:
            if key in quotas:
                val = quotas[key]
                color = get_quota_color(val)
                
                # 100%の場合はリセット日時を "-"、それ未満は MM/DD HH:MM
                reset_text = "—"
                quota_type = None
                if val < 100 and resets_data and reset_key in resets_data:
                    iso_str = resets_data[reset_key]
                    if iso_str:
                        quota_type = determine_quota_type(iso_str)
                        try:
                            if iso_str.endswith('Z'):
                                iso_str = iso_str[:-1] + '+00:00'
                            dt_utc = datetime.datetime.fromisoformat(iso_str)
                            dt_local = dt_utc.astimezone()
                            reset_text = dt_local.strftime('%m/%d %H:%M')
                        except Exception:
                            pass
                
                display_name_with_type = display_name
                # 制限タイプを suffix に追加
                if quota_type == "5h":
                    display_name_with_type = f"{display_name} [5h]"
                elif quota_type == "W":
                    display_name_with_type = f"{display_name} [Weekly]"
                
                # 円形プログレスリング画像の生成（テキスト合成版）
                base64_img = generate_circular_progress_base64(val, display_name_with_type, reset_text)
                
                if base64_img:
                    # 画像内にテキストが合成されているため、SwiftBarには画像のみを出力する
                    lines.append(f" | image={base64_img}")
                else:
                    # Pillowがない場合のテキストフォールバック (2行に分割)
                    filled = max(0, min(10, round(val / 10)))
                    bar = "█" * filled + "░" * (10 - filled)
                    lines.append(f"{display_name_with_type}  {bar}  {val}% | font=\"Menlo-Bold\" size=14 color={color}")
                    lines.append(f"{INDENT}{INDENT}(Reset: {reset_text}) | font=\"Menlo-Bold\" size=12 color={color}")
        
    if credits_data:
        g1_cred = credits_data.get("googleOneAi")
        if g1_cred is not None:
            lines.append("---")
            lines.append("💳 Available Credits | font=\"Helvetica-Bold\" size=12 color=#ffffff")
            lines.append(f"{INDENT}Google One AI Credit: {g1_cred} | font=monospace size=12 color=#34c759")
            
    # 言語選択UI
    lines.append("---")
    script_path = os.path.realpath(__file__)
    lines.append(f"{msg['lang_header']} | font=\"Helvetica-Bold\" size=12 color=#ffffff")
    check_en = " [✓]" if lang == "en" else ""
    check_ja = " [✓]" if lang == "ja" else ""
    lines.append(f"{INDENT}🇺🇸 English{check_en} | terminal=false refresh=true bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--set-lang\" param3=\"en\"")
    lines.append(f"{INDENT}🇯🇵 日本語{check_ja} | terminal=false refresh=true bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--set-lang\" param3=\"ja\"")
    
    # About セクション
    lines.append("---")
    lines.append(f"{msg['about_header']} | font=\"Helvetica-Bold\" size=12 color=#ffffff")
    lines.append(f"{INDENT}{msg['about_version']} | font=monospace size=11 color=#8e8e93")
    lines.append(f"{INDENT}{msg['about_website']} | font=monospace size=11 href=https://note.com/us_kabu_journal/n/nb99ef3e525ce color=#007aff")
    lines.append(f"{INDENT}{msg['about_copyright']} | font=monospace size=11 color=#8e8e93")

    # 再読み込みボタン
    lines.append("---")
    lines.append(f"{msg['refresh']} | refresh=true font=sans-serif terminal=false bash=\"/usr/bin/python3\" param1=\"{script_path}\" param2=\"--force\"")
    
    return "\n".join(lines)



def do_bg_fetch():
    lock_file = os.path.expanduser("~/.gemini/antigravity/daemon/fetch.lock")
    if os.path.exists(lock_file):
        try:
            mtime = os.path.getmtime(lock_file)
            if time.time() - mtime < 30:  # 30秒以内のロックがあればスキップ
                return
        except:
            pass

    # ロック取得
    try:
        os.makedirs(os.path.dirname(lock_file), exist_ok=True)
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
    except:
        pass

    try:
        servers = find_lsp_info(force=True)
        if not servers:
            return
        
        for srv in servers:
            success = False
            for port in srv["ports"]:
                data = fetch_quota_from_api(port, srv["csrf_token"])
                if data:
                    update_quota_cache_data(data)
                    success = True
                    break
            if success:
                break
    except Exception as e:
        write_error_log(f"BG fetch error: {e}")
    finally:
        # ロック解除
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass

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
