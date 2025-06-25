#!/usr/bin/env python3
"""
HYPEの「No trading signals detected」問題の詳細分析
"""
import asyncio
from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
from config.unified_config_manager import UnifiedConfigManager
from datetime import datetime, timedelta, timezone
import json

async def debug_hype_analysis():
    print("🔍 HYPE「No trading signals detected」問題の詳細分析")
    print("=" * 60)
    
    # Exchange設定の確認
    try:
        with open('exchange_config.json', 'r') as f:
            config = json.load(f)
            exchange = config.get('default_exchange', 'hyperliquid')
    except:
        exchange = 'hyperliquid'
    
    print(f"📊 使用取引所: {exchange}")
    
    # ボット初期化
    bot = HighLeverageBotOrchestrator(use_default_plugins=True, exchange=exchange)
    symbol = 'HYPE'
    timeframe = '1h'  # 最もデータが豊富な時間足を使用
    config_name = 'Conservative_ML'
    
    print(f"🎯 分析対象: {symbol} {timeframe} {config_name}")
    
    # 統合設定管理から条件を取得
    try:
        config_manager = UnifiedConfigManager()
        conditions = config_manager.get_entry_conditions(timeframe, config_name)
        print(f"📋 エントリー条件:")
        print(f"  - 最低レバレッジ: {conditions['min_leverage']}x")
        print(f"  - 最低信頼度: {conditions['min_confidence']:.1%}")
        print(f"  - 最低RR比: {conditions['min_risk_reward']}")
    except Exception as e:
        print(f"⚠️ 設定読み込みエラー: {e}")
        # デフォルト値を使用
        conditions = {
            'min_leverage': 3.0,
            'min_confidence': 0.50,
            'min_risk_reward': 2.5
        }
        print(f"📋 デフォルトエントリー条件使用:")
        print(f"  - 最低レバレッジ: {conditions['min_leverage']}x")
        print(f"  - 最低信頼度: {conditions['min_confidence']:.1%}")
        print(f"  - 最低RR比: {conditions['min_risk_reward']}")
    
    print("\n🔄 実際の分析実行（サンプル10回）...")
    
    # 過去90日間から10回のサンプル分析
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=90)
    
    sample_times = []
    interval = timedelta(days=9)  # 9日間隔で10回
    current_time = start_time
    
    for i in range(10):
        sample_times.append(current_time)
        current_time += interval
    
    condition_met_count = 0
    failed_analysis_count = 0
    successful_analysis_count = 0
    
    for i, target_time in enumerate(sample_times, 1):
        try:
            print(f"\n📊 サンプル分析 #{i} ({target_time.strftime('%Y-%m-%d %H:%M')} JST)")
            
            # 実際のハイレバボット分析を実行
            result = bot.analyze_symbol(symbol, timeframe, config_name, is_backtest=True, target_timestamp=target_time)
            
            if not result or 'current_price' not in result:
                print(f"  ❌ 分析結果なし")
                failed_analysis_count += 1
                continue
            
            successful_analysis_count += 1
            
            leverage = result.get('leverage', 0)
            confidence = result.get('confidence', 0) / 100.0
            risk_reward = result.get('risk_reward_ratio', 0)
            current_price = result.get('current_price', 0)
            
            print(f"  📈 価格: ${current_price:.4f}")
            print(f"  ⚖️ レバレッジ: {leverage:.1f}x (必要: {conditions['min_leverage']}x)")
            print(f"  🎯 信頼度: {confidence:.1%} (必要: {conditions['min_confidence']:.1%})")
            print(f"  📊 RR比: {risk_reward:.1f} (必要: {conditions['min_risk_reward']})")
            
            # 条件チェック
            leverage_ok = leverage >= conditions['min_leverage']
            confidence_ok = confidence >= conditions['min_confidence']
            risk_reward_ok = risk_reward >= conditions['min_risk_reward']
            price_ok = current_price > 0
            
            all_conditions_met = leverage_ok and confidence_ok and risk_reward_ok and price_ok
            
            if all_conditions_met:
                condition_met_count += 1
                print(f"  ✅ 条件満足 → シグナル生成可能")
            else:
                print(f"  ❌ 条件不満足:")
                if not leverage_ok:
                    print(f"     - レバレッジ不足: {leverage:.1f} < {conditions['min_leverage']}")
                if not confidence_ok:
                    print(f"     - 信頼度不足: {confidence:.1%} < {conditions['min_confidence']:.1%}")
                if not risk_reward_ok:
                    print(f"     - RR比不足: {risk_reward:.1f} < {conditions['min_risk_reward']}")
                if not price_ok:
                    print(f"     - 価格無効: {current_price}")
            
        except Exception as e:
            print(f"  ❌ 分析エラー: {str(e)[:100]}")
            failed_analysis_count += 1
    
    print("\n" + "=" * 60)
    print("📊 HYPE分析結果サマリー")
    print("=" * 60)
    print(f"🔍 サンプル分析数: {len(sample_times)}")
    print(f"✅ 成功分析数: {successful_analysis_count}")
    print(f"❌ 失敗分析数: {failed_analysis_count}")
    print(f"🎯 条件満足数: {condition_met_count}")
    print(f"📈 条件満足率: {(condition_met_count / successful_analysis_count * 100):.1f}%" if successful_analysis_count > 0 else "N/A")
    
    # 結論
    print("\n🔬 問題分析結果:")
    if condition_met_count == 0:
        print("❌ 全サンプルで条件を満たさず → エントリー条件が厳しすぎる可能性")
        print("💡 推奨対策:")
        print("   1. エントリー条件の緩和（min_leverage, min_confidence, min_risk_reward）")
        print("   2. 他の時間足での分析（5m, 15m, 30m）")
        print("   3. 戦略パラメータの調整")
    elif condition_met_count < successful_analysis_count * 0.1:  # 10%未満
        print("⚠️ 条件満足率が低い → 条件の調整を検討")
        print("💡 推奨対策:")
        print("   1. 部分的な条件緩和")
        print("   2. 市場環境に応じた動的調整")
    else:
        print("✅ 条件満足は可能 → 他の要因が問題の可能性")
        print("💡 調査項目:")
        print("   1. 支持線・抵抗線検出の問題")
        print("   2. 市場データの品質")
        print("   3. TP/SL計算の問題")

if __name__ == "__main__":
    asyncio.run(debug_hype_analysis())