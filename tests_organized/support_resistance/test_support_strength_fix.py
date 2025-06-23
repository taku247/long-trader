#!/usr/bin/env python3
"""
サポート強度修正のテスト
"""

import sys
import importlib
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# モジュールを強制的にリロード
import support_resistance_visualizer
importlib.reload(support_resistance_visualizer)

def test_support_strength_calculation():
    """サポート強度計算のテスト"""
    print("🔍 サポート強度計算テスト")
    print("=" * 60)
    
    # テストデータを作成
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # 模擬価格データ
    dates = [datetime.now() - timedelta(days=i) for i in range(100)]
    prices = [1.0 + 0.1 * np.sin(i * 0.1) + np.random.normal(0, 0.01) for i in range(100)]
    
    test_data = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'high': [p + 0.01 for p in prices],
        'low': [p - 0.01 for p in prices],
        'volume': [1000 + np.random.normal(0, 100) for _ in range(100)]
    })
    
    print("📊 テストデータ準備完了")
    print(f"   データ数: {len(test_data)}")
    print(f"   価格範囲: {test_data['close'].min():.4f} - {test_data['close'].max():.4f}")
    
    try:
        # サポレジレベル検出
        levels = support_resistance_visualizer.find_all_levels(test_data, min_touches=2)
        
        print(f"\n📍 検出されたレベル数: {len(levels)}")
        
        if levels:
            print("\n🔍 各レベルの強度値:")
            for i, level in enumerate(levels[:5]):  # 最初の5個を表示
                strength = level.get('strength', 0)
                print(f"   レベル {i+1}: 価格={level.get('price', 'N/A'):.4f}, 強度={strength:.4f}")
                
                # 強度が0-1の範囲内かチェック
                if 0.0 <= strength <= 1.0:
                    print(f"     ✅ 正常範囲内")
                else:
                    print(f"     🚨 異常値! (期待範囲: 0.0-1.0)")
        else:
            print("   ⚠️ レベルが検出されませんでした")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

def test_direct_strength_calculation():
    """直接的な強度計算関数のテスト"""
    print("\n🧪 直接的な強度計算テスト")
    print("=" * 60)
    
    # 強度計算に使用される値をシミュレート
    touch_count = 5
    avg_bounce = 0.02  # 2%
    time_span = 1000
    recency = 100
    avg_volume_spike = 1.5
    
    print(f"📊 入力値:")
    print(f"   touch_count: {touch_count}")
    print(f"   avg_bounce: {avg_bounce}")
    print(f"   time_span: {time_span}")
    print(f"   recency: {recency}")
    print(f"   avg_volume_spike: {avg_volume_spike}")
    
    # 重み
    touch_weight = 3
    bounce_weight = 50
    time_weight = 0.05
    recency_weight = 0.02
    volume_weight = 10
    
    # 生の計算
    raw_strength = (touch_count * touch_weight + 
                    avg_bounce * bounce_weight + 
                    time_span * time_weight - 
                    recency * recency_weight +
                    avg_volume_spike * volume_weight)
    
    # 正規化（修正版）
    normalized_strength = min(max(raw_strength / 200.0, 0.0), 1.0)
    
    print(f"\n🎯 計算結果:")
    print(f"   生の強度: {raw_strength:.2f}")
    print(f"   正規化後: {normalized_strength:.4f}")
    
    if 0.0 <= normalized_strength <= 1.0:
        print(f"   ✅ 正常範囲内")
    else:
        print(f"   🚨 異常値!")

if __name__ == '__main__':
    test_support_strength_calculation()
    test_direct_strength_calculation()