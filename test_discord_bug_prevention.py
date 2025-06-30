#!/usr/bin/env python3
"""
Discord通知システムのバグ防止テスト

「既存分析でDiscord通知がスキップされる」バグの再発防止に特化したテスト
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# システムパスに追加
sys.path.insert(0, str(Path(__file__).parent))

class TestDiscordBugPrevention(unittest.TestCase):
    """Discord通知システムのバグ防止テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_dir = Path(self.temp_dir) / "test_analysis"
        self.test_db_dir.mkdir(parents=True, exist_ok=True)
        self.test_db_path = self.test_db_dir / "analysis.db"
        
        # テスト用のWebhook URL設定
        self.original_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        os.environ['DISCORD_WEBHOOK_URL'] = "https://discord.com/api/webhooks/test/bug_prevention"
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if self.original_webhook_url:
            os.environ['DISCORD_WEBHOOK_URL'] = self.original_webhook_url
        elif 'DISCORD_WEBHOOK_URL' in os.environ:
            del os.environ['DISCORD_WEBHOOK_URL']
        
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_test_database(self):
        """テスト用データベースの作成"""
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    config TEXT NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    total_return REAL DEFAULT 0.0,
                    win_rate REAL DEFAULT 0.0,
                    sharpe_ratio REAL DEFAULT 0.0,
                    max_drawdown REAL DEFAULT 0.0,
                    avg_leverage REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    execution_id TEXT,
                    task_status TEXT DEFAULT 'pending',
                    task_started_at TEXT,
                    task_completed_at TEXT,
                    error_message TEXT
                )
            ''')
            conn.commit()
    
    @patch('discord_notifier.requests.post')
    def test_bug_existing_analysis_must_send_notifications(self, mock_post):
        """🐛バグ防止: 既存分析でも必ずDiscord通知が送信されることを確認"""
        
        # Discord通知のモック
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # テスト用データベース作成
        self._create_test_database()
        
        # 既存分析データを作成
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO analyses (symbol, timeframe, config, total_trades, total_return, 
                                    win_rate, sharpe_ratio, max_drawdown, avg_leverage, execution_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ("BTC", "1h", "Conservative_ML", 10, 15.5, 0.6, 1.2, -5.0, 2.5, "existing_001"))
            conn.commit()
        
        # ScalableAnalysisSystemのインスタンス作成
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = self.test_db_path
        system.base_dir = self.test_db_dir
        
        # テスト実行: 既存分析を再実行
        result, metrics = system._generate_single_analysis(
            symbol="BTC",
            timeframe="1h",
            config="Conservative_ML",
            execution_id="bug_prevention_test_001"
        )
        
        # 結果検証
        self.assertFalse(result)  # 既存分析のためFalse
        self.assertIsNone(metrics)
        
        # 🐛バグ防止: 既存分析でも必ずDiscord通知が送信される
        self.assertGreaterEqual(mock_post.call_count, 1, 
                               "既存分析でもDiscord通知が送信されるべき")
        
        # 開始通知が送信されていることを確認
        calls = mock_post.call_args_list
        start_notification_found = False
        skip_notification_found = False
        
        for call in calls:
            content = call[1]['json']['content']
            if "🔄 子プロセス開始" in content and "BTC" in content:
                start_notification_found = True
            if "⏩ 子プロセススキップ" in content and "既存分析" in content:
                skip_notification_found = True
        
        self.assertTrue(start_notification_found, "既存分析でも開始通知が送信されるべき")
        self.assertTrue(skip_notification_found, "既存分析ではスキップ通知が送信されるべき")
    
    @patch('discord_notifier.requests.post')
    def test_bug_notification_order_must_be_consistent(self, mock_post):
        """🐛バグ防止: Discord通知の順序が一貫していることを確認"""
        
        # Discord通知のモック
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # テスト用データベース作成
        self._create_test_database()
        
        # ScalableAnalysisSystemのインスタンス作成
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = self.test_db_path
        system.base_dir = self.test_db_dir
        
        # 新規分析と既存分析の両方をテスト
        test_cases = [
            ("NEW_SYMBOL", "1h", "Test_Strategy", True),   # 新規分析
            ("NEW_SYMBOL", "1h", "Test_Strategy", False),  # 既存分析（2回目）
        ]
        
        notification_sequences = []
        
        for symbol, timeframe, config, is_new in test_cases:
            mock_post.reset_mock()
            
            # モック設定
            with patch('scalable_analysis_system.ScalableAnalysisSystem._analysis_exists') as mock_exists:
                with patch('scalable_analysis_system.ScalableAnalysisSystem._generate_real_analysis') as mock_generate:
                    mock_exists.return_value = not is_new  # 新規分析の場合False、既存の場合True
                    mock_generate.return_value = {"test": "data"}
                    
                    with patch('scalable_analysis_system.ScalableAnalysisSystem._calculate_metrics') as mock_metrics:
                        with patch('scalable_analysis_system.ScalableAnalysisSystem._save_compressed_data') as mock_save:
                            with patch('scalable_analysis_system.ScalableAnalysisSystem._should_generate_chart') as mock_chart:
                                with patch('scalable_analysis_system.ScalableAnalysisSystem._save_to_database') as mock_db:
                                    mock_metrics.return_value = {"total_trades": 1}
                                    mock_save.return_value = "/test/path"
                                    mock_chart.return_value = False
                                    
                                    # テスト実行
                                    result, metrics = system._generate_single_analysis(
                                        symbol=symbol,
                                        timeframe=timeframe,
                                        config=config,
                                        execution_id=f"order_test_{len(notification_sequences)}"
                                    )
            
            # 通知順序を記録
            calls = mock_post.call_args_list
            sequence = []
            for call in calls:
                content = call[1]['json']['content']
                if "🔄 子プロセス開始" in content:
                    sequence.append("START")
                elif "✅ 子プロセス完了" in content:
                    sequence.append("SUCCESS")
                elif "⏩ 子プロセススキップ" in content:
                    sequence.append("SKIP")
                elif "❌ 子プロセス失敗" in content:
                    sequence.append("FAIL")
            
            notification_sequences.append((is_new, sequence))
        
        # 通知順序の検証
        for is_new, sequence in notification_sequences:
            self.assertGreater(len(sequence), 0, "必ず何らかの通知が送信されるべき")
            self.assertEqual(sequence[0], "START", "最初の通知は必ず開始通知であるべき")
            
            if is_new:
                self.assertIn("SUCCESS", sequence, "新規分析では成功通知があるべき")
            else:
                self.assertIn("SKIP", sequence, "既存分析ではスキップ通知があるべき")
    
    @patch('discord_notifier.requests.post')
    def test_bug_early_return_must_not_skip_notifications(self, mock_post):
        """🐛バグ防止: 早期リターンでDiscord通知がスキップされないことを確認"""
        
        # Discord通知のモック
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # テスト用データベース作成
        self._create_test_database()
        
        # ScalableAnalysisSystemのインスタンス作成
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = self.test_db_path
        system.base_dir = self.test_db_dir
        
        # 早期リターンが発生する条件をテスト
        early_return_conditions = [
            ("既存分析チェック", True, False),  # _analysis_exists() == True
        ]
        
        for condition_name, analysis_exists, generate_error in early_return_conditions:
            with self.subTest(condition=condition_name):
                mock_post.reset_mock()
                
                with patch('scalable_analysis_system.ScalableAnalysisSystem._analysis_exists') as mock_exists:
                    mock_exists.return_value = analysis_exists
                    
                    if generate_error:
                        with patch('scalable_analysis_system.ScalableAnalysisSystem._generate_real_analysis') as mock_generate:
                            mock_generate.side_effect = Exception("テストエラー")
                            
                            # テスト実行
                            result, metrics = system._generate_single_analysis(
                                symbol="EARLY_RETURN_TEST",
                                timeframe="30m",
                                config="Test_Config",
                                execution_id=f"early_return_{condition_name}"
                            )
                    else:
                        # テスト実行
                        result, metrics = system._generate_single_analysis(
                            symbol="EARLY_RETURN_TEST",
                            timeframe="30m",
                            config="Test_Config",
                            execution_id=f"early_return_{condition_name}"
                        )
                
                # 🐛バグ防止: 早期リターンでもDiscord通知は送信される
                self.assertGreater(mock_post.call_count, 0, 
                                 f"{condition_name}でも Discord通知が送信されるべき")
                
                # 開始通知は必ず送信される
                calls = mock_post.call_args_list
                start_notification_found = False
                for call in calls:
                    content = call[1]['json']['content']
                    if "🔄 子プロセス開始" in content:
                        start_notification_found = True
                        break
                
                self.assertTrue(start_notification_found, 
                              f"{condition_name}でも開始通知が送信されるべき")


def run_bug_prevention_tests():
    """バグ防止テストの実行"""
    print("🐛 Discord通知バグ防止テスト開始")
    print("=" * 60)
    
    # テストスイート作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordBugPrevention))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print(f"🐛 バグ防止テスト結果サマリー:")
    print(f"   ✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ 失敗: {len(result.failures)}")
    print(f"   💥 エラー: {len(result.errors)}")
    print(f"   📊 総テスト数: {result.testsRun}")
    
    if result.wasSuccessful():
        print("🎉 全バグ防止テスト成功！Discord通知システムのバグ防止が確認されました。")
        return True
    else:
        print("⚠️ バグ防止テストで失敗があります。実装を確認してください。")
        for failure in result.failures:
            print(f"   ❌ 失敗: {failure[0]}")
        for error in result.errors:
            print(f"   💥 エラー: {error[0]}")
        return False


if __name__ == '__main__':
    success = run_bug_prevention_tests()
    sys.exit(0 if success else 1)