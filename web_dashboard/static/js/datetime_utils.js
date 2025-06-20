/**
 * 日時表示ユーティリティ
 * UTC aware対応の日時フォーマット関数
 */

class DateTimeUtils {
    /**
     * UTC時刻でフォーマット（UTC表記付き）
     * @param {string} isoString - ISO 8601文字列
     * @returns {string} フォーマットされた日時文字列
     */
    static formatDateTimeUTC(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        
        // UTC時刻でフォーマット
        const options = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZone: 'UTC'
        };
        
        const formatted = date.toLocaleString('ja-JP', options);
        return `${formatted} UTC`;
    }
    
    /**
     * ローカル時刻でフォーマット（タイムゾーン表記付き）
     * @param {string} isoString - ISO 8601文字列
     * @returns {string} フォーマットされた日時文字列
     */
    static formatDateTimeLocal(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        
        // ローカル時刻でフォーマット
        const options = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        };
        
        const formatted = date.toLocaleString('ja-JP', options);
        const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        return `${formatted} (${timeZone})`;
    }
    
    /**
     * JST時刻でフォーマット（JST表記付き）
     * @param {string} isoString - ISO 8601文字列
     * @returns {string} フォーマットされた日時文字列
     */
    static formatDateTimeJST(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        
        // JST時刻でフォーマット
        const options = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZone: 'Asia/Tokyo'
        };
        
        const formatted = date.toLocaleString('ja-JP', options);
        return `${formatted} JST`;
    }
    
    /**
     * 両方の時刻を表示（UTC + JST）
     * @param {string} isoString - ISO 8601文字列
     * @returns {string} UTC時刻とJST時刻の両方
     */
    static formatDateTimeBoth(isoString) {
        if (!isoString) return '-';
        const utc = this.formatDateTimeUTC(isoString);
        const jst = this.formatDateTimeJST(isoString);
        return `${jst} / ${utc}`;
    }
    
    /**
     * 相対時間表示（〜前）
     * @param {string} isoString - ISO 8601文字列
     * @returns {string} 相対時間文字列
     */
    static formatRelativeTime(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffSeconds < 60) {
            return `${diffSeconds}秒前`;
        } else if (diffMinutes < 60) {
            return `${diffMinutes}分前`;
        } else if (diffHours < 24) {
            return `${diffHours}時間前`;
        } else {
            return `${diffDays}日前`;
        }
    }
    
    /**
     * 実行時間のフォーマット
     * @param {number} seconds - 秒数
     * @returns {string} フォーマットされた実行時間
     */
    static formatDuration(seconds) {
        if (!seconds || seconds < 0) return '-';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}時間${minutes}分${secs}秒`;
        } else if (minutes > 0) {
            return `${minutes}分${secs}秒`;
        } else {
            return `${secs}秒`;
        }
    }
    
    /**
     * 設定可能なフォーマッター
     * @param {string} isoString - ISO 8601文字列
     * @param {Object} options - フォーマットオプション
     * @returns {string} フォーマットされた日時文字列
     */
    static formatDateTime(isoString, options = {}) {
        const {
            showUTC = false,
            showJST = true,
            showBoth = false,
            showSeconds = false,
            showRelative = false
        } = options;
        
        if (!isoString) return '-';
        
        if (showRelative) {
            return this.formatRelativeTime(isoString);
        }
        
        if (showBoth) {
            return this.formatDateTimeBoth(isoString);
        }
        
        if (showUTC) {
            return this.formatDateTimeUTC(isoString);
        }
        
        // デフォルトはJST
        return this.formatDateTimeJST(isoString);
    }
}

// グローバルに公開
window.DateTimeUtils = DateTimeUtils;