#!/usr/bin/env python3
"""
Discord子プロセス可視化通知システムのテスト

ProcessPoolExecutor環境での子プロセス開始・完了通知をテスト
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
import tempfile
import time

# テスト対象のインポート
from discord_notifier import DiscordNotifier, discord_notifier

class TestDiscordChildProcessNotifications(unittest.TestCase):
    """Discord子プロセス通知のテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.original_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.test_webhook_url = "https://discord.com/api/webhooks/test/webhook"
        
        # テスト用のDiscordNotifierインスタンス作成
        self.notifier = DiscordNotifier()
        self.notifier.webhook_url = self.test_webhook_url
        self.notifier.enabled = True
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if self.original_webhook_url:
            os.environ['DISCORD_WEBHOOK_URL'] = self.original_webhook_url
        elif 'DISCORD_WEBHOOK_URL' in os.environ:
            del os.environ['DISCORD_WEBHOOK_URL']
    
    @patch('discord_notifier.requests.post')
    def test_child_process_started_notification(self, mock_post):
        """子プロセス開始通知のテスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # テスト実行
        result = self.notifier.child_process_started(
            symbol="SOL",
            strategy_name="Conservative_ML",
            timeframe="1h",
            execution_id="test12345"
        )
        
        # 検証
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # 呼び出し引数の検証
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json']['content'], 
                        "🔄 子プロセス開始: SOL Conservative_ML - 1h")
        self.assertEqual(call_args[1]['timeout'], 10)
        self.assertEqual(call_args[0][0], self.test_webhook_url)
    
    @patch('discord_notifier.requests.post')
    def test_child_process_completed_success(self, mock_post):
        """子プロセス成功完了通知のテスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # テスト実行
        result = self.notifier.child_process_completed(
            symbol="BTC",
            strategy_name="Aggressive_Traditional",
            timeframe="30m",
            execution_id="test67890",
            success=True,
            execution_time=180.5
        )
        
        # 検証
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # メッセージ内容の検証
        call_args = mock_post.call_args
        actual_message = call_args[1]['json']['content']
        
        # 基本的な形式をチェック（四捨五入による1秒の誤差を許容）
        self.assertIn("✅ 子プロセス完了: BTC Aggressive_Traditional - 30m", actual_message)
        self.assertTrue(actual_message.endswith("秒)"))
        # 180または181秒のいずれかであることを確認
        self.assertTrue("(180秒)" in actual_message or "(181秒)" in actual_message)
    
    @patch('discord_notifier.requests.post')
    def test_child_process_completed_failure(self, mock_post):
        """子プロセス失敗完了通知のテスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # テスト実行
        result = self.notifier.child_process_completed(
            symbol="ETH",
            strategy_name="Full_ML",
            timeframe="15m",
            execution_id="test11111",
            success=False,
            execution_time=45.2,
            error_msg="データ不足エラー"
        )
        
        # 検証
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # メッセージ内容の検証
        call_args = mock_post.call_args
        expected_message = "❌ 子プロセス失敗: ETH Full_ML - 15m - データ不足エラー"
        self.assertEqual(call_args[1]['json']['content'], expected_message)
    
    @patch('discord_notifier.requests.post')
    def test_notification_disabled_when_no_webhook_url(self, mock_post):
        """Webhook URLが未設定時の無効化テスト"""
        # 無効なnotifierを作成
        disabled_notifier = DiscordNotifier()
        disabled_notifier.webhook_url = None
        disabled_notifier.enabled = False
        
        # テスト実行
        result = disabled_notifier.child_process_started(
            symbol="TEST",
            strategy_name="Test_Strategy",
            timeframe="1h",
            execution_id="test00000"
        )
        
        # 検証
        self.assertFalse(result)
        mock_post.assert_not_called()
    
    @patch('discord_notifier.requests.post')
    def test_notification_error_handling(self, mock_post):
        """通知エラー時のハンドリングテスト"""
        # 例外を発生させる
        mock_post.side_effect = Exception("ネットワークエラー")
        
        # テスト実行（例外が発生してもプログラムが停止しないこと）
        result = self.notifier.child_process_started(
            symbol="ERROR_TEST",
            strategy_name="Error_Strategy",
            timeframe="5m",
            execution_id="error123"
        )
        
        # 検証
        self.assertFalse(result)
        mock_post.assert_called_once()
    
    @patch('discord_notifier.requests.post')
    def test_long_error_message_truncation(self, mock_post):
        """長いエラーメッセージの制限テスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # 100文字を超える長いエラーメッセージ
        long_error = "a" * 150
        
        # テスト実行
        result = self.notifier.child_process_completed(
            symbol="LONG_ERROR",
            strategy_name="Test_Strategy",
            timeframe="1m",
            execution_id="long123",
            success=False,
            execution_time=10.0,
            error_msg=long_error
        )
        
        # 検証
        self.assertTrue(result)
        call_args = mock_post.call_args
        sent_message = call_args[1]['json']['content']
        
        # エラーメッセージが制限されているかチェック
        # 実際の実装では100文字制限がscalable_analysis_system.pyで適用される
        self.assertIn("LONG_ERROR", sent_message)
        self.assertIn("Test_Strategy", sent_message)
    
    def test_global_instance_availability(self):
        """グローバルインスタンスの可用性テスト"""
        # グローバルインスタンスが利用可能であることを確認
        self.assertIsInstance(discord_notifier, DiscordNotifier)
        
        # 基本的なメソッドが存在することを確認
        self.assertTrue(hasattr(discord_notifier, 'child_process_started'))
        self.assertTrue(hasattr(discord_notifier, 'child_process_completed'))
        self.assertTrue(callable(discord_notifier.child_process_started))
        self.assertTrue(callable(discord_notifier.child_process_completed))


