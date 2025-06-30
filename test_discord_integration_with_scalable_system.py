#!/usr/bin/env python3
"""
Discord通知とscalable_analysis_systemの統合テスト

実際の_generate_single_analysis関数でのDiscord通知統合をテスト
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# システムパスに追加
sys.path.insert(0, str(Path(__file__).parent))

class TestDiscordScalableSystemIntegration(unittest.TestCase):
    """Discord通知とscalable_analysis_systemの統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        # ディレクトリパスをテストDBパスとして使用（ScalableAnalysisSystemがディレクトリを期待するため）
        self.test_db_dir = Path(self.temp_dir) / "test_analysis"
        self.test_db_dir.mkdir(parents=True, exist_ok=True)
        self.test_db_path = self.test_db_dir / "analysis.db"
        
        # テスト用のWebhook URL設定
        self.original_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        os.environ['DISCORD_WEBHOOK_URL'] = "https://discord.com/api/webhooks/test/integration"
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if self.original_webhook_url:
            os.environ['DISCORD_WEBHOOK_URL'] = self.original_webhook_url
        elif 'DISCORD_WEBHOOK_URL' in os.environ:
            del os.environ['DISCORD_WEBHOOK_URL']
        
        # 一時ファイル削除
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_test_database(self):
        """テスト用データベースの作成"""
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    config TEXT NOT NULL,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_trades INTEGER,
                    win_rate REAL,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    avg_leverage REAL,
                    chart_path TEXT,
                    compressed_path TEXT,
                    status TEXT DEFAULT 'pending',
                    execution_id TEXT,
                    task_status TEXT DEFAULT 'pending',
                    task_started_at TIMESTAMP,
                    task_completed_at TIMESTAMP,
                    error_message TEXT
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON analyses (symbol, timeframe)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_config ON analyses (config)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sharpe ON analyses (sharpe_ratio)')
            
            conn.commit()
    
    @patch('discord_notifier.requests.post')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._generate_real_analysis')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._analysis_exists')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._calculate_metrics')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._save_compressed_data')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._should_generate_chart')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._save_to_database')
    def test_successful_analysis_with_discord_notifications(self, 
                                                           mock_save_db,
                                                           mock_should_chart,
                                                           mock_save_compressed,
                                                           mock_calc_metrics,
                                                           mock_analysis_exists,
                                                           mock_generate_real,
                                                           mock_post):
        """成功分析時のDiscord通知統合テスト"""
        
        # テスト用データベース作成
        self._create_test_database()
        
        # モック設定
        mock_analysis_exists.return_value = False
        mock_generate_real.return_value = {"test": "data"}
        mock_calc_metrics.return_value = {
            "total_trades": 10,
            "win_rate": 0.6,
            "total_return_pct": 15.5
        }
        mock_save_compressed.return_value = "/test/path"
        mock_should_chart.return_value = False
        
        # Discord通知のモック
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # ScalableAnalysisSystemのインスタンス作成（初期化をスキップ）
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = self.test_db_path
        system.base_dir = self.test_db_dir
        
        # テスト実行
        result, metrics = system._generate_single_analysis(
            symbol="TEST_SOL",
            timeframe="1h", 
            config="Conservative_ML",
            execution_id="test123456"
        )
        
        # 結果検証
        self.assertTrue(result)
        self.assertIsNotNone(metrics)
        
        # Discord通知が2回呼ばれることを確認（開始・完了）
        self.assertEqual(mock_post.call_count, 2)
        
        # 通知内容の検証
        calls = mock_post.call_args_list
        
        # 1回目: 開始通知
        start_call = calls[0]
        start_message = start_call[1]['json']['content']
        self.assertIn("🔄 子プロセス開始: TEST_SOL Conservative_ML - 1h", start_message)
        
        # 2回目: 完了通知
        complete_call = calls[1]
        complete_message = complete_call[1]['json']['content']
        self.assertIn("✅ 子プロセス完了: TEST_SOL Conservative_ML - 1h", complete_message)
        self.assertIn("秒)", complete_message)
    
    @patch('discord_notifier.requests.post')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._generate_real_analysis')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._analysis_exists')
    def test_failed_analysis_with_discord_notifications(self, 
                                                       mock_analysis_exists,
                                                       mock_generate_real,
                                                       mock_post):
        """失敗分析時のDiscord通知統合テスト"""
        
        # テスト用データベース作成
        self._create_test_database()
        
        # モック設定
        mock_analysis_exists.return_value = False
        mock_generate_real.side_effect = Exception("テストエラー: データ不足")
        
        # Discord通知のモック
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # ScalableAnalysisSystemのインスタンス作成（初期化をスキップ）
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = self.test_db_path
        system.base_dir = self.test_db_dir
        
        # テスト実行
        result, metrics = system._generate_single_analysis(
            symbol="TEST_FAIL",
            timeframe="30m", 
            config="Aggressive_Traditional",
            execution_id="fail123456"
        )
        
        # 結果検証
        self.assertFalse(result)
        self.assertIsNone(metrics)
        
        # Discord通知が2回呼ばれることを確認（開始・失敗）
        self.assertEqual(mock_post.call_count, 2)
        
        # 通知内容の検証
        calls = mock_post.call_args_list
        
        # 1回目: 開始通知
        start_call = calls[0]
        start_message = start_call[1]['json']['content']
        self.assertIn("🔄 子プロセス開始: TEST_FAIL Aggressive_Traditional - 30m", start_message)
        
        # 2回目: 失敗通知
        fail_call = calls[1]
        fail_message = fail_call[1]['json']['content']
        self.assertIn("❌ 子プロセス失敗: TEST_FAIL Aggressive_Traditional - 30m", fail_message)
        self.assertIn("テストエラー: データ不足", fail_message)
    
    @patch('discord_notifier.requests.post')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._analysis_exists')
    def test_existing_analysis_skip_with_discord_notifications(self, 
                                                              mock_analysis_exists,
                                                              mock_post):
        """🐛バグ防止: 既存分析スキップ時でもDiscord通知が送られることを確認"""
        
        # テスト用データベース作成
        self._create_test_database()
        
        # モック設定: 既存分析があることをシミュレート
        mock_analysis_exists.return_value = True
        
        # Discord通知のモック
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # ScalableAnalysisSystemのインスタンス作成（初期化をスキップ）
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = self.test_db_path
        system.base_dir = self.test_db_dir
        
        # テスト実行
        result, metrics = system._generate_single_analysis(
            symbol="EXISTING",
            timeframe="15m", 
            config="Full_ML",
            execution_id="existing123"
        )
        
        # 結果検証
        self.assertFalse(result)  # 既存分析のためFalse
        self.assertIsNone(metrics)
        
        # 🐛バグ防止: 既存分析でもDiscord通知が2回送られることを確認
        self.assertEqual(mock_post.call_count, 2)  # 開始通知 + スキップ通知
        
        # 通知内容の検証
        calls = mock_post.call_args_list
        
        # 1回目: 開始通知
        start_call = calls[0]
        start_message = start_call[1]['json']['content']
        self.assertIn("🔄 子プロセス開始: EXISTING Full_ML - 15m", start_message)
        
        # 2回目: スキップ通知
        skip_call = calls[1]
        skip_message = skip_call[1]['json']['content']
        self.assertIn("⏩ 子プロセススキップ: EXISTING Full_ML - 15m", skip_message)
        self.assertIn("既存分析", skip_message)
    
    @patch('discord_notifier.requests.post')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._generate_real_analysis')
    @patch('scalable_analysis_system.ScalableAnalysisSystem._analysis_exists')
    def test_discord_notification_failure_does_not_break_analysis(self, 
                                                                 mock_analysis_exists,
                                                                 mock_generate_real,
                                                                 mock_post):
        """Discord通知失敗時に分析処理が中断されないテスト"""
        
        # テスト用データベース作成  
        self._create_test_database()
        
        # モック設定
        mock_analysis_exists.return_value = False
        mock_generate_real.side_effect = Exception("分析エラー")
        # Discord通知でエラーを発生させる
        mock_post.side_effect = Exception("Discord通信エラー")
        
        # ScalableAnalysisSystemのインスタンス作成（初期化をスキップ）
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem.__new__(ScalableAnalysisSystem)
        system.db_path = self.test_db_path
        system.base_dir = self.test_db_dir
        
        # テスト実行（例外が発生してもプログラムが停止しないこと）
        result, metrics = system._generate_single_analysis(
            symbol="DISCORD_FAIL",
            timeframe="5m", 
            config="Test_Strategy",
            execution_id="discord_fail123"
        )
        
        # 結果検証: 分析自体は失敗するが、プログラムは正常に動作
        self.assertFalse(result)
        self.assertIsNone(metrics)
        
        # Discord通知が試行されることを確認
        self.assertEqual(mock_post.call_count, 2)  # 開始と失敗の2回試行


