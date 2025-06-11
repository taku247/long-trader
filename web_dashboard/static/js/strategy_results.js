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
                
                // Validate data structure
                if (!data || typeof data !== 'object') {
                    throw new Error('Invalid response format');
                }
                
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

        try {
            // Sort results with error handling
            const sortBy = document.getElementById('sort-by').value;
            const sortedResults = [...this.resultsData].sort((a, b) => {
                const valueA = a[sortBy];
                const valueB = b[sortBy];
                
                // Handle null/undefined values
                if (valueA == null && valueB == null) return 0;
                if (valueA == null) return 1;
                if (valueB == null) return -1;
                
                // Handle non-numeric values
                if (typeof valueA !== 'number' || typeof valueB !== 'number') {
                    console.warn(`Non-numeric values found for ${sortBy}:`, valueA, valueB);
                    return String(valueB).localeCompare(String(valueA));
                }
                
                return valueB - valueA;
            });

            // Render best strategy recommendation
            this.renderBestStrategy(sortedResults[0]);

            // Render summary cards
            this.renderSummaryCards(sortedResults);

            // Render chart
            this.renderPerformanceChart(sortedResults);

            // Render table
            this.renderResultsTable(sortedResults);
        } catch (error) {
            console.error('Error rendering results:', error);
            this.showMessageBanner('結果の表示中にエラーが発生しました', 'error');
        }
    }

    renderBestStrategy(bestStrategy) {
        const infoDiv = document.getElementById('best-strategy-info');
        
        try {
            // Safe value extraction with defaults
            const sharpe = (bestStrategy.sharpe_ratio != null) ? bestStrategy.sharpe_ratio.toFixed(2) : 'N/A';
            const winRate = (bestStrategy.win_rate != null) ? (bestStrategy.win_rate * 100).toFixed(1) : 'N/A';
            const totalReturn = (bestStrategy.total_return != null) ? (bestStrategy.total_return * 100).toFixed(1) : 'N/A';
            const maxDD = (bestStrategy.max_drawdown != null) ? (Math.abs(bestStrategy.max_drawdown) * 100).toFixed(1) : 'N/A';
            
            infoDiv.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="fas fa-clock"></i> 時間足</h6>
                        <p class="h5 text-primary">${bestStrategy.timeframe || 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="fas fa-brain"></i> 戦略</h6>
                        <p class="h5 text-primary">${this.formatStrategy(bestStrategy.config)}</p>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-md-3">
                        <h6>シャープ比</h6>
                        <p class="h5 text-success">${sharpe}</p>
                    </div>
                    <div class="col-md-3">
                        <h6>勝率</h6>
                        <p class="h5 text-success">${winRate}${winRate !== 'N/A' ? '%' : ''}</p>
                    </div>
                    <div class="col-md-3">
                        <h6>総リターン</h6>
                        <p class="h5 text-success">${totalReturn}${totalReturn !== 'N/A' ? '%' : ''}</p>
                    </div>
                    <div class="col-md-3">
                        <h6>最大DD</h6>
                        <p class="h5 text-warning">${maxDD}${maxDD !== 'N/A' ? '%' : ''}</p>
                    </div>
                </div>
            `;

            // Store best strategy for use button
            this.bestStrategy = bestStrategy;
        } catch (error) {
            console.error('Error rendering best strategy:', error);
            infoDiv.innerHTML = '<div class="alert alert-warning">最良戦略情報の表示でエラーが発生しました</div>';
        }
    }

    renderSummaryCards(results) {
        try {
            // Filter out invalid values and calculate averages safely
            const validSharpe = results.filter(r => r.sharpe_ratio != null && typeof r.sharpe_ratio === 'number');
            const validWinRate = results.filter(r => r.win_rate != null && typeof r.win_rate === 'number');
            const validReturn = results.filter(r => r.total_return != null && typeof r.total_return === 'number');
            
            const avgSharpe = validSharpe.length > 0 ? 
                validSharpe.reduce((sum, r) => sum + r.sharpe_ratio, 0) / validSharpe.length : 0;
            const avgWinRate = validWinRate.length > 0 ? 
                validWinRate.reduce((sum, r) => sum + r.win_rate, 0) / validWinRate.length : 0;
            const avgReturn = validReturn.length > 0 ? 
                validReturn.reduce((sum, r) => sum + r.total_return, 0) / validReturn.length : 0;

            document.getElementById('avg-sharpe').textContent = avgSharpe.toFixed(2);
            document.getElementById('avg-winrate').textContent = (avgWinRate * 100).toFixed(1) + '%';
            document.getElementById('avg-return').textContent = (avgReturn * 100).toFixed(1) + '%';
            document.getElementById('total-patterns').textContent = results.length.toString();
        } catch (error) {
            console.error('Error rendering summary cards:', error);
            // Set fallback values
            document.getElementById('avg-sharpe').textContent = 'N/A';
            document.getElementById('avg-winrate').textContent = 'N/A';
            document.getElementById('avg-return').textContent = 'N/A';
            document.getElementById('total-patterns').textContent = '0';
        }
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
        // Create enhanced modal for trade details with exit info and TP/SL
        const modalHtml = `
            <div class="modal fade" id="tradeDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-chart-line"></i> ${symbol} ${timeframe} ${this.formatStrategy(config)} - トレード詳細
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-3">
                                <div class="col-md-3">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">総トレード数</h5>
                                            <h3 class="text-primary">${trades.length}</h3>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">勝率</h5>
                                            <h3 class="text-success">${(trades.filter(t => t.is_success).length / trades.length * 100).toFixed(1)}%</h3>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">平均PnL</h5>
                                            <h3 class="text-info">${(trades.reduce((sum, t) => sum + t.pnl_pct, 0) / trades.length * 100).toFixed(2)}%</h3>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-light">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">平均レバレッジ</h5>
                                            <h3 class="text-warning">${(trades.reduce((sum, t) => sum + t.leverage, 0) / trades.length).toFixed(1)}x</h3>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="trade-details-table">
                                <table class="table table-sm table-hover">
                                    <thead class="table-dark">
                                        <tr>
                                            <th scope="col">No.</th>
                                            <th scope="col">エントリー時刻</th>
                                            <th scope="col">クローズ時刻</th>
                                            <th scope="col">エントリー価格</th>
                                            <th scope="col">クローズ価格</th>
                                            <th scope="col">利確ライン</th>
                                            <th scope="col">損切ライン</th>
                                            <th scope="col">レバレッジ</th>
                                            <th scope="col">PnL (%)</th>
                                            <th scope="col">結果</th>
                                            <th scope="col">信頼度</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${trades.slice(0, 100).map((trade, i) => {
                                            const duration = trade.exit_time && trade.entry_time ? 
                                                this.calculateDuration(trade.entry_time, trade.exit_time) : 'N/A';
                                            const exitReason = this.determineExitReason(trade);
                                            
                                            return `
                                            <tr class="${trade.is_success ? 'table-success' : 'table-danger'}" style="opacity: 0.9;">
                                                <td><strong>${i + 1}</strong></td>
                                                <td>
                                                    <small>${this.formatDateTime(trade.entry_time)}</small>
                                                </td>
                                                <td>
                                                    <small>${this.formatDateTime(trade.exit_time)}</small>
                                                    ${duration !== 'N/A' ? `<br><span class="badge bg-secondary">${duration}</span>` : ''}
                                                </td>
                                                <td>
                                                    ${trade.entry_price ? `$${trade.entry_price.toFixed(2)}` : 'N/A'}
                                                </td>
                                                <td>
                                                    ${trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : 'N/A'}
                                                </td>
                                                <td class="text-success">
                                                    ${trade.take_profit_price ? `$${trade.take_profit_price.toFixed(2)}` : 'N/A'}
                                                </td>
                                                <td class="text-danger">
                                                    ${trade.stop_loss_price ? `$${trade.stop_loss_price.toFixed(2)}` : 'N/A'}
                                                </td>
                                                <td>
                                                    <span class="badge bg-warning text-dark">${trade.leverage.toFixed(1)}x</span>
                                                </td>
                                                <td class="${trade.pnl_pct >= 0 ? 'text-success' : 'text-danger'}">
                                                    <strong>${(trade.pnl_pct * 100).toFixed(2)}%</strong>
                                                </td>
                                                <td>
                                                    ${trade.is_success ? '✅ 利確' : '❌ 損切'}
                                                    <br><small class="text-muted">${exitReason}</small>
                                                </td>
                                                <td>
                                                    <span class="badge bg-info">${(trade.confidence * 100).toFixed(0)}%</span>
                                                </td>
                                            </tr>
                                        `;}).join('')}
                                    </tbody>
                                </table>
                            </div>
                            ${trades.length > 100 ? `<p class="text-muted">最初の100件のみ表示（全${trades.length}件）</p>` : ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">閉じる</button>
                            <button type="button" class="btn btn-primary" onclick="strategyResultsManager.exportTradeDetails('${symbol}', '${timeframe}', '${config}')">
                                <i class="fas fa-download"></i> CSV出力
                            </button>
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

    // Helper methods for trade details display
    formatDateTime(dateTimeStr) {
        if (!dateTimeStr || dateTimeStr === 'N/A') return 'N/A';
        try {
            // Simple regex-based formatting for "YYYY-MM-DD HH:MM:SS JST" format
            const match = dateTimeStr.match(/(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/);
            if (match) {
                const [, year, month, day, hour, minute] = match;
                return `${month}/${day} ${hour}:${minute}`;
            }
            
            // Fallback: try to parse as date
            const dateStr = dateTimeStr.replace(' JST', '');
            const date = new Date(dateStr);
            if (!isNaN(date.getTime())) {
                return date.toLocaleString('ja-JP', { 
                    month: '2-digit', 
                    day: '2-digit', 
                    hour: '2-digit', 
                    minute: '2-digit' 
                });
            }
            
            // If all else fails, return original
            return dateTimeStr;
        } catch (e) {
            console.warn('Date formatting error:', e, 'for date:', dateTimeStr);
            return dateTimeStr;
        }
    }

    calculateDuration(entryTime, exitTime) {
        if (!entryTime || !exitTime || entryTime === 'N/A' || exitTime === 'N/A') return 'N/A';
        try {
            // Parse dates with JST handling
            const entry = this.parseJSTDate(entryTime);
            const exit = this.parseJSTDate(exitTime);
            
            if (!entry || !exit) return 'N/A';
            
            const durationMs = exit - entry;
            
            if (durationMs < 0) return 'N/A';
            
            const hours = Math.floor(durationMs / (1000 * 60 * 60));
            const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
            
            if (hours > 0) {
                return `${hours}h${minutes}m`;
            } else {
                return `${minutes}m`;
            }
        } catch (e) {
            console.warn('Duration calculation error:', e);
            return 'N/A';
        }
    }

    parseJSTDate(dateTimeStr) {
        if (!dateTimeStr || dateTimeStr === 'N/A') return null;
        try {
            // Remove JST timezone
            let dateStr = dateTimeStr;
            if (dateStr.includes(' JST')) {
                dateStr = dateStr.replace(' JST', '');
            }
            
            // Try standard parsing first
            let date = new Date(dateStr);
            
            // If that fails, try manual parsing
            if (isNaN(date.getTime())) {
                const match = dateStr.match(/(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/);
                if (match) {
                    const [, year, month, day, hour, minute, second] = match;
                    date = new Date(year, month - 1, day, hour, minute, second);
                }
            }
            
            return isNaN(date.getTime()) ? null : date;
        } catch (e) {
            console.warn('Date parsing error:', e);
            return null;
        }
    }

    determineExitReason(trade) {
        if (!trade.exit_price || !trade.entry_price) {
            return trade.is_success ? 'Target' : 'Stop';
        }
        
        const exitPrice = trade.exit_price;
        const entryPrice = trade.entry_price;
        const returnPct = (exitPrice - entryPrice) / entryPrice;
        
        if (trade.is_success) {
            // For profitable trades
            if (returnPct >= 0.035) {  // 3.5%+ return
                return 'TP達成';
            } else if (returnPct >= 0.015) {  // 1.5-3.5% return
                return '部分利確';
            } else {
                return '手動利確';
            }
        } else {
            // For losing trades
            if (returnPct <= -0.025) {  // -2.5% or worse
                return 'SL発動';
            } else if (returnPct <= -0.01) {  // -1% to -2.5%
                return '早期損切';
            } else {
                return '手動損切';
            }
        }
    }

    async exportTradeDetails(symbol, timeframe, config) {
        try {
            this.showMessageBanner(`${symbol} ${timeframe} ${this.formatStrategy(config)} のトレード詳細をエクスポート中...`, 'info');
            
            const response = await fetch(`/api/strategy-results/${symbol}/${timeframe}/${config}/trades`);
            if (response.ok) {
                const trades = await response.json();
                
                // Create CSV content
                const csvHeaders = [
                    'No.', 'エントリー時刻', 'クローズ時刻', 'エントリー価格', 'クローズ価格', 
                    '利確ライン', '損切ライン', 'レバレッジ', 'PnL(%)', '結果', '信頼度'
                ];
                
                const csvRows = trades.map((trade, i) => [
                    i + 1,
                    trade.entry_time || 'N/A',
                    trade.exit_time || 'N/A',
                    trade.entry_price ? trade.entry_price.toFixed(2) : 'N/A',
                    trade.exit_price ? trade.exit_price.toFixed(2) : 'N/A',
                    trade.take_profit_price ? trade.take_profit_price.toFixed(2) : 'N/A',
                    trade.stop_loss_price ? trade.stop_loss_price.toFixed(2) : 'N/A',
                    trade.leverage.toFixed(1),
                    (trade.pnl_pct * 100).toFixed(2),
                    trade.is_success ? '利確' : '損切',
                    (trade.confidence * 100).toFixed(0)
                ]);
                
                const csvContent = [csvHeaders, ...csvRows]
                    .map(row => row.map(cell => `"${cell}"`).join(','))
                    .join('\n');
                
                // Download CSV
                const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${symbol}_${timeframe}_${config}_trades.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showMessageBanner('トレード詳細CSVをダウンロードしました', 'success');
            } else {
                throw new Error('Failed to export trade details');
            }
        } catch (error) {
            console.error('Error exporting trade details:', error);
            this.showMessageBanner('トレード詳細のエクスポートに失敗しました', 'error');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.strategyResultsManager = new StrategyResultsManager();
});