const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { exec } = require('child_process');

function activate(context) {
    console.log('Antigravity Quota Monitor is now active!');

    // 1. macOS環境であるかチェック
    if (os.platform() !== 'darwin') {
        return;
    }

    // 2. SwiftBarのプラグインディレクトリの解決
    const homeDir = os.homedir();
    const pluginsDir = path.join(homeDir, 'Library/Application Support/SwiftBar/plugins');
    const sourceDir = path.join(context.extensionPath, 'app');

    // 3. 自動コピー処理の定義
    function setupSwiftBarPlugin() {
        try {
            // プラグインディレクトリが存在しない場合は作成
            if (!fs.existsSync(pluginsDir)) {
                fs.mkdirSync(pluginsDir, { recursive: true });
            }

            // 元ファイルパス
            const srcStatus = path.join(sourceDir, 'antigravity_status.py');
            const srcQuota = path.join(sourceDir, 'get_quota.js');

            // コピー先パス
            const destStatus = path.join(pluginsDir, 'antigravity_status.30s.py');
            const destQuota = path.join(pluginsDir, 'get_quota.js');

            // ファイルのコピー
            fs.copyFileSync(srcStatus, destStatus);
            fs.copyFileSync(srcQuota, destQuota);

            // 実行権限の付与 (chmod +x)
            fs.chmodSync(destStatus, 0o755);
            fs.chmodSync(destQuota, 0o755);

            console.log('SwiftBar plugin files successfully copied and permissions set.');

            // 4. SwiftBarの設定確認と起動・リフレッシュ処理
            checkAndConfigureSwiftBar(pluginsDir);

        } catch (error) {
            console.error('Failed to copy SwiftBar plugin files:', error);
            vscode.window.showErrorMessage('Antigravity Quota: SwiftBarプラグインの配置に失敗しました。');
        }
    }

    // 遅延実行（VS Codeが完全に立ち上がるのを待つ）
    setTimeout(setupSwiftBarPlugin, 3000);
}

function checkAndConfigureSwiftBar(pluginsDir) {
    // 5. SwiftBarのPluginDirectory設定を確認し、未設定の場合は書き込み
    exec('defaults read com.ameba.SwiftBar PluginDirectory', (err, stdout) => {
        const currentDir = stdout ? stdout.trim() : '';

        // パスが設定されていない、または現在のプラグインディレクトリと異なる場合
        if (err || currentDir !== pluginsDir) {
            exec(`defaults write com.ameba.SwiftBar PluginDirectory "${pluginsDir}"`, (writeErr) => {
                if (!writeErr) {
                    console.log('SwiftBar PluginDirectory configured successfully.');
                    restartSwiftBar();
                } else {
                    console.error('Failed to set SwiftBar PluginDirectory via defaults:', writeErr);
                }
            });
        } else {
            // すでに設定が正しい場合、起動確認とリフレッシュのみ行う
            exec('pgrep -x SwiftBar', (pgrepErr) => {
                if (pgrepErr) {
                    // 起動していない場合は起動
                    startSwiftBar();
                } else {
                    // すでに起動している場合はリフレッシュURLを叩く
                    refreshSwiftBar();
                }
            });
        }
    });
}

function startSwiftBar() {
    exec('open -a SwiftBar', (err) => {
        if (err) {
            console.log('SwiftBar app not found or failed to start.');
            vscode.window.showInformationMessage(
                'Antigravity Quota: メニューバー表示には SwiftBar アプリが必要です。インストールしてください。',
                'GitHubで確認'
            ).then(selection => {
                if (selection === 'GitHubで確認') {
                    vscode.env.openExternal(vscode.Uri.parse('https://github.com/swiftbar/SwiftBar'));
                }
            });
        } else {
            vscode.window.showInformationMessage('Antigravity Quota: macOS メニューバー（SwiftBar）と自動連携しました！');
        }
    });
}

function restartSwiftBar() {
    exec('killall SwiftBar', () => {
        setTimeout(startSwiftBar, 1000);
    });
}

function refreshSwiftBar() {
    exec('open -g "swiftbar://refreshAll"', (err) => {
        if (err) {
            console.error('Failed to refresh SwiftBar:', err);
        } else {
            console.log('SwiftBar refresh triggered successfully.');
        }
    });
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
