#!/usr/bin/env python3
"""
全ての検証テスト実行スクリプト

158.70のようなサポート強度異常値バグや、
信頼度90%のような異常値を包括的に検知するテストスイートを実行。
"""

import sys
import subprocess
from pathlib import Path

def run_test_file(test_file):
    """個別テストファイルを実行"""
    print(f"\n{'='*60}")
    print(f"🧪 実行中: {test_file}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=120)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return result.returncode == 0
    
    except subprocess.TimeoutExpired:
        print(f"❌ タイムアウト: {test_file} が120秒以内に完了しませんでした")
        return False
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        return False

def main():
    """全ての検証テストを実行"""
    print("🔧 Long Trader システム検証テスト開始")
    print("=" * 60)
    print("🎯 検証対象:")
    print("  - サポート強度範囲バグ（158.70バグ）")
    print("  - 信頼度異常値（90%超バグ）")
    print("  - NameError回帰防止")
    print("  - データ型範囲検証")
    print("=" * 60)
    
    # テストファイルリスト
    test_files = [
        "tests/test_support_strength_validation.py",
        "tests/test_data_range_validation.py", 
        "tests/test_confidence_anomaly_detection.py",
        "tests/test_nameerror_prevention.py",
        "tests/test_leverage_engine_robustness.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        test_path = Path(test_file)
        if test_path.exists():
            success = run_test_file(str(test_path))
            results[test_file] = success
        else:
            print(f"⚠️ テストファイルが見つかりません: {test_file}")
            results[test_file] = False
    
    # 結果サマリー
    print("\n" + "="*60)
    print("📋 全体テスト結果サマリー")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests
    
    for test_file, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"  {status}: {test_file}")
    
    print(f"\n📊 統計:")
    print(f"  総テストファイル数: {total_tests}")
    print(f"  成功: {passed_tests}")
    print(f"  失敗: {failed_tests}")
    print(f"  成功率: {passed_tests/total_tests*100:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 全ての検証テストに合格しました！")
        print("✅ 158.70バグの再発防止が確認されました")
        print("✅ 信頼度異常値の検知が動作しています")
        print("✅ NameErrorバグの回帰防止が機能しています")
        print("✅ システム全体のデータ範囲が適正です")
        
        print("\n🛡️ システムの健全性:")
        print("  - サポート強度: 0.0-1.0範囲内で正常動作")
        print("  - 信頼度計算: 異常な高値（90%超）を防止")
        print("  - レバレッジ判定: 市場条件に基づく適切な値")
        print("  - エラーハンドリング: 堅牢な例外処理")
        
        return True
    else:
        print(f"\n⚠️ {failed_tests}個のテストが失敗しました")
        print("システムにバグが存在する可能性があります。")
        print("失敗したテストを個別に確認してください。")
        
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)