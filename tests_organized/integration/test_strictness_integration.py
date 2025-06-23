#!/usr/bin/env python3
"""
厳しさレベル統合システムのテスト

developmentレベルで銘柄追加テストを実行し、
実際にシグナルが生成されることを確認
"""

import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_strictness_integration():
    """厳しさレベル統合システムのテスト"""
    print("🧪 厳しさレベル統合システムテスト")
    print("=" * 60)
    
    from config.unified_config_manager import UnifiedConfigManager
    
    # シングルトンをリセット（新しい設定を反映）
    UnifiedConfigManager._instance = None
    UnifiedConfigManager._initialized = False
    
    config_manager = UnifiedConfigManager()
    
    # 現在のレベル表示
    print("\n📊 統合設定システム状況:")
    current_level = config_manager.get_current_strictness_level()
    print(f"   現在の厳しさレベル: {current_level}")
    
    # レベル別比較表示
    config_manager.print_strictness_comparison("15m", "Aggressive_ML")
    
    # developmentレベルに変更
    print(f"\n🔧 developmentレベルに変更...")
    config_manager.set_strictness_level('development')
    
    # development条件を確認
    dev_conditions = config_manager.get_entry_conditions('15m', 'Aggressive_ML', 'development')
    print(f"\n📋 Development レベル条件 (15m Aggressive_ML):")
    print(f"   最小レバレッジ: {dev_conditions['min_leverage']:.1f}x")
    print(f"   最小信頼度: {dev_conditions['min_confidence'] * 100:.0f}%")
    print(f"   最小RR比: {dev_conditions['min_risk_reward']:.1f}")
    print(f"   厳しさシステム使用: {dev_conditions.get('using_strictness_system', False)}")
    
    # 実際に銘柄追加テストを実行
    print(f"\n🚀 Development条件での銘柄追加テスト:")
    print("-" * 50)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem()
        
        # テスト実行
        symbol, timeframe, config = "ETH", "15m", "Aggressive_ML"
        print(f"\nテスト対象: {symbol} {timeframe} {config}")
        
        start_time = datetime.now()
        
        # より短期間での評価（developmentレベルで条件緩和済み）
        trades_data = system._generate_real_analysis(
            symbol, timeframe, config,
            evaluation_period_days=2  # 2日間
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"⏱️ 処理時間: {duration:.2f}秒")
        
        if trades_data and len(trades_data) > 0:
            print(f"✅ シグナル生成成功: {len(trades_data)}件")
            
            # 統計情報
            entry_prices = [t.get('entry_price', 0) for t in trades_data]
            leverages = [t.get('leverage', 0) for t in trades_data]
            
            print(f"\n📊 生成されたシグナル統計:")
            print(f"   エントリー価格範囲: ${min(entry_prices):.2f} - ${max(entry_prices):.2f}")
            print(f"   レバレッジ範囲: {min(leverages):.1f}x - {max(leverages):.1f}x")
            print(f"   価格の種類数: {len(set(entry_prices))}")
            
            # 最初の3件表示
            print(f"\n📋 最初の3件:")
            for i, trade in enumerate(trades_data[:3]):
                print(f"   {i+1}. Entry: ${trade.get('entry_price', 0):.2f}, "
                      f"TP: ${trade.get('take_profit_price', 0):.2f}, "
                      f"SL: ${trade.get('stop_loss_price', 0):.2f}, "
                      f"Leverage: {trade.get('leverage', 0):.1f}x")
            
            # ハードコード値チェック
            if len(set(entry_prices)) == 1:
                print(f"⚠️ 警告: 全て同じエントリー価格（ハードコード値の可能性）")
            else:
                print(f"✅ 適切な価格多様性を確認")
                
        else:
            print(f"❌ シグナル生成なし（developmentレベルでも条件が厳しい可能性）")
    
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
    
    # standardレベルに戻す
    print(f"\n🔄 standardレベルに戻します...")
    config_manager.set_strictness_level('standard')
    
    print(f"\n✅ 厳しさレベル統合システムテスト完了")

if __name__ == "__main__":
    test_strictness_integration()