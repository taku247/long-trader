/**
 * Alert History Analysis JavaScript
 * チャート表示とアラート分析機能
 */

class AlertAnalysis {
    constructor() {
        this.currentSymbol = 'HYPE';
        this.currentPeriod = 30;
        this.currentStrategy = '';
        this.chartData = null;
        this.alertData = null;
        
        this.init();
    }
    
    init() {
        this.attachEventListeners();
        this.loadInitialData();
    }
    
    attachEventListeners() {
        // フィルター適用
        document.getElementById('btn-apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });
        
        // データ更新
        document.getElementById('btn-refresh-data').addEventListener('click', () => {
            this.refreshData();
        });
        
        // ソート変更
        document.querySelectorAll('input[name="alert-sort"]').forEach(radio => {
            radio.addEventListener('change', () => {
                this.sortAlertList();
            });
        });
    }
    
    async loadInitialData() {
        await this.loadData();
    }
    
    applyFilters() {
        this.currentSymbol = document.getElementById('symbol-select').value;
        this.currentPeriod = parseInt(document.getElementById('period-select').value);
        this.currentStrategy = document.getElementById('strategy-select').value;
        
        document.getElementById('chart-symbol-label').textContent = this.currentSymbol;
        
        this.loadData();
    }
    
    async refreshData() {
        this.showLoading();
        await this.loadData();
    }
    
    async loadData() {
        try {
            this.showLoading();
            
            // 並列でデータ取得
            const [chartResponse, alertResponse, statsResponse] = await Promise.all([
                fetch(`/api/analysis/chart-data?symbol=${this.currentSymbol}&days=${this.currentPeriod}`),
                fetch(`/api/analysis/alerts?symbol=${this.currentSymbol}&days=${this.currentPeriod}&strategy=${this.currentStrategy}`),
                fetch(`/api/analysis/statistics?symbol=${this.currentSymbol}&strategy=${this.currentStrategy}`)
            ]);
            
            const chartData = await chartResponse.json();
            const alertData = await alertResponse.json();
            const statsData = await statsResponse.json();
            
            this.chartData = chartData;
            this.alertData = alertData;
            
            // 表示更新
            this.updateChart();
            this.updateStatistics(statsData);
            this.updateAlertList();
            
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('データの読み込みに失敗しました');
        }
    }
    
    updateChart() {
        if (!this.chartData || !this.chartData.prices) {
            this.showError('チャートデータがありません');
            return;
        }
        
        // ローソク足データ
        const candlestickTrace = {
            type: 'candlestick',
            x: this.chartData.prices.map(d => d.timestamp),
            open: this.chartData.prices.map(d => d.open),
            high: this.chartData.prices.map(d => d.high),
            low: this.chartData.prices.map(d => d.low),
            close: this.chartData.prices.map(d => d.close),
            name: `${this.currentSymbol} 価格`,
            increasing: {line: {color: '#26a69a'}},
            decreasing: {line: {color: '#ef5350'}}
        };
        
        const traces = [candlestickTrace];
        
        // アラートポイント
        if (this.alertData && this.alertData.length > 0) {
            const successAlerts = this.alertData.filter(a => a.performance && a.performance.is_success);
            const failAlerts = this.alertData.filter(a => a.performance && !a.performance.is_success);
            const pendingAlerts = this.alertData.filter(a => !a.performance);
            
            // 成功アラート
            if (successAlerts.length > 0) {
                traces.push({
                    type: 'scatter',
                    mode: 'markers',
                    x: successAlerts.map(a => a.timestamp),
                    y: successAlerts.map(a => a.entry_price),
                    marker: {
                        symbol: 'triangle-up',
                        size: 12,
                        color: '#4caf50',
                        line: {color: '#2e7d32', width: 2}
                    },
                    text: successAlerts.map(a => 
                        `✅ 成功<br>レバレッジ: ${a.leverage}x<br>信頼度: ${a.confidence}%<br>リターン: +${a.performance.current_change_percent}%`
                    ),
                    hovertemplate: '%{text}<extra></extra>',
                    name: '成功アラート',
                    customdata: successAlerts.map(a => a.alert_id)
                });
            }
            
            // 失敗アラート
            if (failAlerts.length > 0) {
                traces.push({
                    type: 'scatter',
                    mode: 'markers',
                    x: failAlerts.map(a => a.timestamp),
                    y: failAlerts.map(a => a.entry_price),
                    marker: {
                        symbol: 'triangle-down',
                        size: 12,
                        color: '#f44336',
                        line: {color: '#c62828', width: 2}
                    },
                    text: failAlerts.map(a => 
                        `❌ 失敗<br>レバレッジ: ${a.leverage}x<br>信頼度: ${a.confidence}%<br>リターン: ${a.performance.current_change_percent}%`
                    ),
                    hovertemplate: '%{text}<extra></extra>',
                    name: '失敗アラート',
                    customdata: failAlerts.map(a => a.alert_id)
                });
            }
            
            // 進行中アラート
            if (pendingAlerts.length > 0) {
                traces.push({
                    type: 'scatter',
                    mode: 'markers',
                    x: pendingAlerts.map(a => a.timestamp),
                    y: pendingAlerts.map(a => a.entry_price),
                    marker: {
                        symbol: 'circle',
                        size: 10,
                        color: '#ff9800',
                        line: {color: '#ef6c00', width: 2}
                    },
                    text: pendingAlerts.map(a => 
                        `⏳ 進行中<br>レバレッジ: ${a.leverage}x<br>信頼度: ${a.confidence}%`
                    ),
                    hovertemplate: '%{text}<extra></extra>',
                    name: '進行中',
                    customdata: pendingAlerts.map(a => a.alert_id)
                });
            }
        }
        
        const layout = {
            title: `${this.currentSymbol} 価格チャート + アラート履歴`,
            xaxis: {
                title: '時間',
                type: 'date',
                rangeslider: {visible: false}
            },
            yaxis: {
                title: '価格 (USD)',
                side: 'left'
            },
            showlegend: true,
            hovermode: 'closest',
            margin: {l: 50, r: 50, t: 50, b: 50}
        };
        
        const config = {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d']
        };
        
        Plotly.newPlot('price-chart', traces, layout, config);
        
        // クリックイベント
        document.getElementById('price-chart').on('plotly_click', (data) => {
            if (data.points && data.points.length > 0) {
                const point = data.points[0];
                if (point.customdata) {
                    this.showAlertDetail(point.customdata);
                }
            }
        });
    }
    
    updateStatistics(stats) {
        document.getElementById('total-alerts-stat').textContent = stats.total_alerts || 0;
        document.getElementById('success-rate-stat').textContent = `${(stats.success_rate || 0).toFixed(1)}%`;
        document.getElementById('avg-return-stat').textContent = `${(stats.average_return || 0).toFixed(1)}%`;
        document.getElementById('max-gain-stat').textContent = `+${(stats.max_gain || 0).toFixed(1)}%`;
        document.getElementById('max-loss-stat').textContent = `${(stats.max_loss || 0).toFixed(1)}%`;
        
        // 戦略別統計
        const strategyContainer = document.getElementById('strategy-stats');
        if (stats.by_strategy && Object.keys(stats.by_strategy).length > 0) {
            strategyContainer.innerHTML = Object.entries(stats.by_strategy).map(([strategy, data]) => 
                `<div class="d-flex justify-content-between mb-1">
                    <span>${strategy}:</span>
                    <span class="badge bg-secondary">${data.success_rate.toFixed(1)}% (${data.count}件)</span>
                </div>`
            ).join('');
        } else {
            strategyContainer.innerHTML = '<div class="text-muted">データなし</div>';
        }
    }
    
    updateAlertList() {
        const container = document.getElementById('alert-list-container');
        
        if (!this.alertData || this.alertData.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-search fa-2x mb-2"></i>
                    <p>該当するアラートが見つかりません</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.alertData.map(alert => this.createAlertListItem(alert)).join('');
    }
    
    createAlertListItem(alert) {
        const performance = alert.performance;
        const statusBadge = performance ? 
            (performance.is_success ? '<span class="badge bg-success">✅ 成功</span>' : '<span class="badge bg-danger">❌ 失敗</span>') :
            '<span class="badge bg-warning">⏳ 進行中</span>';
        
        const returnText = performance ? 
            `${performance.current_change_percent > 0 ? '+' : ''}${performance.current_change_percent.toFixed(1)}%` : 
            '-';
        
        return `
            <div class="alert-item trading-opportunity" onclick="window.analysis.showAlertDetail('${alert.alert_id}')">
                <div class="alert-header">
                    <h6 class="alert-title">${alert.symbol} - ${alert.strategy}</h6>
                    <span class="alert-timestamp">${new Date(alert.timestamp).toLocaleString('ja-JP')}</span>
                </div>
                <div class="alert-metadata">
                    <span class="alert-meta-item">レバレッジ: ${alert.leverage}x</span>
                    <span class="alert-meta-item">信頼度: ${alert.confidence}%</span>
                    <span class="alert-meta-item">価格: $${alert.entry_price}</span>
                    <span class="alert-meta-item">リターン: ${returnText}</span>
                    ${statusBadge}
                </div>
            </div>
        `;
    }
    
    sortAlertList() {
        if (!this.alertData) return;
        
        const sortType = document.querySelector('input[name="alert-sort"]:checked').id;
        
        switch (sortType) {
            case 'sort-time':
                this.alertData.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                break;
            case 'sort-performance':
                this.alertData.sort((a, b) => {
                    const aReturn = a.performance ? a.performance.current_change_percent : -999;
                    const bReturn = b.performance ? b.performance.current_change_percent : -999;
                    return bReturn - aReturn;
                });
                break;
            case 'sort-leverage':
                this.alertData.sort((a, b) => b.leverage - a.leverage);
                break;
        }
        
        this.updateAlertList();
    }
    
    async showAlertDetail(alertId) {
        try {
            const response = await fetch(`/api/analysis/alert-detail/${alertId}`);
            const detail = await response.json();
            
            const modalContent = document.getElementById('modal-alert-details');
            modalContent.innerHTML = this.createAlertDetailHTML(detail);
            
            const modal = new bootstrap.Modal(document.getElementById('alertDetailModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error loading alert detail:', error);
            this.showError('アラート詳細の読み込みに失敗しました');
        }
    }
    
    createAlertDetailHTML(detail) {
        const performance = detail.performance;
        
        return `
            <div class="row">
                <div class="col-md-6">
                    <h6>基本情報</h6>
                    <table class="table table-sm">
                        <tr><td>銘柄</td><td><strong>${detail.symbol}</strong></td></tr>
                        <tr><td>検知時刻</td><td>${new Date(detail.timestamp).toLocaleString('ja-JP')}</td></tr>
                        <tr><td>エントリー価格</td><td>$${detail.entry_price}</td></tr>
                        <tr><td>推奨レバレッジ</td><td>${detail.leverage}x</td></tr>
                        <tr><td>信頼度</td><td>${detail.confidence}%</td></tr>
                        <tr><td>戦略</td><td>${detail.strategy}</td></tr>
                        <tr><td>時間足</td><td>${detail.timeframe}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>パフォーマンス</h6>
                    ${performance ? `
                        <table class="table table-sm">
                            <tr><td>現在価格</td><td>$${performance.current_price}</td></tr>
                            <tr><td>現在リターン</td><td class="${performance.current_change_percent >= 0 ? 'text-success' : 'text-danger'}">${performance.current_change_percent > 0 ? '+' : ''}${performance.current_change_percent.toFixed(2)}%</td></tr>
                            <tr><td>最大利益</td><td class="text-success">+${performance.max_gain.toFixed(2)}%</td></tr>
                            <tr><td>最大損失</td><td class="text-danger">${performance.min_loss.toFixed(2)}%</td></tr>
                            <tr><td>経過時間</td><td>${performance.elapsed_hours.toFixed(1)}時間</td></tr>
                            <tr><td>成功判定</td><td>${performance.is_success ? '<span class="badge bg-success">✅ 成功</span>' : '<span class="badge bg-danger">❌ 失敗</span>'}</td></tr>
                        </table>
                        ${performance.success_reason ? `<p class="text-muted"><small>判定理由: ${performance.success_reason}</small></p>` : ''}
                    ` : '<p class="text-muted">パフォーマンス計算中...</p>'}
                </div>
            </div>
            ${performance && performance.checkpoints ? `
                <div class="mt-3">
                    <h6>時間別パフォーマンス</h6>
                    <div class="row">
                        ${Object.entries(performance.checkpoints).map(([period, data]) => `
                            <div class="col-6 col-md-3 mb-2">
                                <div class="text-center">
                                    <div class="badge ${data.change_percent >= 0 ? 'bg-success' : 'bg-danger'} mb-1">
                                        ${period}
                                    </div>
                                    <div>${data.change_percent > 0 ? '+' : ''}${data.change_percent}%</div>
                                    <small class="text-muted">$${data.price}</small>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
    }
    
    showLoading() {
        document.getElementById('price-chart').innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-spinner fa-spin fa-2x mb-2"></i>
                <p>データを読み込み中...</p>
            </div>
        `;
    }
    
    showError(message) {
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>${message}</span>
                <button type="button" class="btn-close btn-close-sm" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.analysis = new AlertAnalysis();
});