const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { exec, execSync } = require('child_process');

function activate(context) {
    console.log('Antigravity Quota Monitor is now active!');

    // 1. macOS環境であるかチェック
    if (os.platform() !== 'darwin') {
        vscode.window.showWarningMessage('Antigravity Quota Monitor (AQM) is currently only supported on macOS (requires SwiftBar).');
        return;
    }

    // 2. SwiftBarのプラグインディレクトリの解決
    //    ユーザーが既にSwiftBarで別のプラグインディレクトリを設定している場合はそちらを尊重する。
    //    未設定の場合のみデフォルトパスを使用する。
    const homeDir = os.homedir();
    const defaultPluginsDir = path.join(homeDir, 'Library/Application Support/SwiftBar/plugins');
    let pluginsDir = defaultPluginsDir;
    try {
        const existingDir = execSync('defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null', { encoding: 'utf-8' }).trim();
        if (existingDir && fs.existsSync(existingDir)) {
            pluginsDir = existingDir;
        }
    } catch (_) {
        // SwiftBarが未インストール or 未設定の場合はデフォルトパスを使用
    }
    const sourceDir = path.join(context.extensionPath, 'app');

    // 3. 自動コピー処理の定義
    function setupSwiftBarPlugin() {
        try {
            // プラグインディレクトリが存在しない場合は作成
            if (!fs.existsSync(pluginsDir)) {
                fs.mkdirSync(pluginsDir, { recursive: true });
            }

            // 元ファイルパスと存在確認
            const srcStatus = path.join(sourceDir, 'antigravity_status.py');
            if (!fs.existsSync(srcStatus)) {
                console.error(`Source file not found: ${srcStatus}`);
                vscode.window.showErrorMessage('Antigravity Quota: プラグインのソースファイルが見つかりません。拡張機能を再インストールしてください。');
                return;
            }

            // 古いプラグインファイル群の完全クリーンアップ（二重起動や競合を完璧に防ぐ）
            // ハードコードではなく、ディレクトリ内の全ファイルを動的スキャンし、
            // 「antigravity_status」または「get_quota」を含むファイルをすべて削除する。
            // これにより、過去のどのバージョン（1s, 2s, 5s, 10s, 30s等）が残っていても確実に一掃される。
            try {
                const existingFiles = fs.readdirSync(pluginsDir);
                for (const file of existingFiles) {
                    if (file.startsWith('antigravity_status') || file.startsWith('get_quota')) {
                        const filePath = path.join(pluginsDir, file);
                        try {
                            fs.unlinkSync(filePath);
                            console.log(`Old plugin file cleaned up: ${file}`);
                        } catch (unlinkErr) {
                            console.error(`Failed to clean up old file ${file}:`, unlinkErr);
                        }
                    }
                }
            } catch (readErr) {
                console.error('Failed to scan plugins directory for cleanup:', readErr);
            }

            // 新しいコピー先パス (常駐ストリーミング形式: 認識のために時間指定が必要)
            // macOSの NSStatusItem VisibleCC キャッシュの呪いを確実に回避するため、2sへ名前を変更します。
            const destStatus = path.join(pluginsDir, 'antigravity_status.2s.py');

            // ファイルのコピー
            fs.copyFileSync(srcStatus, destStatus);

            // 実行権限の付与 (chmod +x)
            fs.chmodSync(destStatus, 0o755);

            console.log('SwiftBar plugin file successfully copied and permissions set (2-second refresh active).');

            // 4. macOS NSStatusItem VisibleCC キャッシュの呪いを強制解除
            // Disable→Enable時にSwiftBarのメニューバーアイテムが非表示キャッシュに捕まるのを防ぐ
            forceResetVisibilityCache();

            // 5. SwiftBarの設定確認と起動・リフレッシュ処理
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
    // SwiftBarのPluginDirectory設定を確認
    exec('defaults read com.ameba.SwiftBar PluginDirectory', (err, stdout) => {
        const currentDir = stdout ? stdout.trim() : '';

        if (err || !currentDir) {
            // 未設定の場合のみ書き込む（ユーザーの既存設定は絶対に上書きしない）
            exec(`defaults write com.ameba.SwiftBar PluginDirectory "${pluginsDir}"`, (writeErr) => {
                if (!writeErr) {
                    console.log('SwiftBar PluginDirectory configured successfully.');
                    restartSwiftBar();
                } else {
                    console.error('Failed to set SwiftBar PluginDirectory via defaults:', writeErr);
                }
            });
        } else {
            // 設定が既にある場合、起動確認と完全再起動
            exec('pgrep -x SwiftBar', (pgrepErr) => {
                if (pgrepErr) {
                    startSwiftBar();
                } else {
                    restartSwiftBar();
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
    exec('killall SwiftBar', (killErr) => {
        // killallのエラー（SwiftBar未起動等）は無視してよい
        // プロセス終了を確実に待つため2秒の遅延を設定
        setTimeout(startSwiftBar, 2000);
    });
}

function forceResetVisibilityCache() {
    // macOS NSStatusItem VisibleCC キャッシュの全アイテムを強制的に「表示」に設定
    // SwiftBarはプラグインを Item-N 形式で管理するため、全スロットを有効化する
    // execSync を使い、plist書き込みの競合を防ぐ（直列実行で安全性を保証）
    try {
        for (let i = 0; i <= 15; i++) {
            execSync(`defaults write com.ameba.SwiftBar "NSStatusItem VisibleCC Item-${i}" -bool true`);
        }
        console.log('SwiftBar VisibleCC cache force-reset completed for Item-0 to Item-15.');
    } catch (cacheErr) {
        console.error('Failed to reset VisibleCC cache:', cacheErr);
    }
}

function deactivate() {
    try {
        const homeDir = os.homedir();
        const defaultPluginsDir = path.join(homeDir, 'Library/Application Support/SwiftBar/plugins');
        let pluginsDir = defaultPluginsDir;
        try {
            const existingDir = execSync('defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null', { encoding: 'utf-8' }).trim();
            if (existingDir && fs.existsSync(existingDir)) {
                pluginsDir = existingDir;
            }
        } catch (_) {}
        
        const destStatus = path.join(pluginsDir, 'antigravity_status.2s.py');
        if (fs.existsSync(destStatus)) {
            fs.unlinkSync(destStatus);
            console.log('SwiftBar plugin file cleaned up on deactivate.');
        }
    } catch (err) {
        console.error('Failed to clean up SwiftBar plugin on deactivate:', err);
    }
}

module.exports = {
    activate,
    deactivate
};
