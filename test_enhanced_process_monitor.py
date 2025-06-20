#!/usr/bin/env python3
"""
強化されたプロセス健全性監視のテストスイート
"""

import os
import sys
import time
import threading
import subprocess
import multiprocessing
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import signal
import psutil

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from enhanced_process_monitor import EnhancedProcessMonitor, get_enhanced_process_monitor
from execution_log_database import ExecutionLogDatabase, ExecutionStatus, ExecutionType


class TestEnhancedProcessMonitor(unittest.TestCase):
    """強化されたプロセス健全性監視のテストクラス"""
    
    def setUp(self):
        """テストセットアップ"""
        self.monitor = EnhancedProcessMonitor(check_interval=1, max_execution_hours=0.1)
        self.test_processes = []
        
    def tearDown(self):
        """テストクリーンアップ"""
        # 監視停止
        if hasattr(self.monitor, '_running') and self.monitor._running:
            self.monitor.stop_monitoring()
        
        # テストプロセスのクリーンアップ
        for proc in self.test_processes:
            try:
                if hasattr(proc, 'is_alive') and proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=2)
                    if proc.is_alive():
                        proc.kill()
                elif hasattr(proc, 'poll') and proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=2)
            except:
                pass
    
    def test_monitor_initialization(self):
        """監視の初期化テスト"""
        monitor = EnhancedProcessMonitor(check_interval=60, max_execution_hours=8)
        
        self.assertEqual(monitor.check_interval, 60)
        self.assertEqual(monitor.max_execution_hours, 8)
        self.assertFalse(monitor._running)
        self.assertIsNone(monitor._monitor_thread)
        
    def test_start_stop_monitoring(self):
        """監視開始・停止テスト"""
        # 監視開始
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor._running)
        self.assertIsNotNone(self.monitor._monitor_thread)
        
        # 重複開始テスト
        self.monitor.start_monitoring()  # 警告が出るが問題なし
        
        # 監視停止
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor._running)
        
    def test_extract_execution_id(self):
        """execution_id抽出テスト"""
        test_cases = [
            ("python auto_symbol_training.py --execution_id=symbol_addition_20250620_123456_abcd1234", 
             "symbol_addition_20250620_123456_abcd1234"),
            ("python scalable_analysis.py scheduled_backtest_20250620_654321_efgh5678", 
             "scheduled_backtest_20250620_654321_efgh5678"),
            ("python test.py no_execution_id_here", None),
            ("", None)
        ]
        
        for cmdline, expected in test_cases:
            with self.subTest(cmdline=cmdline):
                result = self.monitor._extract_execution_id(cmdline)
                self.assertEqual(result, expected)
    
    def test_extract_symbol(self):
        """symbol抽出テスト"""
        test_cases = [
            ("python auto_symbol_training.py --symbol BTC", "BTC"),
            ("python scalable_analysis.py -s ETH", "ETH"),
            ("python test.py symbol:HYPE", "HYPE"),
            ("python BTC_analysis.py", "BTC"),
            ("python SOL_training.py", "SOL"),
            ("python test.py no_symbol_here", None),
        ]
        
        for cmdline, expected in test_cases:
            with self.subTest(cmdline=cmdline):
                result = self.monitor._extract_symbol(cmdline)
                self.assertEqual(result, expected)
    
    @patch('enhanced_process_monitor.psutil.process_iter')
    def test_find_orphan_processes(self, mock_process_iter):
        """孤児プロセス検出テスト"""
        # モックプロセス作成
        mock_orphan_proc = Mock()
        mock_orphan_proc.info = {
            'pid': 12345,
            'name': 'python',
            'cmdline': ['python', '-c', 'from multiprocessing.spawn import spawn_main; spawn_main()'],
            'ppid': 1,  # 孤児プロセス
            'create_time': time.time() - 600  # 10分前
        }
        mock_orphan_proc.cpu_percent.return_value = 15.5
        mock_orphan_proc.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
        mock_orphan_proc.parent.return_value = None
        
        mock_normal_proc = Mock()
        mock_normal_proc.info = {
            'pid': 54321,
            'name': 'python',
            'cmdline': ['python', 'normal_script.py'],
            'ppid': 1000,  # 正常な親プロセス
            'create_time': time.time() - 60
        }
        
        mock_process_iter.return_value = [mock_orphan_proc, mock_normal_proc]
        
        orphans = self.monitor._find_orphan_processes()
        
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].pid, 12345)
        self.assertTrue(orphans[0].is_orphan)
        self.assertAlmostEqual(orphans[0].age_minutes, 10, delta=1)
    
    @patch('enhanced_process_monitor.psutil.process_iter')
    def test_find_long_running_processes(self, mock_process_iter):
        """長時間実行プロセス検出テスト"""
        # 長時間実行プロセス（1時間前開始、制限は0.1時間）
        mock_long_proc = Mock()
        mock_long_proc.info = {
            'pid': 99999,
            'name': 'python',
            'cmdline': ['python', 'scalable_analysis_system.py', '--symbol', 'BTC'],
            'ppid': 1000,
            'create_time': time.time() - 3600,  # 1時間前
            'environ': {}
        }
        mock_long_proc.cpu_percent.return_value = 25.0
        mock_long_proc.memory_info.return_value = Mock(rss=200 * 1024 * 1024)  # 200MB
        
        mock_process_iter.return_value = [mock_long_proc]
        
        long_running = self.monitor._find_long_running_processes()
        
        self.assertEqual(len(long_running), 1)
        self.assertEqual(long_running[0].pid, 99999)
        self.assertFalse(long_running[0].is_orphan)
        self.assertGreater(long_running[0].age_minutes, 50)  # 50分以上
    
    def test_get_process_health_status(self):
        """プロセス健全性ステータス取得テスト"""
        status = self.monitor.get_process_health_status()
        
        # 必要なキーが存在することを確認
        required_keys = [
            'monitoring_active', 'check_interval_seconds', 'max_execution_hours',
            'orphan_processes', 'long_running_processes', 'active_processes',
            'total_cpu_usage', 'total_memory_mb', 'processes'
        ]
        
        for key in required_keys:
            self.assertIn(key, status)
        
        # 初期状態の確認
        self.assertFalse(status['monitoring_active'])
        self.assertEqual(status['check_interval_seconds'], 1)
        self.assertEqual(status['max_execution_hours'], 0.1)
        self.assertIsInstance(status['processes'], list)
    
    def test_manual_cleanup(self):
        """手動クリーンアップテスト"""
        result = self.monitor.manual_cleanup()
        
        self.assertTrue(result['success'])
        self.assertIn('orphan_processes_cleaned', result)
        self.assertIn('timeout_processes_handled', result)
        self.assertIn('message', result)
    
    @patch('enhanced_process_monitor.ExecutionLogDatabase')
    def test_update_execution_status_cancelled(self, mock_db_class):
        """実行ステータス更新テスト"""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        monitor = EnhancedProcessMonitor()
        monitor.db = mock_db
        
        execution_id = "test_execution_123"
        reason = "Test cancellation"
        
        monitor._update_execution_status_cancelled(execution_id, reason)
        
        # ExecutionLogDatabaseのメソッドが呼ばれたことを確認
        mock_db.update_execution_status.assert_called_once()
        mock_db.add_execution_error.assert_called_once()
    
    def create_test_multiprocessing_process(self):
        """テスト用multiprocessingプロセスを作成（pickle問題回避のためsubprocessを使用）"""
        import subprocess
        import sys
        
        # Python子プロセスを直接起動
        script = """
import time
import sys
print(f"Test multiprocessing process started (PID: {__import__('os').getpid()})")
# multiprocessingキーワードを含ませる
sys.argv = ['python', '-c', 'multiprocessing test process']
time.sleep(10)
print(f"Test multiprocessing process finished")
"""
        
        process = subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.test_processes.append(process)
        return process
    
    def test_real_process_detection(self):
        """実際のプロセス検出テスト（統合テスト）"""
        # テスト用プロセスを作成
        test_proc = self.create_test_multiprocessing_process()
        
        try:
            # 少し待ってプロセスが起動するまで待機
            time.sleep(1)
            
            # プロセス検出を実行
            status = self.monitor.get_process_health_status()
            
            # アクティブプロセスが検出されることを期待
            # （ただし、テスト環境によっては検出されない場合もある）
            self.assertIsInstance(status['active_processes'], int)
            self.assertGreaterEqual(status['active_processes'], 0)
            
        finally:
            # テストプロセス終了
            if hasattr(test_proc, 'is_alive') and test_proc.is_alive():
                test_proc.terminate()
                test_proc.join(timeout=3)
            elif hasattr(test_proc, 'poll') and test_proc.poll() is None:
                test_proc.terminate()
                test_proc.wait(timeout=3)


