#!/usr/bin/env python3
"""
銘柄追加テスト（条件緩和版）
実際にシグナルが生成されることを確認
"""

import sys
import os
import json
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def temporarily_relax_conditions():
    """一時的に条件を緩和"""
    config_path = "config/trading_conditions.json"
    
    # 元の設定をバックアップ
    with open(config_path, 'r', encoding='utf-8') as f:
        original_config = json.load(f)
    
    # 条件を緩和
    relaxed_config = original_config.copy()
    for timeframe in relaxed_config['entry_conditions_by_timeframe']:
        conditions = relaxed_config['entry_conditions_by_timeframe'][timeframe]
        # 条件を大幅に緩和
        conditions['min_leverage'] = max(1.0, conditions.get('min_leverage', 3.0) * 0.3)  # 70%減
        conditions['min_confidence'] = max(0.1, conditions.get('min_confidence', 0.5) * 0.6)  # 40%減
        conditions['min_risk_reward'] = max(0.5, conditions.get('min_risk_reward', 2.0) * 0.5)  # 50%減
    
    # 一時設定を保存
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(relaxed_config, f, indent=2, ensure_ascii=False)
    
    print("✅ 条件を一時的に緩和しました")
    
    return original_config

def restore_conditions(original_config):
    """元の条件に復元"""
    config_path = "config/trading_conditions.json"
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(original_config, f, indent=2, ensure_ascii=False)
    
    print("✅ 元の条件に復元しました")

def test_relaxed_conditions():
    """緩和条件でのテスト"""
    print("🧪 条件緩和テスト")
    print("=" * 60)
    
    # 条件を一時的に緩和
    original_config = temporarily_relax_conditions()
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        # シングルトンをリセット（新しい設定を反映するため）
        from config.unified_config_manager import UnifiedConfigManager
        UnifiedConfigManager._instance = None
        UnifiedConfigManager._initialized = False
        
        system = ScalableAnalysisSystem()
        
        # 緩和後の条件を表示
        config_manager = UnifiedConfigManager()
        print("\n📋 緩和後の条件（15m足 Aggressive_ML）:")
        conditions = config_manager.get_entry_conditions('15m', 'Aggressive_ML')
        print(f"   最小レバレッジ: {conditions.get('min_leverage')}x")
        print(f"   最小信頼度: {conditions.get('min_confidence') * 100:.0f}%")
        print(f"   最小RR比: {conditions.get('min_risk_reward')}")
        
        # テスト実行
        symbol, timeframe, config = "ETH", "15m", "Aggressive_ML"
        
        print(f"\n🚀 テスト実行: {symbol} {timeframe} {config}")
        print("-" * 50)
        
        start_time = datetime.now()
        
        # より短期間での評価
        trades_data = system._generate_real_analysis(
            symbol, timeframe, config,
            evaluation_period_days=3  # 3日間のみ
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"⏱️ 処理時間: {duration:.2f}秒")
        
        if trades_data and len(trades_data) > 0:
            print(f"✅ シグナル生成成功: {len(trades_data)}件")
            
            # 最初の3件を表示
            print("\n📊 生成されたシグナル（最初の3件）:")
            for i, trade in enumerate(trades_data[:3]):
                print(f"   {i+1}. Entry: ${trade.get('entry_price', 0):.2f}, "
                      f"TP: ${trade.get('take_profit_price', 0):.2f}, "
                      f"SL: ${trade.get('stop_loss_price', 0):.2f}, "
                      f"Leverage: {trade.get('leverage', 0):.1f}x")
            
            # 価格の多様性確認
            entry_prices = [t.get('entry_price', 0) for t in trades_data]
            unique_prices = len(set(entry_prices))
            print(f"\n💰 価格多様性: {unique_prices}種類のエントリー価格")
            
            if unique_prices == 1:
                print("⚠️ 警告: 全て同じエントリー価格（ハードコード値の可能性）")
            else:
                print("✅ 適切な価格多様性を確認")
                
        else:
            print("❌ シグナル生成なし（条件をさらに緩和する必要があるかもしれません）")
    
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 元の条件に復元
        restore_conditions(original_config)
        
        # シングルトンをリセット（元の設定を反映するため）
        UnifiedConfigManager._instance = None
        UnifiedConfigManager._initialized = False
    
    print("\n✅ 条件緩和テスト完了")

if __name__ == "__main__":
    test_relaxed_conditions()