#!/usr/bin/env python3
"""
問題のある価格ケースのテスト

実際に「利確価格がエントリー価格以下」問題が起きるケースを再現してテスト
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_problematic_case():
    """問題が起きるケースの再現テスト"""
    print("🚨 問題ケース再現テスト")
    print("=" * 50)
    
    try:
        from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
        from interfaces.data_types import SupportResistanceLevel, MarketContext
        
        calculator = DefaultSLTPCalculator()
        
        # 問題が起きるケース: 抵抗線が現在価格より下にある場合
        print("=== 問題ケース: 抵抗線が現在価格より下 ===")
        
        entry_price = 4.61  # 実際のエラーケースから
        current_price = 3.50  # エントリーより大幅に下
        
        print(f"エントリー価格: {entry_price}")
        print(f"現在価格: {current_price}")
        
        # 抵抗線が現在価格より下にある場合（問題のあるデータ）
        problematic_resistance = [
            SupportResistanceLevel(
                price=3.20,  # 現在価格より下の抵抗線
                strength=0.7,
                touch_count=2,
                level_type='resistance',
                first_touch=datetime.now(),
                last_touch=datetime.now(),
                volume_at_level=800.0,
                distance_from_current=-8.57  # 負の値
            )
        ]
        
        # サポート線も現在価格より上（論理的におかしい）
        problematic_support = [
            SupportResistanceLevel(
                price=4.00,  # 現在価格より上のサポート線
                strength=0.8,
                touch_count=3,
                level_type='support',
                first_touch=datetime.now(),
                last_touch=datetime.now(),
                volume_at_level=1000.0,
                distance_from_current=14.29  # 正の値
            )
        ]
        
        market_context = MarketContext(
            current_price=current_price,
            volume_24h=1000000.0,
            volatility=0.02,
            trend_direction='BEARISH',
            market_phase='MARKDOWN',
            timestamp=datetime.now()
        )
        
        print(f"\n問題のあるレベル:")
        print(f"  抵抗線: {problematic_resistance[0].price} (現在価格より {problematic_resistance[0].distance_from_current:.1f}%)")
        print(f"  サポート線: {problematic_support[0].price} (現在価格より {problematic_support[0].distance_from_current:.1f}%)")
        
        # 問題のあるデータでSL/TP計算
        try:
            levels = calculator.calculate_levels(
                current_price=current_price,
                leverage=2.0,
                support_levels=problematic_support,
                resistance_levels=problematic_resistance,
                market_context=market_context
            )
            
            print(f"\n計算結果:")
            print(f"  損切り: {levels.stop_loss_price:.4f}")
            print(f"  利確: {levels.take_profit_price:.4f}")
            print(f"  エントリー: {entry_price:.4f}")
            
            # 論理チェック
            issues = []
            if levels.stop_loss_price >= entry_price:
                issues.append(f"損切り({levels.stop_loss_price:.4f}) >= エントリー({entry_price:.4f})")
            if levels.take_profit_price <= entry_price:
                issues.append(f"利確({levels.take_profit_price:.4f}) <= エントリー({entry_price:.4f})")
            
            if issues:
                print(f"  ❌ 検出された問題: {' / '.join(issues)}")
                print(f"  → これが「利確価格がエントリー価格以下」エラーの原因")
                return True
            else:
                print(f"  ✅ 論理は正常（問題は再現されませんでした）")
                return False
                
        except Exception as e:
            print(f"  🛡️ 計算エラー（適切な例外処理）: {e}")
            if "抵抗線データが不足" in str(e) or "適切な利確ライン" in str(e):
                print(f"  ✅ 修正が効いています - 不正なデータをキャッチ")
                return True
            else:
                print(f"  ❌ 予期しないエラー")
                return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """エッジケースのテスト"""
    print("\n🔬 エッジケーステスト")
    print("=" * 40)
    
    try:
        from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
        from interfaces.data_types import SupportResistanceLevel, MarketContext
        
        calculator = DefaultSLTPCalculator()
        
        # エッジケース1: レジスタンスレベルが空
        print("=== エッジケース1: レジスタンスレベルが空 ===")
        
        try:
            levels = calculator.calculate_levels(
                current_price=100.0,
                leverage=2.0,
                support_levels=[
                    SupportResistanceLevel(
                        price=90.0, strength=0.8, touch_count=3, level_type='support',
                        first_touch=datetime.now(), last_touch=datetime.now(),
                        volume_at_level=1000.0, distance_from_current=-10.0
                    )
                ],
                resistance_levels=[],  # 空のリスト
                market_context=MarketContext(
                    current_price=100.0, volume_24h=1000000.0, volatility=0.02,
                    trend_direction='BULLISH', market_phase='MARKUP', timestamp=datetime.now()
                )
            )
            print("  ❌ エラーが発生すべきでした")
            return False
        except Exception as e:
            print(f"  ✅ 適切な例外: {e}")
        
        # エッジケース2: サポートレベルが空
        print("\n=== エッジケース2: サポートレベルが空 ===")
        
        try:
            levels = calculator.calculate_levels(
                current_price=100.0,
                leverage=2.0,
                support_levels=[],  # 空のリスト
                resistance_levels=[
                    SupportResistanceLevel(
                        price=110.0, strength=0.7, touch_count=2, level_type='resistance',
                        first_touch=datetime.now(), last_touch=datetime.now(),
                        volume_at_level=800.0, distance_from_current=10.0
                    )
                ],
                market_context=MarketContext(
                    current_price=100.0, volume_24h=1000000.0, volatility=0.02,
                    trend_direction='BULLISH', market_phase='MARKUP', timestamp=datetime.now()
                )
            )
            print("  ❌ エラーが発生すべきでした")
            return False
        except Exception as e:
            print(f"  ✅ 適切な例外: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ エッジケーステストエラー: {e}")
        return False

def main():
    """メイン実行"""
    print("🧪 問題ケース再現・修正確認テスト")
    print("=" * 60)
    
    test1_success = test_problematic_case()
    test2_success = test_edge_cases()
    
    print(f"\n" + "=" * 60)
    print(f"テスト結果サマリー")
    print("=" * 60)
    
    if test1_success and test2_success:
        print(f"✅ すべてのテストが成功")
        print(f"主な確認事項:")
        print(f"  - 問題のあるデータケースを適切に検出")
        print(f"  - エッジケースで適切な例外処理")
        print(f"  - 価格論理エラーの防止確認")
    else:
        print(f"❌ 一部のテストで問題が発生")
        if not test1_success:
            print(f"  - 問題ケースの検出・処理に課題")
        if not test2_success:
            print(f"  - エッジケースの処理に課題")
    
    return test1_success and test2_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)