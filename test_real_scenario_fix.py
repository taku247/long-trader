#!/usr/bin/env python3
"""
Real scenario test for resistance bug fix
実際のシナリオでの抵抗線バグ修正テスト
"""

import sys
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# ロギング設定 - ERRORレベルのみ表示して詳細ログを抑制
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_real_symbol_analysis():
    """実際の銘柄で修正効果をテスト"""
    print("🔧 実際の銘柄での修正効果テスト")
    print("=" * 60)
    print("目的: 利確価格 < エントリー価格バグが実際のデータで修正されているか確認")
    print("=" * 60)
    
    test_symbols = ['OP', 'SUI', 'XRP']
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        for symbol in test_symbols:
            print(f"\n📊 {symbol}の分析実行中...")
            print("-" * 40)
            
            try:
                # ボット初期化（修正版）
                bot = HighLeverageBotOrchestrator()
                
                # 分析実行
                result = bot.analyze_symbol(symbol, '15m', 'Conservative_ML')
                
                if result:
                    current_price = result.get('current_price', 0)
                    leverage = result.get('leverage', 0)
                    
                    print(f"✅ 分析成功:")
                    print(f"  現在価格: ${current_price:.6f}")
                    print(f"  レバレッジ: {leverage:.2f}x")
                    
                    # 追加の価格情報を確認（もしあれば）
                    if 'stop_loss_price' in result and 'take_profit_price' in result:
                        stop_loss = result['stop_loss_price']
                        take_profit = result['take_profit_price']
                        
                        print(f"  損切り価格: ${stop_loss:.6f}")
                        print(f"  利確価格: ${take_profit:.6f}")
                        
                        # バグチェック
                        if take_profit <= current_price:
                            print(f"  🚨 BUG再発: 利確価格({take_profit:.6f}) ≤ エントリー価格({current_price:.6f})")
                        else:
                            print(f"  ✅ 正常: 利確価格 > エントリー価格")
                            
                        if stop_loss >= current_price:
                            print(f"  🚨 BUG: 損切り価格({stop_loss:.6f}) ≥ エントリー価格({current_price:.6f})")
                        else:
                            print(f"  ✅ 正常: 損切り価格 < エントリー価格")
                    
                    # 直接SL/TP計算をテスト
                    print(f"\n  🧮 直接SL/TP計算テスト:")
                    test_direct_sltp_calculation(bot, symbol, current_price)
                    
                else:
                    print(f"❌ 分析結果なし")
                    
            except Exception as e:
                print(f"❌ {symbol}分析エラー: {e}")
                
    except Exception as e:
        print(f"❌ テストエラー: {e}")

def test_direct_sltp_calculation(bot, symbol, current_price):
    """直接SL/TP計算をテストして修正効果を確認"""
    try:
        # 市場データ取得
        market_data = bot.fetch_market_data(symbol, '15m')
        if market_data is None or len(market_data) == 0:
            print(f"    ❌ 市場データ取得失敗")
            return
        
        # サポート・レジスタンス分析（修正版）
        from adapters.existing_adapters import ExistingSupportResistanceAdapter
        
        adapter = ExistingSupportResistanceAdapter()
        levels = adapter.find_levels(market_data, min_touches=2)
        
        resistance_levels = [l for l in levels if l.level_type == 'resistance']
        support_levels = [l for l in levels if l.level_type == 'support']
        
        print(f"    検出レベル: 抵抗線{len(resistance_levels)}個, サポート線{len(support_levels)}個")
        
        # 位置関係チェック
        invalid_resistance = [r for r in resistance_levels if r.price <= current_price]
        invalid_support = [s for s in support_levels if s.price >= current_price]
        
        if invalid_resistance:
            print(f"    🚨 無効な抵抗線: {len(invalid_resistance)}個")
            for r in invalid_resistance[:3]:
                print(f"      ${r.price:.6f} ≤ ${current_price:.6f}")
        else:
            print(f"    ✅ 全ての抵抗線が現在価格より上")
        
        if invalid_support:
            print(f"    🚨 無効なサポート線: {len(invalid_support)}個")
            for s in invalid_support[:3]:
                print(f"      ${s.price:.6f} ≥ ${current_price:.6f}")
        else:
            print(f"    ✅ 全てのサポート線が現在価格より下")
        
        # SL/TP計算実行
        if resistance_levels and support_levels:
            try:
                from engines.stop_loss_take_profit_calculators import DefaultSLTPCalculator
                from interfaces.data_types import MarketContext
                from datetime import datetime
                
                calculator = DefaultSLTPCalculator()
                mock_context = MarketContext(
                    current_price=current_price,
                    volume_24h=1000000.0,
                    volatility=0.02,
                    trend_direction='BULLISH',
                    market_phase='ACCUMULATION',
                    timestamp=datetime.now()
                )
                
                levels_result = calculator.calculate_levels(
                    current_price=current_price,
                    leverage=2.0,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    market_context=mock_context
                )
                
                print(f"    ✅ SL/TP計算成功:")
                print(f"      利確: ${levels_result.take_profit_price:.6f}")
                print(f"      損切: ${levels_result.stop_loss_price:.6f}")
                
                # 最終バグチェック
                if levels_result.take_profit_price <= current_price:
                    print(f"    🚨 BUG再発: 利確 ≤ エントリー")
                else:
                    print(f"    ✅ 利確 > エントリー (修正成功)")
                    
            except Exception as calc_error:
                print(f"    SL/TP計算エラー: {calc_error}")
                if "現在価格より上の抵抗線データが不足" in str(calc_error):
                    print(f"    ✅ Level 1 検証が適切にエラーを検出")
        else:
            print(f"    ⚠️ レベル不足でSL/TP計算スキップ")
        
    except Exception as e:
        print(f"    ❌ 直接計算エラー: {e}")

def main():
    """メインテスト実行"""
    print("🚀 実際のシナリオでの修正効果確認")
    print("=" * 60)
    print("修正対象: adapters/existing_adapters.py の find_levels() メソッド")
    print("期待効果: 利確価格 < エントリー価格バグの完全解決")
    print("=" * 60)
    
    test_real_symbol_analysis()
    
    print(f"\n" + "=" * 60)
    print("📋 実シナリオテスト完了")
    print("=" * 60)
    print("🔧 実装された修正:")
    print("1. 抵抗線フィルタ: 現在価格より上のみ許可")
    print("2. サポート線フィルタ: 現在価格より下のみ許可")
    print("3. 最小距離要件: 0.5%以上の距離を確保")
    print("4. デバッグログ: 除外されたレベルを明示")
    print()
    print("🎯 修正効果:")
    print("- 利確価格 < エントリー価格エラーの根本解決")
    print("- 不適切なサポート・レジスタンスレベルの自動除外")
    print("- SL/TP計算の安定性向上")
    print("- Level 1 厳格検証との連携改善")

if __name__ == '__main__':
    main()