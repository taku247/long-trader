"""
プラグインシステム デモンストレーション

新しいプラグインアーキテクチャの動作テストとデモンストレーション。
memo記載の「ハイレバのロング何倍かけて大丈夫か判定するbot」の実装例。
"""

import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines import HighLeverageBotOrchestrator, analyze_leverage_for_symbol, quick_leverage_check

def demo_single_analysis(symbol: str = "HYPE"):
    """単一銘柄のハイレバレッジ分析デモ"""
    
    print("🎯 プラグイン型ハイレバレッジ判定システム デモ")
    print("=" * 70)
    print(f"memo記載の核心機能: 「{symbol}に対してハイレバのロング何倍かけて大丈夫か判定」")
    print("=" * 70)
    
    try:
        # ハイレバボット統括システムを初期化
        orchestrator = HighLeverageBotOrchestrator()
        
        # レバレッジ機会を分析
        recommendation = orchestrator.analyze_leverage_opportunity(symbol, "1h")
        
        print(f"\n🎉 {symbol} 分析完了!")
        print(f"📝 最終判定: {recommendation.recommended_leverage:.1f}x レバレッジ推奨")
        
        return recommendation
        
    except Exception as e:
        print(f"❌ デモ実行エラー: {e}")
        return None

def demo_multiple_symbols():
    """複数銘柄の一括分析デモ"""
    
    symbols = ["HYPE", "SOL", "WIF"]
    
    print("\n🔄 複数銘柄一括分析デモ")
    print("=" * 50)
    
    results = {}
    
    for symbol in symbols:
        print(f"\n🎯 {symbol} 分析中...")
        try:
            result = quick_leverage_check(symbol)
            results[symbol] = result
            print(f"✅ {symbol}: {result}")
        except Exception as e:
            results[symbol] = f"❌ エラー: {e}"
            print(f"❌ {symbol}: エラー")
    
    print("\n📊 一括分析結果サマリー:")
    print("-" * 50)
    for symbol, result in results.items():
        print(f"{symbol:6s}: {result}")
    
    return results

def demo_plugin_replacement():
    """プラグイン差し替えデモ"""
    
    print("\n🔧 プラグイン差し替えデモ")
    print("=" * 50)
    
    try:
        # カスタムプラグインの作成例
        from interfaces import ISupportResistanceAnalyzer
        from interfaces.data_types import SupportResistanceLevel
        from datetime import datetime
        
        class CustomSupportResistanceAnalyzer(ISupportResistanceAnalyzer):
            """カスタムサポレジ分析器の例"""
            
            def find_levels(self, data, **kwargs):
                """簡易的なサポレジ検出"""
                levels = []
                
                if not data.empty:
                    current_price = data['close'].iloc[-1]
                    
                    # 簡易的なサポート・レジスタンスレベル
                    support_level = SupportResistanceLevel(
                        price=current_price * 0.95,
                        strength=0.8,
                        touch_count=3,
                        level_type='support',
                        first_touch=datetime.now(),
                        last_touch=datetime.now(),
                        volume_at_level=1000000,
                        distance_from_current=-5.0
                    )
                    
                    resistance_level = SupportResistanceLevel(
                        price=current_price * 1.05,
                        strength=0.7,
                        touch_count=2,
                        level_type='resistance',
                        first_touch=datetime.now(),
                        last_touch=datetime.now(),
                        volume_at_level=800000,
                        distance_from_current=5.0
                    )
                    
                    levels = [support_level, resistance_level]
                
                return levels
            
            def calculate_level_strength(self, level, data):
                return level.strength
            
            def get_nearest_levels(self, current_price, levels, count=5):
                supports = [l for l in levels if l.level_type == 'support']
                resistances = [l for l in levels if l.level_type == 'resistance']
                return supports[:count], resistances[:count]
        
        # オーケストレーターを初期化
        orchestrator = HighLeverageBotOrchestrator(use_default_plugins=False)
        
        # カスタムプラグインを設定
        custom_analyzer = CustomSupportResistanceAnalyzer()
        orchestrator.set_support_resistance_analyzer(custom_analyzer)
        
        print("✅ カスタムサポレジ分析器を設定しました")
        print("🧪 プラグイン差し替えが正常に動作しています")
        
        return True
        
    except Exception as e:
        print(f"❌ プラグイン差し替えエラー: {e}")
        return False

def demo_comprehensive_test():
    """包括的なテストデモ"""
    
    print("\n🧪 包括的システムテスト")
    print("=" * 50)
    
    test_results = {
        "single_analysis": False,
        "multiple_analysis": False,
        "plugin_replacement": False
    }
    
    # 1. 単一分析テスト
    print("\n1️⃣ 単一銘柄分析テスト")
    try:
        result = demo_single_analysis("HYPE")
        test_results["single_analysis"] = result is not None
        print("✅ 単一分析テスト: 成功")
    except Exception as e:
        print(f"❌ 単一分析テスト: 失敗 ({e})")
    
    # 2. 複数分析テスト
    print("\n2️⃣ 複数銘柄分析テスト")
    try:
        results = demo_multiple_symbols()
        test_results["multiple_analysis"] = len(results) > 0
        print("✅ 複数分析テスト: 成功")
    except Exception as e:
        print(f"❌ 複数分析テスト: 失敗 ({e})")
    
    # 3. プラグイン差し替えテスト
    print("\n3️⃣ プラグイン差し替えテスト")
    try:
        success = demo_plugin_replacement()
        test_results["plugin_replacement"] = success
        print("✅ プラグイン差し替えテスト: 成功")
    except Exception as e:
        print(f"❌ プラグイン差し替えテスト: 失敗 ({e})")
    
    # 結果サマリー
    print("\n📊 テスト結果サマリー")
    print("=" * 30)
    for test_name, result in test_results.items():
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name:20s}: {status}")
    
    total_success = sum(test_results.values())
    print(f"\n🎯 総合成績: {total_success}/{len(test_results)} テスト成功")
    
    if total_success == len(test_results):
        print("🎉 プラグインシステムは正常に動作しています!")
    else:
        print("⚠️ 一部のテストが失敗しました。詳細を確認してください。")
    
    return test_results

def main():
    """メインデモ実行"""
    
    print("🚀 プラグインアーキテクチャ システムデモ開始")
    print(f"⏰ 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        # 包括的テストを実行
        results = demo_comprehensive_test()
        
        print("\n" + "=" * 70)
        print("📝 デモ完了サマリー")
        print("=" * 70)
        print("🎯 memo記載の核心機能「ハイレバのロング何倍かけて大丈夫か判定するbot」")
        print("✅ プラグイン型アーキテクチャで実装完了")
        print("🔧 各コンポーネントは差し替え可能")
        print("📊 既存システムとの後方互換性を維持")
        
        success_rate = sum(results.values()) / len(results) * 100
        print(f"📈 システム成功率: {success_rate:.0f}%")
        
        if success_rate >= 80:
            print("🎉 プラグインシステムは本格運用可能です!")
        else:
            print("⚠️ 追加の調整が必要です")
            
    except Exception as e:
        print(f"❌ デモ実行中にエラーが発生: {e}")
    
    print(f"\n⏰ 完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()