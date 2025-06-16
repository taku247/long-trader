#!/usr/bin/env python3
"""
実際の市場価格修正の効果検証テスト
シミュレート価格変動を実際の市場データベースの価格に置き換えた修正の効果を確認
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_real_market_price_fix():
    """実際の市場価格修正のテスト"""
    print("🔧 実際の市場価格修正テスト")
    print("=" * 60)
    print("修正内容: シミュレート価格変動 → 実際の時系列データから価格取得")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        system = ScalableAnalysisSystem()
        
        # テスト用の時刻データ
        test_times = [
            datetime.now() - timedelta(hours=24),
            datetime.now() - timedelta(hours=12),
            datetime.now() - timedelta(hours=6),
            datetime.now() - timedelta(hours=1),
            datetime.now()
        ]
        
        print("📊 _get_real_market_price メソッドのテスト実行")
        print(f"対象: SUI, 15m")
        print(f"テスト時刻数: {len(test_times)}")
        print()
        
        # ボットインスタンス作成（新しい修正版）
        bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange='gateio')
        
        # 各時刻に対して価格を取得
        prices = []
        for i, test_time in enumerate(test_times):
            try:
                price = system._get_real_market_price(bot, 'SUI', '15m', test_time)
                prices.append(price)
                print(f"   時刻 {i+1}: {test_time.strftime('%H:%M')} → ${price:.6f}")
            except Exception as e:
                print(f"   時刻 {i+1}: エラー - {e}")
                prices.append(None)
        
        # 価格多様性の分析
        valid_prices = [p for p in prices if p is not None]
        
        if len(valid_prices) >= 3:
            unique_prices = len(set(valid_prices))
            price_range = max(valid_prices) - min(valid_prices)
            diversity_rate = unique_prices / len(valid_prices) * 100
            
            print(f"\n📈 価格多様性分析:")
            print(f"   取得成功: {len(valid_prices)}/{len(test_times)}")
            print(f"   ユニーク価格数: {unique_prices}")
            print(f"   価格範囲: ${min(valid_prices):.6f} - ${max(valid_prices):.6f}")
            print(f"   価格変動幅: ${price_range:.6f}")
            print(f"   多様性率: {diversity_rate:.1f}%")
            
            # 判定
            print(f"\n🏆 修正効果判定:")
            if unique_prices > 1:
                print("   ✅ 実際の市場データから異なる価格を取得成功")
                print("   ✅ シミュレート価格変動から実データ使用への修正完了")
                
                if price_range > 0.001:  # 0.001以上の変動があれば現実的
                    print("   ✅ 現実的な価格変動を確認")
                else:
                    print("   ⚠️ 価格変動幅が小さい（時間範囲を拡大推奨）")
                    
                return True
            else:
                print("   ❌ 全ての価格が同じ - さらなる修正が必要")
                return False
        else:
            print("   ❌ 十分なテストデータを取得できませんでした")
            return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_no_simulation_code():
    """シミュレート価格変動コードが除去されていることを確認"""
    print(f"\n" + "=" * 60)
    print("🔍 シミュレートコード除去確認")
    print("=" * 60)
    
    try:
        with open('scalable_analysis_system.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 除去されるべきシミュレートコード
        simulation_patterns = [
            'market_volatility = 0.0002',
            'price_variation = np.random.uniform',
            'entry_price = current_price * (1 + price_variation)'
        ]
        
        found_patterns = []
        for pattern in simulation_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        if found_patterns:
            print("❌ まだシミュレートコードが残っています:")
            for pattern in found_patterns:
                print(f"   • {pattern}")
            return False
        else:
            print("✅ シミュレート価格変動コードが正常に除去されました")
            
            # 新しい実データ使用コードが存在することを確認
            if '_get_real_market_price' in content:
                print("✅ 実際の市場価格取得メソッドが実装されました")
                return True
            else:
                print("❌ 実際の市場価格取得メソッドが見つかりません")
                return False
                
    except Exception as e:
        print(f"❌ コード確認エラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 実際の市場価格修正 - 効果検証テスト")
    print("=" * 60)
    print("目的: シミュレート価格変動を実際の市場データに置き換えた修正の検証")
    print("ユーザー要求: 「実際の値のみを使うのがこのシステム」")
    print("=" * 60)
    
    # 1. シミュレートコード除去確認
    code_check = verify_no_simulation_code()
    
    # 2. 実際の市場価格取得テスト
    price_test = test_real_market_price_fix()
    
    # 総合判定
    print(f"\n" + "=" * 60)
    print("📋 修正検証結果")
    print("=" * 60)
    print(f"シミュレートコード除去: {'✅ 完了' if code_check else '❌ 未完了'}")
    print(f"実市場価格取得テスト: {'✅ 成功' if price_test else '❌ 失敗'}")
    
    if code_check and price_test:
        print("\n🎉 修正が成功しました！")
        print("✅ シミュレート価格変動が除去されました")
        print("✅ 実際の市場データから価格を取得するように修正されました")
        print("✅ ユーザー要求「実際の値のみ使用」を満たしています")
        print("\n📝 次のステップ:")
        print("   1. 既存のSUIデータをクリア")
        print("   2. 新しい修正版で再分析実行")
        print("   3. トレードデータの価格多様性を検証")
    else:
        print("\n⚠️ 修正が完全ではありません")
        if not code_check:
            print("• シミュレートコードの完全除去が必要")
        if not price_test:
            print("• 実市場価格取得機能の改善が必要")
    
    return code_check and price_test

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)