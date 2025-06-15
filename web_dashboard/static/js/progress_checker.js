/**
 * 銘柄分析進捗チェッカー
 * ブラウザからボタンひとつで分析進捗を確認
 */

class ProgressChecker {
    constructor() {
        this.pollingInterval = 5000; // 5秒間隔
        this.isPolling = false;
        this.currentSymbol = null;
    }

    /**
     * 進捗チェックUIを初期化
     */
    initializeUI() {
        // 進捗チェックボタンを各銘柄行に追加
        this.addProgressButtons();
        
        // リアルタイム進捗モニターを初期化
        this.initializeProgressMonitor();
    }

    /**
     * 進捗チェックボタンを追加
     */
    addProgressButtons() {
        const symbolRows = document.querySelectorAll('.symbol-row');
        symbolRows.forEach(row => {
            const symbol = row.dataset.symbol;
            
            // 進捗チェックボタンを作成
            const progressBtn = document.createElement('button');
            progressBtn.className = 'btn btn-info btn-sm ms-2';
            progressBtn.innerHTML = '<i class="fas fa-chart-line"></i> 進捗確認';
            progressBtn.onclick = () => this.checkProgress(symbol);
            
            // ボタンを行に追加
            const actionCol = row.querySelector('.action-column');
            if (actionCol) {
                actionCol.appendChild(progressBtn);
            }
        });
    }

    /**
     * 特定銘柄の進捗をチェック
     */
    async checkProgress(symbol) {
        try {
            console.log(`📊 ${symbol}の進捗をチェック中...`);
            
            // 進捗データを取得
            const progressData = await this.fetchProgressData(symbol);
            
            // 進捗モーダルを表示
            this.showProgressModal(symbol, progressData);
            
        } catch (error) {
            console.error('進捗チェックエラー:', error);
            this.showErrorAlert('進捗データの取得に失敗しました');
        }
    }

    /**
     * 進捗データを取得
     */
    async fetchProgressData(symbol) {
        try {
            // 複数のAPIを並列で呼び出し
            const [progressResponse, executionResponse] = await Promise.all([
                fetch(`/api/strategy-results/symbols-with-progress`),
                fetch(`/api/executions?symbol=${symbol}&limit=5`)
            ]);

            const allProgress = await progressResponse.json();
            const executions = await executionResponse.json();

            // 指定銘柄のデータを抽出
            const symbolProgress = allProgress.find(item => item.symbol === symbol);
            
            if (!symbolProgress) {
                throw new Error(`${symbol}の進捗データが見つかりません`);
            }

            return {
                symbol: symbol,
                progress: symbolProgress,
                executions: executions,
                timestamp: new Date().toISOString()
            };

        } catch (error) {
            console.error('API呼び出しエラー:', error);
            throw error;
        }
    }

