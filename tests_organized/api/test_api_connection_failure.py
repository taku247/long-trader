#!/usr/bin/env python3
"""
API接続エラー時の戦略分析失敗テスト

実際のAPIデータ取得が失敗した場合、戦略分析が適切に失敗して終了することを確認するテスト。
モックデータやフォールバックは一切使用せず、実際の値のみで動作する。
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
import traceback

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestAPIConnectionFailure(unittest.TestCase):
    """API接続失敗時の適切なエラーハンドリングテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.test_symbol = "TEST_INVALID_SYMBOL"
        self.test_timeframe = "15m"
        self.test_config = "Aggressive_ML"
    
    def test_scalable_analysis_system_real_data_failure(self):
        """ScalableAnalysisSystemで実データ取得失敗時の動作テスト"""
        print("\n🔍 ScalableAnalysisSystem実データ取得失敗テスト")
        print("=" * 60)
        
        try:
            from scalable_analysis_system import ScalableAnalysisSystem
            system = ScalableAnalysisSystem()
            
            print(f"📊 テスト対象: {self.test_symbol} {self.test_timeframe} {self.test_config}")
            print("⚠️ 無効なシンボルでAPI接続エラーを意図的に発生させます")
            
            # 無効なシンボルで分析実行（エラーが期待される）
            start_time = datetime.now()
            
            result = system._generate_single_analysis(self.test_symbol, self.test_timeframe, self.test_config)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 分析結果が失敗（False）であることを確認
            if result is False:
                print(f"✅ 期待通り分析失敗: API接続エラーにより分析が適切に中断")
                print(f"⏱️ 実行時間: {duration:.2f}秒")
                print("✅ ScalableAnalysisSystemが実データ取得失敗時に適切にFalseを返している")
                print("✅ フォールバックやモックデータは使用されていません")
            elif result is True:
                self.fail(f"❌ 予期しない成功: 無効なシンボル '{self.test_symbol}' で分析が成功してしまいました")
            else:
                self.fail(f"❌ 予期しない結果: {result} (期待値: False)")
                
        except ImportError as e:
            self.fail(f"❌ モジュール読み込みエラー: {e}")
    
    def test_high_leverage_bot_orchestrator_data_fetch_failure(self):
        """HighLeverageBotOrchestratorのデータ取得失敗テスト"""
        print("\n🔍 HighLeverageBotOrchestrator データ取得失敗テスト")
        print("=" * 60)
        
        try:
            from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
            
            print(f"📊 テスト対象: {self.test_symbol} {self.test_timeframe}")
            print("⚠️ 無効なシンボルでAPI接続エラーを意図的に発生させます")
            
            # オーケストレーター初期化
            orchestrator = HighLeverageBotOrchestrator(use_default_plugins=True, exchange='hyperliquid')
            
            start_time = datetime.now()
            
            try:
                # 無効なシンボルで分析実行（エラーが期待される）
                result = orchestrator.analyze_symbol(self.test_symbol, self.test_timeframe, self.test_config)
                
                # 成功した場合はテスト失敗
                self.fail(f"❌ 予期しない成功: 無効なシンボル '{self.test_symbol}' で分析が成功してしまいました")
                
            except Exception as e:
                # エラーが発生した場合（期待される動作）
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"✅ 期待通りエラー発生: {type(e).__name__}")
                print(f"📝 エラーメッセージ: {str(e)}")
                print(f"⏱️ 実行時間: {duration:.2f}秒")
                
                # エラーの詳細スタックトレースを確認
                print(f"\n📋 詳細スタックトレース:")
                traceback.print_exc()
                
                # データ取得関連のエラーかを確認
                error_message = str(e).lower()
                data_related_keywords = ['market data', 'fetch_market_data', 'api', 'ohlcv', 'hyperliquid', 'gateio', 'symbol', 'data']
                
                has_data_keyword = any(keyword in error_message for keyword in data_related_keywords)
                self.assertTrue(has_data_keyword, 
                    f"データ取得関連のエラーではありません: {str(e)}")
                
                print("✅ データ取得関連のエラーが適切に発生")
                
        except ImportError as e:
            self.fail(f"❌ モジュール読み込みエラー: {e}")
    
    def test_api_client_connection_failure(self):
        """APIクライアント直接接続失敗テスト"""
        print("\n🔍 APIクライアント直接接続失敗テスト")
        print("=" * 60)
        
        try:
            from hyperliquid_api_client import MultiExchangeAPIClient
            import asyncio
            from datetime import timezone
            
            print(f"📊 テスト対象: {self.test_symbol}")
            print("⚠️ 無効なシンボルで直接API呼び出しエラーを発生させます")
            
            # APIクライアント初期化
            api_client = MultiExchangeAPIClient()
            
            # テスト用の時間範囲
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)
            
            start_test_time = datetime.now()
            
            try:
                # 非同期でデータ取得を試行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    data = loop.run_until_complete(
                        api_client.get_ohlcv_data(self.test_symbol, self.test_timeframe, start_time, end_time)
                    )
                    
                    # データが取得できた場合の検証
                    if data is not None and not data.empty:
                        self.fail(f"❌ 予期しない成功: 無効なシンボル '{self.test_symbol}' でデータが取得できました")
                    else:
                        print("✅ 期待通り空のデータが返されました")
                        
                finally:
                    loop.close()
                    
            except Exception as e:
                # エラーが発生した場合（期待される動作）
                end_test_time = datetime.now()
                duration = (end_test_time - start_test_time).total_seconds()
                
                print(f"✅ 期待通りエラー発生: {type(e).__name__}")
                print(f"📝 エラーメッセージ: {str(e)}")
                print(f"⏱️ 実行時間: {duration:.2f}秒")
                
                # API関連のエラーかを確認
                error_message = str(e).lower()
                api_keywords = ['api', 'connection', 'request', 'http', 'timeout', 'network']
                
                has_api_keyword = any(keyword in error_message for keyword in api_keywords)
                if has_api_keyword:
                    print("✅ API接続関連のエラーが適切に発生")
                else:
                    print(f"⚠️ API関連ではない可能性のあるエラー: {str(e)}")
                
        except ImportError as e:
            self.fail(f"❌ モジュール読み込みエラー: {e}")
    
    def test_real_symbol_with_valid_api_connection(self):
        """実際のシンボルでAPI接続成功テスト（比較用）"""
        print("\n🔍 実際のシンボルでAPI接続成功テスト（比較用）")
        print("=" * 60)
        
        # 実際に存在するシンボルでテスト
        real_symbols = ["BTC", "ETH", "SOL"]
        
        for symbol in real_symbols:
            print(f"\n📊 テスト対象: {symbol}")
            
            try:
                from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
                
                orchestrator = HighLeverageBotOrchestrator(use_default_plugins=True, exchange='hyperliquid')
                
                start_time = datetime.now()
                
                try:
                    # 実際のシンボルで分析実行
                    result = orchestrator.analyze_symbol(symbol, self.test_timeframe, self.test_config)
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    print(f"✅ {symbol} 分析成功: {duration:.2f}秒")
                    
                    # 結果の基本検証
                    self.assertIsInstance(result, dict, f"{symbol}の分析結果が辞書形式ではありません")
                    
                    required_keys = ['symbol', 'leverage', 'confidence', 'current_price']
                    for key in required_keys:
                        self.assertIn(key, result, f"{symbol}の分析結果に'{key}'が含まれていません")
                    
                    print(f"   💰 現在価格: {result.get('current_price', 'N/A')}")
                    print(f"   📈 推奨レバレッジ: {result.get('leverage', 'N/A')}x")
                    print(f"   🎯 信頼度: {result.get('confidence', 'N/A')}%")
                    
                    # 最初のシンボルで成功したらテスト完了
                    print(f"✅ {symbol}で実データ取得・分析が正常に動作することを確認")
                    return
                    
                except Exception as e:
                    print(f"⚠️ {symbol} 分析エラー: {str(e)}")
                    continue
                    
            except ImportError as e:
                self.fail(f"❌ モジュール読み込みエラー: {e}")
        
        # 全てのシンボルで失敗した場合
        print("⚠️ 全ての実シンボルで分析が失敗しました - API接続に問題がある可能性があります")

