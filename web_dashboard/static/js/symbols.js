// Symbol Management JavaScript

class SymbolManager {
    constructor() {
        this.symbols = [];
        this.executions = new Map();
        this.updateInterval = null;
        this.init();
    }

    init() {
        // Initialize event listeners
        document.getElementById('btn-add-symbol').addEventListener('click', () => this.addSymbol());
        document.getElementById('new-symbol-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addSymbol();
        });
        document.getElementById('btn-refresh-symbols').addEventListener('click', () => this.loadSymbols());
        
        // Popular symbol tags
        document.querySelectorAll('.popular-symbol-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                document.getElementById('new-symbol-input').value = e.target.dataset.symbol;
                document.getElementById('new-symbol-input').focus();
            });
        });
        
        // Load initial data
        this.loadSymbols();
        this.loadExecutions();
        
        // Start periodic updates
        this.startPeriodicUpdates();
    }

    async addSymbol() {
        const input = document.getElementById('new-symbol-input');
        const symbol = input.value.trim().toUpperCase();
        
        if (!symbol) {
            this.showMessage('銘柄名を入力してください', 'warning');
            return;
        }
        
        // Basic validation
        if (!symbol.match(/^[A-Z0-9]{2,10}$/)) {
            this.showMessage('銘柄名は2-10文字の英数字で入力してください', 'error');
            return;
        }
        
        // Disable button during processing
        const addButton = document.getElementById('btn-add-symbol');
        addButton.disabled = true;
        addButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 処理中...';
        
        try {
            const response = await fetch('/api/symbol/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showMessage(`${symbol} の分析を開始しました`, 'success');
                input.value = '';
                
                // Add to executions
                if (data.execution_id) {
                    this.executions.set(data.execution_id, {
                        symbol: data.symbol,
                        status: 'started',
                        startTime: new Date()
                    });
                    this.updateExecutionsDisplay();
                }
                
                // Show warnings if any
                if (data.warnings && data.warnings.length > 0) {
                    const warningHtml = data.warnings.map(w => 
                        `<div class="validation-warning"><i class="fas fa-exclamation-triangle"></i> ${w}</div>`
                    ).join('');
                    
                    // Add warning to message area
                    const messageArea = document.getElementById('message-area');
                    const warningDiv = document.createElement('div');
                    warningDiv.innerHTML = warningHtml;
                    messageArea.appendChild(warningDiv);
                }
                
                // Refresh executions list
                this.loadExecutions();
                
            } else {
                this.showMessage(data.error || '銘柄の追加に失敗しました', 'error');
                
                // Show validation status if available
                if (data.validation_status) {
                    this.showMessage(`バリデーション状態: ${data.validation_status}`, 'warning');
                }
                
                if (data.suggestion) {
                    this.showMessage(data.suggestion, 'info');
                }
            }
        } catch (error) {
            console.error('Error adding symbol:', error);
            this.showMessage('銘柄の追加中にエラーが発生しました', 'error');
        } finally {
            // Re-enable button
            addButton.disabled = false;
            addButton.innerHTML = '<i class="fas fa-search"></i> 分析開始';
        }
    }

    async loadSymbols() {
        const loadingDiv = document.getElementById('symbols-loading');
        const gridDiv = document.getElementById('symbols-grid');
        const emptyDiv = document.getElementById('symbols-empty');
        
        loadingDiv.style.display = 'block';
        gridDiv.style.display = 'none';
        emptyDiv.style.display = 'none';
        
        try {
            const response = await fetch('/api/strategy-results/symbols-with-progress');
            const symbols = await response.json();
            
            this.symbols = symbols;
            
            if (symbols.length === 0) {
                emptyDiv.style.display = 'block';
            } else {
                this.renderSymbols(symbols);
                gridDiv.style.display = 'grid';
            }
        } catch (error) {
            console.error('Error loading symbols:', error);
            this.showMessage('銘柄情報の読み込みに失敗しました', 'error');
        } finally {
            loadingDiv.style.display = 'none';
        }
    }

    renderSymbols(symbols) {
        const gridDiv = document.getElementById('symbols-grid');
        gridDiv.innerHTML = '';
        
        symbols.forEach(symbol => {
            const card = this.createSymbolCard(symbol);
            gridDiv.appendChild(card);
        });
    }

    createSymbolCard(symbol) {
        const card = document.createElement('div');
        card.className = 'card symbol-card';
        
        // Status badge configuration
        const statusConfig = {
            'completed': { class: 'bg-success', text: '分析完了' },
            'nearly_complete': { class: 'bg-warning', text: '分析中 (ほぼ完了)' },
            'in_progress': { class: 'bg-info', text: '分析中' },
            'started': { class: 'bg-secondary', text: '開始済み' },
            'failed': { class: 'bg-danger', text: '分析失敗' },
            'stalled': { class: 'bg-warning text-dark', text: '分析停止' }
        };
        
        const config = statusConfig[symbol.status] || statusConfig['started'];
        
        card.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <h4 class="card-title mb-0">${symbol.symbol}</h4>
                    <span class="badge ${config.class} symbol-status-badge">${config.text}</span>
                </div>
                
                <div class="symbol-stats">
                    <div class="d-flex justify-content-between mb-2">
                        <span class="text-muted">進捗:</span>
                        <span class="fw-bold">${symbol.completed_patterns}/${symbol.total_patterns} (${symbol.completion_rate}%)</span>
                    </div>
                    
                    <!-- Progress bar -->
                    <div class="progress mb-3" style="height: 8px;">
                        <div class="progress-bar ${symbol.status === 'completed' ? 'bg-success' : 'bg-info'}" 
                             style="width: ${symbol.completion_rate}%"></div>
                    </div>
                    
                    ${symbol.avg_sharpe !== undefined ? `
                    <div class="d-flex justify-content-between mb-2">
                        <span class="text-muted">平均シャープレシオ:</span>
                        <span class="fw-bold ${symbol.avg_sharpe > 0 ? 'text-success' : 'text-danger'}">
                            ${symbol.avg_sharpe.toFixed(2)}
                        </span>
                    </div>
                    ` : ''}
                    
                    <!-- Failure/Stall Information -->
                    ${symbol.status === 'failed' && symbol.failure_reason ? `
                    <div class="alert alert-danger p-2 mb-2">
                        <small><i class="fas fa-exclamation-triangle"></i> ${symbol.failure_reason}</small>
                    </div>
                    ` : ''}
                    
                    ${symbol.status === 'stalled' && symbol.time_stalled_hours ? `
                    <div class="alert alert-warning p-2 mb-2">
                        <small><i class="fas fa-clock"></i> ${symbol.time_stalled_hours}時間停止中</small>
                    </div>
                    ` : ''}
                </div>
                
                <div class="mt-3">
                    ${symbol.status === 'completed' ? `
                        <button class="btn btn-sm btn-outline-primary w-100" onclick="symbolManager.viewDetails('${symbol.symbol}')">
                            <i class="fas fa-info-circle"></i> 詳細を見る
                        </button>
                    ` : symbol.status === 'failed' ? `
                        <button class="btn btn-sm btn-outline-danger w-100" onclick="symbolManager.retryAnalysis('${symbol.symbol}')">
                            <i class="fas fa-redo"></i> 再実行
                        </button>
                    ` : symbol.status === 'stalled' ? `
                        <div class="btn-group w-100" role="group">
                            <button class="btn btn-sm btn-outline-warning" onclick="symbolManager.retryAnalysis('${symbol.symbol}')">
                                <i class="fas fa-redo"></i> 再実行
                            </button>
                            <button class="btn btn-sm btn-outline-info" onclick="symbolManager.viewExecutionLog('${symbol.execution_id}')">
                                <i class="fas fa-list"></i> ログ
                            </button>
                        </div>
                    ` : `
                        <button class="btn btn-sm btn-outline-secondary w-100" disabled>
                            <i class="fas fa-clock"></i> 分析中...
                        </button>
                    `}
                </div>
            </div>
        `;
        
        return card;
    }
    
    retryAnalysis(symbol) {
        if (confirm(`${symbol}の分析を再実行しますか？\n\n未完了のパターンのみを実行します。`)) {
            this.addSymbolForRetry(symbol);
        }
    }
    
    async addSymbolForRetry(symbol) {
        try {
            this.showMessage(`${symbol}の分析を再開しています...`, 'info');
            
            const response = await fetch('/api/symbol/retry', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    symbol: symbol,
                    retry_incomplete: true
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showMessage(`${symbol}の分析を再開しました (実行ID: ${result.execution_id})`, 'success');
                
                // Refresh symbols list
                setTimeout(() => this.loadSymbols(), 2000);
            } else {
                const error = await response.json();
                this.showMessage(`再実行エラー: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Retry error:', error);
            this.showMessage('再実行に失敗しました', 'error');
        }
    }
    
    viewExecutionLog(executionId) {
        // Open execution logs page with specific execution ID
        window.open(`/execution-logs?execution_id=${executionId}`, '_blank');
    }

    async viewDetails(symbol) {
        const modal = new bootstrap.Modal(document.getElementById('symbolDetailsModal'));
        document.getElementById('modal-symbol-name').textContent = symbol;
        document.getElementById('btn-view-strategy-results').href = `/strategy-results?symbol=${symbol}`;
        
        const contentDiv = document.getElementById('modal-symbol-content');
        contentDiv.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> 読み込み中...</div>';
        
        modal.show();
        
        try {
            const response = await fetch(`/api/strategy-results/${symbol}`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                // Find best strategy
                const bestStrategy = data.results.reduce((best, current) => 
                    current.sharpe_ratio > best.sharpe_ratio ? current : best
                );
                
                contentDiv.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <h6>分析サマリー</h6>
                            <ul class="list-unstyled">
                                <li><strong>総パターン数:</strong> ${data.total_patterns}</li>
                                <li><strong>分析時間足:</strong> 1h, 4h</li>
                                <li><strong>最終更新:</strong> ${new Date(data.results[0].generated_at).toLocaleString('ja-JP')}</li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6>最良戦略</h6>
                            <ul class="list-unstyled">
                                <li><strong>設定:</strong> ${bestStrategy.config}</li>
                                <li><strong>時間足:</strong> ${bestStrategy.timeframe}</li>
                                <li><strong>シャープレシオ:</strong> ${bestStrategy.sharpe_ratio.toFixed(2)}</li>
                                <li><strong>勝率:</strong> ${(bestStrategy.win_rate * 100).toFixed(1)}%</li>
                            </ul>
                        </div>
                    </div>
                    
                    <hr>
                    
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i> 
                        より詳細な分析結果は「戦略結果を見る」ボタンから確認できます
                    </div>
                `;
            } else {
                contentDiv.innerHTML = '<div class="alert alert-warning">詳細データが見つかりませんでした</div>';
            }
        } catch (error) {
            console.error('Error loading symbol details:', error);
            contentDiv.innerHTML = '<div class="alert alert-danger">詳細の読み込みに失敗しました</div>';
        }
    }

    async loadExecutions() {
        try {
            const response = await fetch('/api/executions?limit=10');
            const executions = await response.json();
            
            // Filter for active executions
            const activeExecutions = executions.filter(e => 
                e.status === 'running' || e.status === 'training' || e.status === 'backtesting'
            );
            
            if (activeExecutions.length > 0) {
                activeExecutions.forEach(exec => {
                    this.executions.set(exec.execution_id, exec);
                });
                this.updateExecutionsDisplay();
            }
        } catch (error) {
            console.error('Error loading executions:', error);
        }
    }

    updateExecutionsDisplay() {
        const container = document.getElementById('active-executions');
        const list = document.getElementById('executions-list');
        
        if (this.executions.size === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        list.innerHTML = '';
        
        this.executions.forEach((exec, id) => {
            const item = document.createElement('div');
            item.className = 'execution-item';
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${exec.symbol}</h6>
                        <small class="text-muted">実行ID: ${id.substring(0, 16)}...</small>
                    </div>
                    <span class="badge bg-${this.getStatusColor(exec.status)}">${this.getStatusText(exec.status)}</span>
                </div>
                <div class="progress mt-2" style="height: 20px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" 
                         style="width: ${exec.progress || 0}%">
                        ${exec.progress || 0}%
                    </div>
                </div>
                ${exec.current_task ? `<small class="text-muted mt-1 d-block">${exec.current_task}</small>` : ''}
            `;
            list.appendChild(item);
        });
    }

    async updateExecutionStatus(executionId) {
        try {
            const response = await fetch(`/api/execution/${executionId}/status`);
            const status = await response.json();
            
            if (response.ok && status) {
                this.executions.set(executionId, status);
                
                // Remove completed executions
                if (status.status === 'completed' || status.status === 'failed') {
                    setTimeout(() => {
                        this.executions.delete(executionId);
                        this.updateExecutionsDisplay();
                        
                        // Reload symbols if completed
                        if (status.status === 'completed') {
                            this.loadSymbols();
                        }
                    }, 3000);
                }
                
                this.updateExecutionsDisplay();
            }
        } catch (error) {
            console.error('Error updating execution status:', error);
        }
    }

    getStatusColor(status) {
        const colors = {
            'running': 'primary',
            'training': 'info',
            'backtesting': 'warning',
            'completed': 'success',
            'failed': 'danger'
        };
        return colors[status] || 'secondary';
    }

    getStatusText(status) {
        const texts = {
            'running': '実行中',
            'training': '学習中',
            'backtesting': 'バックテスト中',
            'completed': '完了',
            'failed': '失敗'
        };
        return texts[status] || status;
    }

    startPeriodicUpdates() {
        // Update execution statuses every 5 seconds
        this.updateInterval = setInterval(() => {
            this.executions.forEach((exec, id) => {
                if (exec.status !== 'completed' && exec.status !== 'failed') {
                    this.updateExecutionStatus(id);
                }
            });
        }, 5000);
    }

    showMessage(message, type = 'info') {
        const messageArea = document.getElementById('message-area');
        const alertClass = {
            'info': 'alert-info',
            'success': 'alert-success',
            'warning': 'alert-warning',
            'error': 'alert-danger'
        }[type] || 'alert-info';
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        messageArea.appendChild(alertDiv);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 10000);
    }
}