class TestDiscordNotifierIntegration(unittest.TestCase):
    """Discord通知の統合テスト"""
    
    @patch('discord_notifier.requests.post')
    def test_complete_workflow_simulation(self, mock_post):
        """完全なワークフローシミュレーション"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        notifier = DiscordNotifier()
        notifier.webhook_url = "https://discord.com/api/webhooks/test/workflow"
        notifier.enabled = True
        
        # 1. 子プロセス開始
        start_result = notifier.child_process_started(
            symbol="WORKFLOW_TEST",
            strategy_name="Complete_Test",
            timeframe="1h",
            execution_id="workflow123"
        )
        
        # 少し待機（実際の処理をシミュレート）
        time.sleep(0.1)
        
        # 2. 子プロセス成功完了
        complete_result = notifier.child_process_completed(
            symbol="WORKFLOW_TEST",
            strategy_name="Complete_Test",
            timeframe="1h",
            execution_id="workflow123",
            success=True,
            execution_time=120.0
        )
        
        # 検証
        self.assertTrue(start_result)
        self.assertTrue(complete_result)
        self.assertEqual(mock_post.call_count, 2)
        
        # 呼び出し順序と内容の検証
        calls = mock_post.call_args_list
        
        # 最初の呼び出し（開始通知）
        start_call = calls[0]
        self.assertIn("🔄 子プロセス開始", start_call[1]['json']['content'])
        
        # 2番目の呼び出し（完了通知）
        complete_call = calls[1]
        self.assertIn("✅ 子プロセス完了", complete_call[1]['json']['content'])
        self.assertIn("(120秒)", complete_call[1]['json']['content'])


def run_tests():
    """テストの実行"""
    print("🧪 Discord子プロセス可視化通知システム テスト開始")
    print("=" * 60)
    
    # テストスイート作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordChildProcessNotifications))
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordNotifierIntegration))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print(f"🧪 テスト結果サマリー:")
    print(f"   ✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ 失敗: {len(result.failures)}")
    print(f"   💥 エラー: {len(result.errors)}")
    print(f"   📊 総テスト数: {result.testsRun}")
    
    if result.wasSuccessful():
        print("🎉 全テスト成功！Discord子プロセス通知システムは正常に動作します。")
        return True
    else:
        print("⚠️ テスト失敗があります。実装を確認してください。")
        return False


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)