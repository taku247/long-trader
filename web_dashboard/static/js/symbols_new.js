/**
 * 統合進捗表示 - 銘柄管理システム
 * タブ切り替え + 進捗バー + 詳細進捗の統合表示
 */

class SymbolProgressManager {
    constructor() {
        this.updateInterval = 20000; // 20秒
        this.currentTab = 'running';
        this.symbolsData = {
            running: [],
            completed: [],
            pending: [],
            failed: []
        };
        this.updateTimer = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
        this.startAutoUpdate();
    }
    
    bindEvents() {
        // タブ切り替え
        document.querySelectorAll('.symbol-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });
        
        // 銘柄追加
        document.getElementById('btn-add-symbol').addEventListener('click', () => {
            this.addSymbol();
        });
        
        // Enter キーでの銘柄追加
        document.getElementById('new-symbol-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.addSymbol();
            }
        });
        
        // 人気銘柄クリック
        document.querySelectorAll('.popular-symbol-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                const symbol = e.target.getAttribute('data-symbol');
                document.getElementById('new-symbol-input').value = symbol;
            });
        });
        
        // 取引所切り替え
        window.switchExchange = (exchange) => {
            this.switchExchange(exchange);
        };
        
        // 管理機能: ゾンビプロセスクリーンアップ
        document.getElementById('btn-cleanup-zombies').addEventListener('click', () => {
            this.cleanupZombieProcesses();
        });
        
        // 管理機能: 手動リセット
        const selectRunning = document.getElementById('select-running-symbol');
        const btnReset = document.getElementById('btn-manual-reset');
        
        selectRunning.addEventListener('change', (e) => {
            btnReset.disabled = !e.target.value;
        });
        
        btnReset.addEventListener('click', () => {
            const executionId = selectRunning.value;
            if (executionId) {
                this.manualResetExecution(executionId);
            }
        });
    }
    
    switchTab(tabName) {
        // タブボタンの状態更新
        document.querySelectorAll('.symbol-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // タブコンテンツの表示切り替え
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        this.currentTab = tabName;
    }
    
    async addSymbol() {
        const symbolInput = document.getElementById('new-symbol-input');
        const symbol = symbolInput.value.trim().toUpperCase();
        
        if (!symbol) {
            this.showMessage('銘柄名を入力してください', 'warning');
            return;
        }
        
        // 既存チェック
        const allSymbols = [
            ...this.symbolsData.running,
            ...this.symbolsData.completed,
            ...this.symbolsData.pending,
            ...this.symbolsData.failed
        ];
        
        if (allSymbols.some(s => s.symbol === symbol)) {
            this.showMessage(`${symbol} は既に追加されています`, 'warning');
            return;
        }
        
        try {
            this.showMessage(`${symbol} の分析を開始しています...`, 'info');
            
            const response = await fetch('/api/symbol/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ symbol: symbol })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showMessage(`${symbol} の分析が開始されました`, 'success');
                symbolInput.value = '';
                
                // 即座に進捗を更新
                setTimeout(() => {
                    this.updateSymbolsData();
                }, 2000);
                
                // 実行中タブに切り替え
                this.switchTab('running');
            } else {
                this.showMessage(`エラー: ${result.error || '不明なエラー'}`, 'danger');
            }
        } catch (error) {
            this.showMessage(`ネットワークエラー: ${error.message}`, 'danger');
        }
    }
    
    async loadInitialData() {
        try {
            await this.updateSymbolsData();
        } catch (error) {
            console.error('初期データ読み込みエラー:', error);
            this.showMessage('初期データの読み込みに失敗しました', 'danger');
        }
    }
    
    async updateSymbolsData() {
        try {
            const response = await fetch('/api/symbols/status');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.symbolsData = data;
            
            this.updateTabCounts();
            this.renderSymbols();
            this.updateLastUpdated();
            this.updateRunningSymbolSelect();  // 実行中銘柄のセレクトボックスを更新
            
        } catch (error) {
            console.error('データ更新エラー:', error);
            // エラー時も最終更新時刻は更新（接続状況を示すため）
            this.updateLastUpdated(true);
        }
    }
    
    updateTabCounts() {
        const counts = {
            running: this.symbolsData.running.length,
            completed: this.symbolsData.completed.length,
            pending: this.symbolsData.pending.length,
            failed: this.symbolsData.failed.length
        };
        
        Object.keys(counts).forEach(tab => {
            const badge = document.getElementById(`${tab}-count`);
            if (badge) {
                badge.textContent = counts[tab];
            }
        });
    }
    
    renderSymbols() {
        Object.keys(this.symbolsData).forEach(status => {
            const container = document.getElementById(`${status}-symbols`);
            if (!container) return;
            
            const symbols = this.symbolsData[status];
            
            if (symbols.length === 0) {
                container.innerHTML = this.getEmptyStateHTML(status);
            } else {
                container.innerHTML = symbols.map(symbol => 
                    this.renderSymbolCard(symbol, status)
                ).join('');
            }
        });
    }
    
    renderSymbolCard(symbol, status) {
        const progressPercent = symbol.overall_progress || 0;
        const elapsedTime = this.formatDuration(symbol.elapsed_time || 0);
        const estimatedRemaining = symbol.estimated_remaining ? 
            this.formatDuration(symbol.estimated_remaining) : '不明';
        
        let statusIcon = '';
        switch (status) {
            case 'running':
                statusIcon = '🔄';
                break;
            case 'completed':
                statusIcon = '✅';
                break;
            case 'pending':
                statusIcon = '⏳';
                break;
            case 'failed':
                statusIcon = '❌';
                break;
        }
        
        return `
            <div class="symbol-status-card ${status}">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h5 class="mb-0">
                        ${statusIcon} ${symbol.symbol}
                        <small class="text-muted ms-2">${symbol.current_phase || ''}</small>
                    </h5>
                    <span class="badge bg-primary">${progressPercent}%</span>
                </div>
                
                <!-- Progress Bar -->
                <div class="symbol-progress-bar mb-3">
                    <div class="symbol-progress-fill ${status}" 
                         style="width: ${progressPercent}%"></div>
                </div>
                
                ${status === 'running' ? this.renderDetailedProgress(symbol) : ''}
                ${status === 'completed' ? this.renderCompletedInfo(symbol) : ''}
                
                <div class="time-info">
                    ${status === 'running' ? 
                        `📊 経過時間: ${elapsedTime} | 予測残り: ${estimatedRemaining}` :
                        status === 'completed' ?
                        `📊 完了時間: ${elapsedTime}` :
                        `📊 待機中...`
                    }
                </div>
            </div>
        `;
    }
    
    renderDetailedProgress(symbol) {
        if (!symbol.phase_progress) return '';
        
        const phases = symbol.phase_progress;
        let html = '<div class="mt-2">';
        
        // データ取得フェーズ
        if (phases.data_fetch) {
            const phase = phases.data_fetch;
            html += `
                <div class="strategy-group">
                    <small><strong>📥 データ取得:</strong> 
                    ${phase.status === 'completed' ? 
                        `✅ 完了 (${phase.duration || 0}s)` : 
                        '🔄 実行中...'
                    }</small>
                </div>
            `;
        }
        
        // 戦略群別進捗
        const strategyGroups = [
            { key: '1h_strategies', name: '1h足戦略群' },
            { key: '30m_strategies', name: '30m足戦略群' },
            { key: '15m_strategies', name: '15m足戦略群' },
            { key: '5m_strategies', name: '5m足戦略群' },
            { key: '3m_strategies', name: '3m足戦略群' },
            { key: '1m_strategies', name: '短期足戦略群' }
        ];
        
        strategyGroups.forEach(group => {
            if (phases[group.key]) {
                const phase = phases[group.key];
                const completed = phase.completed || 0;
                const total = phase.total || 3;
                const progress = phase.progress || 0;
                
                html += `
                    <div class="strategy-group">
                        <div class="d-flex justify-content-between align-items-center">
                            <small><strong>├─ ${group.name}:</strong></small>
                            <small>[${completed}/${total}完了] ${progress}%</small>
                        </div>
                        <div class="strategy-icons mt-1">
                            ${this.renderStrategyIcons(completed, total)}
                        </div>
                    </div>
                `;
            }
        });
        
        html += '</div>';
        return html;
    }
    
    renderStrategyIcons(completed, total) {
        let icons = '';
        for (let i = 0; i < total; i++) {
            if (i < completed) {
                icons += '<span class="strategy-icon completed" title="完了"></span>';
            } else if (i === completed) {
                icons += '<span class="strategy-icon running" title="実行中"></span>';
            } else {
                icons += '<span class="strategy-icon pending" title="待機中"></span>';
            }
        }
        return icons;
    }
    
    renderCompletedInfo(symbol) {
        if (!symbol.best_strategy) return '';
        
        const strategy = symbol.best_strategy;
        return `
            <div class="mt-2">
                <div class="strategy-group">
                    <small><strong>🏆 最高成績:</strong> Sharpe ${(strategy.sharpe_ratio || 0).toFixed(2)}</small>
                    <br>
                    <small><strong>📊 推奨レバレッジ:</strong> ${(strategy.recommended_leverage || 0).toFixed(1)}x</small>
                    <br>
                    <small><strong>💰 最大収益率:</strong> ${(strategy.max_return || 0) >= 0 ? '+' : ''}${(strategy.max_return || 0).toFixed(1)}%</small>
                </div>
            </div>
        `;
    }
    
    getEmptyStateHTML(status) {
        const messages = {
            running: { icon: 'fas fa-cogs', text: '現在実行中の銘柄はありません' },
            completed: { icon: 'fas fa-check-circle', text: '完了した銘柄はまだありません' },
            pending: { icon: 'fas fa-clock', text: '待機中の銘柄はありません' },
            failed: { icon: 'fas fa-exclamation-triangle', text: '失敗した銘柄はありません' }
        };
        
        const msg = messages[status];
        return `
            <div class="empty-state">
                <i class="${msg.icon}"></i>
                <p>${msg.text}</p>
            </div>
        `;
    }
    
    formatDuration(seconds) {
        if (!seconds || seconds < 0) return '0秒';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}時間${minutes}分`;
        } else if (minutes > 0) {
            return `${minutes}分${secs}秒`;
        } else {
            return `${secs}秒`;
        }
    }
    
    updateLastUpdated(isError = false) {
        const now = new Date();
        const timeString = now.toTimeString().slice(0, 8);
        const element = document.getElementById('last-updated');
        
        if (element) {
            if (isError) {
                element.textContent = `最終更新: ${timeString} (エラー)`;
                element.style.color = '#dc3545';
            } else {
                element.textContent = `最終更新: ${timeString}`;
                element.style.color = '';
            }
        }
    }
    
    startAutoUpdate() {
        // 初回更新の遅延を設定
        setTimeout(() => {
            this.updateSymbolsData();
        }, 2000);
        
        // 定期更新を開始
        this.updateTimer = setInterval(() => {
            this.updateSymbolsData();
        }, this.updateInterval);
    }
    
    stopAutoUpdate() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
    
    showMessage(message, type = 'info') {
        const messageArea = document.getElementById('message-area');
        if (!messageArea) return;
        
        const alertClass = `alert-${type}`;
        const iconClass = {
            'success': 'fas fa-check-circle',
            'danger': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        }[type] || 'fas fa-info-circle';
        
        messageArea.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="${iconClass} me-2"></i>${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // 5秒後に自動で消す
        setTimeout(() => {
            const alert = messageArea.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }
    
    switchExchange(exchange) {
        const exchangeLabel = exchange === 'hyperliquid' ? 'Hyperliquid' : 'Gate.io';
        document.getElementById('current-exchange').textContent = exchangeLabel;
        
        // 取引所切り替えAPI呼び出し（必要に応じて実装）
        this.showMessage(`取引所を${exchangeLabel}に切り替えました`, 'success');
    }
    
    destroy() {
        this.stopAutoUpdate();
    }
    
    // 管理機能: 実行中銘柄のセレクトボックスを更新
    updateRunningSymbolSelect() {
        const select = document.getElementById('select-running-symbol');
        if (!select) return;
        
        const currentValue = select.value;
        select.innerHTML = '<option value="">実行中の銘柄を選択...</option>';
        
        this.symbolsData.running.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol.execution_id;
            option.textContent = `${symbol.symbol} (${symbol.overall_progress}% - ${symbol.execution_id.substring(0, 20)}...)`;
            select.appendChild(option);
        });
        
        // 以前の選択を復元
        if (currentValue && Array.from(select.options).some(opt => opt.value === currentValue)) {
            select.value = currentValue;
        }
    }
    
    // 管理機能: ゾンビプロセスクリーンアップ
    async cleanupZombieProcesses() {
        if (!confirm('12時間以上停滞している実行を失敗扱いにします。\n続行しますか？')) {
            return;
        }
        
        try {
            const response = await fetch('/api/admin/cleanup-zombies', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showMessage(`✅ ${result.cleaned_count}件のゾンビプロセスをクリーンアップしました`, 'success');
                // データを更新
                await this.updateSymbolsData();
            } else {
                this.showMessage(`エラー: ${result.error || '不明なエラー'}`, 'danger');
            }
        } catch (error) {
            this.showMessage(`ネットワークエラー: ${error.message}`, 'danger');
        }
    }
    
    // 管理機能: 手動リセット
    async manualResetExecution(executionId) {
        const symbol = this.symbolsData.running.find(s => s.execution_id === executionId);
        if (!symbol) {
            this.showMessage('選択した実行が見つかりません', 'warning');
            return;
        }
        
        if (!confirm(`${symbol.symbol}の実行を停止します。\n続行しますか？`)) {
            return;
        }
        
        try {
            const response = await fetch('/api/admin/reset-execution', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ execution_id: executionId })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showMessage(`✅ ${symbol.symbol}の実行を停止しました`, 'success');
                // セレクトボックスをリセット
                document.getElementById('select-running-symbol').value = '';
                document.getElementById('btn-manual-reset').disabled = true;
                // データを更新
                await this.updateSymbolsData();
            } else {
                this.showMessage(`エラー: ${result.error || '不明なエラー'}`, 'danger');
            }
        } catch (error) {
            this.showMessage(`ネットワークエラー: ${error.message}`, 'danger');
        }
    }
}

// グローバルインスタンス
let symbolProgressManager;

// ページ読み込み時に初期化
document.addEventListener('DOMContentLoaded', function() {
    symbolProgressManager = new SymbolProgressManager();
});

// ページを離れる時にタイマーをクリア
window.addEventListener('beforeunload', function() {
    if (symbolProgressManager) {
        symbolProgressManager.destroy();
    }
});