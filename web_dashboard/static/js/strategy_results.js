/**
 * Strategy Results Page JavaScript
 * 戦略分析結果ページの制御とAPI通信
 */

class StrategyResultsManager {
    constructor() {
        this.currentSymbol = null;
        this.resultsData = [];
        this.chart = null;
        this.dataTable = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadAvailableSymbols();
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

    bindEvents() {
        // Symbol selection and loading
        document.getElementById('btn-load-results').addEventListener('click', () => this.loadStrategyResults());
        document.getElementById('symbol-select').addEventListener('change', (e) => {
            if (e.target.value) {
                this.loadStrategyResults();
            }
        });

        // Refresh button
        document.getElementById('btn-refresh-results').addEventListener('click', () => {
            this.loadAvailableSymbols();
            if (this.currentSymbol) {
                this.loadStrategyResults();
            }
        });

        // Sort change
        document.getElementById('sort-by').addEventListener('change', () => {
            if (this.resultsData.length > 0) {
                this.renderResults();
            }
        });

        // Use recommended strategy
        document.getElementById('btn-use-strategy').addEventListener('click', () => this.useRecommendedStrategy());

        // Export functionality
        document.getElementById('btn-export-csv').addEventListener('click', () => this.exportToCSV());
        document.getElementById('btn-show-trades').addEventListener('click', () => this.showTradeDetails());
    }

    async loadAvailableSymbols() {
        try {
            this.showMessageBanner('利用可能な銘柄を読み込み中...', 'info');
            
            // Get symbols that have completed analysis
            const response = await fetch('/api/strategy-results/symbols');
            if (response.ok) {
                const symbols = await response.json();
                
                const symbolSelect = document.getElementById('symbol-select');
                symbolSelect.innerHTML = '<option value="">銘柄を選択してください</option>';
                
                symbols.forEach(symbol => {
                    const option = document.createElement('option');
                    option.value = symbol.symbol;
                    option.textContent = `${symbol.symbol} (${symbol.pattern_count}パターン分析済み)`;
                    symbolSelect.appendChild(option);
                });
                
                this.showMessageBanner(`${symbols.length}銘柄の分析結果が利用可能です`, 'success');
            } else {
                throw new Error('Failed to load symbols');
            }
        } catch (error) {
            console.error('Error loading symbols:', error);
            this.showMessageBanner('銘柄の読み込みに失敗しました', 'error');
        }
    }

    async loadStrategyResults() {
        const symbol = document.getElementById('symbol-select').value;
        if (!symbol) {
            this.showMessageBanner('銘柄を選択してください', 'warning');
            return;
        }

        try {
            this.showMessageBanner(`${symbol}の分析結果を読み込み中...`, 'info');
            this.currentSymbol = symbol;

            // Load analysis results for the symbol
            const response = await fetch(`/api/strategy-results/${symbol}`);
            if (response.ok) {
                const data = await response.json();
                this.resultsData = data.results || [];
                
                if (this.resultsData.length === 0) {
                    this.showMessageBanner(`${symbol}の分析結果が見つかりません`, 'warning');
                    this.hideAllSections();
                    return;
                }

                document.getElementById('best-symbol-name').textContent = symbol;
                this.showMessageBanner(`${symbol}の${this.resultsData.length}パターンの分析結果を読み込みました`, 'success');
                
                this.renderResults();
                this.showAllSections();
                
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Error loading strategy results:', error);
            this.showMessageBanner(`${symbol}の分析結果の読み込みに失敗しました`, 'error');
            this.hideAllSections();
        }
    }

    renderResults() {
        if (this.resultsData.length === 0) return;

        // Sort results
        const sortBy = document.getElementById('sort-by').value;
        const sortedResults = [...this.resultsData].sort((a, b) => b[sortBy] - a[sortBy]);

        // Render best strategy recommendation
        this.renderBestStrategy(sortedResults[0]);

        // Render summary cards
        this.renderSummaryCards(sortedResults);

        // Render chart
        this.renderPerformanceChart(sortedResults);

        // Render table
        this.renderResultsTable(sortedResults);
    }

    renderBestStrategy(bestStrategy) {
        const infoDiv = document.getElementById('best-strategy-info');
        
        infoDiv.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-clock"></i> 時間足</h6>
                    <p class="h5 text-primary">${bestStrategy.timeframe}</p>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-brain"></i> 戦略</h6>
                    <p class="h5 text-primary">${this.formatStrategy(bestStrategy.config)}</p>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-md-3">
                    <h6>シャープ比</h6>
                    <p class="h5 text-success">${bestStrategy.sharpe_ratio.toFixed(2)}</p>
                </div>
                <div class="col-md-3">
                    <h6>勝率</h6>
                    <p class="h5 text-success">${(bestStrategy.win_rate * 100).toFixed(1)}%</p>
                </div>
                <div class="col-md-3">
                    <h6>総リターン</h6>
                    <p class="h5 text-success">${(bestStrategy.total_return * 100).toFixed(1)}%</p>
                </div>
                <div class="col-md-3">
                    <h6>最大DD</h6>
                    <p class="h5 text-warning">${(Math.abs(bestStrategy.max_drawdown) * 100).toFixed(1)}%</p>
                </div>
            </div>
        `;

        // Store best strategy for use button
        this.bestStrategy = bestStrategy;
    }

    renderSummaryCards(results) {
        const avgSharpe = results.reduce((sum, r) => sum + r.sharpe_ratio, 0) / results.length;
        const avgWinRate = results.reduce((sum, r) => sum + r.win_rate, 0) / results.length;
        const avgReturn = results.reduce((sum, r) => sum + r.total_return, 0) / results.length;

        document.getElementById('avg-sharpe').textContent = avgSharpe.toFixed(2);
        document.getElementById('avg-winrate').textContent = (avgWinRate * 100).toFixed(1) + '%';
        document.getElementById('avg-return').textContent = (avgReturn * 100).toFixed(1) + '%';
        document.getElementById('total-patterns').textContent = results.length.toString();
    }

    renderPerformanceChart(results) {
        const ctx = document.getElementById('performance-chart').getContext('2d');
        
        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
        }

        // Group by strategy
        const strategies = {};
        results.forEach(result => {
            const strategy = this.formatStrategy(result.config);
            if (!strategies[strategy]) {
                strategies[strategy] = [];
            }
            strategies[strategy].push(result);
        });

        const datasets = Object.keys(strategies).map((strategy, index) => {
            const colors = ['#007bff', '#28a745', '#ffc107'];
            return {
                label: strategy,
                data: strategies[strategy].map(r => ({
                    x: r.sharpe_ratio,
                    y: r.total_return * 100,
                    timeframe: r.timeframe
                })),
                backgroundColor: colors[index % colors.length],
                borderColor: colors[index % colors.length],
                borderWidth: 2
            };
        });

        this.chart = new Chart(ctx, {
            type: 'scatter',
            data: { datasets },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'シャープ比 vs 総リターン'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const point = context.parsed;
                                const data = context.raw;
                                return `${context.dataset.label} (${data.timeframe}): シャープ比 ${point.x.toFixed(2)}, リターン ${point.y.toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'シャープ比'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '総リターン (%)'
                        }
                    }
                }
            }
        });
    }

    renderResultsTable(results) {
        const tbody = document.getElementById('results-tbody');
        tbody.innerHTML = '';

        results.forEach((result, index) => {
            const row = document.createElement('tr');
            if (index === 0) {
                row.classList.add('table-success'); // Highlight best result
            }
            
            row.innerHTML = `
                <td><span class="badge ${index === 0 ? 'bg-warning' : 'bg-secondary'}">${index + 1}</span></td>
                <td><strong>${result.timeframe}</strong></td>
                <td>${this.formatStrategy(result.config)}</td>
                <td><strong>${result.sharpe_ratio.toFixed(2)}</strong></td>
                <td>${(result.win_rate * 100).toFixed(1)}%</td>
                <td class="${result.total_return >= 0 ? 'text-success' : 'text-danger'}">${(result.total_return * 100).toFixed(1)}%</td>
                <td class="text-warning">${(Math.abs(result.max_drawdown) * 100).toFixed(1)}%</td>
                <td>${result.avg_leverage.toFixed(1)}x</td>
                <td>${result.total_trades}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="strategyResultsManager.viewTradeDetails('${result.symbol}', '${result.timeframe}', '${result.config}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });

        // Initialize/refresh DataTable
        if (this.dataTable) {
            this.dataTable.destroy();
        }
        
        this.dataTable = $('#results-table').DataTable({
            pageLength: 25,
            order: [], // Maintain current sort
            columnDefs: [
                { orderable: false, targets: [9] } // Disable sorting on action column
            ],
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/ja.json'
            }
        });
    }

    formatStrategy(config) {
        const strategyNames = {
            'Conservative_ML': '保守的ML',
            'Aggressive_Traditional': '積極的従来型',
            'Full_ML': 'フルML'
        };
        return strategyNames[config] || config;
    }

    showAllSections() {
        document.getElementById('recommendation-section').style.display = 'block';
        document.getElementById('summary-cards').style.display = 'block';
        document.getElementById('chart-section').style.display = 'block';
        document.getElementById('results-section').style.display = 'block';
    }

    hideAllSections() {
        document.getElementById('recommendation-section').style.display = 'none';
        document.getElementById('summary-cards').style.display = 'none';
        document.getElementById('chart-section').style.display = 'none';
        document.getElementById('results-section').style.display = 'none';
    }

    async useRecommendedStrategy() {
        if (!this.bestStrategy) {
            this.showMessageBanner('推奨戦略が選択されていません', 'error');
            return;
        }

        try {
            const strategy = this.bestStrategy;
            this.showMessageBanner(`${strategy.symbol} ${strategy.timeframe} ${this.formatStrategy(strategy.config)} を監視システムに追加中...`, 'info');

            // Add to monitoring system
            const response = await fetch('/api/monitor/add-strategy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: strategy.symbol,
                    timeframe: strategy.timeframe,
                    strategy: strategy.config,
                    leverage_limit: strategy.avg_leverage
                })
            });

            if (response.ok) {
                this.showMessageBanner(`✅ ${strategy.symbol} の監視を開始しました！`, 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to add strategy');
            }
        } catch (error) {
            console.error('Error using recommended strategy:', error);
            this.showMessageBanner('監視システムへの追加に失敗しました', 'error');
        }
    }

    async exportToCSV() {
        if (!this.currentSymbol || this.resultsData.length === 0) {
            this.showMessageBanner('エクスポートするデータがありません', 'warning');
            return;
        }

        try {
            const response = await fetch(`/api/strategy-results/${this.currentSymbol}/export`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${this.currentSymbol}_strategy_results.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showMessageBanner('CSVファイルをダウンロードしました', 'success');
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            console.error('Error exporting CSV:', error);
            this.showMessageBanner('CSVエクスポートに失敗しました', 'error');
        }
    }

    async viewTradeDetails(symbol, timeframe, config) {
        this.showMessageBanner(`${symbol} ${timeframe} ${this.formatStrategy(config)} のトレード詳細を読み込み中...`, 'info');
        
        try {
            const response = await fetch(`/api/strategy-results/${symbol}/${timeframe}/${config}/trades`);
            if (response.ok) {
                const trades = await response.json();
                this.showTradeDetailsModal(symbol, timeframe, config, trades);
            } else {
                throw new Error('Failed to load trade details');
            }
        } catch (error) {
            console.error('Error loading trade details:', error);
            this.showMessageBanner('トレード詳細の読み込みに失敗しました', 'error');
        }
    }

    showTradeDetailsModal(symbol, timeframe, config, trades) {
        // Create modal for trade details (simplified implementation)
        const modalHtml = `
            <div class="modal fade" id="tradeDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${symbol} ${timeframe} ${this.formatStrategy(config)} - トレード詳細</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>総トレード数: ${trades.length}</p>
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>No.</th>
                                            <th>エントリー時刻</th>
                                            <th>レバレッジ</th>
                                            <th>PnL (%)</th>
                                            <th>成功</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${trades.slice(0, 50).map((trade, i) => `
                                            <tr class="${trade.is_success ? 'table-success' : 'table-danger'}">
                                                <td>${i + 1}</td>
                                                <td>${trade.entry_time}</td>
                                                <td>${trade.leverage.toFixed(1)}x</td>
                                                <td class="${trade.pnl_pct >= 0 ? 'text-success' : 'text-danger'}">${(trade.pnl_pct * 100).toFixed(2)}%</td>
                                                <td>${trade.is_success ? '✅' : '❌'}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                            ${trades.length > 50 ? `<p class="text-muted">最初の50件のみ表示（全${trades.length}件）</p>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('tradeDetailsModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('tradeDetailsModal'));
        modal.show();
    }

    async showTradeDetails() {
        if (!this.bestStrategy) {
            this.showMessageBanner('戦略が選択されていません', 'warning');
            return;
        }
        
        const strategy = this.bestStrategy;
        await this.viewTradeDetails(strategy.symbol, strategy.timeframe, strategy.config);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.strategyResultsManager = new StrategyResultsManager();
});