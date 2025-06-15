#!/usr/bin/env python3
"""
エントリー価格統一問題の詳細調査
DOTのトレード結果で全てのエントリー価格、利確ライン、損切りライン、レバレッジが同一値になる問題を調査
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_entry_price_uniformity():
    """エントリー価格統一問題の調査"""
    print("🔍 エントリー価格統一問題 - 詳細調査")
    print("=" * 70)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem()
        
        # DOTの複数戦略を確認
        test_cases = [
            ('DOT', '1h', 'Conservative_ML'),
            ('DOT', '30m', 'Aggressive_Traditional'),
            ('DOT', '15m', 'Full_ML'),
        ]
        
        all_issues_found = []
        
        for symbol, timeframe, config in test_cases:
            print(f"\n📊 {symbol} {timeframe} {config} 分析")
            print("-" * 50)
            
            try:
                trades_data = system.load_compressed_trades(symbol, timeframe, config)
                
                if trades_data is not None and len(trades_data) >= 10:
                    print(f"✅ トレードデータ読み込み成功: {len(trades_data)}件")
                    
                    # 価格データ収集
                    entry_prices = []
                    tp_prices = []
                    sl_prices = []
                    leverages = []
                    exit_prices = []
                    
                    for trade in trades_data[:10]:  # 最初の10件を分析
                        entry_prices.append(trade.get('entry_price'))
                        tp_prices.append(trade.get('take_profit_price'))
                        sl_prices.append(trade.get('stop_loss_price'))
                        leverages.append(trade.get('leverage'))
                        exit_prices.append(trade.get('exit_price'))
                    
                    # 統一性チェック
                    issues = {}
                    
                    if len(set(entry_prices)) == 1:
                        issues['entry_price'] = entry_prices[0]
                        print(f"❌ エントリー価格統一: {entry_prices[0]}")
                    else:
                        print(f"✅ エントリー価格多様性: {len(set(entry_prices))}種類")
                    
                    if len(set(tp_prices)) == 1:
                        issues['take_profit'] = tp_prices[0]
                        print(f"❌ 利確ライン統一: {tp_prices[0]}")
                    else:
                        print(f"✅ 利確ライン多様性: {len(set(tp_prices))}種類")
                    
                    if len(set(sl_prices)) == 1:
                        issues['stop_loss'] = sl_prices[0]
                        print(f"❌ 損切りライン統一: {sl_prices[0]}")
                    else:
                        print(f"✅ 損切りライン多様性: {len(set(sl_prices))}種類")
                    
                    if len(set(leverages)) == 1:
                        issues['leverage'] = leverages[0]
                        print(f"❌ レバレッジ統一: {leverages[0]}x")
                    else:
                        print(f"✅ レバレッジ多様性: {len(set(leverages))}種類")
                    
                    # 実際の価格変動確認（exit_priceは実際のOHLCVから取得されるはず）
                    if len(set(exit_prices)) > 1:
                        print(f"✅ 実際の価格変動確認: {len(set(exit_prices))}種類のクローズ価格")
                        print(f"   範囲: {min(exit_prices):.4f} - {max(exit_prices):.4f}")
                    else:
                        print(f"❌ クローズ価格も統一: {exit_prices[0]}")
                    
                    if issues:
                        all_issues_found.append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'config': config,
                            'issues': issues
                        })
                
                else:
                    print("❌ トレードデータ不足")
                    
            except Exception as e:
                print(f"❌ データ読み込みエラー: {e}")
        
        return all_issues_found
        
    except Exception as e:
        print(f"❌ システムエラー: {e}")
        import traceback
        traceback.print_exc()
        return []

def analyze_backtest_engine_logic():
    """バックテストエンジンのロジック分析"""
    print("\n🔍 バックテストエンジンロジック分析")
    print("=" * 70)
    
    try:
        # バックテストエンジンの実装を確認
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        
        print("✅ HighLeverageBotOrchestrator インポート成功")
        
        # インスタンス作成してメソッド確認
        bot = HighLeverageBotOrchestrator()
        
        print("📊 利用可能メソッド:")
        methods = [method for method in dir(bot) if not method.startswith('_')]
        for method in methods[:10]:  # 最初の10個
            print(f"  - {method}")
        
        # analyze_leverage_opportunityメソッドの動作確認
        print("\n🎯 leverage機会分析テスト:")
        
        try:
            result = bot.analyze_leverage_opportunity("DOT", "1h")
            
            print(f"✅ 分析実行成功")
            print(f"  現在価格: {result.market_conditions.current_price}")
            print(f"  推奨レバレッジ: {result.recommended_leverage}x")
            print(f"  信頼度: {result.confidence}%")
            
            # 価格が時間と共に変化するかテスト
            import time
            time.sleep(2)
            result2 = bot.analyze_leverage_opportunity("DOT", "1h")
            
            if result.market_conditions.current_price != result2.market_conditions.current_price:
                print("✅ 価格は時間と共に変化")
            else:
                print("❌ 価格が変化していない（キャッシュまたは固定値の可能性）")
                
        except Exception as analysis_error:
            print(f"❌ 分析エラー: {analysis_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ エンジン分析エラー: {e}")
        return False

def investigate_root_cause():
    """根本原因の調査"""
    print("\n🔍 根本原因調査")
    print("=" * 70)
    
    # 仮説
    hypotheses = [
        "バックテストで同一の現在価格を使用している",
        "エントリーシグナルが全て同じタイミングで発生",
        "TP/SL計算ロジックが固定値を使用",
        "レバレッジ計算が市場状況を反映していない",
        "時系列データの処理に問題がある"
    ]
    
    print("🤔 考えられる原因:")
    for i, hypothesis in enumerate(hypotheses, 1):
        print(f"  {i}. {hypothesis}")
    
    print("\n💡 推奨調査項目:")
    print("  1. バックテストエンジンのエントリー価格決定ロジック")
    print("  2. TP/SL価格計算アルゴリズム")
    print("  3. レバレッジ決定メカニズム")
    print("  4. 時系列データの使用方法")
    print("  5. シグナル生成タイミング")

def create_test_recommendations():
    """テスト推奨事項の作成"""
    print("\n📋 テスト改善推奨事項")
    print("=" * 70)
    
    recommendations = [
        {
            "category": "単体テスト追加",
            "items": [
                "エントリー価格多様性テスト",
                "TP/SL価格計算テスト", 
                "レバレッジ決定ロジックテスト",
                "時系列データ処理テスト"
            ]
        },
        {
            "category": "統合テスト強化",
            "items": [
                "複数時間軸での価格多様性確認",
                "異なる市場状況でのバックテスト",
                "リアルタイム価格vs固定価格の検証"
            ]
        },
        {
            "category": "監視機能追加",
            "items": [
                "価格統一検知アラート",
                "レバレッジ多様性監視",
                "異常パターン自動検出"
            ]
        }
    ]
    
    for rec in recommendations:
        print(f"\n🎯 {rec['category']}:")
        for item in rec['items']:
            print(f"  • {item}")

def main():
    """メイン実行関数"""
    print("🚀 エントリー価格統一問題 - 包括的調査")
    print("=" * 70)
    print("目的: DOTトレード結果の価格統一問題を詳細調査し、改善提案を作成")
    print("=" * 70)
    
    # 1. エントリー価格統一問題の確認
    issues = test_entry_price_uniformity()
    
    # 2. バックテストエンジンのロジック分析
    engine_ok = analyze_backtest_engine_logic()
    
    # 3. 根本原因の調査
    investigate_root_cause()
    
    # 4. テスト改善推奨事項
    create_test_recommendations()
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 調査結果サマリー")
    print("=" * 70)
    
    if issues:
        print(f"❌ 価格統一問題確認: {len(issues)}件の戦略で問題発見")
        for issue in issues:
            print(f"  • {issue['symbol']} {issue['timeframe']} {issue['config']}")
    else:
        print("✅ 価格統一問題なし")
    
    if engine_ok:
        print("✅ バックテストエンジン基本動作確認")
    else:
        print("❌ バックテストエンジン動作不安定")
    
    print("\n🎯 次のアクション:")
    print("1. バックテストエンジンのエントリー価格決定ロジック詳細調査")
    print("2. 価格多様性確保のためのテスト実装")
    print("3. 統一価格検知の自動監視機能追加")
    print("4. ハードコード値とは異なる、この統一価格問題の修正")

if __name__ == '__main__':
    main()