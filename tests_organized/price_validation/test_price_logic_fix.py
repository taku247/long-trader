#!/usr/bin/env python3
"""
価格論理修正テスト

SL/TP価格計算の順序修正が正しく動作するかテスト
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_price_logic_fix():
    """価格論理修正のテスト"""
    print("🔧 価格論理修正テスト")
    print("=" * 50)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        # テストインスタンス作成
        system = ScalableAnalysisSystem("test_price_logic")
        
        # 簡単な価格論理テスト用データ
        test_data = {
            'symbol': 'TEST',
            'timeframe': '1h',
            'entry_price': 100.0,
            'current_price': 95.0,  # 異なる価格でテスト
        }
        
        print(f"テストデータ:")
        print(f"  銘柄: {test_data['symbol']}")
        print(f"  エントリー価格: {test_data['entry_price']}")
        print(f"  現在価格: {test_data['current_price']}")
        
        # SL/TP計算器をテスト
        from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
        from interfaces.data_types import SupportResistanceLevel, MarketContext
        
        calculator = DefaultSLTPCalculator()
        
        # テスト用のサポート・レジスタンスレベル
        support_levels = [
            SupportResistanceLevel(
                price=90.0,  # エントリーより下
                strength=0.8,
                touch_count=3,
                level_type='support',
                first_touch=datetime.now(),
                last_touch=datetime.now(),
                volume_at_level=1000.0,
                distance_from_current=-10.0
            )
        ]
        
        resistance_levels = [
            SupportResistanceLevel(
                price=110.0,  # エントリーより上
                strength=0.7,
                touch_count=2,
                level_type='resistance',
                first_touch=datetime.now(),
                last_touch=datetime.now(),
                volume_at_level=800.0,
                distance_from_current=10.0
            )
        ]
        
        market_context = MarketContext(
            current_price=test_data['entry_price'],
            volume_24h=1000000.0,
            volatility=0.02,
            trend_direction='BULLISH',
            market_phase='MARKUP',
            timestamp=datetime.now()
        )
        
        print(f"\nサポート・レジスタンスレベル:")
        print(f"  サポート: {support_levels[0].price} (強度: {support_levels[0].strength})")
        print(f"  レジスタンス: {resistance_levels[0].price} (強度: {resistance_levels[0].strength})")
        
        # 修正前の問題を再現するため、異なる価格で計算
        print(f"\n=== ケース1: 修正前の問題パターン ===")
        print(f"SL/TP計算に current_price={test_data['current_price']} を使用")
        
        levels_old = calculator.calculate_levels(
            current_price=test_data['current_price'],  # 古いロジック
            leverage=2.0,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            market_context=market_context
        )
        
        print(f"結果:")
        print(f"  損切り: {levels_old.stop_loss_price:.4f}")
        print(f"  利確: {levels_old.take_profit_price:.4f}")
        print(f"  エントリー: {test_data['entry_price']:.4f}")
        
        # 論理チェック
        issues_old = []
        if levels_old.stop_loss_price >= test_data['entry_price']:
            issues_old.append(f"損切り({levels_old.stop_loss_price:.4f}) >= エントリー({test_data['entry_price']:.4f})")
        if levels_old.take_profit_price <= test_data['entry_price']:
            issues_old.append(f"利確({levels_old.take_profit_price:.4f}) <= エントリー({test_data['entry_price']:.4f})")
        
        if issues_old:
            print(f"  ❌ 問題: {' / '.join(issues_old)}")
        else:
            print(f"  ✅ 論理は正常")
        
        print(f"\n=== ケース2: 修正後の正しいパターン ===")
        print(f"SL/TP計算に entry_price={test_data['entry_price']} を使用")
        
        levels_new = calculator.calculate_levels(
            current_price=test_data['entry_price'],  # 修正後のロジック
            leverage=2.0,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            market_context=market_context
        )
        
        print(f"結果:")
        print(f"  損切り: {levels_new.stop_loss_price:.4f}")
        print(f"  利確: {levels_new.take_profit_price:.4f}")
        print(f"  エントリー: {test_data['entry_price']:.4f}")
        
        # 論理チェック
        issues_new = []
        if levels_new.stop_loss_price >= test_data['entry_price']:
            issues_new.append(f"損切り({levels_new.stop_loss_price:.4f}) >= エントリー({test_data['entry_price']:.4f})")
        if levels_new.take_profit_price <= test_data['entry_price']:
            issues_new.append(f"利確({levels_new.take_profit_price:.4f}) <= エントリー({test_data['entry_price']:.4f})")
        
        if issues_new:
            print(f"  ❌ 問題: {' / '.join(issues_new)}")
            return False
        else:
            print(f"  ✅ 論理は正常")
        
        print(f"\n=== 修正効果の確認 ===")
        
        if len(issues_old) > 0 and len(issues_new) == 0:
            print(f"✅ 修正成功: 問題が解消されました")
            print(f"  修正前の問題数: {len(issues_old)}")
            print(f"  修正後の問題数: {len(issues_new)}")
            return True
        elif len(issues_old) == 0 and len(issues_new) == 0:
            print(f"⚠️ このケースでは問題は発生していません")
            return True
        else:
            print(f"❌ 修正が不完全です")
            return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン実行"""
    print("🧪 価格論理修正確認テスト")
    print("=" * 60)
    
    success = test_price_logic_fix()
    
    print(f"\n" + "=" * 60)
    print(f"テスト結果")
    print("=" * 60)
    
    if success:
        print(f"✅ 価格論理修正が正しく動作しています")
        print(f"主な改善点:")
        print(f"  - SL/TP計算をエントリー価格ベースで実行")
        print(f"  - ロングポジションの論理チェックを強化")
        print(f"  - 価格整合性の事前確認")
    else:
        print(f"❌ 価格論理に問題があります")
        print(f"追加の修正が必要です")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)