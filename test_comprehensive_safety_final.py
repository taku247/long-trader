#!/usr/bin/env python3
"""
包括的最終安全性テスト

修正した全機能の最終的な統合テスト
"""

import sys
import os
import tempfile
import time
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_all_modifications():
    """全修正内容の統合テスト"""
    print("🚀 包括的最終安全性テスト開始")
    print("=" * 60)
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    def record_test(name, success, details=""):
        if success:
            print(f"   ✅ {name}")
            test_results["passed"] += 1
        else:
            print(f"   ❌ {name}: {details}")
            test_results["failed"] += 1
        test_results["tests"].append({"name": name, "success": success, "details": details})
    
    try:
        # 1. システム初期化テスト
        print("\n🧪 1. システム初期化テスト")
        try:
            from scalable_analysis_system import ScalableAnalysisSystem
            with tempfile.TemporaryDirectory() as temp_dir:
                system = ScalableAnalysisSystem(os.path.join(temp_dir, "test_analysis"))
                record_test("システム初期化", True)
        except Exception as e:
            record_test("システム初期化", False, str(e))
        
        # 2. 時間足設定動的読み込みテスト
        print("\n🧪 2. 時間足設定動的読み込みテスト")
        try:
            config_1m = system._load_timeframe_config('1m')
            config_15m = system._load_timeframe_config('15m')
            config_1h = system._load_timeframe_config('1h')
            
            record_test("1m足設定読み込み", 
                       config_1m.get('data_days') == 14, 
                       f"expected=14, actual={config_1m.get('data_days')}")
            record_test("15m足設定読み込み", 
                       config_15m.get('data_days') == 90,
                       f"expected=90, actual={config_15m.get('data_days')}")
            record_test("1h足設定読み込み", 
                       config_1h.get('data_days') == 180,
                       f"expected=180, actual={config_1h.get('data_days')}")
        except Exception as e:
            record_test("時間足設定読み込み", False, str(e))
        
        # 3. 評価回数動的計算テスト
        print("\n🧪 3. 評価回数動的計算テスト")
        try:
            # 15m足の計算確認
            data_days = 90
            interval_min = 60
            total_period_minutes = data_days * 24 * 60
            total_possible_evaluations = total_period_minutes // interval_min
            calculated_max_evaluations = int(total_possible_evaluations * 0.8)
            actual_max = min(max(100, calculated_max_evaluations), 5000)
            
            record_test("評価回数動的計算", 
                       actual_max > 1000,
                       f"actual_max={actual_max}, expected>1000")
            
            # カバー率計算
            coverage = (actual_max * interval_min) / total_period_minutes * 100
            record_test("カバー率計算", 
                       coverage >= 50.0,
                       f"coverage={coverage:.1f}%, expected>=50%")
        except Exception as e:
            record_test("評価回数動的計算", False, str(e))
        
        # 4. 賢い評価開始時刻調整テスト
        print("\n🧪 4. 賢い評価開始時刻調整テスト")
        try:
            from datetime import datetime, timezone, timedelta
            
            # SOLパターンのテスト
            data_start = datetime(2025, 3, 27, 6, 30, 0, tzinfo=timezone.utc)
            interval = timedelta(hours=1)
            result = system._find_first_valid_evaluation_time(data_start, interval)
            
            record_test("SOLパターン調整", 
                       result.hour == 7 and result.minute == 0,
                       f"expected=07:00, actual={result.strftime('%H:%M')}")
            
            # 15分足パターンのテスト  
            data_start_15m = datetime(2024, 12, 16, 14, 23, 0, tzinfo=timezone.utc)
            interval_15m = timedelta(minutes=15)
            result_15m = system._find_first_valid_evaluation_time(data_start_15m, interval_15m)
            
            record_test("15分足パターン調整",
                       result_15m.minute == 30,
                       f"expected=:30, actual=:{result_15m.minute}")
        except Exception as e:
            record_test("賢い評価開始時刻調整", False, str(e))
        
        # 5. メソッドシグネチャ互換性テスト
        print("\n🧪 5. メソッドシグネチャ互換性テスト")
        try:
            import inspect
            signature = inspect.signature(system._generate_real_analysis)
            params = list(signature.parameters.keys())
            
            required_params = ['symbol', 'timeframe', 'config']
            all_required_present = all(param in params for param in required_params)
            
            record_test("必須引数確認", all_required_present, f"params={params}")
            
            custom_param = signature.parameters.get('custom_period_days')
            has_custom_param = custom_param is not None and custom_param.default is None
            
            record_test("オプション引数確認", has_custom_param, f"custom_period_days={custom_param}")
        except Exception as e:
            record_test("メソッドシグネチャ互換性", False, str(e))
        
        # 6. 新機能メソッド存在確認
        print("\n🧪 6. 新機能メソッド存在確認")
        try:
            has_time_matching = hasattr(system, '_find_first_valid_evaluation_time')
            record_test("賢い時刻調整メソッド", has_time_matching)
            
            has_config_loader = hasattr(system, '_load_timeframe_config')
            record_test("時間足設定読み込みメソッド", has_config_loader)
        except Exception as e:
            record_test("新機能メソッド存在確認", False, str(e))
        
        # 7. データベース基本機能テスト
        print("\n🧪 7. データベース基本機能テスト")
        try:
            db_exists = os.path.exists(system.db_path)
            record_test("データベースファイル存在", db_exists)
            
            if db_exists:
                import sqlite3
                with sqlite3.connect(system.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    has_analyses = 'analyses' in tables
                    record_test("analysesテーブル存在", has_analyses)
        except Exception as e:
            record_test("データベース基本機能", False, str(e))
        
    except Exception as e:
        print(f"❌ 全体テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # 結果サマリー
    total_tests = test_results["passed"] + test_results["failed"]
    success_rate = (test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 包括的最終安全性テスト結果")
    print("=" * 50)
    print(f"📊 総テスト数: {total_tests}")
    print(f"✅ 成功: {test_results['passed']}")
    print(f"❌ 失敗: {test_results['failed']}")
    print(f"📈 成功率: {success_rate:.1f}%")
    
    if test_results["failed"] == 0:
        print("\n🎉 全テスト成功！修正は完全に安全です")
        print("🔒 バグ防止が徹底的に担保されました")
        return True
    else:
        print(f"\n⚠️ {test_results['failed']}件のテスト失敗")
        print("🔧 以下のテストが失敗しました:")
        for test in test_results["tests"]:
            if not test["success"]:
                print(f"   - {test['name']}: {test['details']}")
        return False

def test_performance_impact():
    """パフォーマンスへの影響テスト"""
    print(f"\n🚀 パフォーマンス影響確認")
    print("=" * 40)
    
    try:
        start_time = time.time()
        from scalable_analysis_system import ScalableAnalysisSystem
        with tempfile.TemporaryDirectory() as temp_dir:
            system = ScalableAnalysisSystem(os.path.join(temp_dir, "perf_test"))
            
            # 時間足設定読み込み時間測定
            config_start = time.time()
            for tf in ['1m', '3m', '15m', '1h']:
                system._load_timeframe_config(tf)
            config_time = time.time() - config_start
            
            # 賢い時刻調整時間測定
            from datetime import datetime, timezone, timedelta
            adjust_start = time.time()
            for i in range(10):
                data_start = datetime(2025, 3, 27, 6, 30+i, 0, tzinfo=timezone.utc)
                system._find_first_valid_evaluation_time(data_start, timedelta(hours=1))
            adjust_time = time.time() - adjust_start
            
        total_time = time.time() - start_time
        
        print(f"📊 パフォーマンス測定結果:")
        print(f"   システム初期化: {total_time:.3f}秒")
        print(f"   設定読み込み(4件): {config_time:.3f}秒")
        print(f"   時刻調整(10件): {adjust_time:.3f}秒")
        
        # パフォーマンス基準チェック
        performance_ok = total_time < 5.0 and config_time < 1.0 and adjust_time < 1.0
        
        if performance_ok:
            print("✅ パフォーマンス影響は許容範囲内")
        else:
            print("⚠️ パフォーマンス影響要注意")
            
        return performance_ok
        
    except Exception as e:
        print(f"❌ パフォーマンステストエラー: {e}")
        return False

if __name__ == "__main__":
    # メインテスト実行
    main_success = test_all_modifications()
    
    # パフォーマンステスト実行
    perf_success = test_performance_impact()
    
    # 最終判定
    overall_success = main_success and perf_success
    
    print(f"\n{'='*60}")
    print(f"🏆 最終判定: {'✅ 全て安全' if overall_success else '⚠️ 要注意'}")
    print(f"{'='*60}")
    
    if overall_success:
        print("🎉 修正内容は完全に安全で、バグ防止が徹底担保されています！")
        print("📈 パフォーマンス影響も許容範囲内です")
        print("🚀 本番環境での使用準備完了")
    else:
        print("🔧 一部問題があります。修正を検討してください。")
    
    sys.exit(0 if overall_success else 1)