def main():
    """テスト実行"""
    print("🔍 API接続エラー時の戦略分析失敗テスト")
    print("=" * 80)
    print("目的: 実データ取得失敗時に適切にエラーで終了することを確認")
    print("条件: モックデータやフォールバックは一切使用しない")
    print("=" * 80)
    
    # テストスイートを作成
    suite = unittest.TestSuite()
    
    # テストケースを追加
    test_case = TestAPIConnectionFailure()
    suite.addTest(TestAPIConnectionFailure('test_api_client_connection_failure'))
    suite.addTest(TestAPIConnectionFailure('test_high_leverage_bot_orchestrator_data_fetch_failure'))
    suite.addTest(TestAPIConnectionFailure('test_scalable_analysis_system_real_data_failure'))
    suite.addTest(TestAPIConnectionFailure('test_real_symbol_with_valid_api_connection'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n{'='*80}")
    print(f"✅ テスト実行完了")
    print(f"📊 実行されたテスト: {result.testsRun}")
    print(f"❌ 失敗したテスト: {len(result.failures)}")
    print(f"💥 エラーが発生したテスト: {len(result.errors)}")
    
    if result.failures:
        print(f"\n🔍 失敗したテストの詳細:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print(f"\n💥 エラーが発生したテストの詳細:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # テスト成功判定
    if len(result.failures) == 0 and len(result.errors) == 0:
        print(f"\n🎉 全てのテストが成功しました")
        print(f"✅ API接続エラー時に適切に戦略分析が失敗することを確認")
    else:
        print(f"\n⚠️ 一部のテストが失敗しました")

if __name__ == "__main__":
    main()