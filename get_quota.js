/*
 * Copyright 2026 Madoka (US Stock Journal Editorial Director)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const { exec } = require('child_process');
const http = require('http');

// 1. LSPプロセスのPIDとCSRFトークンを特定します
function findLspInfo() {
    return new Promise((resolve, reject) => {
        exec('ps aux | grep -i language_server', (err, stdout) => {
            if (err) return reject(err);
            const lines = stdout.split('\n');
            const lspLine = lines.find(l => l.includes('language_server') && !l.includes('grep') && !l.includes('zsh'));
            if (!lspLine) return reject(new Error('Language server process not found'));

            // PIDの抽出
            const parts = lspLine.trim().split(/\s+/);
            const pid = parseInt(parts[1]);

            // CSRFトークンの抽出
            const csrfMatch = lspLine.match(/--csrf_token\s+([a-fA-F0-9-]+)/);
            if (!csrfMatch) return reject(new Error('CSRF token not found in process arguments'));

            resolve({ pid, csrfToken: csrfMatch[1] });
        });
    });
}

// 2. 指定したPIDがLISTENしているポートを特定します
function findListeningPorts(pid) {
    return new Promise((resolve, reject) => {
        exec(`lsof -a -p ${pid} -i -P -n | grep LISTEN`, (err, stdout) => {
            if (err) return reject(err);
            const ports = [];
            const lines = stdout.trim().split('\n');
            for (const line of lines) {
                const match = line.match(/:(\d+)\s+\(LISTEN\)/);
                if (match) {
                    ports.push(parseInt(match[1]));
                }
            }
            if (ports.length === 0) return reject(new Error('No listening ports found for PID ' + pid));
            resolve([...new Set(ports)].sort());
        });
    });
}

// 3. ローカルAPIに対してConnectプロトコルのリクエストを送信します
function fetchQuotaFromApiHttp(port, csrfToken) {
    return new Promise((resolve, reject) => {
        const bodyData = JSON.stringify({
            metadata: {
                ideName: 'antigravity',
                extensionName: 'antigravity',
                locale: 'en'
            }
        });
        
        const options = {
            hostname: '127.0.0.1',
            port: port,
            path: '/exa.language_server_pb.LanguageServerService/GetUserStatus',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(bodyData),
                'Connect-Protocol-Version': '1',
                'X-Codeium-Csrf-Token': csrfToken
            },
            timeout: 3000
        };

        const req = http.request(options, (res) => {
            let resData = '';
            res.on('data', chunk => resData += chunk);
            res.on('end', () => {
                resolve({ status: res.status || res.statusCode, headers: res.headers, body: resData });
            });
        });

        req.on('error', reject);
        req.write(bodyData);
        req.end();
    });
}

// 4. APIのレスポンスをPython側と互換性のあるフォーマットに変換します
const labelToKey = {
    "Gemini 3.5 Flash (Medium)": "F-Med",
    "Gemini 3.5 Flash (High)": "F-High",
    "Gemini 3.5 Flash (Low)": "F-Low",
    "Gemini 3.1 Pro (Low)": "P-Low",
    "Gemini 3.1 Pro (High)": "P-High",
    "Claude Sonnet 4.6 (Thinking)": "Sonnet",
    "Claude Opus 4.6 (Thinking)": "Opus",
    "GPT-OSS 120B (Medium)": "GPT-120"
};

async function main() {
    try {
        const lspInfo = await findLspInfo();
        const ports = await findListeningPorts(lspInfo.pid);

        let quotaData = null;
        let resetsData = null;
        let success = false;
        let errors = [];
        let dataObj = null;

        for (const port of ports) {
            try {
                const res = await fetchQuotaFromApiHttp(port, lspInfo.csrfToken);
                if (res.status === 200) {
                    const data = JSON.parse(res.body);
                    if (data && data.userStatus && data.userStatus.cascadeModelConfigData && Array.isArray(data.userStatus.cascadeModelConfigData.clientModelConfigs)) {
                        quotaData = {};
                        resetsData = {};
                        const configs = data.userStatus.cascadeModelConfigData.clientModelConfigs;
                        for (const m of configs) {
                            const key = labelToKey[m.label];
                            if (key) {
                                if (m.quotaInfo) {
                                    if (typeof m.quotaInfo.remainingFraction === 'number') {
                                        quotaData[key] = Math.round(m.quotaInfo.remainingFraction * 100);
                                    } else {
                                        // proto3 の JSON シリアライズ仕様により、0 (0%) の場合は remainingFraction フィールド自体が省略されることがある
                                        // したがって、quotaInfo は存在するが remainingFraction が無い場合は 0% と解釈する
                                        quotaData[key] = 0;
                                    }
                                } else {
                                    // quotaInfo が全く存在しない場合はクォータ制限なし (100%) とみなす
                                    quotaData[key] = 100;
                                }
                                if (m.quotaInfo && m.quotaInfo.resetTime) {
                                    resetsData[key] = m.quotaInfo.resetTime;
                                }
                            }
                        }
                        success = true;
                        dataObj = data;
                        break;
                    } else {
                        errors.push(`Port ${port} response format mismatch`);
                    }
                } else {
                    errors.push(`Port ${port} responded with status ${res.status}`);
                }
            } catch (e) {
                errors.push(`Port ${port} failed: ${e.message}`);
            }
        }

        if (success && quotaData) {
            let credits = null;
            if (dataObj && dataObj.userStatus && dataObj.userStatus.planStatus) {
                const ps = dataObj.userStatus.planStatus;
                credits = {
                    availablePrompt: ps.availablePromptCredits,
                    monthlyPrompt: ps.planInfo ? ps.planInfo.monthlyPromptCredits : null,
                    availableFlow: ps.availableFlowCredits,
                    monthlyFlow: ps.planInfo ? ps.planInfo.monthlyFlowCredits : null,
                };
                if (dataObj.userStatus.userTier && Array.isArray(dataObj.userStatus.userTier.availableCredits) && dataObj.userStatus.userTier.availableCredits[0]) {
                    credits.googleOneAi = dataObj.userStatus.userTier.availableCredits[0].creditAmount;
                }
            }
            console.log(JSON.stringify({ success: true, quota: quotaData, resets: resetsData, credits: credits }));
        } else {
            console.log(JSON.stringify({ success: false, reason: `Failed to fetch from API: ${errors.join('; ')}` }));
        }
    } catch (e) {
        console.log(JSON.stringify({ success: false, reason: e.message }));
    }
}

main();
