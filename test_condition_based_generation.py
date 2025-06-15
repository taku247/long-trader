#!/usr/bin/env python3
"""
条件ベースシグナル生成動作確認テスト

max_evaluations=100の設定で、実際にシグナルが生成されるかを確認
"""

import sys
import os
from datetime import datetime
import json

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_condition_based_generation():
    """条件ベースシグナル生成のテスト"""
    print("🎯 条件ベースシグナル生成テスト")
    print("=" * 60)
    
    # 設定ファイルの現在値を表示
    config_path = "config/timeframe_conditions.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    print("\n📋 現在の設定値:")
    for timeframe, settings in config_data['timeframe_configs'].items():
        print(f"\n🕐 {timeframe}:")
        print(f"   最大評価回数: {settings.get('max_evaluations', 'N/A')}回")
        if 'entry_conditions' in settings:
            ec = settings['entry_conditions']
            print(f"   最小レバレッジ: {ec.get('min_leverage', 'N/A')}x")
            print(f"   最小信頼度: {ec.get('min_confidence', 'N/A') * 100:.0f}%")
            print(f"   最小RR比: {ec.get('min_risk_reward', 'N/A')}")
    
    # 複数の条件でテスト
    test_cases = [
        ("SOL", "5m", "Aggressive_ML"),
        ("ETH", "15m", "Conservative_ML"),
        ("BTC", "1h", "Conservative_ML"),
    ]
    
    from scalable_analysis_system import ScalableAnalysisSystem
    system = ScalableAnalysisSystem()
    
    results = []
    
    for symbol, timeframe, config in test_cases:
        print(f"\n🔍 テスト: {symbol} {timeframe} {config}")
        print("-" * 50)
        
        try:
            start_time = datetime.now()
            
            # テスト実行（短期間で）
            trades_data = system._generate_real_analysis(
                symbol, timeframe, config,
                evaluation_period_days=7  # 7日間で評価
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if trades_data and len(trades_data) > 0:
                print(f"✅ シグナル生成成功: {len(trades_data)}件")
                print(f"⏱️ 処理時間: {duration:.2f}秒")
                
                # 最初の取引を表示
                first_trade = trades_data[0]
                print(f"📊 最初の取引:")
                print(f"   エントリー: ${first_trade.get('entry_price', 'N/A'):.4f}")
                print(f"   TP: ${first_trade.get('take_profit_price', 'N/A'):.4f}")
                print(f"   SL: ${first_trade.get('stop_loss_price', 'N/A'):.4f}")
                print(f"   レバレッジ: {first_trade.get('leverage', 'N/A')}x")
                
                results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'config': config,
                    'trades': len(trades_data),
                    'duration': duration,
                    'success': True
                })
            else:
                print(f"⚠️ シグナルなし（条件未達）")
                print(f"⏱️ 処理時間: {duration:.2f}秒")
                
                results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'config': config,
                    'trades': 0,
                    'duration': duration,
                    'success': False
                })
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            results.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'config': config,
                'trades': 0,
                'duration': 0,
                'success': False,
                'error': str(e)
            })
    
    # サマリー表示
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー:")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['success'])
    total_trades = sum(r['trades'] for r in results)
    total_duration = sum(r['duration'] for r in results)
    
    print(f"✅ 成功: {success_count}/{len(results)}")
    print(f"📈 総シグナル数: {total_trades}")
    print(f"⏱️ 総処理時間: {total_duration:.2f}秒")
    
    if success_count == 0:
        print("\n⚠️ 全てのテストでシグナルが生成されませんでした")
        print("💡 以下を検討してください:")
        print("   1. 条件を緩和する（min_leverage, min_confidence を下げる）")
        print("   2. 評価期間を延長する")
        print("   3. max_evaluations を増やす")

if __name__ == "__main__":
    test_condition_based_generation()