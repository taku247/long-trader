/**
 * Long Trader Dashboard JavaScript
 */

class Dashboard {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.currentAlerts = [];
        this.currentFilter = 'all';
        this.alertsLimit = 20;
        
        this.init();
    }
    
    init() {
        // Skip socket initialization - using HTTP polling instead
        // this.initializeSocket();
        this.attachEventListeners();
        this.updateStatus();
        this.loadCurrentExchange(); // Load current exchange on startup
        
        // Update status every 10 seconds using HTTP polling
        setInterval(() => {
            this.updateStatus();
        }, 10000);
        
        // Update alerts every 5 seconds
        setInterval(() => {
            this.loadAlerts();
        }, 5000);
    }
    
    initializeSocket() {
        // SocketIO disabled - using HTTP polling instead
        console.log('Using HTTP polling mode instead of WebSocket');
        this.isConnected = true;
        this.updateConnectionStatus('connected', 'HTTP接続');
    }
    
    attachEventListeners() {
        // Monitor control buttons
        document.getElementById('btn-start-monitor').addEventListener('click', () => {
            this.startMonitor();
        });
        
        document.getElementById('btn-stop-monitor').addEventListener('click', () => {
            this.stopMonitor();
        });
        
        
        // Alert filters
        document.querySelectorAll('input[name="alert-filter"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentFilter = e.target.id.replace('filter-', '');
                this.filterAlerts();
            });
        });
        
        // Load more alerts button
        document.getElementById('btn-load-more-alerts').addEventListener('click', () => {
            this.loadMoreAlerts();
        });
        
    }
    
    updateConnectionStatus(status, text) {
        const statusElement = document.getElementById('connection-status');
        statusElement.className = `badge me-3 ${status}`;
        statusElement.textContent = text;
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            
            this.updateSystemStatus(status);
            
            // Also update statistics
            await this.updateStatistics();
            await this.loadAlerts();
            
        } catch (error) {
            console.error('Error updating status:', error);
            this.showMessageBanner('ステータス更新エラー', 'error');
        }
    }
    
    updateSystemStatus(status) {
        // Update monitor status
        const monitorStatus = document.getElementById('monitor-status');
        if (status.running === true) {
            monitorStatus.className = 'badge running';
            monitorStatus.textContent = '動作中';
        } else {
            monitorStatus.className = 'badge stopped';
            monitorStatus.textContent = '停止中';
        }
        
        // Update uptime
        const uptime = this.formatUptime(status.uptime_seconds || 0);
        document.getElementById('uptime').textContent = uptime;
        
        // Update monitored symbols
        const symbols = status.monitored_symbols || [];
        document.getElementById('monitored-symbols-count').textContent = symbols.length;
        
        const symbolsContainer = document.getElementById('monitored-symbols');
        if (symbols.length > 0) {
            symbolsContainer.innerHTML = symbols.map(symbol => 
                `<span class="symbol-tag">${symbol}</span>`
            ).join('');
        } else {
            symbolsContainer.innerHTML = '<span class="text-muted">なし</span>';
        }
        
        // Update last update time
        const lastUpdate = status.start_time ? 
            new Date().toLocaleString('ja-JP') : '-';
        document.getElementById('last-update').textContent = lastUpdate;
    }
    
    async updateStatistics() {
        try {
            const response = await fetch('/api/statistics');
            const stats = await response.json();
            
            document.getElementById('total-alerts').textContent = stats.total_alerts || 0;
            document.getElementById('alerts-24h').textContent = stats.alerts_last_24h || 0;
            
            // Update alerts by type
            const byTypeContainer = document.getElementById('alerts-by-type');
            const byType = stats.by_type || {};
            
            if (Object.keys(byType).length > 0) {
                byTypeContainer.innerHTML = Object.entries(byType).map(([type, count]) => {
                    const label = this.getAlertTypeLabel(type);
                    return `<div class="d-flex justify-content-between">
                        <span>${label}:</span>
                        <span class="badge bg-secondary">${count}</span>
                    </div>`;
                }).join('');
            } else {
                byTypeContainer.innerHTML = '<span class="text-muted">データなし</span>';
            }
            
        } catch (error) {
            console.error('Error updating statistics:', error);
        }
    }
    
    async loadAlerts() {
        try {
            const response = await fetch(`/api/alerts?limit=${this.alertsLimit}`);
            const alerts = await response.json();
            
            this.currentAlerts = alerts;
            this.displayAlerts(alerts);
            
        } catch (error) {
            console.error('Error loading alerts:', error);
            this.showNotification('アラート読み込みエラー', 'error');
        }
    }
    
    async loadMoreAlerts() {
        try {
            this.alertsLimit += 20;
            await this.loadAlerts();
        } catch (error) {
            console.error('Error loading more alerts:', error);
        }
    }
    
    displayAlerts(alerts) {
        const container = document.getElementById('alerts-container');
        
        if (!alerts || alerts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-bell-slash"></i>
                    <p>アラートはありません</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = alerts.map(alert => this.createAlertElement(alert)).join('');
    }
    
    createAlertElement(alert) {
        const timestamp = new Date(alert.timestamp).toLocaleString('ja-JP');
        const typeClass = alert.alert_type.replace('_', '-');
        const priorityClass = `priority-${alert.priority}`;
        
        let metadata = '';
        if (alert.alert_type === 'trading_opportunity') {
            metadata = `
                <div class="alert-metadata">
                    ${alert.leverage ? `<span class="alert-meta-item">レバレッジ: ${alert.leverage.toFixed(1)}x</span>` : ''}
                    ${alert.confidence ? `<span class="alert-meta-item">信頼度: ${alert.confidence.toFixed(1)}%</span>` : ''}
                    ${alert.strategy ? `<span class="alert-meta-item">戦略: ${alert.strategy}</span>` : ''}
                    ${alert.timeframe ? `<span class="alert-meta-item">時間足: ${alert.timeframe}</span>` : ''}
                </div>
            `;
        } else if (alert.symbol) {
            metadata = `
                <div class="alert-metadata">
                    <span class="alert-meta-item">銘柄: ${alert.symbol}</span>
                </div>
            `;
        }
        
        return `
            <div class="alert-item ${typeClass}" data-type="${alert.alert_type}">
                <div class="alert-header">
                    <h6 class="alert-title ${priorityClass}">${alert.title}</h6>
                    <span class="alert-timestamp">${timestamp}</span>
                </div>
                <div class="alert-message">${this.formatAlertMessage(alert.message)}</div>
                ${metadata}
            </div>
        `;
    }
    
    formatAlertMessage(message) {
        // Convert \\n to actual line breaks and format for display
        return message.replace(/\\\\n/g, '<br>').replace(/\\n/g, '<br>');
    }
    
    addNewAlerts(newAlerts) {
        if (!newAlerts || newAlerts.length === 0) return;
        
        // Add new alerts to the beginning of current alerts
        newAlerts.forEach(alert => {
            // Check if alert already exists
            const exists = this.currentAlerts.some(existing => existing.alert_id === alert.alert_id);
            if (!exists) {
                this.currentAlerts.unshift(alert);
                this.showNotification(`新しいアラート: ${alert.title}`, 'info');
            }
        });
        
        // Re-display alerts with current filter
        this.filterAlerts();
    }
    
    filterAlerts() {
        let filteredAlerts = this.currentAlerts;
        
        if (this.currentFilter !== 'all') {
            const filterMap = {
                'trading': 'trading_opportunity',
                'risk': 'risk_warning',
                'system': 'system_status'
            };
            
            const filterType = filterMap[this.currentFilter];
            if (filterType) {
                filteredAlerts = this.currentAlerts.filter(alert => alert.alert_type === filterType);
            }
        }
        
        this.displayAlerts(filteredAlerts);
    }
    
    async startMonitor() {
        try {
            const symbolsInput = document.getElementById('symbols-input').value.trim();
            const intervalInput = document.getElementById('interval-input').value;
            
            const symbols = symbolsInput ? symbolsInput.split(',').map(s => s.trim()) : ['HYPE', 'SOL'];
            const intervalMinutes = parseInt(intervalInput);
            
            const response = await fetch('/api/monitor/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    symbols: symbols,
                    interval_minutes: intervalMinutes
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showMessageBanner('監視システムを開始しました', 'success');
                await this.updateStatus();
            } else {
                this.showMessageBanner(`エラー: ${result.error}`, 'error', false);
            }
            
        } catch (error) {
            console.error('Error starting monitor:', error);
            this.showMessageBanner('監視開始エラー', 'error');
        }
    }
    
    async stopMonitor() {
        try {
            const response = await fetch('/api/monitor/stop', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showMessageBanner('監視システムを停止しました', 'warning');
                await this.updateStatus();
            } else {
                this.showMessageBanner(`エラー: ${result.error}`, 'error', false);
            }
            
        } catch (error) {
            console.error('Error stopping monitor:', error);
            this.showMessageBanner('監視停止エラー', 'error');
        }
    }
    
    clearAlerts() {
        this.currentAlerts = [];
        this.displayAlerts([]);
        this.showNotification('アラート履歴をクリアしました', 'info');
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

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>${message}</span>
                <button type="button" class="btn-close btn-close-sm" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    formatUptime(seconds) {
        if (seconds < 60) {
            return `${seconds}秒`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            return `${minutes}分`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}時間${minutes}分`;
        }
    }
    
    getAlertTypeLabel(type) {
        const labels = {
            'trading_opportunity': '取引機会',
            'risk_warning': 'リスク警告',
            'system_status': 'システム',
            'error': 'エラー'
        };
        return labels[type] || type;
    }
    
    // Exchange Management Methods
    async loadCurrentExchange() {
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
    
    async loadAlerts() {
        try {
            const response = await fetch(`/api/alerts?limit=${this.alertsLimit}`);
            if (response.ok) {
                const alerts = await response.json();
                this.displayAlerts(alerts);
            }
        } catch (error) {
            console.error('Error loading alerts:', error);
        }
    }
    
    async switchExchange(exchange) {
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
                this.showNotification(data.message, 'success');
                
                // Refresh the page after a short delay to ensure all systems use new exchange
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                
            } else {
                this.showNotification(data.error || 'Failed to switch exchange', 'error');
            }
        } catch (error) {
            console.error('Error switching exchange:', error);
            this.showNotification('Error switching exchange', 'error');
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});

// Global function for HTML onclick handlers
function switchExchange(exchange) {
    if (window.dashboard) {
        window.dashboard.switchExchange(exchange);
    }
}