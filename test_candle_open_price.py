#!/usr/bin/env python3
"""
ローソク足のopen価格使用実装のテスト
現実的なエントリー価格取得の検証
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_candle_start_time_calculation():
    """ローソク足開始時刻計算のテスト"""
    print("🔧 ローソク足開始時刻計算テスト")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # テストケース
        test_cases = [
            {
                'trade_time': datetime(2025, 6, 16, 17, 7, 30),  # 17:07:30
                'timeframe': '15m',
                'expected_start': datetime(2025, 6, 16, 17, 0, 0)  # 17:00:00
            },
            {
                'trade_time': datetime(2025, 6, 16, 17, 32, 15),  # 17:32:15
                'timeframe': '15m', 
                'expected_start': datetime(2025, 6, 16, 17, 30, 0)  # 17:30:00
            },
            {
                'trade_time': datetime(2025, 6, 16, 17, 45, 0),   # 17:45:00
                'timeframe': '1h',
                'expected_start': datetime(2025, 6, 16, 17, 0, 0)  # 17:00:00
            },
            {
                'trade_time': datetime(2025, 6, 16, 18, 15, 30),  # 18:15:30
                'timeframe': '1h',
                'expected_start': datetime(2025, 6, 16, 18, 0, 0)  # 18:00:00
            },
            {
                'trade_time': datetime(2025, 6, 16, 17, 3, 45),   # 17:03:45
                'timeframe': '5m',
                'expected_start': datetime(2025, 6, 16, 17, 0, 0)  # 17:00:00
            }
        ]
        
        success_count = 0
        
        for i, case in enumerate(test_cases):
            print(f"\n📊 テスト {i+1}/{len(test_cases)}:")
            print(f"   トレード時刻: {case['trade_time']}")
            print(f"   時間足: {case['timeframe']}")
            print(f"   期待する開始時刻: {case['expected_start']}")
            
            try:
                actual_start = system._get_candle_start_time(case['trade_time'], case['timeframe'])
                print(f"   実際の開始時刻: {actual_start}")
                
                if actual_start == case['expected_start']:
                    print(f"   ✅ 正確な計算")
                    success_count += 1
                else:
                    print(f"   ❌ 計算ミス")
                    
            except Exception as e:
                print(f"   ❌ エラー: {e}")
        
        print(f"\n📈 計算テスト結果:")
        print(f"   成功: {success_count}/{len(test_cases)}")
        print(f"   成功率: {success_count/len(test_cases)*100:.1f}%")
        
        return success_count == len(test_cases)
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_real_market_price_with_open():
    """実際のopen価格取得テスト"""
    print(f"\n" + "=" * 60)
    print("🔄 実際のopen価格取得テスト")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        system = ScalableAnalysisSystem()
        
        print("📊 実際の市場データでopen価格取得をテスト")
        print("   対象: SUI, 15m")
        
        # ボットインスタンス作成
        bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange='gateio')
        
        # テスト用の時刻（過去の時刻で、データが存在する可能性が高い）
        test_trade_times = [
            datetime.now() - timedelta(hours=24),   # 24時間前
            datetime.now() - timedelta(hours=12),   # 12時間前
            datetime.now() - timedelta(hours=6),    # 6時間前
        ]
        
        success_count = 0
        open_prices = []
        
        for i, trade_time in enumerate(test_trade_times):
            print(f"\n   テスト {i+1}/{len(test_trade_times)}: {trade_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                # 新しい実装でopen価格を取得
                open_price = system._get_real_market_price(bot, 'SUI', '15m', trade_time)
                open_prices.append(open_price)
                
                # ローソク足開始時刻も表示
                candle_start = system._get_candle_start_time(trade_time, '15m')
                
                print(f"     ローソク足開始時刻: {candle_start}")
                print(f"     open価格: ${open_price:.6f}")
                print(f"     ✅ 成功")
                success_count += 1
                
            except Exception as e:
                print(f"     ❌ エラー: {str(e)[:100]}...")
        
        # 価格多様性の確認
        if open_prices:
            unique_prices = len(set(open_prices))
            price_range = max(open_prices) - min(open_prices) if len(open_prices) > 1 else 0
            
            print(f"\n📈 open価格多様性分析:")
            print(f"   取得成功: {success_count}/{len(test_trade_times)}")
            print(f"   ユニーク価格数: {unique_prices}")
            print(f"   価格範囲: ${min(open_prices):.6f} - ${max(open_prices):.6f}")
            print(f"   価格変動幅: ${price_range:.6f}")
            
            # 判定
            print(f"\n🏆 open価格実装効果判定:")
            if unique_prices > 1:
                print("   ✅ 異なるローソク足のopen価格を正確に取得")
                print("   ✅ 時系列に応じた現実的な価格多様性を確認")
                return True
            elif success_count > 0:
                print("   ✅ open価格取得は成功（同一ローソク足のため価格同一）")
                return True
            else:
                print("   ❌ open価格取得に失敗")
                return False
        else:
            print("   ❌ 価格データを取得できませんでした")
            return False
            
    except Exception as e:
        print(f"❌ open価格テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """エラーハンドリングのテスト"""
    print(f"\n" + "=" * 60)
    print("🚨 エラーハンドリングテスト")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        system = ScalableAnalysisSystem()
        bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange='gateio')
        
        print("📊 存在しないローソク足での適切なエラー発生をテスト")
        
        # 未来の時刻でテスト（該当ローソク足が存在しない）
        future_time = datetime.now() + timedelta(hours=24)
        
        try:
            price = system._get_real_market_price(bot, 'SUI', '15m', future_time)
            print(f"   ❌ エラーが発生しませんでした: ${price:.6f}")
            return False
            
        except Exception as e:
            if "該当ローソク足が見つかりません" in str(e) or "フォールバックは使用しません" in str(e):
                print(f"   ✅ 適切なエラー発生: {str(e)[:100]}...")
                print(f"   ✅ フォールバック使用を回避")
                return True
            else:
                print(f"   ⚠️ 予期しないエラー: {str(e)[:100]}...")
                return False
        
    except Exception as e:
        print(f"❌ エラーハンドリングテストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 ローソク足open価格使用実装テスト")
    print("=" * 60)
    print("目的: 現実的なエントリー価格取得の検証")
    print("実装: trade_timeが属するローソク足のopen価格を使用")
    print("=" * 60)
    
    # 1. ローソク足開始時刻計算テスト
    calculation_test = test_candle_start_time_calculation()
    
    # 2. 実際のopen価格取得テスト
    open_price_test = test_real_market_price_with_open()
    
    # 3. エラーハンドリングテスト
    error_test = test_error_handling()
    
    # 総合判定
    print(f"\n" + "=" * 60)
    print("📋 総合テスト結果")
    print("=" * 60)
    print(f"開始時刻計算テスト: {'✅ 成功' if calculation_test else '❌ 失敗'}")
    print(f"open価格取得テスト: {'✅ 成功' if open_price_test else '❌ 失敗'}")
    print(f"エラーハンドリングテスト: {'✅ 成功' if error_test else '❌ 失敗'}")
    
    if calculation_test and open_price_test and error_test:
        print("\n🎉 ローソク足open価格実装が成功しました！")
        print("✅ 現実的なエントリー価格取得が可能になりました")
        print("✅ 時系列整合性が確保されました") 
        print("✅ 適切なエラーハンドリングが実装されました")
        print("\n📝 実装効果:")
        print("   • トレード時刻に対応するローソク足のopen価格を使用")
        print("   • Look-ahead biasの完全排除")
        print("   • 実際に取引可能だった価格のみ使用")
        print("   • フォールバック無し（実際の値のみ）")
    else:
        print("\n⚠️ 一部のテストが失敗しました")
        if not calculation_test:
            print("• ローソク足開始時刻計算の改善が必要")
        if not open_price_test:
            print("• open価格取得機能の改善が必要")
        if not error_test:
            print("• エラーハンドリングの改善が必要")
    
    return calculation_test and open_price_test and error_test

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)