// Initialize when DOM is ready
let symbolManager;
document.addEventListener('DOMContentLoaded', () => {
    symbolManager = new SymbolManager();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (symbolManager && symbolManager.updateInterval) {
        clearInterval(symbolManager.updateInterval);
    }
});

// Exchange switching functions
async function loadCurrentExchange() {
    try {
        const response = await fetch('/api/exchange/current');
        const data = await response.json();
        
        if (data.current_exchange) {
            const exchangeElement = document.getElementById('current-exchange');
            if (exchangeElement) {
                exchangeElement.textContent = data.current_exchange === 'hyperliquid' ? 'Hyperliquid' : 'Gate.io';
            }
        }
    } catch (error) {
        console.error('Error loading current exchange:', error);
    }
}

async function switchExchange(exchange) {
    try {
        const response = await fetch('/api/exchange/switch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ exchange: exchange })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Update UI
            const exchangeElement = document.getElementById('current-exchange');
            if (exchangeElement) {
                exchangeElement.textContent = exchange === 'hyperliquid' ? 'Hyperliquid' : 'Gate.io';
            }
            
            // Show success notification
            if (symbolManager) {
                symbolManager.showMessage(data.message, 'success');
            }
            
            // Refresh the page after a short delay to ensure all systems use new exchange
            setTimeout(() => {
                window.location.reload();
            }, 1500);
            
        } else {
            if (symbolManager) {
                symbolManager.showMessage(data.error || 'Failed to switch exchange', 'error');
            }
        }
    } catch (error) {
        console.error('Error switching exchange:', error);
        if (symbolManager) {
            symbolManager.showMessage('Error switching exchange', 'error');
        }
    }
}

// Load current exchange on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentExchange();
});