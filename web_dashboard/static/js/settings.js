/**
 * Settings page JavaScript
 * 設定ページの UI 制御とAPI通信
 */

class SettingsManager {
    constructor() {
        this.symbols = [];
        this.settingsData = {};
        this.init();
    }

    showMessageBanner(message, type = 'info', autoHide = true) {
        const messageArea = document.getElementById('message-area');
        
        // Remove existing banner if any
        const existingBanner = messageArea.querySelector('.message-banner');
        if (existingBanner) {
            existingBanner.remove();
        }
        
        // Get appropriate icon for message type
        const icons = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-circle',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle'
        };
        
        const banner = document.createElement('div');
        banner.className = `message-banner ${type}`;
        banner.innerHTML = `
            <div class="message-content">
                <i class="${icons[type] || icons.info}"></i>
                <span>${message}</span>
            </div>
            <button class="close-btn" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        messageArea.appendChild(banner);
        
        // Auto hide after 8 seconds for success/info, 12 seconds for warnings/errors
        if (autoHide) {
            const hideDelay = (type === 'error' || type === 'warning') ? 12000 : 8000;
            setTimeout(() => {
                if (banner.parentElement) {
                    banner.style.animation = 'slideUp 0.3s ease-out';
                    setTimeout(() => banner.remove(), 300);
                }
            }, hideDelay);
        }
    }

    init() {
        this.bindEvents();
        this.loadSettings();
    }

    bindEvents() {
        // Symbol management
        document.getElementById('btn-add-symbol').addEventListener('click', () => this.showAddSymbolForm());
        document.getElementById('btn-confirm-add').addEventListener('click', () => this.addSymbol());
        document.getElementById('new-symbol-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addSymbol();
        });

        // Settings save/reset
        document.getElementById('btn-save-settings').addEventListener('click', () => this.saveSettings());
        document.getElementById('btn-reset-settings').addEventListener('click', () => this.resetSettings());

        // Discord settings
        document.getElementById('discord-enabled').addEventListener('change', (e) => {
            this.toggleDiscordSettings(e.target.checked);
        });
        document.getElementById('btn-test-discord').addEventListener('click', () => this.testDiscord());

        // Profile management
        document.getElementById('btn-load-profile').addEventListener('click', () => this.loadProfile());
        document.getElementById('btn-save-profile').addEventListener('click', () => this.saveProfile());

        // Import/Export
        document.getElementById('btn-export-settings').addEventListener('click', () => this.exportSettings());
        document.getElementById('btn-import-settings').addEventListener('click', () => this.importSettings());
        document.getElementById('import-file-input').addEventListener('change', (e) => this.handleFileImport(e));

        // Symbol edit modal
        document.getElementById('btn-save-symbol-edit').addEventListener('click', () => this.saveSymbolEdit());
        
        // Scheduler management
        document.getElementById('btn-start-scheduler').addEventListener('click', () => this.startScheduler());
        document.getElementById('btn-stop-scheduler').addEventListener('click', () => this.stopScheduler());
        document.getElementById('btn-refresh-tasks').addEventListener('click', () => this.loadSchedulerStatus());
        
    }

    async loadSettings() {
        try {
            this.showStatus('設定を読み込み中...', 'info');
            
            // Load current configuration
            const response = await fetch('/api/config');
            if (response.ok) {
                this.settingsData = await response.json();
                this.populateForm();
            }
            
            // Load monitored symbols from monitor status
            const statusResponse = await fetch('/api/status');
            if (statusResponse.ok) {
                const status = await statusResponse.json();
                this.symbols = status.monitored_symbols || [];
                this.renderSymbolsList();
            }

            this.showStatus('設定の読み込みが完了しました', 'success');
            
            // Load scheduler status
            await this.loadSchedulerStatus();
            
        } catch (error) {
            console.error('Settings load error:', error);
            this.showStatus('設定の読み込みに失敗しました', 'error');
        }
    }

    populateForm() {
        // Alert conditions
        if (this.settingsData.alerts) {
            document.getElementById('leverage-threshold').value = this.settingsData.alerts.leverage_threshold || 10.0;
            document.getElementById('confidence-threshold').value = this.settingsData.alerts.confidence_threshold || 70;
            document.getElementById('cooldown-minutes').value = this.settingsData.alerts.cooldown_minutes || 60;
            document.getElementById('max-alerts-hour').value = this.settingsData.alerts.max_alerts_hour || 10;
        }

        // Notification settings
        if (this.settingsData.notifications) {
            const discordEnabled = this.settingsData.notifications.discord?.enabled || false;
            document.getElementById('discord-enabled').checked = discordEnabled;
            this.toggleDiscordSettings(discordEnabled);

            // Log settings
            document.getElementById('log-level').value = this.settingsData.notifications.console?.level || 'INFO';
            document.getElementById('log-file-enabled').checked = this.settingsData.notifications.file?.enabled || true;
        }
    }

    renderSymbolsList() {
        const container = document.getElementById('symbols-list');
        container.innerHTML = '';

        if (this.symbols.length === 0) {
            container.innerHTML = '<div class="text-muted text-center py-3">監視銘柄が設定されていません</div>';
            return;
        }

        this.symbols.forEach(symbol => {
            const symbolElement = this.createSymbolElement(symbol);
            container.appendChild(symbolElement);
        });
    }

    createSymbolElement(symbol) {
        const div = document.createElement('div');
        div.className = 'symbol-item d-flex justify-content-between align-items-center mb-2 p-2 border rounded';
        
        const symbolInfo = typeof symbol === 'string' ? { name: symbol, interval: '全時間足', strategy: '全戦略 (18パターン)', enabled: true } : symbol;
        
        // Status-specific display
        let statusBadge = '';
        let statusIcon = '';
        
        switch (symbolInfo.status) {
            case 'analyzing':
                statusBadge = '<span class="badge bg-warning ms-2"><i class="fas fa-spinner fa-spin"></i> 分析中</span>';
                statusIcon = '🔄';
                break;
            case 'completed':
                statusBadge = '<span class="badge bg-success ms-2"><i class="fas fa-check"></i> 分析完了 (18パターン)</span>';
                statusIcon = '✅';
                break;
            case 'failed':
                statusBadge = '<span class="badge bg-danger ms-2"><i class="fas fa-times"></i> 失敗</span>';
                statusIcon = '❌';
                break;
            default:
                statusBadge = symbolInfo.enabled !== false ? '<span class="badge bg-success ms-2">有効</span>' : '<span class="badge bg-secondary ms-2">無効</span>';
                statusIcon = '📊';
        }
        
        div.innerHTML = `
            <div class="symbol-info">
                <strong>${statusIcon} ${symbolInfo.name}</strong>
                <small class="text-muted ms-2">${symbolInfo.interval || '15m'} - ${symbolInfo.strategy || 'Conservative_ML'}</small>
                ${statusBadge}
            </div>
            <div class="symbol-actions">
                <button class="btn btn-outline-primary btn-sm me-1" onclick="settingsManager.editSymbol('${symbolInfo.name}')" ${symbolInfo.status === 'analyzing' ? 'disabled' : ''}>
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="settingsManager.removeSymbol('${symbolInfo.name}')" ${symbolInfo.status === 'analyzing' ? 'disabled' : ''}>
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        return div;
    }

    showAddSymbolForm() {
        const form = document.getElementById('add-symbol-form');
        const btn = document.getElementById('btn-add-symbol');
        
        if (form.style.display === 'none') {
            form.style.display = 'block';
            btn.innerHTML = '<i class="fas fa-times"></i> キャンセル';
            document.getElementById('new-symbol-input').focus();
        } else {
            form.style.display = 'none';
            btn.innerHTML = '<i class="fas fa-plus"></i> 銘柄追加';
            this.clearAddForm();
        }
    }

    async addSymbol() {
        const nameInput = document.getElementById('new-symbol-input');
        const name = nameInput.value.trim().toUpperCase();

        if (!name) {
            this.showMessageBanner('銘柄名を入力してください', 'error');
            nameInput.focus();
            return;
        }

        // Check for duplicates
        if (this.symbols.some(s => (typeof s === 'string' ? s : s.name) === name)) {
            this.showMessageBanner('この銘柄は既に追加されています', 'error');
            nameInput.focus();
            return;
        }

        try {
            // Show loading state
            const addBtn = document.getElementById('btn-confirm-add');
            const originalText = addBtn.innerHTML;
            addBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 学習・分析中...';
            addBtn.disabled = true;
            
            this.showMessageBanner(`${name}の学習・バックテストを開始しています...`, 'info');

            // Call API to add symbol and start training/backtesting
            const response = await fetch('/api/symbol/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    symbol: name,
                    auto_train: true,
                    all_timeframes: true,
                    all_strategies: true
                })
            });

            if (response.ok) {
                const result = await response.json();
                
                // Add to symbols list with analyzing status
                const newSymbol = {
                    name: name,
                    status: 'analyzing',
                    execution_id: result.execution_id,
                    interval: '全時間足',
                    strategy: '全戦略 (18パターン)',
                    enabled: true,
                    added_at: new Date().toISOString()
                };

                this.symbols.push(newSymbol);
                this.renderSymbolsList();
                this.showAddSymbolForm(); // Hide form
                this.clearAddForm();
                
                this.showMessageBanner(`${name}の分析を開始しました。完了まで数分かかります。`, 'success');
                
                // Start polling for completion
                this.pollAnalysisProgress(result.execution_id, name);
                
            } else {
                const error = await response.json();
                
                // Handle validation errors more specifically
                const userMessage = error.user_message || error.error;
                const suggestion = error.suggestion || '正しい銘柄名を入力してください';
                
                if (error.validation_status === 'invalid') {
                    this.showMessageBanner(`❌ ${userMessage}`, 'error', false);
                    this.showDetailedError(name, error.error, suggestion);
                } else if (error.validation_status === 'inactive') {
                    this.showMessageBanner(`⚠️ ${userMessage}`, 'error', false);
                    this.showDetailedError(name, error.error, '後でもう一度お試しください');
                } else if (error.validation_status === 'error') {
                    this.showMessageBanner(`🔥 ${userMessage}`, 'error', false);
                    this.showDetailedError(name, error.error, 'ネットワーク接続を確認してもう一度お試しください');
                } else {
                    this.showMessageBanner(`エラー: ${userMessage}`, 'error', false);
                    this.showDetailedError(name, error.error, suggestion);
                }
            }

            // Reset button
            addBtn.innerHTML = originalText;
            addBtn.disabled = false;

        } catch (error) {
            console.error('Symbol addition error:', error);
            this.showMessageBanner('銘柄追加に失敗しました', 'error');
            
            // Reset button
            const addBtn = document.getElementById('btn-confirm-add');
            addBtn.innerHTML = '<i class="fas fa-plus"></i> 銘柄追加・分析開始';
            addBtn.disabled = false;
        }
    }

    async pollAnalysisProgress(executionId, symbolName) {
        /**
         * 分析進捗をポーリングで確認
         */
        const maxAttempts = 60; // 30分間ポーリング
        let attempts = 0;

        const checkProgress = async () => {
            try {
                const response = await fetch(`/api/execution/${executionId}/status`);
                if (response.ok) {
                    const status = await response.json();
                    
                    if (status.status === 'SUCCESS') {
                        this.showMessageBanner(`${symbolName}の分析が完了しました！履歴分析ページで結果を確認できます。`, 'success');
                        // Update symbol status instead of refreshing entire list
                        this.updateSymbolStatus(symbolName, 'completed');
                        return;
                    } else if (status.status === 'FAILED') {
                        // Get detailed error message from errors array
                        let errorMessage = 'Unknown error';
                        if (status.errors && status.errors.length > 0) {
                            const latestError = status.errors[status.errors.length - 1];
                            errorMessage = latestError.error_message || latestError.message || errorMessage;
                        } else if (status.current_operation && status.current_operation.includes('エラー:')) {
                            errorMessage = status.current_operation.replace('エラー: ', '');
                        } else if (status.error) {
                            errorMessage = status.error;
                        }
                        
                        this.showMessageBanner(`❌ ${symbolName}の分析に失敗しました: ${errorMessage}`, 'error', false);
                        // Update symbol status to failed
                        this.updateSymbolStatus(symbolName, 'failed');
                        return;
                    } else if (status.status === 'RUNNING') {
                        // Update progress if available
                        if (status.progress) {
                            this.showMessageBanner(`${symbolName}分析中... ${status.progress.current_operation} (${Math.round(status.progress.percentage)}%)`, 'info');
                            // Update symbol status to show progress
                            this.updateSymbolStatus(symbolName, 'analyzing');
                        }
                    }
                }
                
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkProgress, 30000); // Check every 30 seconds
                } else {
                    this.showStatus(`${symbolName}の分析がタイムアウトしました。ログを確認してください。`, 'warning');
                }
                
            } catch (error) {
                console.error('Progress check error:', error);
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkProgress, 30000);
                }
            }
        };

        // Start checking after 30 seconds
        setTimeout(checkProgress, 30000);
    }

    updateSymbolStatus(symbolName, newStatus) {
        // Find and update the symbol status
        const symbolIndex = this.symbols.findIndex(s => (typeof s === 'string' ? s : s.name) === symbolName);
        if (symbolIndex !== -1) {
            if (typeof this.symbols[symbolIndex] === 'string') {
                // Convert string to object
                this.symbols[symbolIndex] = {
                    name: this.symbols[symbolIndex],
                    status: newStatus,
                    interval: '全時間足',
                    strategy: '全戦略 (18パターン)',
                    enabled: true
                };
            } else {
                this.symbols[symbolIndex].status = newStatus;
            }
            
            // Re-render the symbols list to show updated status
            this.renderSymbolsList();
        }
    }

    clearAddForm() {
        document.getElementById('new-symbol-input').value = '';
    }

    editSymbol(symbolName) {
        const symbol = this.symbols.find(s => (typeof s === 'string' ? s : s.name) === symbolName);
        if (!symbol) return;

        const symbolInfo = typeof symbol === 'string' ? { name: symbol, interval: '15m', strategy: 'Conservative_ML', enabled: true } : symbol;

        // Populate modal
        document.getElementById('edit-symbol-original').value = symbolName;
        document.getElementById('edit-symbol-name').value = symbolInfo.name;
        document.getElementById('edit-symbol-interval').value = symbolInfo.interval?.replace('m', '') || '15';
        document.getElementById('edit-symbol-strategy').value = symbolInfo.strategy || 'Conservative_ML';
        document.getElementById('edit-symbol-enabled').checked = symbolInfo.enabled !== false;

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editSymbolModal'));
        modal.show();
    }

    saveSymbolEdit() {
        const originalName = document.getElementById('edit-symbol-original').value;
        const interval = document.getElementById('edit-symbol-interval').value;
        const strategy = document.getElementById('edit-symbol-strategy').value;
        const enabled = document.getElementById('edit-symbol-enabled').checked;

        const symbolIndex = this.symbols.findIndex(s => (typeof s === 'string' ? s : s.name) === originalName);
        if (symbolIndex === -1) return;

        this.symbols[symbolIndex] = {
            name: originalName,
            interval: interval + 'm',
            strategy: strategy,
            enabled: enabled
        };

        this.renderSymbolsList();
        
        // Hide modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editSymbolModal'));
        modal.hide();
        
        this.showStatus(`${originalName}の設定を更新しました`, 'success');
    }

    removeSymbol(symbolName) {
        if (confirm(`${symbolName}を監視銘柄から削除しますか？`)) {
            this.symbols = this.symbols.filter(s => (typeof s === 'string' ? s : s.name) !== symbolName);
            this.renderSymbolsList();
            this.showStatus(`${symbolName}を削除しました`, 'success');
        }
    }

    toggleDiscordSettings(enabled) {
        const settings = document.getElementById('discord-settings');
        settings.style.display = enabled ? 'block' : 'none';
    }

    async testDiscord() {
        const webhook = document.getElementById('discord-webhook').value;
        if (!webhook) {
            this.showStatus('Webhook URLを入力してください', 'error');
            return;
        }

        try {
            this.showStatus('Discord通知をテスト中...', 'info');
            
            const response = await fetch('/api/test-discord', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ webhook_url: webhook })
            });

            if (response.ok) {
                this.showStatus('Discordテスト通知が送信されました', 'success');
            } else {
                const error = await response.json();
                this.showStatus(`Discordテストエラー: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Discord test error:', error);
            this.showStatus('Discord通知のテストに失敗しました', 'error');
        }
    }

    async saveSettings() {
        try {
            this.showStatus('設定を保存中...', 'info');

            const settings = {
                symbols: this.symbols,
                alerts: {
                    leverage_threshold: parseFloat(document.getElementById('leverage-threshold').value),
                    confidence_threshold: parseInt(document.getElementById('confidence-threshold').value),
                    cooldown_minutes: parseInt(document.getElementById('cooldown-minutes').value),
                    max_alerts_hour: parseInt(document.getElementById('max-alerts-hour').value)
                },
                notifications: {
                    discord: {
                        enabled: document.getElementById('discord-enabled').checked,
                        webhook_url: document.getElementById('discord-webhook').value,
                        mention_role: document.getElementById('discord-mention').value
                    },
                    console: {
                        level: document.getElementById('log-level').value
                    },
                    file: {
                        enabled: document.getElementById('log-file-enabled').checked
                    }
                }
            };

            const response = await fetch('/api/settings/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });

            if (response.ok) {
                this.showStatus('設定が保存されました', 'success');
                this.updateLastSaved();
            } else {
                const error = await response.json();
                this.showStatus(`設定保存エラー: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Settings save error:', error);
            this.showStatus('設定の保存に失敗しました', 'error');
        }
    }

    async resetSettings() {
        if (confirm('設定を初期値にリセットしますか？この操作は元に戻せません。')) {
            try {
                this.showStatus('設定をリセット中...', 'info');
                
                const response = await fetch('/api/settings/reset', {
                    method: 'POST'
                });

                if (response.ok) {
                    this.showStatus('設定がリセットされました', 'success');
                    await this.loadSettings();
                } else {
                    const error = await response.json();
                    this.showStatus(`設定リセットエラー: ${error.error}`, 'error');
                }
            } catch (error) {
                console.error('Settings reset error:', error);
                this.showStatus('設定のリセットに失敗しました', 'error');
            }
        }
    }

    async loadProfile() {
        const profileName = document.getElementById('profile-select').value;
        try {
            this.showStatus(`プロファイル「${profileName}」を読み込み中...`, 'info');
            
            const response = await fetch(`/api/settings/profile/${profileName}`);
            if (response.ok) {
                const profileData = await response.json();
                this.settingsData = profileData;
                this.symbols = profileData.symbols || [];
                this.populateForm();
                this.renderSymbolsList();
                this.showStatus(`プロファイル「${profileName}」を読み込みました`, 'success');
            } else {
                const error = await response.json();
                this.showStatus(`プロファイル読み込みエラー: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Profile load error:', error);
            this.showStatus('プロファイルの読み込みに失敗しました', 'error');
        }
    }

    async saveProfile() {
        const profileName = document.getElementById('new-profile-name').value.trim();
        if (!profileName) {
            this.showStatus('プロファイル名を入力してください', 'error');
            document.getElementById('new-profile-name').focus();
            return;
        }

        try {
            this.showStatus(`プロファイル「${profileName}」を保存中...`, 'info');
            
            const currentSettings = this.getCurrentSettings();
            
            const response = await fetch('/api/settings/profile/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: profileName,
                    settings: currentSettings
                })
            });

            if (response.ok) {
                this.showStatus(`プロファイル「${profileName}」を保存しました`, 'success');
                document.getElementById('new-profile-name').value = '';
                // Update profile select options
                this.updateProfileOptions();
            } else {
                const error = await response.json();
                this.showStatus(`プロファイル保存エラー: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Profile save error:', error);
            this.showStatus('プロファイルの保存に失敗しました', 'error');
        }
    }

    getCurrentSettings() {
        return {
            symbols: this.symbols,
            alerts: {
                leverage_threshold: parseFloat(document.getElementById('leverage-threshold').value),
                confidence_threshold: parseInt(document.getElementById('confidence-threshold').value),
                cooldown_minutes: parseInt(document.getElementById('cooldown-minutes').value),
                max_alerts_hour: parseInt(document.getElementById('max-alerts-hour').value)
            },
            notifications: {
                discord: {
                    enabled: document.getElementById('discord-enabled').checked,
                    webhook_url: document.getElementById('discord-webhook').value,
                    mention_role: document.getElementById('discord-mention').value
                },
                console: {
                    level: document.getElementById('log-level').value
                },
                file: {
                    enabled: document.getElementById('log-file-enabled').checked
                }
            }
        };
    }

    exportSettings() {
        const settings = this.getCurrentSettings();
        const dataStr = JSON.stringify(settings, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `long-trader-settings-${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        this.showStatus('設定をエクスポートしました', 'success');
    }

    importSettings() {
        document.getElementById('import-file-input').click();
    }

    handleFileImport(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const settings = JSON.parse(e.target.result);
                this.settingsData = settings;
                this.symbols = settings.symbols || [];
                this.populateForm();
                this.renderSymbolsList();
                this.showStatus('設定をインポートしました', 'success');
            } catch (error) {
                console.error('Import error:', error);
                this.showStatus('設定ファイルの読み込みに失敗しました', 'error');
            }
        };
        reader.readAsText(file);
        
        // Reset file input
        event.target.value = '';
    }

    async updateProfileOptions() {
        try {
            const response = await fetch('/api/settings/profiles');
            if (response.ok) {
                const profiles = await response.json();
                const select = document.getElementById('profile-select');
                
                // Clear existing options except defaults
                while (select.children.length > 3) {
                    select.removeChild(select.lastChild);
                }
                
                // Add custom profiles
                profiles.forEach(profile => {
                    const option = document.createElement('option');
                    option.value = profile.name;
                    option.textContent = profile.name;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Profile options update error:', error);
        }
    }

    showStatus(message, type = 'info') {
        // Use the new message banner system
        this.showMessageBanner(message, type);
        
        // Also update the bottom status element if it exists
        const statusElement = document.getElementById('settings-status');
        if (statusElement) {
            const icons = {
                'info': 'fas fa-info-circle',
                'success': 'fas fa-check-circle',
                'error': 'fas fa-exclamation-circle',
                'warning': 'fas fa-exclamation-triangle'
            };
            
            const colors = {
                'info': 'text-primary',
                'success': 'text-success',
                'error': 'text-danger',
                'warning': 'text-warning'
            };
            
            statusElement.innerHTML = `<i class="${icons[type]} ${colors[type]}"></i> ${message}`;
            
            // Auto-hide success/info messages after 5 seconds
            if (type === 'success' || type === 'info') {
                setTimeout(() => {
                    statusElement.innerHTML = '<i class="fas fa-info-circle"></i> 設定を変更した後は「設定保存」ボタンを押してください';
                    statusElement.className = 'text-muted';
                }, 5000);
            }
        }
    }
    
    showDetailedError(symbol, technicalError, userFriendlyMessage) {
        // Create a more detailed error modal or alert
        const errorDetails = `
            <div class="alert alert-danger alert-dismissible" role="alert">
                <h6 class="alert-heading">
                    <i class="fas fa-exclamation-triangle"></i> 銘柄追加エラー: ${symbol}
                </h6>
                <p class="mb-2"><strong>説明:</strong> ${userFriendlyMessage}</p>
                <hr>
                <p class="mb-0">
                    <small><strong>技術的詳細:</strong> ${technicalError}</small>
                </p>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        // Insert into status area for detailed display
        const statusElement = document.getElementById('settings-status');
        statusElement.innerHTML = errorDetails;
        
        // Also focus back to input for easy retry
        const symbolInput = document.getElementById('new-symbol-input');
        if (symbolInput) {
            symbolInput.value = '';
            symbolInput.focus();
        }
        
        // Scroll to status area to ensure visibility
        statusElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    updateLastSaved() {
        const lastSavedElement = document.getElementById('last-saved');
        const now = new Date();
        lastSavedElement.textContent = `最終保存: ${now.toLocaleString('ja-JP')}`;
    }
    
    // Scheduler Management Methods
    async loadSchedulerStatus() {
        try {
            const response = await fetch('/api/scheduler/status');
            if (response.ok) {
                const status = await response.json();
                this.updateSchedulerDisplay(status);
                
                // Load tasks
                const tasksResponse = await fetch('/api/scheduler/tasks');
                if (tasksResponse.ok) {
                    const tasks = await tasksResponse.json();
                    this.displayScheduledTasks(tasks);
                }
            }
        } catch (error) {
            console.error('Scheduler status load error:', error);
            this.showStatus('スケジューラー状況の読み込みに失敗しました', 'error');
        }
    }
    
    updateSchedulerDisplay(status) {
        // Status badge
        const statusElement = document.getElementById('scheduler-status');
        if (status.running) {
            statusElement.innerHTML = '<span class="badge bg-success">実行中</span>';
        } else {
            statusElement.innerHTML = '<span class="badge bg-secondary">停止中</span>';
        }
        
        // Statistics
        document.getElementById('scheduler-total-tasks').textContent = status.total_tasks || 0;
        document.getElementById('scheduler-enabled-tasks').textContent = status.enabled_tasks || 0;
        document.getElementById('scheduler-next-execution').textContent = 
            status.next_execution ? new Date(status.next_execution).toLocaleString('ja-JP') : '-';
        
        // Button states
        document.getElementById('btn-start-scheduler').disabled = status.running;
        document.getElementById('btn-stop-scheduler').disabled = !status.running;
    }
    
    displayScheduledTasks(tasks) {
        const container = document.getElementById('scheduled-tasks-list');
        const emptyState = document.getElementById('scheduler-empty-state');
        
        if (!tasks || tasks.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        container.innerHTML = '';
        
        tasks.forEach(task => {
            const taskElement = this.createTaskElement(task);
            container.appendChild(taskElement);
        });
    }
    
    createTaskElement(task) {
        const div = document.createElement('div');
        div.className = 'task-item d-flex justify-content-between align-items-center mb-2 p-3 border rounded';
        
        const typeLabels = {
            'SCHEDULED_BACKTEST': 'バックテスト',
            'SCHEDULED_TRAINING': 'ML学習',
            'MONTHLY_OPTIMIZATION': '戦略最適化'
        };
        
        const frequencyLabels = {
            'hourly': '1時間毎',
            '4hourly': '4時間毎',
            'daily': '日次',
            'weekly': '週次',
            'monthly': '月次'
        };
        
        div.innerHTML = `
            <div class="task-info">
                <div class="task-title">
                    <strong>${task.symbol || (task.symbols ? task.symbols.join(', ') : 'All')}</strong>
                    <span class="badge bg-info ms-2">${typeLabels[task.type] || task.type}</span>
                    <span class="badge bg-secondary ms-1">${frequencyLabels[task.frequency] || task.frequency}</span>
                </div>
                <div class="task-details text-muted small">
                    ID: ${task.task_id}
                    ${task.last_executed ? `| 前回実行: ${new Date(task.last_executed).toLocaleString('ja-JP')}` : ''}
                    ${task.consecutive_failures > 0 ? `| 連続失敗: ${task.consecutive_failures}回` : ''}
                </div>
            </div>
            <div class="task-actions">
                <div class="form-check form-switch">
                    <input class="form-check-input task-toggle" type="checkbox" 
                           ${task.enabled ? 'checked' : ''} 
                           data-task-id="${task.task_id}">
                    <label class="form-check-label text-muted small">
                        ${task.enabled ? '有効' : '無効'}
                    </label>
                </div>
            </div>
        `;
        
        // Add toggle event listener
        const toggle = div.querySelector('.task-toggle');
        toggle.addEventListener('change', () => this.toggleTask(task.task_id, toggle.checked));
        
        return div;
    }
    
    async startScheduler() {
        try {
            this.showStatus('スケジューラーを開始しています...', 'info');
            
            const response = await fetch('/api/scheduler/start', {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showStatus(result.message, 'success');
                await this.loadSchedulerStatus();
            } else {
                const error = await response.json();
                this.showStatus(`スケジューラー開始エラー: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Scheduler start error:', error);
            this.showStatus('スケジューラーの開始に失敗しました', 'error');
        }
    }
    
    async stopScheduler() {
        if (!confirm('スケジューラーを停止しますか？実行中のタスクがある場合は完了まで待機します。')) {
            return;
        }
        
        try {
            this.showStatus('スケジューラーを停止しています...', 'info');
            
            const response = await fetch('/api/scheduler/stop', {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showStatus(result.message, 'success');
                await this.loadSchedulerStatus();
            } else {
                const error = await response.json();
                this.showStatus(`スケジューラー停止エラー: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Scheduler stop error:', error);
            this.showStatus('スケジューラーの停止に失敗しました', 'error');
        }
    }
    
    async toggleTask(taskId, enabled) {
        try {
            const response = await fetch(`/api/scheduler/task/${taskId}/toggle`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.showStatus(`タスク ${taskId} を${enabled ? '有効' : '無効'}にしました`, 'success');
                await this.loadSchedulerStatus();
            } else {
                const error = await response.json();
                this.showStatus(`タスク切り替えエラー: ${error.error}`, 'error');
                // Revert toggle state
                await this.loadSchedulerStatus();
            }
        } catch (error) {
            console.error('Task toggle error:', error);
            this.showStatus('タスクの切り替えに失敗しました', 'error');
            // Revert toggle state
            await this.loadSchedulerStatus();
        }
    }
    

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
});