    /**
     * 進捗モーダルを表示
     */
    showProgressModal(symbol, data) {
        const { progress, executions } = data;
        
        // モーダルHTML作成
        const modalHtml = `
            <div class="modal fade" id="progressModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-chart-line"></i> ${symbol} 分析進捗
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${this.generateProgressContent(symbol, progress, executions)}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">閉じる</button>
                            <button type="button" class="btn btn-primary" onclick="progressChecker.startRealtimeMonitoring('${symbol}')">
                                <i class="fas fa-sync-alt"></i> リアルタイム監視開始
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 既存のモーダルを削除してから新しいモーダルを追加
        const existingModal = document.getElementById('progressModal');
        if (existingModal) {
            existingModal.remove();
        }

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // モーダルを表示
        const modal = new bootstrap.Modal(document.getElementById('progressModal'));
        modal.show();
    }

    /**
     * 進捗コンテンツを生成
     */
    generateProgressContent(symbol, progress, executions) {
        const completionRate = progress.completion_rate || 0;
        const status = progress.status || 'unknown';
        const completedPatterns = progress.completed_patterns || 0;
        const totalPatterns = progress.total_patterns || 18;

        // ステータス色の決定
        const statusBadgeClass = this.getStatusBadgeClass(status);
        const progressBarClass = this.getProgressBarClass(completionRate);

        return `
            <div class="row">
                <!-- 基本情報 -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-info-circle"></i> 基本情報</h6>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <tr>
                                    <td><strong>銘柄:</strong></td>
                                    <td>${symbol}</td>
                                </tr>
                                <tr>
                                    <td><strong>ステータス:</strong></td>
                                    <td><span class="badge ${statusBadgeClass}">${status}</span></td>
                                </tr>
                                <tr>
                                    <td><strong>完了パターン:</strong></td>
                                    <td>${completedPatterns} / ${totalPatterns}</td>
                                </tr>
                                <tr>
                                    <td><strong>進捗率:</strong></td>
                                    <td>${completionRate}%</td>
                                </tr>
                                <tr>
                                    <td><strong>平均Sharpe比:</strong></td>
                                    <td>${progress.avg_sharpe || 'N/A'}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- 進捗バー -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-tasks"></i> 進捗状況</h6>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <div class="d-flex justify-content-between">
                                    <span>分析進捗</span>
                                    <span>${completionRate}%</span>
                                </div>
                                <div class="progress">
                                    <div class="progress-bar ${progressBarClass}" style="width: ${completionRate}%"></div>
                                </div>
                            </div>
                            
                            ${this.generatePatternBreakdown(completedPatterns, totalPatterns)}
                        </div>
                    </div>
                </div>
            </div>

            <!-- 戦略別進捗 -->
            <div class="row mt-3">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-layer-group"></i> 戦略別進捗</h6>
                        </div>
                        <div class="card-body">
                            ${this.generateStrategyBreakdown(symbol)}
                        </div>
                    </div>
                </div>
            </div>

            <!-- 実行履歴 -->
            <div class="row mt-3">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-history"></i> 最近の実行履歴</h6>
                        </div>
                        <div class="card-body">
                            ${this.generateExecutionHistory(executions)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * ステータスバッジクラスを取得
     */
    getStatusBadgeClass(status) {
        const statusClasses = {
            'completed': 'bg-success',
            'in_progress': 'bg-primary',
            'nearly_complete': 'bg-info',
            'started': 'bg-warning',
            'failed': 'bg-danger',
            'stalled': 'bg-warning'
        };
        return statusClasses[status] || 'bg-secondary';
    }

    /**
     * 進捗バークラスを取得
     */
    getProgressBarClass(completionRate) {
        if (completionRate >= 90) return 'bg-success';
        if (completionRate >= 70) return 'bg-info';
        if (completionRate >= 40) return 'bg-warning';
        return 'bg-danger';
    }

    /**
     * パターン内訳を生成
     */
    generatePatternBreakdown(completed, total) {
        const remaining = total - completed;
        
        return `
            <div class="row text-center">
                <div class="col-6">
                    <div class="text-success">
                        <i class="fas fa-check-circle fa-2x"></i>
                        <div><strong>${completed}</strong></div>
                        <div><small>完了</small></div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="text-muted">
                        <i class="fas fa-clock fa-2x"></i>
                        <div><strong>${remaining}</strong></div>
                        <div><small>残り</small></div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 戦略別進捗を生成
     */
    generateStrategyBreakdown(symbol) {
        // 戦略別の詳細進捗を表示
        // 実際のAPIからデータを取得する場合は、ここでfetchを行う
        return `
            <div class="row">
                <div class="col-md-4">
                    <div class="text-center">
                        <h6>Conservative_ML</h6>
                        <div class="progress mb-2">
                            <div class="progress-bar bg-info" style="width: 83%"></div>
                        </div>
                        <small>5/6 時間軸完了</small>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="text-center">
                        <h6>Aggressive_Traditional</h6>
                        <div class="progress mb-2">
                            <div class="progress-bar bg-warning" style="width: 67%"></div>
                        </div>
                        <small>4/6 時間軸完了</small>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="text-center">
                        <h6>Full_ML</h6>
                        <div class="progress mb-2">
                            <div class="progress-bar bg-success" style="width: 100%"></div>
                        </div>
                        <small>6/6 時間軸完了</small>
                    </div>
                </div>
            </div>
            
            <div class="mt-3">
                <small class="text-muted">
                    <i class="fas fa-info-circle"></i> 
                    各戦略は6つの時間軸(1m, 3m, 5m, 15m, 30m, 1h)で分析されます
                </small>
            </div>
        `;
    }

    /**
     * 実行履歴を生成
     */
    generateExecutionHistory(executions) {
        if (!executions || executions.length === 0) {
            return '<p class="text-muted">実行履歴がありません</p>';
        }

        const historyRows = executions.slice(0, 5).map(exec => {
            const statusBadge = this.getExecutionStatusBadge(exec.status);
            const startTime = exec.started_at ? new Date(exec.started_at).toLocaleString() : 'N/A';
            
            return `
                <tr>
                    <td>${exec.execution_id?.substring(0, 20)}...</td>
                    <td>${statusBadge}</td>
                    <td>${startTime}</td>
                    <td>${exec.triggered_by || 'N/A'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-info" onclick="progressChecker.showExecutionDetails('${exec.execution_id}')">
                            詳細
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        return `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>実行ID</th>
                            <th>ステータス</th>
                            <th>開始時刻</th>
                            <th>トリガー</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${historyRows}
                    </tbody>
                </table>
            </div>
        `;
    }

    /**
     * 実行ステータスバッジを取得
     */
    getExecutionStatusBadge(status) {
        const badges = {
            'RUNNING': '<span class="badge bg-primary">実行中</span>',
            'COMPLETED': '<span class="badge bg-success">完了</span>',
            'FAILED': '<span class="badge bg-danger">失敗</span>',
            'CANCELLED': '<span class="badge bg-warning">キャンセル</span>'
        };
        return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
    }

    /**
     * リアルタイム監視開始
     */
    startRealtimeMonitoring(symbol) {
        this.currentSymbol = symbol;
        this.isPolling = true;
        
        // ボタンの状態を更新
        const monitorBtn = document.querySelector('[onclick*="startRealtimeMonitoring"]');
        if (monitorBtn) {
            monitorBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 監視中...';
            monitorBtn.className = 'btn btn-warning';
            monitorBtn.onclick = () => this.stopRealtimeMonitoring();
        }

        // 定期更新開始
        this.startPolling(symbol);
        
        console.log(`🔄 ${symbol}のリアルタイム監視を開始`);
    }

    /**
     * リアルタイム監視停止
     */
    stopRealtimeMonitoring() {
        this.isPolling = false;
        this.currentSymbol = null;
        
        // ボタンの状態を復元
        const monitorBtn = document.querySelector('[onclick*="stopRealtimeMonitoring"]');
        if (monitorBtn) {
            monitorBtn.innerHTML = '<i class="fas fa-sync-alt"></i> リアルタイム監視開始';
            monitorBtn.className = 'btn btn-primary';
            monitorBtn.onclick = () => this.startRealtimeMonitoring(this.currentSymbol);
        }

        console.log('🛑 リアルタイム監視を停止');
    }

    /**
     * ポーリング開始
     */
    async startPolling(symbol) {
        while (this.isPolling && this.currentSymbol === symbol) {
            try {
                // 進捗データを更新
                const progressData = await this.fetchProgressData(symbol);
                this.updateProgressDisplay(progressData);
                
                // 完了チェック
                if (progressData.progress.completion_rate >= 100) {
                    this.showCompletionNotification(symbol);
                    this.stopRealtimeMonitoring();
                    break;
                }
                
            } catch (error) {
                console.error('ポーリングエラー:', error);
            }

            // 次のポーリングまで待機
            await new Promise(resolve => setTimeout(resolve, this.pollingInterval));
        }
    }

    /**
     * 進捗表示を更新
     */
    updateProgressDisplay(data) {
        const { progress } = data;
        
        // 進捗バーを更新
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress.completion_rate}%`;
            progressBar.className = `progress-bar ${this.getProgressBarClass(progress.completion_rate)}`;
        }

        // 完了パターン数を更新
        const patternCells = document.querySelectorAll('td');
        patternCells.forEach(cell => {
            if (cell.textContent.includes('/')) {
                cell.textContent = `${progress.completed_patterns} / ${progress.total_patterns}`;
            }
        });

        console.log(`📊 ${data.symbol}: ${progress.completion_rate}% (${progress.completed_patterns}/${progress.total_patterns})`);
    }

    /**
     * 完了通知を表示
     */
    showCompletionNotification(symbol) {
        // ブラウザ通知
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`${symbol} 分析完了`, {
                body: '全18パターンの分析が完了しました！',
                icon: '/static/favicon.ico'
            });
        }

        // モーダル内通知
        const modalBody = document.querySelector('#progressModal .modal-body');
        if (modalBody) {
            const alert = document.createElement('div');
            alert.className = 'alert alert-success alert-dismissible fade show';
            alert.innerHTML = `
                <i class="fas fa-check-circle"></i>
                <strong>分析完了！</strong> ${symbol}の全18パターン分析が完了しました。
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            modalBody.insertBefore(alert, modalBody.firstChild);
        }

        console.log(`🎉 ${symbol}の分析が完了しました！`);
    }

    /**
     * 実行詳細を表示
     */
    async showExecutionDetails(executionId) {
        try {
            const response = await fetch(`/api/execution/${executionId}/status`);
            const details = await response.json();
            
            // 詳細モーダルを表示
            this.showExecutionModal(executionId, details);
            
        } catch (error) {
            console.error('実行詳細取得エラー:', error);
            this.showErrorAlert('実行詳細の取得に失敗しました');
        }
    }

    /**
     * エラーアラートを表示
     */
    showErrorAlert(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alert.style.top = '20px';
        alert.style.right = '20px';
        alert.style.zIndex = '9999';
        alert.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alert);
        
        // 5秒後に自動削除
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }

    /**
     * 進捗監視UIを初期化
     */
    initializeProgressMonitor() {
        // ブラウザ通知の許可要求
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }
}

// グローバルインスタンス作成
const progressChecker = new ProgressChecker();

// DOM読み込み完了後に初期化
document.addEventListener('DOMContentLoaded', () => {
    progressChecker.initializeUI();
});