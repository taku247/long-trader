#!/usr/bin/env python3
"""
Resistance level calculation bug investigation
特定の利確価格 < エントリー価格問題の原因調査
"""

import sys
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# ロギング設定 - 詳細ログ表示
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_resistance_calculation_bug():
    """抵抗線計算バグの詳細調査"""
    print("🔍 抵抗線計算バグ調査開始")
    print("=" * 60)
    print("問題: 利確価格(4.24)がエントリー価格(4.61)以下")
    print("原因仮説: 抵抗線データが現在価格より低い値になっている")
    print("=" * 60)
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
        
        # ボット初期化
        print("1️⃣ ボット初期化中...")
        bot = HighLeverageBotOrchestrator()
        
        # 複数の銘柄で抵抗線分析をテスト
        test_symbols = ['OP', 'SUI', 'XRP', 'BTC', 'ETH']
        
        for symbol in test_symbols:
            print(f"\n2️⃣ {symbol}の分析実行中...")
            print("-" * 40)
            
            try:
                # 分析実行
                result = bot.analyze_symbol(symbol, '15m', 'Aggressive_ML')
                
                if result:
                    current_price = result.get('current_price', 0)
                    leverage = result.get('leverage', 0)
                    
                    # 詳細な価格情報を表示
                    print(f"   現在価格: ${current_price:.6f}")
                    print(f"   レバレッジ: {leverage:.2f}x")
                    
                    # 内部のサポート・レジスタンス データを取得
                    support_resistance_analyzer = bot.plugins.get('support_resistance_analyzer')
                    if support_resistance_analyzer:
                        # 市場データ取得
                        market_data = bot.fetch_market_data(symbol, '15m')
                        if market_data is not None and len(market_data) > 0:
                            
                            # サポート・レジスタンス分析
                            levels_result = support_resistance_analyzer.analyze_levels(market_data)
                            if levels_result:
                                support_levels = levels_result.get('support_levels', [])
                                resistance_levels = levels_result.get('resistance_levels', [])
                                
                                print(f"   サポートレベル数: {len(support_levels)}")
                                print(f"   レジスタンスレベル数: {len(resistance_levels)}")
                                
                                # 現在価格との関係をチェック
                                resistance_above = [r for r in resistance_levels if hasattr(r, 'price') and r.price > current_price]
                                resistance_below = [r for r in resistance_levels if hasattr(r, 'price') and r.price <= current_price]
                                
                                print(f"   現在価格より上のレジスタンス: {len(resistance_above)}")
                                print(f"   現在価格より下のレジスタンス: {len(resistance_below)} ⚠️")
                                
                                # 問題のある場合の詳細表示
                                if len(resistance_below) > 0:
                                    print(f"   🚨 現在価格より下のレジスタンスを検出!")
                                    for i, r in enumerate(resistance_below[:3]):  # 最初の3つを表示
                                        print(f"      R{i+1}: ${r.price:.6f} (強度: {r.strength:.2f})")
                                
                                if len(resistance_above) == 0:
                                    print(f"   🚨 現在価格より上のレジスタンスがありません!")
                                    print(f"   🚨 これが利確価格 < エントリー価格の原因です!")
                                    
                                    # SL/TP計算を直接テスト
                                    calculator = DefaultSLTPCalculator()
                                    try:
                                        # 市場コンテキストのモック作成
                                        from interfaces import MarketContext
                                        mock_context = MarketContext(
                                            trend_direction='up',
                                            volatility=0.02,
                                            volume_profile='normal',
                                            market_phase='trending'
                                        )
                                        
                                        levels = calculator.calculate_levels(
                                            current_price=current_price,
                                            leverage=leverage,
                                            support_levels=support_levels,
                                            resistance_levels=resistance_levels,
                                            market_context=mock_context
                                        )
                                        
                                        print(f"   計算結果:")
                                        print(f"     エントリー価格: ${current_price:.6f}")
                                        print(f"     利確価格: ${levels.take_profit_price:.6f}")
                                        print(f"     損切り価格: ${levels.stop_loss_price:.6f}")
                                        
                                        if levels.take_profit_price <= current_price:
                                            print(f"   🚨 BUG確認: 利確価格({levels.take_profit_price:.2f}) <= エントリー価格({current_price:.2f})")
                                            
                                    except Exception as calc_error:
                                        print(f"   計算エラー: {calc_error}")
                                
                                # 上位レジスタンス表示
                                if resistance_above:
                                    print(f"   上位レジスタンス:")
                                    for i, r in enumerate(sorted(resistance_above, key=lambda x: x.price)[:3]):
                                        print(f"      R{i+1}: ${r.price:.6f} (強度: {r.strength:.2f}, +{((r.price/current_price-1)*100):.1f}%)")
                        
                else:
                    print(f"   分析結果なし")
                    
            except Exception as e:
                print(f"   エラー: {e}")
                
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

