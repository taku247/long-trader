#!/usr/bin/env python3
"""
TOKEN001系の1000.0ハードコード値の発生箇所を特定するデバッグスクリプト

実際にTOKEN001の分析を実行して、どこで1000.0が生成されているかをトレース
"""

import sys
import os
import pandas as pd
from datetime import datetime, timezone, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_token001_analysis():
    """TOKEN001の分析をデバッグ実行"""
    print("🔍 TOKEN001分析のデバッグ実行")
    print("=" * 50)
    
    try:
        # ScalableAnalysisSystemを使ってTOKEN001を分析
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # TOKEN001の分析を1件だけ実行
        print("\n📊 TOKEN001_1m_Config_19 の分析を実行...")
        
        try:
            result = system._generate_single_analysis(
                symbol="TOKEN001",
                timeframe="1m", 
                strategy="Config_19"
            )
            
            print("✅ 分析結果:")
            print(f"   結果の型: {type(result)}")
            
            if isinstance(result, list):
                print(f"   件数: {len(result)}")
                if result:
                    first_trade = result[0]
                    print(f"   最初のトレード: {first_trade}")
                    
                    if 'entry_price' in first_trade:
                        print(f"   🎯 entry_price: {first_trade['entry_price']}")
                    if 'take_profit_price' in first_trade:
                        print(f"   🎯 take_profit_price: {first_trade.get('take_profit_price', 'N/A')}")
                    if 'stop_loss_price' in first_trade:
                        print(f"   🎯 stop_loss_price: {first_trade.get('stop_loss_price', 'N/A')}")
            
        except Exception as e:
            print(f"❌ 分析エラー: {e}")
            print(f"   エラータイプ: {type(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ システム初期化エラー: {e}")

def debug_bot_orchestrator_directly():
    """HighLeverageBotOrchestratorを直接テスト"""
    print("\n🔍 HighLeverageBotOrchestrator直接テスト")
    print("=" * 50)
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange="gateio")
        
        # TOKEN001で分析を実行
        print("\n📊 TOKEN001の分析を実行...")
        
        try:
            result = bot.analyze_symbol("TOKEN001", "1m", "Config_19")
            
            print("✅ Bot分析結果:")
            print(f"   結果の型: {type(result)}")
            print(f"   内容: {result}")
            
            if isinstance(result, dict):
                current_price = result.get('current_price')
                print(f"   🎯 current_price: {current_price}")
                entry_price = result.get('entry_price')
                print(f"   🎯 entry_price: {entry_price}")
                
        except Exception as e:
            print(f"❌ Bot分析エラー: {e}")
            print(f"   エラータイプ: {type(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Bot初期化エラー: {e}")

def debug_api_client_token001():
    """APIクライアントでTOKEN001データ取得を試行"""
    print("\n🔍 APIクライアントでTOKEN001データ取得テスト")
    print("=" * 50)
    
    try:
        from hyperliquid_api_client import MultiExchangeAPIClient
        import asyncio
        
        client = MultiExchangeAPIClient()
        
        # 90日間のデータを取得を試行
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=90)
        
        print(f"📅 期間: {start_time} → {end_time}")
        
        # 非同期でデータを取得
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("🔄 TOKEN001のOHLCVデータ取得中...")
            data = loop.run_until_complete(
                client.get_ohlcv_data("TOKEN001", "1m", start_time, end_time)
            )
            
            print("✅ データ取得結果:")
            print(f"   データの型: {type(data)}")
            
            if data is not None and not data.empty:
                print(f"   データ件数: {len(data)}")
                print(f"   カラム: {list(data.columns)}")
                print(f"   最新価格: {data['close'].iloc[-1]}")
                
                # 最初の数件を表示
                print(f"   最初の3件:")
                print(data.head(3))
            else:
                print("   ❌ データが空またはNone")
                
        except Exception as e:
            print(f"❌ データ取得エラー: {e}")
            print(f"   エラータイプ: {type(e)}")
            import traceback
            traceback.print_exc()
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ APIクライアント初期化エラー: {e}")

def check_test_orchestrator_usage():
    """TestHighLeverageBotOrchestratorが使用されているかチェック"""
    print("\n🔍 TestHighLeverageBotOrchestrator使用状況チェック")
    print("=" * 50)
    
    try:
        from engines.test_high_leverage_bot_orchestrator import TestHighLeverageBotOrchestrator
        
        test_bot = TestHighLeverageBotOrchestrator()
        
        # TOKEN001で分析を実行
        print("📊 TestHighLeverageBotOrchestratorでTOKEN001分析...")
        
        result = test_bot.analyze_leverage_opportunity("TOKEN001", "1m")
        
        print("✅ TestBot分析結果:")
        print(f"   結果の型: {type(result)}")
        print(f"   recommended_leverage: {result.recommended_leverage}")
        print(f"   current_price: {result.market_conditions.current_price}")
        print(f"   stop_loss_price: {result.stop_loss_price}")
        print(f"   take_profit_price: {result.take_profit_price}")
        
        # analyze_symbolメソッドがあるかチェック
        if hasattr(test_bot, 'analyze_symbol'):
            print("\n📊 analyze_symbolメソッドでテスト...")
            symbol_result = test_bot.analyze_symbol("TOKEN001", "1m", "Config_19")
            print(f"   analyze_symbol結果: {symbol_result}")
        else:
            print("   ❌ analyze_symbolメソッドなし")
            
    except Exception as e:
        print(f"❌ TestBot実行エラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン実行関数"""
    print("🔍 TOKEN001系 1000.0ハードコード値 発生箇所デバッグ")
    print("=" * 60)
    
    # 1. ScalableAnalysisSystemを使った分析
    debug_token001_analysis()
    
    # 2. HighLeverageBotOrchestratorを直接使った分析
    debug_bot_orchestrator_directly()
    
    # 3. APIクライアントでのデータ取得テスト
    debug_api_client_token001()
    
    # 4. TestHighLeverageBotOrchestrator使用状況チェック
    check_test_orchestrator_usage()
    
    print("\n" + "=" * 60)
    print("✅ デバッグ完了")
    print("=" * 60)

if __name__ == '__main__':
    main()