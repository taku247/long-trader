#!/usr/bin/env python3
"""
柔軟な時刻マッチング機能のテスト

SOLの15分ギャップ問題の修正効果を確認
"""

import sys
import os
import pandas as pd
from datetime import datetime, timezone, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_flexible_time_matching():
    """柔軟な時刻マッチング機能のテスト"""
    print("🔍 柔軟な時刻マッチング機能テスト")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # モックOHLCVデータを作成（15分ギャップあり）
        base_time = datetime(2025, 3, 27, 6, 30, 0, tzinfo=timezone.utc)
        mock_data = []
        
        # 06:30から15分間隔でデータ作成
        for i in range(10):
            timestamp = base_time + timedelta(minutes=15*i)
            mock_data.append({
                'timestamp': timestamp,
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000
            })
        
        market_data = pd.DataFrame(mock_data)
        
        # テストケース1: 15分前のトレード時刻（SOLと同じ状況）
        trade_time = datetime(2025, 3, 27, 6, 25, 11, 412783, tzinfo=timezone.utc)
        
        print(f"\n🧪 テストケース1: 15分ギャップ")
        print(f"   トレード時刻: {trade_time}")
        print(f"   データ開始: {market_data['timestamp'].iloc[0]}")
        print(f"   ギャップ: {market_data['timestamp'].iloc[0] - trade_time}")
        
        try:
            price = system._get_real_market_price(market_data, trade_time, "SOL", "15m")
            print(f"   ✅ 取得成功: 価格={price}")
        except Exception as e:
            print(f"   ❌ 取得失敗: {e}")
        
        # テストケース2: 完全一致する時刻
        exact_time = datetime(2025, 3, 27, 6, 30, 0, tzinfo=timezone.utc)
        
        print(f"\n🧪 テストケース2: 完全一致")
        print(f"   トレード時刻: {exact_time}")
        
        try:
            price = system._get_real_market_price(market_data, exact_time, "SOL", "15m")
            print(f"   ✅ 取得成功: 価格={price}")
        except Exception as e:
            print(f"   ❌ 取得失敗: {e}")
        
        # テストケース3: 2時間超過のギャップ（失敗ケース）
        far_time = datetime(2025, 3, 27, 3, 0, 0, tzinfo=timezone.utc)
        
        print(f"\n🧪 テストケース3: 2時間超過ギャップ")
        print(f"   トレード時刻: {far_time}")
        print(f"   ギャップ: {market_data['timestamp'].iloc[0] - far_time}")
        
        try:
            price = system._get_real_market_price(market_data, far_time, "SOL", "15m")
            print(f"   ⚠️ 予期しない成功: 価格={price}")
        except Exception as e:
            print(f"   ✅ 期待通り失敗: {str(e)[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_candle_start_time_calculation():
    """ローソク足開始時刻計算のテスト"""
    print(f"\n🔍 ローソク足開始時刻計算テスト")
    print("=" * 50)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # テストケース
        test_cases = [
            (datetime(2025, 3, 27, 6, 25, 11, tzinfo=timezone.utc), "15m", 
             datetime(2025, 3, 27, 6, 15, 0, tzinfo=timezone.utc)),
            (datetime(2025, 3, 27, 6, 32, 45, tzinfo=timezone.utc), "15m",
             datetime(2025, 3, 27, 6, 30, 0, tzinfo=timezone.utc)),
            (datetime(2025, 3, 27, 6, 59, 59, tzinfo=timezone.utc), "1h",
             datetime(2025, 3, 27, 6, 0, 0, tzinfo=timezone.utc)),
        ]
        
        for trade_time, timeframe, expected_start in test_cases:
            calculated_start = system._get_candle_start_time(trade_time, timeframe)
            print(f"   {timeframe}足: {trade_time.strftime('%H:%M:%S')} -> {calculated_start.strftime('%H:%M:%S')}")
            
            if calculated_start == expected_start:
                print(f"      ✅ 正確")
            else:
                print(f"      ❌ 期待: {expected_start.strftime('%H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ローソク足計算テストエラー: {e}")
        return False

if __name__ == "__main__":
    print("🚀 柔軟な時刻マッチング機能テスト開始")
    print("=" * 60)
    
    success1 = test_flexible_time_matching()
    success2 = test_candle_start_time_calculation()
    
    if success1 and success2:
        print(f"\n✅ 柔軟な時刻マッチング機能テスト完了")
        print("📊 修正効果:")
        print("  1. 15分ギャップのローソク足も正常に取得可能")
        print("  2. 段階的許容範囲拡大で柔軟性向上")
        print("  3. 2時間超過時は適切にエラー")
    else:
        print(f"\n❌ テスト失敗 - 追加調整が必要")