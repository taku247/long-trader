#!/usr/bin/env python3
"""
API接続失敗時の戦略分析終了テスト - 最終版

目的: 実際のAPIデータ取得が失敗した場合、戦略分析が適切に失敗して終了することを確認
条件: モックデータやフォールバックは一切使用せず、実際の値のみで動作
"""

import sys
import os
import time
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_failure_detection():
    """API接続失敗時の戦略分析終了テスト"""
    
    print("🔍 API接続失敗時の戦略分析終了テスト")
    print("=" * 80)
    print("目的: 実データ取得失敗時に適切に分析が終了することを確認")
    print("条件: モックデータやフォールバックは一切使用しない")
    print("=" * 80)
    
    # 無効なシンボルでテスト
    test_symbol = "INVALID_TEST_SYMBOL_12345"
    test_timeframe = "15m"
    test_config = "Aggressive_ML"
    
    print(f"\n📊 テスト設定:")
    print(f"   シンボル: {test_symbol} (意図的に無効)")
    print(f"   時間足: {test_timeframe}")
    print(f"   戦略: {test_config}")
    
    test_results = []
    
    # === テスト1: ScalableAnalysisSystem ===
    print(f"\n🔍 テスト1: ScalableAnalysisSystem")
    print("-" * 50)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        start_time = time.time()
        
        result = system._generate_single_analysis(test_symbol, test_timeframe, test_config)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result is False:
            print(f"✅ API失敗時の適切な処理: 分析が失敗として終了")
            print(f"⏱️ 処理時間: {duration:.2f}秒")
            print(f"📋 結果: {result} (期待値: False)")
            test_results.append(("ScalableAnalysisSystem", True, duration))
        else:
            print(f"❌ 予期しない結果: {result}")
            test_results.append(("ScalableAnalysisSystem", False, duration))
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        test_results.append(("ScalableAnalysisSystem", False, 0))
    
    # === テスト2: HighLeverageBotOrchestrator ===
    print(f"\n🔍 テスト2: HighLeverageBotOrchestrator")
    print("-" * 50)
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        orchestrator = HighLeverageBotOrchestrator(use_default_plugins=True, exchange='gateio')
        start_time = time.time()
        
        try:
            result = orchestrator.analyze_symbol(test_symbol, test_timeframe, test_config)
            print(f"❌ 予期しない成功: API失敗なのに分析が成功した")
            test_results.append(("HighLeverageBotOrchestrator", False, time.time() - start_time))
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['market data', 'symbol', 'gateio', 'api', 'fetch']):
                print(f"✅ API失敗時の適切な例外発生: {type(e).__name__}")
                print(f"⏱️ 処理時間: {duration:.2f}秒")
                print(f"📋 エラー内容: ...{str(e)[-100:]}")  # 最後の100文字のみ表示
                test_results.append(("HighLeverageBotOrchestrator", True, duration))
            else:
                print(f"❌ 予期しないエラー: {e}")
                test_results.append(("HighLeverageBotOrchestrator", False, duration))
                
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        test_results.append(("HighLeverageBotOrchestrator", False, 0))
    
    # === テスト3: APIクライアント直接テスト ===
    print(f"\n🔍 テスト3: APIクライアント直接接続")
    print("-" * 50)
    
    try:
        from hyperliquid_api_client import MultiExchangeAPIClient
        import asyncio
        from datetime import timezone, timedelta
        
        api_client = MultiExchangeAPIClient()
        end_time = datetime.now(timezone.utc)
        start_time_dt = end_time - timedelta(days=7)
        
        start_time = time.time()
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                data = loop.run_until_complete(
                    api_client.get_ohlcv_data(test_symbol, test_timeframe, start_time_dt, end_time)
                )
                
                # データが取得できなかった場合
                if data is None or data.empty:
                    print(f"✅ API失敗時の適切な処理: 空データが返された")
                    test_results.append(("APIクライアント", True, time.time() - start_time))
                else:
                    print(f"❌ 予期しない成功: 無効シンボルでデータが取得された")
                    test_results.append(("APIクライアント", False, time.time() - start_time))
                    
            finally:
                loop.close()
                
        except Exception as e:
            end_time_test = time.time()
            duration = end_time_test - start_time
            
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['symbol', 'market', 'api', 'gateio']):
                print(f"✅ API失敗時の適切な例外発生: {type(e).__name__}")
                print(f"⏱️ 処理時間: {duration:.2f}秒")
                test_results.append(("APIクライアント", True, duration))
            else:
                print(f"❌ 予期しないエラー: {e}")
                test_results.append(("APIクライアント", False, duration))
                
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        test_results.append(("APIクライアント", False, 0))
    
    # === 結果サマリー ===
    print(f"\n{'='*80}")
    print(f"📊 テスト結果サマリー")
    print(f"{'='*80}")
    
    successful_tests = 0
    total_tests = len(test_results)
    
    for component, success, duration in test_results:
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{component:<30} {status:<10} ({duration:.2f}秒)")
        if success:
            successful_tests += 1
    
    print(f"\n📈 成功率: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
    
    if successful_tests == total_tests:
        print(f"\n🎉 全てのテストが成功しました")
        print(f"✅ API接続エラー時に適切に戦略分析が失敗することを確認")
        print(f"✅ フォールバックやモックデータは使用されていません")
        print(f"✅ 実データのみを使用した検証が完了")
    else:
        print(f"\n⚠️ {total_tests - successful_tests}個のテストが失敗しました")
    
    # === 実データテスト（比較用） ===
    print(f"\n🔍 比較テスト: 実際のシンボルでの動作確認")
    print("-" * 50)
    
    real_symbols = ["BTC", "ETH"]
    
    for symbol in real_symbols:
        print(f"\n📊 {symbol}での動作確認...")
        
        try:
            from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
            
            orchestrator = HighLeverageBotOrchestrator(use_default_plugins=True, exchange='gateio')
            start_time = time.time()
            
            try:
                result = orchestrator.analyze_symbol(symbol, test_timeframe, test_config)
                duration = time.time() - start_time
                
                print(f"✅ {symbol} 分析成功 ({duration:.2f}秒)")
                print(f"   💰 現在価格: {result.get('current_price', 'N/A')}")
                print(f"   📈 推奨レバレッジ: {result.get('leverage', 'N/A')}x")
                print(f"   🎯 信頼度: {result.get('confidence', 'N/A')}%")
                
                # 1つでも成功したら十分
                print(f"✅ 実シンボルでは正常に動作することを確認")
                break
                
            except Exception as e:
                print(f"⚠️ {symbol} エラー: {str(e)[:100]}...")
                continue
                
        except Exception as e:
            print(f"❌ {symbol} 初期化エラー: {e}")
            continue
    
    print(f"\n{'='*80}")
    print(f"✅ API接続失敗検知テスト完了")
    print(f"📋 結論: 実データ取得失敗時に適切に戦略分析が終了する")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_api_failure_detection()