class TestDiscordEnvironmentVariableHandling(unittest.TestCase):
    """Discord通知の環境変数処理テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.original_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if self.original_webhook_url:
            os.environ['DISCORD_WEBHOOK_URL'] = self.original_webhook_url
        elif 'DISCORD_WEBHOOK_URL' in os.environ:
            del os.environ['DISCORD_WEBHOOK_URL']
    
    def test_discord_disabled_without_webhook_url(self):
        """Webhook URL未設定時のDiscord無効化テスト"""
        # 環境変数を削除
        if 'DISCORD_WEBHOOK_URL' in os.environ:
            del os.environ['DISCORD_WEBHOOK_URL']
        
        # DiscordNotifierのインスタンス作成
        from discord_notifier import DiscordNotifier
        notifier = DiscordNotifier()
        
        # 無効化されていることを確認
        self.assertFalse(notifier.enabled)
        self.assertIsNone(notifier.webhook_url)
    
    def test_discord_enabled_with_webhook_url(self):
        """Webhook URL設定時のDiscord有効化テスト"""
        # 環境変数を設定
        test_url = "https://discord.com/api/webhooks/test/environment"
        os.environ['DISCORD_WEBHOOK_URL'] = test_url
        
        # DiscordNotifierのインスタンス作成
        from discord_notifier import DiscordNotifier
        notifier = DiscordNotifier()
        
        # 有効化されていることを確認
        self.assertTrue(notifier.enabled)
        self.assertEqual(notifier.webhook_url, test_url)


def run_integration_tests():
    """統合テストの実行"""
    print("🔗 Discord通知とscalable_analysis_system統合テスト開始")
    print("=" * 60)
    
    # テストスイート作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordScalableSystemIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordEnvironmentVariableHandling))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print(f"🔗 統合テスト結果サマリー:")
    print(f"   ✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ 失敗: {len(result.failures)}")
    print(f"   💥 エラー: {len(result.errors)}")
    print(f"   📊 総テスト数: {result.testsRun}")
    
    if result.wasSuccessful():
        print("🎉 全統合テスト成功！Discord通知システムとscalable_analysis_systemは正常に統合されています。")
        return True
    else:
        print("⚠️ 統合テスト失敗があります。実装を確認してください。")
        return False


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)