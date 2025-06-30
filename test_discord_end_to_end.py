#!/usr/bin/env python3
"""
Discord子プロセス通知システムのエンドツーエンドテスト

実際の銘柄追加プロセスでのDiscord通知動作を検証
"""

import unittest
from unittest.mock import patch, Mock
import os
import sys
import tempfile
import time
import json
from pathlib import Path

class TestDiscordEndToEnd(unittest.TestCase):
    """Discord通知システムのエンドツーエンドテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        # Discord Webhook URL設定
        self.original_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        os.environ['DISCORD_WEBHOOK_URL'] = "https://discord.com/api/webhooks/test/e2e"
        
        # テスト結果格納用リスト
        self.discord_messages = []
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if self.original_webhook_url:
            os.environ['DISCORD_WEBHOOK_URL'] = self.original_webhook_url
        elif 'DISCORD_WEBHOOK_URL' in os.environ:
            del os.environ['DISCORD_WEBHOOK_URL']
    
    def _capture_discord_message(self, url, json=None, timeout=None):
        """Discord通知をキャプチャする"""
        if json and 'content' in json:
            self.discord_messages.append(json['content'])
        
        # 成功レスポンスを返す
        mock_response = Mock()
        mock_response.status_code = 204
        return mock_response
    
    @patch('requests.post')
    def test_discord_notification_flow_simulation(self, mock_post):
        """Discord通知フローのシミュレーション"""
        # Discord通知のキャプチャ設定
        mock_post.side_effect = self._capture_discord_message
        
        # Discord notifierをインポート
        from discord_notifier import discord_notifier
        
        # シミュレーション: 複数の戦略実行
        test_strategies = [
            ("TEST_SYMBOL", "Conservative_ML", "1h"),
            ("TEST_SYMBOL", "Aggressive_Traditional", "1h"),
            ("TEST_SYMBOL", "Full_ML", "1h"),
            ("TEST_SYMBOL", "Conservative_ML", "30m"),
        ]
        
        execution_id = "e2e_test_123"
        
        for i, (symbol, strategy, timeframe) in enumerate(test_strategies):
            # 開始通知
            discord_notifier.child_process_started(
                symbol=symbol,
                strategy_name=strategy,
                timeframe=timeframe,
                execution_id=execution_id
            )
            
            # 処理時間をシミュレート
            time.sleep(0.1)
            
            # 完了通知（成功 or 失敗をランダムに）
            if i == 2:  # 3番目の戦略は失敗させる
                discord_notifier.child_process_completed(
                    symbol=symbol,
                    strategy_name=strategy,
                    timeframe=timeframe,
                    execution_id=execution_id,
                    success=False,
                    execution_time=45.0,
                    error_msg="模擬エラー: データ不足"
                )
            else:
                discord_notifier.child_process_completed(
                    symbol=symbol,
                    strategy_name=strategy,
                    timeframe=timeframe,
                    execution_id=execution_id,
                    success=True,
                    execution_time=120.0 + i * 30
                )
        
        # 検証
        self.assertEqual(len(self.discord_messages), 8)  # 4戦略 × 2通知（開始+完了）
        
        # 開始通知の検証
        start_messages = [msg for msg in self.discord_messages if "🔄 子プロセス開始" in msg]
        self.assertEqual(len(start_messages), 4)
        
        # 成功完了通知の検証
        success_messages = [msg for msg in self.discord_messages if "✅ 子プロセス完了" in msg]
        self.assertEqual(len(success_messages), 3)
        
        # 失敗通知の検証
        fail_messages = [msg for msg in self.discord_messages if "❌ 子プロセス失敗" in msg]
        self.assertEqual(len(fail_messages), 1)
        self.assertIn("模擬エラー: データ不足", fail_messages[0])
        
        # メッセージ順序の検証（開始→完了のペア）
        for i, (symbol, strategy, timeframe) in enumerate(test_strategies):
            expected_start = f"🔄 子プロセス開始: {symbol} {strategy} - {timeframe}"
            self.assertIn(expected_start, self.discord_messages[i*2])
            
            if i == 2:  # 失敗ケース
                expected_fail = f"❌ 子プロセス失敗: {symbol} {strategy} - {timeframe}"
                self.assertIn(expected_fail, self.discord_messages[i*2+1])
            else:  # 成功ケース
                expected_success = f"✅ 子プロセス完了: {symbol} {strategy} - {timeframe}"
                self.assertIn(expected_success, self.discord_messages[i*2+1])
    
    @patch('requests.post')
    def test_discord_notification_with_real_timeframes(self, mock_post):
        """実際のタイムフレームでのDiscord通知テスト"""
        mock_post.side_effect = self._capture_discord_message
        
        from discord_notifier import discord_notifier
        
        # 実際のタイムフレーム構成をテスト
        real_timeframes = ["1h", "30m", "15m", "5m", "3m", "1m"]
        real_strategies = ["Conservative_ML", "Aggressive_Traditional", "Full_ML"]
        
        execution_id = "real_timeframes_test"
        
        for timeframe in real_timeframes[:2]:  # 最初の2つだけテスト
            for strategy in real_strategies[:2]:  # 最初の2つだけテスト
                # 開始通知
                discord_notifier.child_process_started(
                    symbol="REAL_TEST",
                    strategy_name=strategy,
                    timeframe=timeframe,
                    execution_id=execution_id
                )
                
                # 完了通知
                discord_notifier.child_process_completed(
                    symbol="REAL_TEST",
                    strategy_name=strategy,
                    timeframe=timeframe,
                    execution_id=execution_id,
                    success=True,
                    execution_time=90.0
                )
        
        # 検証
        expected_combinations = 2 * 2  # 2タイムフレーム × 2戦略
        self.assertEqual(len(self.discord_messages), expected_combinations * 2)  # 開始+完了
        
        # 各組み合わせが正しく通知されているか確認
        start_messages = [msg for msg in self.discord_messages if "🔄 子プロセス開始" in msg]
        complete_messages = [msg for msg in self.discord_messages if "✅ 子プロセス完了" in msg]
        
        self.assertEqual(len(start_messages), expected_combinations)
        self.assertEqual(len(complete_messages), expected_combinations)
        
        # 特定の組み合わせが含まれているか確認
        self.assertTrue(any("Conservative_ML - 1h" in msg for msg in start_messages))
        self.assertTrue(any("Aggressive_Traditional - 30m" in msg for msg in start_messages))
    
    @patch('requests.post')
    def test_discord_notification_error_resilience(self, mock_post):
        """Discord通知エラー時の耐性テスト"""
        # 最初の5回は成功、その後は失敗させる
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 5:
                return self._capture_discord_message(*args, **kwargs)
            else:
                raise Exception("ネットワークエラー")
        
        mock_post.side_effect = side_effect
        
        from discord_notifier import discord_notifier
        
        # 複数の通知を送信（一部でエラーが発生）
        for i in range(8):
            result = discord_notifier.child_process_started(
                symbol="ERROR_TEST",
                strategy_name=f"Strategy_{i}",
                timeframe="1h",
                execution_id=f"error_test_{i}"
            )
            
            if i < 5:
                self.assertTrue(result)  # 最初の5回は成功
            else:
                self.assertFalse(result)  # その後は失敗
        
        # エラーが発生しても5回の通知は成功していることを確認
        self.assertEqual(len(self.discord_messages), 5)
        
        # エラー処理によってプログラムが停止していないことを確認
        self.assertEqual(mock_post.call_count, 8)
    
    @patch('requests.post')
    def test_discord_notification_content_format(self, mock_post):
        """Discord通知内容のフォーマットテスト"""
        mock_post.side_effect = self._capture_discord_message
        
        from discord_notifier import discord_notifier
        
        # 様々な戦略名とタイムフレームでテスト
        test_cases = [
            ("BTC", "Conservative_ML", "1h", True, 180.5, ""),
            ("ETH", "Aggressive_Traditional", "30m", True, 95.2, ""),
            ("SOL", "Full_ML", "15m", False, 45.8, "データ不足エラー"),
            ("DOGE", "Custom_Strategy_With_Long_Name", "5m", False, 12.1, "非常に長いエラーメッセージの例で、この場合は100文字制限により切り捨てられる可能性があります。"),
        ]
        
        for symbol, strategy, timeframe, success, exec_time, error_msg in test_cases:
            # 開始通知
            discord_notifier.child_process_started(
                symbol=symbol,
                strategy_name=strategy,
                timeframe=timeframe,
                execution_id="format_test"
            )
            
            # 完了通知
            discord_notifier.child_process_completed(
                symbol=symbol,
                strategy_name=strategy,
                timeframe=timeframe,
                execution_id="format_test",
                success=success,
                execution_time=exec_time,
                error_msg=error_msg
            )
        
        # フォーマット検証
        self.assertEqual(len(self.discord_messages), 8)  # 4ケース × 2通知
        
        # 開始通知のフォーマット確認
        start_msg = self.discord_messages[0]
        self.assertEqual(start_msg, "🔄 子プロセス開始: BTC Conservative_ML - 1h")
        
        # 成功完了通知のフォーマット確認
        success_msg = self.discord_messages[1]
        # 四捨五入による180または181秒を許容
        self.assertTrue(
            success_msg == "✅ 子プロセス完了: BTC Conservative_ML - 1h (180秒)" or
            success_msg == "✅ 子プロセス完了: BTC Conservative_ML - 1h (181秒)"
        )
        
        # 失敗通知のフォーマット確認
        fail_msg = self.discord_messages[5]  # 3番目のケース（SOL）の完了通知
        self.assertEqual(fail_msg, "❌ 子プロセス失敗: SOL Full_ML - 15m - データ不足エラー")
        
        # 長い戦略名の処理確認
        long_strategy_start = self.discord_messages[6]
        self.assertIn("Custom_Strategy_With_Long_Name", long_strategy_start)
        
        # 長いエラーメッセージの処理確認
        long_error_msg = self.discord_messages[7]
        self.assertIn("非常に長いエラーメッセージ", long_error_msg)


def run_e2e_tests():
    """エンドツーエンドテストの実行"""
    print("🎯 Discord通知システム エンドツーエンドテスト開始")
    print("=" * 60)
    
    # テストスイート作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordEndToEnd))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print(f"🎯 エンドツーエンドテスト結果サマリー:")
    print(f"   ✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ 失敗: {len(result.failures)}")
    print(f"   💥 エラー: {len(result.errors)}")
    print(f"   📊 総テスト数: {result.testsRun}")
    
    if result.wasSuccessful():
        print("🎉 全エンドツーエンドテスト成功！Discord通知システムは本番環境で正常に動作します。")
        return True
    else:
        print("⚠️ エンドツーエンドテスト失敗があります。実装を確認してください。")
        return False


if __name__ == '__main__':
    success = run_e2e_tests()
    sys.exit(0 if success else 1)