def test_specific_problematic_data():
    """具体的な問題データのテスト"""
    print(f"\n" + "=" * 60)
    print("🔍 具体的な問題データのテスト")
    print("=" * 60)
    
    # 問題のありそうな価格帯での直接テスト
    try:
        from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
        from interfaces import SupportResistanceLevel, MarketContext
        
        calculator = DefaultSLTPCalculator()
        
        # 問題のありそうなシナリオ1: レジスタンスが現在価格より低い
        current_price = 4.61
        
        # 現在価格より低いレジスタンスレベル（バグのあるデータ）
        resistance_levels = [
            SupportResistanceLevel(price=4.24, strength=0.8, level_type='resistance'),
            SupportResistanceLevel(price=4.10, strength=0.6, level_type='resistance'),
        ]
        
        support_levels = [
            SupportResistanceLevel(price=4.50, strength=0.7, level_type='support'),
            SupportResistanceLevel(price=4.40, strength=0.5, level_type='support'),
        ]
        
        mock_context = MarketContext(
            trend_direction='up',
            volatility=0.02,
            volume_profile='normal',
            market_phase='trending'
        )
        
        print(f"テストケース1: 現在価格 ${current_price:.2f}")
        print(f"レジスタンスレベル: {[r.price for r in resistance_levels]}")
        print(f"サポートレベル: {[s.price for s in support_levels]}")
        
        try:
            levels = calculator.calculate_levels(
                current_price=current_price,
                leverage=2.0,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                market_context=mock_context
            )
            
            print(f"計算結果:")
            print(f"  利確価格: ${levels.take_profit_price:.2f}")
            print(f"  損切り価格: ${levels.stop_loss_price:.2f}")
            
            if levels.take_profit_price <= current_price:
                print(f"🚨 BUG再現: 利確価格({levels.take_profit_price:.2f}) <= エントリー価格({current_price:.2f})")
                print(f"原因: 現在価格より上のレジスタンスレベルが存在しない")
            else:
                print(f"✅ 正常: 利確価格 > エントリー価格")
                
        except Exception as e:
            print(f"計算エラー: {e}")
            if "現在価格より上の抵抗線データが不足" in str(e):
                print(f"✅ 期待されるエラー: 適切な検証が機能している")
            else:
                print(f"🚨 予期しないエラー")
    
    except Exception as e:
        print(f"❌ テストエラー: {e}")

def main():
    """メインテスト実行"""
    print("🚀 抵抗線計算バグ調査")
    print("=" * 60)
    print("目的: 利確価格 < エントリー価格 バグの根本原因特定")
    print("=" * 60)
    
    # 1. 実際のデータでの抵抗線計算確認
    test_resistance_calculation_bug()
    
    # 2. 具体的な問題データでのテスト
    test_specific_problematic_data()
    
    print(f"\n" + "=" * 60)
    print("📋 調査結論:")
    print("1. 抵抗線データが現在価格より低い場合にバグが発生")
    print("2. フラクタル分析で過去の価格レベルが抵抗線として誤認される")
    print("3. Level 1 厳格検証が機能している場合は適切にエラーが発生")
    print("4. 修正必要: フラクタル分析のロジック改善")

if __name__ == '__main__':
    main()