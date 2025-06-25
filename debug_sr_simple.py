#!/usr/bin/env python3
"""簡易版の支持線・抵抗線デバッグツール"""

import pandas as pd
import numpy as np
from support_resistance_visualizer import detect_fractal_levels, cluster_price_levels
from engines.support_resistance_adapter import FlexibleSupportResistanceDetector

def debug_hype():
    print('🔍 HYPEの支持線・抵抗線検出デバッグ\n')
    
    # 仮想データでテスト（HYPEっぽい高ボラティリティ）
    np.random.seed(42)
    n_points = 2160
    
    # 高ボラティリティの価格データ生成
    trend = np.linspace(10, 45, n_points)  # 10ドルから45ドルへ
    noise = np.random.normal(0, 5, n_points)  # 大きなノイズ
    prices = trend + noise
    
    # DataFrameを作成
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n_points, freq='h'),
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 5000000, n_points)
    })
    
    print(f'データポイント: {len(df)}')
    print(f'価格範囲: ${df["low"].min():.2f} ~ ${df["high"].max():.2f}')
    print(f'ボラティリティ: {df["close"].pct_change().std() * 100:.2f}%\n')
    
    # フラクタル検出テスト
    print('📊 フラクタル検出:')
    for window in [3, 5, 10]:
        resistance_indices, support_indices = detect_fractal_levels(df, window=window)
        print(f'  ウィンドウ{window}: 抵抗線{len(resistance_indices)}個, 支持線{len(support_indices)}個')
    
    # デフォルトウィンドウでクラスタリング
    print('\n📊 クラスタリング (ウィンドウ5):')
    resistance_indices, support_indices = detect_fractal_levels(df, window=5)
    
    if len(resistance_indices) > 0:
        resistance_data = [(df['high'].iloc[idx], df['timestamp'].iloc[idx], idx) for idx in resistance_indices]
        
        for tolerance in [0.01, 0.02, 0.05]:
            clusters = cluster_price_levels(resistance_data, tolerance_pct=tolerance)
            print(f'  許容範囲{tolerance*100:.0f}%: {len(clusters)}クラスター')
            touch_counts = [len(c) for c in clusters]
            min_2_touches = sum(1 for tc in touch_counts if tc >= 2)
            print(f'    2回以上タッチ: {min_2_touches}クラスター')
    
    # FlexibleSupportResistanceDetectorテスト
    print('\n📊 FlexibleSupportResistanceDetector:')
    
    current_price = df['close'].iloc[-1]
    
    # デフォルトパラメータ
    detector1 = FlexibleSupportResistanceDetector(min_touches=2, tolerance_pct=0.01, use_ml_enhancement=False)
    try:
        support1, resistance1 = detector1.detect_levels(df, current_price)
        print(f'  デフォルト: 支持線{len(support1)}個, 抵抗線{len(resistance1)}個')
    except Exception as e:
        print(f'  デフォルト: ❌ {e}')
    
    # 緩和パラメータ
    detector2 = FlexibleSupportResistanceDetector(min_touches=1, tolerance_pct=0.02, use_ml_enhancement=False)
    try:
        support2, resistance2 = detector2.detect_levels(df, current_price)
        print(f'  緩和版: 支持線{len(support2)}個, 抵抗線{len(resistance2)}個')
    except Exception as e:
        print(f'  緩和版: ❌ {e}')

if __name__ == "__main__":
    debug_hype()