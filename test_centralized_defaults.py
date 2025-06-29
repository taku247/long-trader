#!/usr/bin/env python3
"""
一元管理システム統合テスト実行スクリプト

全ての一元管理関連テストを実行し、システムの健全性を確認します。
"""

import unittest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

def run_centralized_defaults_tests():
    """一元管理システムの全テストを実行"""
    
    print("=" * 80)
    print("🎯 一元管理システム統合テスト開始")
    print("=" * 80)
    
    # テストスイート作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストモジュールを追加
    test_modules = [
        'tests_organized.config.test_defaults_manager',
        'tests_organized.config.test_centralized_defaults_integrity',
        'tests_organized.ui.test_web_ui_defaults'
    ]
    
    for module_name in test_modules:
        try:
            print(f"\n📁 テストモジュール読み込み: {module_name}")
            module_suite = loader.loadTestsFromName(module_name)
            suite.addTest(module_suite)
            print(f"✅ {module_name} 読み込み成功")
        except Exception as e:
            print(f"❌ {module_name} 読み込み失敗: {e}")
    
    # テスト実行
    print("\n" + "=" * 80)
    print("🚀 テスト実行開始")
    print("=" * 80)
    
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    
    success_rate = ((total_tests - failures - errors) / total_tests * 100) if total_tests > 0 else 0
    
    print(f"📈 実行テスト数: {total_tests}")
    print(f"✅ 成功: {total_tests - failures - errors}")
    print(f"❌ 失敗: {failures}")
    print(f"🚨 エラー: {errors}")
    print(f"⏭️ スキップ: {skipped}")
    print(f"🎯 成功率: {success_rate:.1f}%")
    
    # 失敗・エラーの詳細表示
    if failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors:
        print("\n🚨 エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # 推奨事項
    print("\n" + "=" * 80)
    print("💡 推奨事項")
    print("=" * 80)
    
    if success_rate >= 90:
        print("🎉 一元管理システムは正常に動作しています！")
        print("✅ デフォルト値の変更は config/defaults.json で行ってください")
    elif success_rate >= 70:
        print("⚠️ 一部のテストが失敗していますが、基本機能は動作しています")
        print("🔧 失敗したテストを確認して修正することをお勧めします")
    else:
        print("🚨 重大な問題が検出されました")
        print("🔥 一元管理システムが正しく動作していない可能性があります")
        print("🛠️ 緊急修正が必要です")
    
    print("\n📋 テスト対象項目:")
    print("  1. デフォルト値管理システムの動作")
    print("  2. 'use_default'マーカーの動的解決")
    print("  3. ハードコードされた値の除去確認")
    print("  4. 全システム間の一貫性")
    print("  5. WebUIでのデフォルト値表示")
    print("  6. 後方互換性の保証")
    
    return result.wasSuccessful()


def run_quick_integrity_check():
    """クイック整合性チェック（CIや開発中の確認用）"""
    
    print("🔍 クイック整合性チェック実行")
    print("-" * 40)
    
    issues = []
    
    # 1. defaults.json存在確認
    try:
        from config.defaults_manager import DefaultsManager
        manager = DefaultsManager()
        rr_value = manager.get_min_risk_reward()
        print(f"✅ defaults.json読み込み成功: min_risk_reward = {rr_value}")
    except Exception as e:
        issues.append(f"defaults.json問題: {e}")
        print(f"❌ defaults.json問題: {e}")
    
    # 2. 時間足設定統合確認
    try:
        from config.timeframe_config_manager import TimeframeConfigManager
        tf_manager = TimeframeConfigManager()
        config = tf_manager.get_timeframe_config('15m')
        rr_from_tf = config.get('min_risk_reward')
        print(f"✅ 時間足設定統合成功: 15m min_risk_reward = {rr_from_tf}")
    except Exception as e:
        issues.append(f"時間足設定問題: {e}")
        print(f"❌ 時間足設定問題: {e}")
    
    # 3. ハードコード値チェック（簡易）
    import json
    config_files = [
        "config/timeframe_conditions.json",
        "config/trading_conditions.json"
    ]
    
    hardcoded_found = False
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                content = f.read()
                if '"min_risk_reward": 1.2' in content:
                    hardcoded_found = True
                    issues.append(f"{config_file}にハードコード値1.2が残存")
                    print(f"❌ {config_file}: ハードコード値検出")
        except Exception:
            pass
    
    if not hardcoded_found:
        print("✅ ハードコード値チェック: 問題なし")
    
    # 結果
    if not issues:
        print("\n🎉 クイックチェック完全成功！")
        return True
    else:
        print(f"\n⚠️ {len(issues)}個の問題を検出:")
        for issue in issues:
            print(f"  - {issue}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='一元管理システムテスト実行')
    parser.add_argument('--quick', action='store_true', 
                       help='クイック整合性チェックのみ実行')
    parser.add_argument('--full', action='store_true', 
                       help='全テストを実行（デフォルト）')
    
    args = parser.parse_args()
    
    if args.quick:
        success = run_quick_integrity_check()
    else:
        success = run_centralized_defaults_tests()
    
    # 終了コード設定
    sys.exit(0 if success else 1)