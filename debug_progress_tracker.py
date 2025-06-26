#!/usr/bin/env python3
"""
progress_tracker診断ツール
リアルタイム進捗システムの問題を特定する
"""

import sys
import os
import traceback
from datetime import datetime

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_progress_tracker_basic():
    """基本的なprogress_tracker機能テスト"""
    print("🔍 progress_tracker基本機能テスト開始")
    
    try:
        from web_dashboard.analysis_progress import progress_tracker, SupportResistanceResult
        print("✅ progress_tracker インポート成功")
        
        # テスト実行ID
        test_execution_id = f"debug_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 1. 分析開始
        print(f"📊 テスト実行ID: {test_execution_id}")
        progress_tracker.start_analysis("TEST", test_execution_id)
        print("✅ start_analysis 成功")
        
        # 2. 段階更新
        progress_tracker.update_stage(test_execution_id, "data_validation")
        print("✅ update_stage 成功")
        
        # 3. Support/Resistance更新
        result = SupportResistanceResult(
            status="success",
            supports_count=3,
            resistances_count=2,
            supports=[{"price": 100.0, "strength": 0.8, "touch_count": 5}],
            resistances=[{"price": 110.0, "strength": 0.7, "touch_count": 3}]
        )
        progress_tracker.update_support_resistance(test_execution_id, result)
        print("✅ update_support_resistance 成功")
        
        # 4. 完了
        progress_tracker.complete_analysis(test_execution_id, "signal_detected", "Test completed")
        print("✅ complete_analysis 成功")
        
        # 5. データ取得確認
        recent = progress_tracker.get_all_recent(1)
        print(f"📊 取得データ数: {len(recent)}")
        
        if recent:
            latest = recent[0]
            print(f"🎯 最新データ:")
            print(f"  - symbol: {latest.symbol}")
            print(f"  - execution_id: {latest.execution_id}")
            print(f"  - current_stage: {latest.current_stage}")
            print(f"  - overall_status: {latest.overall_status}")
            print(f"  - support_resistance.status: {latest.support_resistance.status}")
            print(f"  - final_signal: {latest.final_signal}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        traceback.print_exc()
        return False

def test_auto_symbol_trainer_integration():
    """AutoSymbolTrainerとprogress_trackerの統合テスト"""
    print("\n🔍 AutoSymbolTrainer統合テスト開始")
    
    try:
        from auto_symbol_training import AutoSymbolTrainer, PROGRESS_TRACKER_AVAILABLE
        print(f"📊 PROGRESS_TRACKER_AVAILABLE: {PROGRESS_TRACKER_AVAILABLE}")
        
        if PROGRESS_TRACKER_AVAILABLE:
            print("✅ AutoSymbolTrainerでprogress_tracker利用可能")
            
            # progress_trackerへの直接アクセステスト
            from web_dashboard.analysis_progress import progress_tracker
            trainer = AutoSymbolTrainer()
            
            # トレーナーのインスタンス内でprogress_trackerが利用可能か確認
            test_id = f"trainer_test_{datetime.now().strftime('%H%M%S')}"
            progress_tracker.start_analysis("TRAINER_TEST", test_id)
            recent = progress_tracker.get_all_recent(1)
            print(f"📊 トレーナー統合テスト: データ数={len(recent)}")
            
        else:
            print("❌ AutoSymbolTrainerでprogress_tracker利用不可")
            
        return PROGRESS_TRACKER_AVAILABLE
        
    except Exception as e:
        print(f"❌ 統合テストエラー: {e}")
        traceback.print_exc()
        return False

def test_orchestrator_integration():
    """Orchestratorとprogress_trackerの統合テスト"""
    print("\n🔍 Orchestrator統合テスト開始")
    
    try:
        # 環境変数設定（ProcessPoolExecutor環境をシミュレート）
        test_execution_id = f"orch_test_{datetime.now().strftime('%H%M%S')}"
        os.environ['CURRENT_EXECUTION_ID'] = test_execution_id
        
        # プロジェクトルート設定
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Orchestratorでのインポートテスト
        from web_dashboard.analysis_progress import progress_tracker, SupportResistanceResult
        print("✅ Orchestrator環境でprogress_trackerインポート成功")
        
        # 更新テスト
        progress_tracker.start_analysis("ORCH_TEST", test_execution_id)
        
        # Support/Resistance結果更新テスト
        supports_data = [{"price": 150.0, "strength": 0.9, "touch_count": 4}]
        resistances_data = [{"price": 160.0, "strength": 0.8, "touch_count": 3}]
        
        progress_tracker.update_support_resistance(test_execution_id, 
            SupportResistanceResult(
                status="success",
                supports_count=1,
                resistances_count=1,
                supports=supports_data,
                resistances=resistances_data
            ))
        print("✅ Orchestrator環境でupdate_support_resistance成功")
        
        # データ確認
        recent = progress_tracker.get_all_recent(1)
        if recent:
            latest = recent[0]
            print(f"📊 Orchestratorテストデータ確認:")
            print(f"  - execution_id: {latest.execution_id}")
            print(f"  - support_resistance.status: {latest.support_resistance.status}")
            print(f"  - supports_count: {latest.support_resistance.supports_count}")
            
        return True
        
    except Exception as e:
        print(f"❌ Orchestrator統合エラー: {e}")
        traceback.print_exc()
        return False

def test_api_endpoint():
    """APIエンドポイントテスト"""
    print("\n🔍 APIエンドポイントテスト開始")
    
    try:
        import requests
        
        # APIからデータ取得
        response = requests.get("http://localhost:5001/api/analysis/recent?hours=1", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API正常応答: {data['count']}件のデータ")
            
            if data['analyses']:
                latest = data['analyses'][0]
                print(f"📊 最新データ:")
                print(f"  - symbol: {latest['symbol']}")
                print(f"  - execution_id: {latest['execution_id']}")
                print(f"  - current_stage: {latest['current_stage']}")
                print(f"  - overall_status: {latest['overall_status']}")
                print(f"  - support_resistance.status: {latest['support_resistance']['status']}")
            
            return True
        else:
            print(f"❌ API応答エラー: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ APIテストエラー: {e}")
        return False

def main():
    """メイン診断実行"""
    print("🔍 progress_tracker診断ツール開始")
    print("=" * 60)
    
    results = {}
    
    # 1. 基本機能テスト
    results['basic'] = test_progress_tracker_basic()
    
    # 2. AutoSymbolTrainer統合テスト
    results['trainer'] = test_auto_symbol_trainer_integration()
    
    # 3. Orchestrator統合テスト
    results['orchestrator'] = test_orchestrator_integration()
    
    # 4. APIエンドポイントテスト
    results['api'] = test_api_endpoint()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("🎯 診断結果サマリー")
    print("=" * 60)
    
    for test_name, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{test_name:15}: {status}")
    
    # 問題特定
    if not all(results.values()):
        print("\n🚨 問題が検出されました:")
        if not results['basic']:
            print("  - progress_tracker基本機能に問題があります")
        if not results['trainer']:
            print("  - AutoSymbolTrainer統合に問題があります")
        if not results['orchestrator']:
            print("  - Orchestrator統合に問題があります")
        if not results['api']:
            print("  - APIエンドポイントに問題があります")
    else:
        print("\n✅ 全てのテストが成功しました")
        print("   問題は別の箇所にある可能性があります")

if __name__ == "__main__":
    main()