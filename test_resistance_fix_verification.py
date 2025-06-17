#!/usr/bin/env python3
"""
Resistance level bug fix verification
修正された抵抗線フィルタリングの効果を検証
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

def create_problematic_test_data():
    """
    問題を再現するテストデータ作成
    - 過去の高値が現在価格より低い状況を作る
    """
    timestamps = pd.date_range('2025-01-01', periods=200, freq='15min')
    
    # 価格パターン: 4.6 → 4.2 → 4.61 (現在価格4.61、過去の抵抗線4.24)
    prices = []
    for i in range(200):
        if i < 40:
            # 初期期間: 4.6付近
            price = 4.6 + np.random.uniform(-0.1, 0.1)
        elif i < 80:
            # 下落期間: 4.6 → 4.2
            progress = (i - 40) / 40
            price = 4.6 - progress * 0.4 + np.random.uniform(-0.05, 0.05)
        elif i < 120:
            # 底値期間: 4.2付近 (抵抗線4.24が形成される)
            price = 4.24 + np.random.uniform(-0.1, 0.1)
        elif i < 160:
            # 回復期間: 4.24 → 4.5
            progress = (i - 120) / 40
            price = 4.24 + progress * 0.26 + np.random.uniform(-0.03, 0.03)
        else:
            # 最終期間: 4.5 → 4.61 (現在価格)
            progress = (i - 160) / 40
            price = 4.5 + progress * 0.11 + np.random.uniform(-0.02, 0.02)
        
        prices.append(max(price, 4.0))  # 最低価格保証
    
    # OHLCV作成
    data = []
    for i, base_price in enumerate(prices):
        spread = base_price * 0.003
        high = base_price + np.random.uniform(0, spread)
        low = base_price - np.random.uniform(0, spread)
        open_price = base_price + np.random.uniform(-spread/2, spread/2)
        close = base_price + np.random.uniform(-spread/2, spread/2)
        volume = np.random.uniform(1000, 5000)
        
        data.append({
            'timestamp': timestamps[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    # 最後の価格を4.61に設定 (エントリー価格)
    df.loc[df.index[-1], 'close'] = 4.61
    
    return df

def test_before_fix():
    """修正前の動作をシミュレート（直接fractal analysis）"""
    print("🔍 修正前の動作テスト (直接フラクタル分析)")
    print("-" * 50)
    
    df = create_problematic_test_data()
    current_price = df['close'].iloc[-1]
    print(f"現在価格: ${current_price:.2f}")
    
    try:
        from support_resistance_visualizer import detect_fractal_levels, cluster_price_levels
        
        # 直接フラクタル分析（修正前と同様）
        resistance_levels, support_levels = detect_fractal_levels(df)
        resistance_clusters = cluster_price_levels(resistance_levels)
        
        print(f"検出された抵抗線クラスター: {len(resistance_clusters)}")
        
        problematic_clusters = 0
        for cluster in resistance_clusters:
            avg_price = np.mean([level[1] for level in cluster])
            if avg_price <= current_price:
                problematic_clusters += 1
                print(f"  🚨 問題: 抵抗線 ${avg_price:.2f} ≤ 現在価格 ${current_price:.2f}")
        
        print(f"問題のある抵抗線: {problematic_clusters}/{len(resistance_clusters)}")
        return problematic_clusters > 0
        
    except Exception as e:
        print(f"エラー: {e}")
        return False

def test_after_fix():
    """修正後の動作テスト（新しいフィルタリング付き）"""
    print("\n✅ 修正後の動作テスト (フィルタリング付き)")
    print("-" * 50)
    
    df = create_problematic_test_data()
    current_price = df['close'].iloc[-1]
    print(f"現在価格: ${current_price:.2f}")
    
    try:
        from adapters.existing_adapters import ExistingSupportResistanceAdapter
        
        adapter = ExistingSupportResistanceAdapter()
        levels = adapter.find_levels(df, min_touches=2)
        
        # 抵抗線とサポート線を分離
        resistance_levels = [l for l in levels if l.level_type == 'resistance']
        support_levels = [l for l in levels if l.level_type == 'support']
        
        print(f"フィルタ後の抵抗線: {len(resistance_levels)}")
        print(f"フィルタ後のサポート線: {len(support_levels)}")
        
        # 現在価格との関係チェック
        invalid_resistance = [r for r in resistance_levels if r.price <= current_price]
        invalid_support = [s for s in support_levels if s.price >= current_price]
        
        print(f"\n位置関係チェック:")
        print(f"  無効な抵抗線 (≤現在価格): {len(invalid_resistance)}")
        print(f"  無効なサポート線 (≥現在価格): {len(invalid_support)}")
        
        if invalid_resistance:
            print("  🚨 まだ無効な抵抗線が存在:")
            for r in invalid_resistance:
                print(f"    ${r.price:.2f}")
        
        if invalid_support:
            print("  🚨 まだ無効なサポート線が存在:")
            for s in invalid_support:
                print(f"    ${s.price:.2f}")
        
        # 有効なレベルの表示
        if resistance_levels:
            print(f"\n✅ 有効な抵抗線:")
            for r in sorted(resistance_levels, key=lambda x: x.price)[:5]:
                distance = (r.price - current_price) / current_price * 100
                print(f"    ${r.price:.2f} (+{distance:.1f}%, 強度: {r.strength:.2f})")
        
        if support_levels:
            print(f"\n✅ 有効なサポート線:")
            for s in sorted(support_levels, key=lambda x: x.price, reverse=True)[:5]:
                distance = (current_price - s.price) / current_price * 100
                print(f"    ${s.price:.2f} (-{distance:.1f}%, 強度: {s.strength:.2f})")
        
        return len(invalid_resistance) == 0 and len(invalid_support) == 0
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sltp_calculation():
    """修正後のSL/TP計算テスト"""
    print(f"\n🧮 修正後のSL/TP計算テスト")
    print("-" * 50)
    
    df = create_problematic_test_data()
    current_price = df['close'].iloc[-1]
    
    try:
        from adapters.existing_adapters import ExistingSupportResistanceAdapter
        from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
        from interfaces.data_types import MarketContext
        
        # レベル取得
        adapter = ExistingSupportResistanceAdapter()
        levels = adapter.find_levels(df, min_touches=2)
        
        resistance_levels = [l for l in levels if l.level_type == 'resistance']
        support_levels = [l for l in levels if l.level_type == 'support']
        
        print(f"利用可能な抵抗線: {len(resistance_levels)}")
        print(f"利用可能なサポート線: {len(support_levels)}")
        
        if not resistance_levels:
            print("🚨 抵抗線がありません - Level 1 検証でエラーになるはず")
        
        if not support_levels:
            print("🚨 サポート線がありません - Level 1 検証でエラーになるはず")
        
        # SL/TP計算実行
        calculator = DefaultSLTPCalculator()
        mock_context = MarketContext(
            current_price=current_price,
            volume_24h=1000000.0,
            volatility=0.02,
            trend_direction='BULLISH',
            market_phase='ACCUMULATION',
            timestamp=datetime.now()
        )
        
        try:
            levels_result = calculator.calculate_levels(
                current_price=current_price,
                leverage=2.0,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                market_context=mock_context
            )
            
            print(f"\n✅ SL/TP計算成功:")
            print(f"  エントリー価格: ${current_price:.2f}")
            print(f"  利確価格: ${levels_result.take_profit_price:.2f}")
            print(f"  損切り価格: ${levels_result.stop_loss_price:.2f}")
            print(f"  リスクリワード比: {levels_result.risk_reward_ratio:.2f}")
            
            # バグチェック
            if levels_result.take_profit_price <= current_price:
                print(f"🚨 BUG再発: 利確価格({levels_result.take_profit_price:.2f}) ≤ エントリー価格({current_price:.2f})")
                return False
            else:
                print(f"✅ 正常: 利確価格 > エントリー価格")
                return True
                
        except Exception as calc_error:
            print(f"SL/TP計算エラー: {calc_error}")
            if "現在価格より上の抵抗線データが不足" in str(calc_error):
                print("✅ Level 1 検証が正常に機能 - 適切にエラーを検出")
                return True
            else:
                print("🚨 予期しないエラー")
                return False
        
    except Exception as e:
        print(f"テストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🔧 抵抗線バグ修正検証テスト")
    print("=" * 60)
    print("修正内容: 抵抗線は現在価格より上、サポート線は現在価格より下のみ返す")
    print("=" * 60)
    
    # 1. 修正前の問題再現
    had_problem_before = test_before_fix()
    
    # 2. 修正後の動作確認
    fix_works = test_after_fix()
    
    # 3. SL/TP計算テスト
    sltp_works = test_sltp_calculation()
    
    # 結果サマリー
    print(f"\n" + "=" * 60)
    print("📋 修正検証結果")
    print("=" * 60)
    print(f"修正前の問題再現: {'✅ 確認' if had_problem_before else '❌ 再現できず'}")
    print(f"修正後のフィルタリング: {'✅ 正常' if fix_works else '❌ 異常'}")
    print(f"SL/TP計算: {'✅ 正常' if sltp_works else '❌ 異常'}")
    
    if had_problem_before and fix_works and sltp_works:
        print(f"\n🎉 修正が成功しました!")
        print("✅ 利確価格 < エントリー価格バグが解決されました")
        print("✅ 抵抗線・サポート線のフィルタリングが正常に機能")
        print("✅ SL/TP計算が適切に動作")
        
        print(f"\n📝 修正の詳細:")
        print("1. adapters/existing_adapters.py の find_levels() メソッドを修正")
        print("2. 抵抗線は現在価格より上のみ、サポート線は現在価格より下のみ返すように制限")
        print("3. 最小距離要件(0.5%)を追加して、現在価格に近すぎるレベルを除外")
        print("4. デバッグ用のログ出力を追加")
        
    else:
        print(f"\n⚠️ 修正に問題があります")
        print("詳細を確認して追加の修正が必要です")
    
    return had_problem_before and fix_works and sltp_works

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)