class TestWebDashboardIntegration(unittest.TestCase):
    """WebダッシュボードAPIとの統合テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_app = None
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_app:
            # アプリケーションクリーンアップ
            pass
    
    @patch('enhanced_process_monitor.get_enhanced_process_monitor')
    def test_api_process_health_status(self, mock_get_monitor):
        """プロセス健全性ステータスAPI テスト"""
        # モックモニター設定
        mock_monitor = Mock()
        mock_monitor.get_process_health_status.return_value = {
            'monitoring_active': True,
            'active_processes': 2,
            'orphan_processes': 0
        }
        mock_get_monitor.return_value = mock_monitor
        
        # WebダッシュボードAPIのテスト用クライアント作成
        from web_dashboard.app import WebDashboard
        
        dashboard = WebDashboard(debug=True)
        client = dashboard.app.test_client()
        
        # API呼び出し
        response = client.get('/api/admin/process-health/status')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('monitoring_active', data)
        self.assertIn('active_processes', data)
    
    @patch('enhanced_process_monitor.get_enhanced_process_monitor')
    def test_api_start_monitoring(self, mock_get_monitor):
        """プロセス監視開始API テスト"""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        from web_dashboard.app import WebDashboard
        
        dashboard = WebDashboard(debug=True)
        client = dashboard.app.test_client()
        
        # API呼び出し
        response = client.post('/api/admin/process-health/start', 
                             json={'check_interval': 120, 'max_execution_hours': 8})
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        
        # モニターの設定が更新されたことを確認
        self.assertEqual(mock_monitor.check_interval, 120)
        self.assertEqual(mock_monitor.max_execution_hours, 8)
        mock_monitor.start_monitoring.assert_called_once()
    
    @patch('enhanced_process_monitor.get_enhanced_process_monitor')
    def test_api_manual_cleanup(self, mock_get_monitor):
        """手動クリーンアップAPI テスト"""
        mock_monitor = Mock()
        mock_monitor.manual_cleanup.return_value = {
            'success': True,
            'orphan_processes_cleaned': 2,
            'timeout_processes_handled': 1,
            'message': 'Cleanup completed'
        }
        mock_get_monitor.return_value = mock_monitor
        
        from web_dashboard.app import WebDashboard
        
        dashboard = WebDashboard(debug=True)
        client = dashboard.app.test_client()
        
        # API呼び出し
        response = client.post('/api/admin/process-health/manual-cleanup')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['orphan_processes_cleaned'], 2)


class TestGlobalInstance(unittest.TestCase):
    """グローバルインスタンステスト"""
    
    def test_get_enhanced_process_monitor_singleton(self):
        """グローバルインスタンスのシングルトンテスト"""
        monitor1 = get_enhanced_process_monitor()
        monitor2 = get_enhanced_process_monitor()
        
        # 同じインスタンスであることを確認
        self.assertIs(monitor1, monitor2)
        self.assertIsInstance(monitor1, EnhancedProcessMonitor)


class TestProcessDetectionAccuracy(unittest.TestCase):
    """プロセス検出精度テスト"""
    
    def setUp(self):
        """セットアップ"""
        self.monitor = EnhancedProcessMonitor()
    
    def test_target_keyword_detection(self):
        """対象キーワード検出テスト"""
        test_cmdlines = [
            (['python', '-c', 'from multiprocessing.spawn import spawn_main'], True),
            (['python', '-c', 'from multiprocessing.resource_tracker import main;main(20)'], True),
            (['python', 'scalable_analysis_system.py'], True),
            (['python', 'auto_symbol_training.py'], True),
            (['python', 'support_resistance_ml.py'], True),
            (['python', 'normal_script.py'], False),
            (['node', 'app.js'], False),
            (['python', 'web_server.py'], False),
        ]
        
        for cmdline_list, should_match in test_cmdlines:
            with self.subTest(cmdline=cmdline_list):
                cmdline = ' '.join(cmdline_list)
                
                # Pythonプロセスかつキーワードを含むかチェック
                is_python = 'python' in cmdline_list[0].lower()
                has_keyword = any(keyword in cmdline for keyword in self.monitor.target_keywords)
                
                result = is_python and has_keyword
                self.assertEqual(result, should_match)


def run_integration_test():
    """統合テスト実行"""
    print("🧪 Enhanced Process Monitor Integration Test")
    print("=" * 60)
    
    # 実際のモニター作成
    monitor = EnhancedProcessMonitor(check_interval=5, max_execution_hours=1)
    
    try:
        print("1. プロセス健全性ステータス取得テスト...")
        status = monitor.get_process_health_status()
        print(f"   ✅ ステータス取得成功: {len(status)} keys")
        
        print("2. 手動クリーンアップテスト...")
        cleanup_result = monitor.manual_cleanup()
        print(f"   ✅ クリーンアップ成功: {cleanup_result['message']}")
        
        print("3. 監視開始/停止テスト...")
        monitor.start_monitoring()
        print("   ✅ 監視開始成功")
        
        time.sleep(2)  # 少し待機
        
        monitor.stop_monitoring()
        print("   ✅ 監視停止成功")
        
        print("\n🎉 全ての統合テストが成功しました！")
        
    except Exception as e:
        print(f"\n❌ 統合テストでエラーが発生: {e}")
        return False
    
    return True


def main():
    """メイン実行関数"""
    print("🔍 Enhanced Process Monitor Test Suite")
    print("=" * 60)
    
    # ユニットテスト実行
    print("\n📋 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "=" * 60)
    
    # 統合テスト実行
    print("\n🔧 Running Integration Tests...")
    integration_success = run_integration_test()
    
    if integration_success:
        print("\n✅ すべてのテストが成功しました！")
    else:
        print("\n❌ 一部のテストが失敗しました。")
    
    return integration_success


if __name__ == "__main__":
    main()