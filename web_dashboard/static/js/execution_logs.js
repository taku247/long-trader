/**
 * Execution Logs page JavaScript
 * 実行ログページの機能実装
 */

class ExecutionLogsManager {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 20;
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
    }
    
    bindEvents() {
        // フィルター適用
        document.getElementById('btn-apply-filters').addEventListener('click', () => {
            this.currentPage = 1;
            this.loadExecutions();
        });
        
        // フィルタークリア
        document.getElementById('btn-clear-filters').addEventListener('click', () => {
            this.clearFilters();
        });
        
        // 更新ボタン
        document.getElementById('btn-refresh').addEventListener('click', () => {
            this.loadExecutions();
        });
        
        // 自動更新トグル
        document.getElementById('btn-auto-refresh').addEventListener('click', (e) => {
            this.toggleAutoRefresh(e.target.classList.contains('active'));
        });
        
        // 再実行ボタン
        document.getElementById('btn-rerun-execution').addEventListener('click', () => {
            this.rerunExecution();
        });
        
        // Enterキーでフィルター適用
        document.getElementById('filter-symbol').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.currentPage = 1;
                this.loadExecutions();
            }
        });
    }
    
    async loadInitialData() {
        await this.loadStatistics();
        await this.loadExecutions();
    }
    
    async loadStatistics() {
        try {
            const days = document.getElementById('filter-days').value || 7;
            const response = await fetch(`/api/execution-logs/statistics?days=${days}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const stats = await response.json();
            this.updateStatistics(stats);
            
        } catch (error) {
            console.error('Failed to load statistics:', error);
            this.showError('統計データの読み込みに失敗しました');
        }
    }
    
    updateStatistics(stats) {
        document.getElementById('total-executions').textContent = stats.total_executions || '-';
        document.getElementById('success-rate').textContent = 
            stats.success_rate !== undefined ? `${stats.success_rate}%` : '-';
        document.getElementById('avg-duration').textContent = 
            stats.avg_duration_seconds ? this.formatDuration(stats.avg_duration_seconds) : '-';
        document.getElementById('compute-hours').textContent = 
            stats.total_compute_hours !== undefined ? `${stats.total_compute_hours}h` : '-';
    }
    
    async loadExecutions() {
        try {
            this.showLoading(true);
            
            const filters = this.getFilters();
            const params = new URLSearchParams({
                page: this.currentPage,
                page_size: this.pageSize,
                ...filters
            });
            
            const response = await fetch(`/api/execution-logs?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.updateExecutionsTable(data.executions || []);
            this.updatePagination(data.pagination || {});
            this.updateResultsCount(data.total || 0);
            
            this.showLoading(false);
            this.showEmpty(data.executions?.length === 0);
            
        } catch (error) {
            console.error('Failed to load executions:', error);
            this.showError('実行ログの読み込みに失敗しました');
            this.showLoading(false);
        }
    }
    
    getFilters() {
        return {
            execution_type: document.getElementById('filter-type').value,
            symbol: document.getElementById('filter-symbol').value.trim(),
            status: document.getElementById('filter-status').value,
            days: document.getElementById('filter-days').value
        };
    }
    
    clearFilters() {
        document.getElementById('filter-type').value = '';
        document.getElementById('filter-symbol').value = '';
        document.getElementById('filter-status').value = '';
        document.getElementById('filter-days').value = '7';
        
        this.currentPage = 1;
        this.loadExecutions();
        this.loadStatistics();
    }
    
    updateExecutionsTable(executions) {
        const tbody = document.getElementById('executions-table-body');
        tbody.innerHTML = '';
        
        executions.forEach(execution => {
            const row = this.createExecutionRow(execution);
            tbody.appendChild(row);
        });
    }
    
    createExecutionRow(execution) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <span class="execution-id text-truncate-id" 
                      title="${execution.execution_id}"
                      data-execution-id="${execution.execution_id}">
                    ${execution.execution_id.substring(0, 12)}...
                </span>
            </td>
            <td>
                <span class="badge type-badge type-${execution.execution_type.toLowerCase().replace('_', '-')}">
                    ${this.getTypeDisplayName(execution.execution_type)}
                </span>
            </td>
            <td>
                <strong>${execution.symbol || this.formatSymbolsList(execution.symbols)}</strong>
            </td>
            <td>
                <span title="${execution.timestamp_start}">
                    ${this.formatDateTime(execution.timestamp_start)}
                </span>
            </td>
            <td>
                <span class="duration ${this.getDurationClass(execution.duration_seconds)}">
                    ${this.formatDuration(execution.duration_seconds)}
                </span>
            </td>
            <td>
                <span class="status-badge status-${execution.status.toLowerCase()}">
                    <i class="fas ${this.getStatusIcon(execution.status)}"></i>
                    ${this.getStatusDisplayName(execution.status)}
                </span>
            </td>
            <td>
                ${this.createProgressBar(execution)}
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-outline-primary btn-action"
                            onclick="executionLogs.showExecutionDetail('${execution.execution_id}')">
                        <i class="fas fa-info-circle"></i>
                    </button>
                    ${execution.status === 'FAILED' ? `
                        <button class="btn btn-sm btn-outline-warning btn-action"
                                onclick="executionLogs.rerunExecution('${execution.execution_id}')">
                            <i class="fas fa-redo"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        `;
        
        // 実行IDクリックで詳細表示
        row.querySelector('.execution-id').addEventListener('click', () => {
            this.showExecutionDetail(execution.execution_id);
        });
        
        return row;
    }
    
    createProgressBar(execution) {
        const percentage = execution.progress_percentage || 0;
        const completedTasks = execution.completed_tasks ? JSON.parse(execution.completed_tasks).length : 0;
        const totalTasks = execution.total_tasks || 0;
        
        let progressClass = 'bg-primary';
        if (execution.status === 'SUCCESS') progressClass = 'bg-success';
        else if (execution.status === 'FAILED') progressClass = 'bg-danger';
        else if (execution.status === 'CANCELLED') progressClass = 'bg-secondary';
        
        return `
            <div class="execution-progress">
                <div class="progress">
                    <div class="progress-bar ${progressClass}" 
                         role="progressbar" 
                         style="width: ${percentage}%"
                         title="${percentage.toFixed(1)}%">
                    </div>
                </div>
                <small class="progress-text">${completedTasks}/${totalTasks}</small>
            </div>
        `;
    }
    
    async showExecutionDetail(executionId) {
        try {
            const response = await fetch(`/api/execution-logs/${executionId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const execution = await response.json();
            this.populateDetailModal(execution);
            
            const modal = new bootstrap.Modal(document.getElementById('executionDetailModal'));
            modal.show();
            
        } catch (error) {
            console.error('Failed to load execution detail:', error);
            this.showError('実行詳細の読み込みに失敗しました');
        }
    }
    
    populateDetailModal(execution) {
        // 基本情報
        document.getElementById('detail-execution-id').textContent = execution.execution_id;
        document.getElementById('detail-type').innerHTML = `
            <span class="badge type-badge type-${execution.execution_type.toLowerCase().replace('_', '-')}">
                ${this.getTypeDisplayName(execution.execution_type)}
            </span>
        `;
        document.getElementById('detail-symbol').textContent = 
            execution.symbol || this.formatSymbolsList(execution.symbols);
        document.getElementById('detail-start-time').textContent = 
            this.formatDateTime(execution.timestamp_start);
        document.getElementById('detail-end-time').textContent = 
            execution.timestamp_end ? this.formatDateTime(execution.timestamp_end) : '実行中';
        document.getElementById('detail-duration').textContent = 
            this.formatDuration(execution.duration_seconds);
        
        // 進捗情報
        const percentage = execution.progress_percentage || 0;
        const progressBar = document.getElementById('detail-progress-bar');
        progressBar.style.width = `${percentage}%`;
        progressBar.textContent = `${percentage.toFixed(1)}%`;
        
        document.getElementById('detail-current-operation').textContent = 
            execution.current_operation || '-';
        
        const completedTasks = execution.completed_tasks ? JSON.parse(execution.completed_tasks) : [];
        document.getElementById('detail-completed-tasks').textContent = completedTasks.length;
        document.getElementById('detail-total-tasks').textContent = execution.total_tasks || 0;
        
        // ステップ詳細
        this.populateStepsAccordion(execution.steps || []);
        
        // エラー情報
        const errors = execution.errors ? JSON.parse(execution.errors) : [];
        this.populateErrorSection(errors);
        
        // リソース使用状況
        this.populateResourceSection(execution);
        
        // 再実行ボタンの設定
        const rerunBtn = document.getElementById('btn-rerun-execution');
        rerunBtn.dataset.executionId = execution.execution_id;
        rerunBtn.style.display = execution.status === 'FAILED' ? 'inline-block' : 'none';
    }
    
    populateStepsAccordion(steps) {
        const accordion = document.getElementById('stepsAccordion');
        accordion.innerHTML = '';
        
        steps.forEach((step, index) => {
            const stepDiv = document.createElement('div');
            stepDiv.className = `accordion-item step-${step.status.toLowerCase()}`;
            
            const stepId = `step-${index}`;
            
            stepDiv.innerHTML = `
                <h2 class="accordion-header" id="heading-${stepId}">
                    <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" 
                            type="button" 
                            data-bs-toggle="collapse" 
                            data-bs-target="#collapse-${stepId}">
                        <i class="fas ${this.getStepIcon(step.status)} me-2"></i>
                        ${step.step_name}
                        <small class="text-muted ms-2">
                            ${step.duration_seconds ? `(${this.formatDuration(step.duration_seconds)})` : ''}
                        </small>
                    </button>
                </h2>
                <div id="collapse-${stepId}" 
                     class="accordion-collapse collapse ${index === 0 ? 'show' : ''}"
                     data-bs-parent="#stepsAccordion">
                    <div class="accordion-body">
                        <p><strong>ステータス:</strong> ${step.status}</p>
                        <p><strong>開始時刻:</strong> ${this.formatDateTime(step.timestamp_start)}</p>
                        ${step.timestamp_end ? `<p><strong>終了時刻:</strong> ${this.formatDateTime(step.timestamp_end)}</p>` : ''}
                        ${step.result_data ? `
                            <p><strong>結果データ:</strong></p>
                            <pre class="bg-light p-2 rounded"><code>${JSON.stringify(JSON.parse(step.result_data), null, 2)}</code></pre>
                        ` : ''}
                        ${step.error_message ? `
                            <div class="alert alert-danger">
                                <strong>エラー:</strong> ${step.error_message}
                                ${step.error_traceback ? `
                                    <details class="mt-2">
                                        <summary>スタックトレース</summary>
                                        <pre class="mt-2"><code>${step.error_traceback}</code></pre>
                                    </details>
                                ` : ''}
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
            
            accordion.appendChild(stepDiv);
        });
    }
    
    populateErrorSection(errors) {
        const errorSection = document.getElementById('error-section');
        const errorList = document.getElementById('error-list');
        
        if (errors.length === 0) {
            errorSection.style.display = 'none';
            return;
        }
        
        errorSection.style.display = 'block';
        errorList.innerHTML = '';
        
        errors.forEach(error => {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-item';
            errorDiv.innerHTML = `
                <div class="error-title">
                    ${error.error_type || 'Error'} - ${error.timestamp ? this.formatDateTime(error.timestamp) : ''}
                </div>
                <div class="error-message">${error.error_message || 'Unknown error'}</div>
                ${error.traceback ? `
                    <details class="mt-2">
                        <summary>詳細なスタックトレース</summary>
                        <pre class="error-message mt-2">${error.traceback}</pre>
                    </details>
                ` : ''}
            `;
            errorList.appendChild(errorDiv);
        });
    }
    
    populateResourceSection(execution) {
        const resourceSection = document.getElementById('resource-section');
        
        if (!execution.cpu_usage_avg && !execution.memory_peak_mb && !execution.disk_io_mb) {
            resourceSection.style.display = 'none';
            return;
        }
        
        resourceSection.style.display = 'block';
        
        document.getElementById('detail-cpu').textContent = 
            execution.cpu_usage_avg ? execution.cpu_usage_avg.toFixed(1) : '-';
        document.getElementById('detail-memory').textContent = 
            execution.memory_peak_mb || '-';
        document.getElementById('detail-disk').textContent = 
            execution.disk_io_mb || '-';
    }
    
    async rerunExecution(executionId) {
        const targetId = executionId || document.getElementById('btn-rerun-execution').dataset.executionId;
        
        if (!targetId) return;
        
        if (!confirm('この実行を再実行しますか？')) return;
        
        try {
            const response = await fetch(`/api/execution-logs/${targetId}/rerun`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            this.showSuccess(`実行が開始されました: ${result.new_execution_id}`);
            
            // モーダルを閉じる
            const modal = bootstrap.Modal.getInstance(document.getElementById('executionDetailModal'));
            if (modal) modal.hide();
            
            // リストを更新
            this.loadExecutions();
            
        } catch (error) {
            console.error('Failed to rerun execution:', error);
            this.showError('再実行の開始に失敗しました');
        }
    }
    
    updatePagination(pagination) {
        const paginationEl = document.getElementById('pagination');
        paginationEl.innerHTML = '';
        
        if (!pagination.total_pages || pagination.total_pages <= 1) return;
        
        // 前のページ
        if (pagination.current_page > 1) {
            paginationEl.appendChild(this.createPaginationItem('前へ', pagination.current_page - 1));
        }
        
        // ページ番号
        const startPage = Math.max(1, pagination.current_page - 2);
        const endPage = Math.min(pagination.total_pages, pagination.current_page + 2);
        
        if (startPage > 1) {
            paginationEl.appendChild(this.createPaginationItem('1', 1));
            if (startPage > 2) {
                paginationEl.appendChild(this.createPaginationItem('...', null, true));
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            paginationEl.appendChild(this.createPaginationItem(i.toString(), i, false, i === pagination.current_page));
        }
        
        if (endPage < pagination.total_pages) {
            if (endPage < pagination.total_pages - 1) {
                paginationEl.appendChild(this.createPaginationItem('...', null, true));
            }
            paginationEl.appendChild(this.createPaginationItem(pagination.total_pages.toString(), pagination.total_pages));
        }
        
        // 次のページ
        if (pagination.current_page < pagination.total_pages) {
            paginationEl.appendChild(this.createPaginationItem('次へ', pagination.current_page + 1));
        }
    }
    
    createPaginationItem(text, page, disabled = false, active = false) {
        const li = document.createElement('li');
        li.className = `page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}`;
        
        const link = document.createElement('a');
        link.className = 'page-link';
        link.href = '#';
        link.textContent = text;
        
        if (!disabled && page !== null) {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = page;
                this.loadExecutions();
            });
        }
        
        li.appendChild(link);
        return li;
    }
    
    updateResultsCount(total) {
        document.getElementById('results-count').textContent = `${total}件`;
    }
    
    toggleAutoRefresh(enabled) {
        this.autoRefreshEnabled = enabled;
        
        const btn = document.getElementById('btn-auto-refresh');
        
        if (enabled) {
            btn.classList.add('active', 'auto-refresh-active');
            this.autoRefreshInterval = setInterval(() => {
                this.loadExecutions();
            }, 30000); // 30秒間隔
        } else {
            btn.classList.remove('active', 'auto-refresh-active');
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
                this.autoRefreshInterval = null;
            }
        }
    }
    
    showLoading(show) {
        document.getElementById('loading-state').style.display = show ? 'block' : 'none';
    }
    
    showEmpty(show) {
        document.getElementById('empty-state').style.display = show ? 'block' : 'none';
    }
    
    showError(message) {
        // 簡単なアラート表示
        // 本格的な実装では toast や notification システムを使用
        alert(`エラー: ${message}`);
    }
    
    showSuccess(message) {
        // 簡単なアラート表示
        alert(`成功: ${message}`);
    }
    
    // Utility methods
    formatDateTime(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleString('ja-JP', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    formatDuration(seconds) {
        if (!seconds) return '-';
        
        if (seconds < 60) {
            return `${seconds.toFixed(1)}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.floor(seconds % 60);
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
    
    getDurationClass(seconds) {
        if (!seconds) return '';
        if (seconds < 60) return 'short';
        if (seconds < 300) return 'medium';
        return 'long';
    }
    
    formatSymbolsList(symbolsJson) {
        if (!symbolsJson) return '-';
        try {
            const symbols = JSON.parse(symbolsJson);
            return Array.isArray(symbols) ? symbols.join(', ') : symbolsJson;
        } catch {
            return symbolsJson;
        }
    }
    
    getTypeDisplayName(type) {
        const types = {
            'SYMBOL_ADDITION': '銘柄追加',
            'SCHEDULED_BACKTEST': '定期BT',
            'SCHEDULED_TRAINING': '定期学習',
            'EMERGENCY_RETRAIN': '緊急再学習',
            'MANUAL_EXECUTION': '手動実行'
        };
        return types[type] || type;
    }
    
    getStatusDisplayName(status) {
        const statuses = {
            'PENDING': '待機中',
            'RUNNING': '実行中',
            'SUCCESS': '成功',
            'FAILED': '失敗',
            'CANCELLED': 'キャンセル'
        };
        return statuses[status] || status;
    }
    
    getStatusIcon(status) {
        const icons = {
            'PENDING': 'fa-clock',
            'RUNNING': 'fa-spinner fa-spin',
            'SUCCESS': 'fa-check',
            'FAILED': 'fa-times',
            'CANCELLED': 'fa-ban'
        };
        return icons[status] || 'fa-question';
    }
    
    getStepIcon(status) {
        const icons = {
            'SUCCESS': 'fa-check-circle',
            'FAILED': 'fa-times-circle',
            'RUNNING': 'fa-spinner fa-spin',
            'PENDING': 'fa-clock'
        };
        return icons[status] || 'fa-circle';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.executionLogs = new ExecutionLogsManager();
});