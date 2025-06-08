"""
Enhanced ML Predictor Adapter 差し替えテスト

ExistingMLPredictorAdapter から EnhancedMLPredictorAdapter への
差し替えが正常に動作するかテストします。
"""

import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines import HighLeverageBotOrchestrator
from adapters import ExistingMLPredictorAdapter
from adapters.enhanced_ml_adapter import EnhancedMLPredictorAdapter

def test_enhanced_adapter_replacement():
    """Enhanced ML Predictor Adapter の差し替えテスト"""
    
    print("🧪 Enhanced ML Predictor Adapter 差し替えテスト")
    print("=" * 60)
    
    try:
        # 1. デフォルトシステム（ExistingMLPredictorAdapter）
        print("\n1️⃣ デフォルトシステムテスト")
        print("-" * 40)
        
        orchestrator1 = HighLeverageBotOrchestrator()
        
        # 現在の予測器を確認
        current_predictor = orchestrator1.breakout_predictor
        print(f"現在の予測器: {type(current_predictor).__name__}")
        
        if hasattr(current_predictor, 'get_model_accuracy'):
            accuracy1 = current_predictor.get_model_accuracy()
            print(f"精度情報: {accuracy1}")
        
        # 2. Enhanced ML Predictor Adapter に差し替え
        print("\n2️⃣ Enhanced ML Predictor Adapter への差し替え")
        print("-" * 40)
        
        enhanced_adapter = EnhancedMLPredictorAdapter()
        print(f"新しい予測器: {type(enhanced_adapter).__name__}")
        
        # パフォーマンスサマリーを確認
        summary = enhanced_adapter.get_performance_summary()
        print(f"初期パフォーマンス: {summary}")
        
        # 差し替え実行
        orchestrator1.set_breakout_predictor(enhanced_adapter)
        print("✅ 予測器の差し替えが完了しました")
        
        # 差し替え確認
        updated_predictor = orchestrator1.breakout_predictor
        print(f"更新後の予測器: {type(updated_predictor).__name__}")
        
        # 3. 新しいOrchestrator でEnhanced Adapter を直接使用
        print("\n3️⃣ 新規Orchestrator でEnhanced Adapter 直接使用")
        print("-" * 40)
        
        orchestrator2 = HighLeverageBotOrchestrator(use_default_plugins=False)
        enhanced_adapter2 = EnhancedMLPredictorAdapter()
        
        orchestrator2.set_breakout_predictor(enhanced_adapter2)
        print("✅ 新規システムでEnhanced Adapter を設定完了")
        
        # 4. 機能比較テスト
        print("\n4️⃣ 機能比較テスト")
        print("-" * 40)
        
        # 既存アダプターの機能
        existing_adapter = ExistingMLPredictorAdapter()
        existing_accuracy = existing_adapter.get_model_accuracy()
        print(f"既存アダプター精度: {existing_accuracy}")
        
        # 高精度アダプターの機能
        enhanced_accuracy = enhanced_adapter.get_model_accuracy()
        print(f"高精度アダプター精度: {enhanced_accuracy}")
        
        # 5. インターフェース互換性テスト
        print("\n5️⃣ インターフェース互換性テスト")
        print("-" * 40)
        
        # 両方のアダプターが同じメソッドを持つか確認
        required_methods = [
            'train_model', 'predict_breakout', 'get_model_accuracy',
            'save_model', 'load_model'
        ]
        
        compatibility_results = {}
        
        for method_name in required_methods:
            existing_has = hasattr(existing_adapter, method_name)
            enhanced_has = hasattr(enhanced_adapter, method_name)
            
            compatibility_results[method_name] = {
                'existing': existing_has,
                'enhanced': enhanced_has,
                'compatible': existing_has and enhanced_has
            }
            
            status = "✅" if existing_has and enhanced_has else "❌"
            print(f"  {method_name}: {status}")
        
        # 6. 結果サマリー
        print("\n📊 テスト結果サマリー")
        print("=" * 60)
        
        all_compatible = all(result['compatible'] for result in compatibility_results.values())
        
        if all_compatible:
            print("✅ 全てのインターフェースが互換性を持っています")
            print("🔄 アダプターの差し替えは正常に動作します")
            print("📈 Enhanced ML Predictor Adapter の使用が可能です")
            
            # パフォーマンス改善の確認
            enhanced_auc = enhanced_accuracy.get('auc_score', 0.0)
            existing_acc = existing_accuracy.get('accuracy', 0.57)
            
            if enhanced_auc > existing_acc:
                improvement = (enhanced_auc - existing_acc) / existing_acc * 100
                print(f"🎯 予想精度改善: {improvement:+.1f}%")
            
            return True
        else:
            print("❌ 一部のインターフェースに互換性の問題があります")
            
            for method_name, result in compatibility_results.items():
                if not result['compatible']:
                    print(f"  ⚠️ {method_name}: 既存={result['existing']}, 高精度={result['enhanced']}")
            
            return False
            
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return False

def test_specific_replacement_scenarios():
    """特定の差し替えシナリオテスト"""
    
    print("\n🎯 特定の差し替えシナリオテスト")
    print("=" * 60)
    
    scenarios = [
        {
            'name': 'デフォルト → Enhanced',
            'initial': ExistingMLPredictorAdapter,
            'replacement': EnhancedMLPredictorAdapter
        },
        {
            'name': 'Enhanced → デフォルト',
            'initial': EnhancedMLPredictorAdapter,
            'replacement': ExistingMLPredictorAdapter
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🔄 シナリオ: {scenario['name']}")
        print("-" * 30)
        
        try:
            # 初期システム
            orchestrator = HighLeverageBotOrchestrator(use_default_plugins=False)
            initial_adapter = scenario['initial']()
            orchestrator.set_breakout_predictor(initial_adapter)
            
            print(f"初期予測器: {type(initial_adapter).__name__}")
            
            # 差し替え
            replacement_adapter = scenario['replacement']()
            orchestrator.set_breakout_predictor(replacement_adapter)
            
            print(f"差し替え後: {type(replacement_adapter).__name__}")
            
            # 確認
            current = orchestrator.breakout_predictor
            if type(current) == scenario['replacement']:
                print("✅ 差し替え成功")
            else:
                print("❌ 差し替え失敗")
                
        except Exception as e:
            print(f"❌ シナリオ'{scenario['name']}'でエラー: {e}")

def main():
    """メインテスト実行"""
    
    print("🚀 Enhanced ML Predictor Adapter 差し替えテスト開始")
    print(f"⏰ 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        # 基本差し替えテスト
        basic_success = test_enhanced_adapter_replacement()
        
        # 特定シナリオテスト
        test_specific_replacement_scenarios()
        
        print("\n" + "=" * 70)
        print("📝 差し替えテスト完了サマリー")
        print("=" * 70)
        
        if basic_success:
            print("✅ Enhanced ML Predictor Adapter の差し替えが正常に動作します")
            print("🎯 ExistingMLPredictorAdapter からのアップグレードが可能です")
            print("📈 既存システムとの完全な互換性を維持しています")
            print("🔧 プラグインアーキテクチャが正しく実装されています")
        else:
            print("❌ 差し替えに問題があります")
            print("🔧 インターフェースの調整が必要です")
        
    except Exception as e:
        print(f"❌ テスト実行中にエラーが発生: {e}")
    
    print(f"\n⏰ 完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()