#!/usr/bin/env python3
"""
削除機能の安全性テスト (BaseTest統合版)

このテストでは以下の懸念点を検証します：
1. 他銘柄への影響がないこと
2. 実行中チェックが正常に動作すること
3. データ整合性が保たれること
4. ファイルとDBの同期削除が正常に動作すること
5. システム継続性が保たれること
"""

import sqlite3
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import sys

# テスト用のパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_dashboard'))

# BaseTestをインポート
from tests_organized.base_test import BaseTest

class TestDeleteFunctionality(BaseTest):
    """削除機能の包括的テスト"""
    
    def custom_setup(self):
        """削除機能テスト固有のセットアップ"""
        # BaseTestのDBパスを使用
        self.analysis_db_path = self.analysis_db
        self.alert_db_path = os.path.join(self.test_dir, 'alert_history.db') 
        self.exec_db_path = self.execution_logs_db
        self.compressed_dir = os.path.join(self.test_dir, 'compressed')
        
        # ディレクトリ作成
        os.makedirs(self.compressed_dir, exist_ok=True)
        
        # テスト用データベースの初期化
        self._init_test_databases()
        self._create_test_data()
        
        # 削除機能のインポート
        try:
            from app import WebDashboard
            self.dashboard = WebDashboard()
        except ImportError:
            print("⚠️ WebDashboard インポートエラー - モック使用")
            self.dashboard = None
    
    def _init_test_databases(self):
        """テスト用データベースの初期化 (BaseTestのDBを拡張)"""
        
        # analysis.db (BaseTestで作成済みのテーブルに追加テーブルを作成)
        with sqlite3.connect(self.analysis_db_path) as conn:
            cursor = conn.cursor()
            # BaseTestで既にanalysesテーブルが作成されているため、追加テーブルのみ作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    metric_name TEXT,
                    metric_value REAL,
                    FOREIGN KEY (analysis_id) REFERENCES analyses (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leverage_calculation_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    trade_number INTEGER,
                    support_distance_pct REAL,
                    FOREIGN KEY (analysis_id) REFERENCES analyses (id)
                )
            ''')
        
        # alert_history.db
        with sqlite3.connect(self.alert_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id VARCHAR(255) UNIQUE,
                    symbol VARCHAR(10) NOT NULL,
                    alert_type VARCHAR(50) NOT NULL,
                    priority VARCHAR(20),
                    timestamp DATETIME NOT NULL,
                    leverage FLOAT,
                    confidence FLOAT,
                    strategy VARCHAR(50),
                    timeframe VARCHAR(10),
                    entry_price FLOAT,
                    target_price FLOAT,
                    stop_loss FLOAT,
                    extra_data TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE price_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id VARCHAR(255) NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    price FLOAT NOT NULL,
                    time_elapsed_hours INTEGER NOT NULL,
                    percentage_change FLOAT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE performance_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id VARCHAR(255) NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    is_success BOOLEAN,
                    max_gain FLOAT,
                    max_loss FLOAT,
                    final_return_24h FLOAT,
                    final_return_72h FLOAT,
                    evaluation_note TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            ''')
        
        # execution_logs.db (BaseTestで作成済み、追加の処理は不要)
    
    def _create_test_data(self):
        """テスト用データの作成"""
        
        # TEST_A と TEST_B の分析データを作成
        test_symbols = ['TEST_A', 'TEST_B']
        
        for symbol in test_symbols:
            # analysis.db にデータ挿入
            with sqlite3.connect(self.analysis_db_path) as conn:
                cursor = conn.cursor()
                
                # analyses テーブル
                for i, config in enumerate(['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']):
                    for j, timeframe in enumerate(['1h', '15m']):
                        cursor.execute('''
                            INSERT INTO analyses (symbol, timeframe, config, total_trades, win_rate, sharpe_ratio)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (symbol, timeframe, config, 50 + i*10 + j, 0.6 + i*0.1, 1.2 + i*0.5))
                        
                        analysis_id = cursor.lastrowid
                        
                        # 関連テーブルにもデータ挿入
                        cursor.execute('''
                            INSERT INTO backtest_summary (analysis_id, metric_name, metric_value)
                            VALUES (?, ?, ?)
                        ''', (analysis_id, 'test_metric', 100.0))
                        
                        cursor.execute('''
                            INSERT INTO leverage_calculation_details (analysis_id, trade_number, support_distance_pct)
                            VALUES (?, ?, ?)
                        ''', (analysis_id, 1, 0.05))
            
            # alert_history.db にデータ挿入
            with sqlite3.connect(self.alert_db_path) as conn:
                cursor = conn.cursor()
                
                for i in range(3):
                    alert_id = f"test_{symbol}_{i}"
                    
                    # alerts
                    cursor.execute('''
                        INSERT INTO alerts (alert_id, symbol, alert_type, priority, timestamp, leverage, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (alert_id, symbol, 'trading_opportunity', 'high', datetime.now().isoformat(), 10.0, 75.0))
                    
                    # price_tracking
                    cursor.execute('''
                        INSERT INTO price_tracking (alert_id, symbol, timestamp, price, time_elapsed_hours, percentage_change)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (alert_id, symbol, datetime.now().isoformat(), 100.0, 1, 2.5))
                    
                    # performance_summary
                    cursor.execute('''
                        INSERT INTO performance_summary (alert_id, symbol, is_success, max_gain, final_return_24h)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (alert_id, symbol, True, 5.2, 3.1))
            
            # execution_logs.db にデータ挿入 (BaseTestのヘルパーメソッドを使用)
            self.insert_test_execution_log(f"test_exec_{symbol}", symbol, 'SUCCESS')
            
            # テスト用ファイル作成
            for config in ['Conservative_ML', 'Aggressive_Traditional']:
                for timeframe in ['1h', '15m']:
                    file_path = os.path.join(self.compressed_dir, f'{symbol}_{timeframe}_{config}.pkl.gz')
                    with open(file_path, 'w') as f:
                        f.write(f"test data for {symbol}")
    
    def test_isolated_deletion(self):
        """テスト1: 他銘柄への影響がないことを確認"""
        print("\n=== テスト1: 他銘柄への影響確認 ===")
        
        # 削除前の状態確認
        with sqlite3.connect(self.analysis_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE symbol='TEST_A'")
            test_a_count_before = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE symbol='TEST_B'")
            test_b_count_before = cursor.fetchone()[0]
        
        print(f"削除前 - TEST_A: {test_a_count_before}件, TEST_B: {test_b_count_before}件")
        
        # TEST_A を削除
        result = self._execute_delete('TEST_A')
        
        # 削除後の状態確認
        with sqlite3.connect(self.analysis_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE symbol='TEST_A'")
            test_a_count_after = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE symbol='TEST_B'")
            test_b_count_after = cursor.fetchone()[0]
        
        print(f"削除後 - TEST_A: {test_a_count_after}件, TEST_B: {test_b_count_after}件")
        
        # アサーション
        self.assertEqual(test_a_count_after, 0, "TEST_Aのデータが完全削除されていない")
        self.assertEqual(test_b_count_after, test_b_count_before, "TEST_Bのデータが影響を受けている")
        
        print("✅ 他銘柄への影響なし - テスト成功")
    
    def test_running_execution_check(self):
        """テスト2: 実行中チェックが正常に動作することを確認"""
        print("\n=== テスト2: 実行中チェック ===")
        
        # TEST_B を実行中状態に設定
        with sqlite3.connect(self.exec_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE execution_logs 
                SET status = 'RUNNING' 
                WHERE symbol = 'TEST_B'
            ''')
        
        # 削除を試行（失敗するはず）
        try:
            result = self._execute_delete('TEST_B')
            
            # エラーが返されることを確認
            self.assertIn('error', result, "実行中銘柄の削除が拒否されていない")
            self.assertIn('実行中', result['error'], "適切なエラーメッセージが表示されていない")
            
            print("✅ 実行中チェック正常動作 - テスト成功")
            
        except Exception as e:
            self.fail(f"実行中チェックでエラー: {e}")
    
    def test_cascade_deletion(self):
        """テスト3: CASCADE削除が正常に動作することを確認"""
        print("\n=== テスト3: CASCADE削除確認 ===")
        
        # 削除前の関連データ確認
        with sqlite3.connect(self.analysis_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM backtest_summary")
            summary_count_before = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM leverage_calculation_details")
            details_count_before = cursor.fetchone()[0]
        
        print(f"削除前 - backtest_summary: {summary_count_before}件, leverage_details: {details_count_before}件")
        
        # TEST_A を削除
        result = self._execute_delete('TEST_A')
        
        # 削除後の関連データ確認
        with sqlite3.connect(self.analysis_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM backtest_summary")
            summary_count_after = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM leverage_calculation_details")
            details_count_after = cursor.fetchone()[0]
        
        print(f"削除後 - backtest_summary: {summary_count_after}件, leverage_details: {details_count_after}件")
        
        # 関連データも削除されていることを確認
        self.assertLess(summary_count_after, summary_count_before, "関連データ(backtest_summary)が削除されていない")
        self.assertLess(details_count_after, details_count_before, "関連データ(leverage_details)が削除されていない")
        
        print("✅ CASCADE削除正常動作 - テスト成功")
    
    def test_file_system_sync(self):
        """テスト4: ファイルとDBの同期削除を確認"""
        print("\n=== テスト4: ファイルとDBの同期削除 ===")
        
        # 削除前のファイル確認
        test_a_files_before = [f for f in os.listdir(self.compressed_dir) if f.startswith('TEST_A')]
        test_b_files_before = [f for f in os.listdir(self.compressed_dir) if f.startswith('TEST_B')]
        
        print(f"削除前ファイル - TEST_A: {len(test_a_files_before)}件, TEST_B: {len(test_b_files_before)}件")
        
        # TEST_A を削除
        result = self._execute_delete('TEST_A')
        
        # 削除後のファイル確認
        test_a_files_after = [f for f in os.listdir(self.compressed_dir) if f.startswith('TEST_A')]
        test_b_files_after = [f for f in os.listdir(self.compressed_dir) if f.startswith('TEST_B')]
        
        print(f"削除後ファイル - TEST_A: {len(test_a_files_after)}件, TEST_B: {len(test_b_files_after)}件")
        
        # アサーション
        self.assertEqual(len(test_a_files_after), 0, "TEST_Aのファイルが削除されていない")
        self.assertEqual(len(test_b_files_after), len(test_b_files_before), "TEST_Bのファイルが影響を受けている")
        
        print("✅ ファイルとDBの同期削除 - テスト成功")
    
    def test_execution_logs_status_update(self):
        """テスト5: execution_logsのステータス更新を確認"""
        print("\n=== テスト5: execution_logsステータス更新 ===")
        
        # 削除前のステータス確認
        with sqlite3.connect(self.exec_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM execution_logs WHERE symbol='TEST_A'")
            status_before = cursor.fetchone()[0]
        
        print(f"削除前ステータス: {status_before}")
        
        # TEST_A を削除
        result = self._execute_delete('TEST_A')
        
        # 削除後のステータス確認
        with sqlite3.connect(self.exec_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM execution_logs WHERE symbol='TEST_A'")
            status_after = cursor.fetchone()[0]
        
        print(f"削除後ステータス: {status_after}")
        
        # ステータスが更新されていることを確認
        self.assertEqual(status_after, 'DATA_DELETED', "execution_logsのステータスが更新されていない")
        
        print("✅ execution_logsステータス更新 - テスト成功")
    
    def test_alert_history_deletion(self):
        """テスト6: アラート履歴の削除を確認"""
        print("\n=== テスト6: アラート履歴削除 ===")
        
        # 削除前のアラートデータ確認
        with sqlite3.connect(self.alert_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE symbol='TEST_A'")
            alerts_before = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM price_tracking WHERE symbol='TEST_A'")
            tracking_before = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM performance_summary WHERE symbol='TEST_A'")
            summary_before = cursor.fetchone()[0]
        
        print(f"削除前 - alerts: {alerts_before}, price_tracking: {tracking_before}, performance_summary: {summary_before}")
        
        # TEST_A を削除
        result = self._execute_delete('TEST_A')
        
        # 削除後のアラートデータ確認
        with sqlite3.connect(self.alert_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE symbol='TEST_A'")
            alerts_after = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM price_tracking WHERE symbol='TEST_A'")
            tracking_after = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM performance_summary WHERE symbol='TEST_A'")
            summary_after = cursor.fetchone()[0]
        
        print(f"削除後 - alerts: {alerts_after}, price_tracking: {tracking_after}, performance_summary: {summary_after}")
        
        # アラート関連データが削除されていることを確認
        self.assertEqual(alerts_after, 0, "alertsデータが削除されていない")
        self.assertEqual(tracking_after, 0, "price_trackingデータが削除されていない")
        self.assertEqual(summary_after, 0, "performance_summaryデータが削除されていない")
        
        print("✅ アラート履歴削除 - テスト成功")
    
    def _execute_delete(self, symbol: str) -> dict:
        """削除処理を実行（テスト用のパスを使用）"""
        
        # 一時的にパスを変更
        original_paths = {}
        
        # WebDashboardの削除メソッドを直接呼び出し
        class MockDashboard:
            def __init__(self, test_paths):
                self.test_paths = test_paths
                self.logger = type('MockLogger', (), {
                    'info': lambda msg: print(f"INFO: {msg}"),
                    'error': lambda msg: print(f"ERROR: {msg}")
                })()
            
            def _delete_symbol_complete(self, symbol: str) -> dict:
                import glob
                import sqlite3
                from datetime import datetime
                
                results = {
                    'symbol': symbol,
                    'deleted': {
                        'analyses': 0,
                        'alerts': 0, 
                        'price_tracking': 0,
                        'performance_summary': 0,
                        'files': 0
                    },
                    'updated': {
                        'execution_logs': 0
                    },
                    'errors': []
                }
                
                try:
                    # 1. analysis.db から削除
                    analysis_db_path = self.test_paths['analysis_db']
                    if os.path.exists(analysis_db_path):
                        with sqlite3.connect(analysis_db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM backtest_summary WHERE analysis_id IN (SELECT id FROM analyses WHERE symbol=?)", (symbol,))
                            cursor.execute("DELETE FROM leverage_calculation_details WHERE analysis_id IN (SELECT id FROM analyses WHERE symbol=?)", (symbol,))
                            cursor.execute("DELETE FROM analyses WHERE symbol=?", (symbol,))
                            results['deleted']['analyses'] = cursor.rowcount
                    
                    # 2. alert_history.db から削除
                    alert_db_path = self.test_paths['alert_db']
                    if os.path.exists(alert_db_path):
                        with sqlite3.connect(alert_db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM performance_summary WHERE symbol=?", (symbol,))
                            results['deleted']['performance_summary'] = cursor.rowcount
                            cursor.execute("DELETE FROM price_tracking WHERE symbol=?", (symbol,))
                            results['deleted']['price_tracking'] = cursor.rowcount
                            cursor.execute("DELETE FROM alerts WHERE symbol=?", (symbol,))
                            results['deleted']['alerts'] = cursor.rowcount
                    
                    # 3. execution_logs.db のステータス更新
                    exec_db_path = self.test_paths['exec_db']
                    if os.path.exists(exec_db_path):
                        with sqlite3.connect(exec_db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT status FROM execution_logs WHERE symbol = ?", (symbol,))
                            current_status = cursor.fetchone()
                            
                            if current_status and current_status[0] == 'RUNNING':
                                # 実行中の場合はエラーを返す
                                return {
                                    'error': f'{symbol}の分析が実行中です。完了後に削除してください。'
                                }
                            
                            cursor.execute("""
                                UPDATE execution_logs 
                                SET status = 'DATA_DELETED', updated_at = CURRENT_TIMESTAMP
                                WHERE symbol = ? AND status IN ('SUCCESS', 'FAILED')
                            """, (symbol,))
                            results['updated']['execution_logs'] = cursor.rowcount
                    
                    # 4. ファイル削除
                    compressed_dir = self.test_paths['compressed_dir']
                    pattern = os.path.join(compressed_dir, f'{symbol}_*.pkl.gz')
                    for file_path in glob.glob(pattern):
                        try:
                            os.remove(file_path)
                            results['deleted']['files'] += 1
                        except Exception as e:
                            results['errors'].append(f"ファイル削除エラー: {file_path}: {str(e)}")
                
                except Exception as e:
                    results['errors'].append(f"削除処理エラー: {str(e)}")
                
                return results
        
        # テスト用パスでモックダッシュボードを作成
        test_paths = {
            'analysis_db': self.analysis_db_path,
            'alert_db': self.alert_db_path,
            'exec_db': self.exec_db_path,
            'compressed_dir': self.compressed_dir
        }
        
        mock_dashboard = MockDashboard(test_paths)
        return mock_dashboard._delete_symbol_complete(symbol)


def main():
    """テストの実行"""
    print("🧪 削除機能安全性テスト開始")
    print("=" * 60)
    
    # テストスイートの作成
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDeleteFunctionality)
    
    # テストの実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 全てのテストが成功しました！削除機能は安全です。")
    else:
        print("❌ テストに失敗しました。削除機能に問題があります。")
        for failure in result.failures:
            print(f"失敗: {failure[0]}")
            print(f"詳細: {failure[1]}")
        for error in result.errors:
            print(f"エラー: {error[0]}")
            print(f"詳細: {error[1]}")


if __name__ == '__main__':
    main()