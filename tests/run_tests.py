#!/usr/bin/env python3
"""
テスト実行スクリプト

使用方法:
python tests/run_tests.py                    # 全テスト実行
python tests/run_tests.py --unit             # 単体テストのみ
python tests/run_tests.py --integration      # 統合テストのみ
python tests/run_tests.py --coverage         # カバレッジ付きテスト
python tests/run_tests.py --verbose          # 詳細出力
"""

import sys
import os
import unittest
import argparse
import subprocess
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def discover_tests(test_dir, pattern="test_*.py"):
    """テストを自動発見"""
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern=pattern)
    return suite

def run_unit_tests():
    """単体テスト実行"""
    print("🧪 単体テスト実行中...")
    print("=" * 50)
    
    test_dir = Path(__file__).parent
    suite = discover_tests(test_dir, "test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result

def run_integration_tests():
    """統合テスト実行"""
    print("🔗 統合テスト実行中...")
    print("=" * 50)
    
    # 統合テスト用のスクリプトがあれば実行
    integration_script = Path(__file__).parent / "test_integration.py"
    if integration_script.exists():
        result = subprocess.run([sys.executable, str(integration_script)], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    else:
        print("⚠️  統合テストスクリプトが見つかりません")
        return True

def run_with_coverage():
    """カバレッジ付きテスト実行"""
    print("📊 カバレッジ付きテスト実行中...")
    print("=" * 50)
    
    try:
        import coverage
    except ImportError:
        print("❌ coverageパッケージがインストールされていません")
        print("インストール: pip install coverage")
        return False
    
    # カバレッジ開始
    cov = coverage.Coverage()
    cov.start()
    
    # テスト実行
    result = run_unit_tests()
    
    # カバレッジ停止・レポート生成
    cov.stop()
    cov.save()
    
    print("\n📊 カバレッジレポート:")
    print("-" * 30)
    cov.report()
    
    # HTMLレポート生成
    html_dir = Path(__file__).parent / "coverage_html"
    cov.html_report(directory=str(html_dir))
    print(f"\n📄 詳細レポート: {html_dir}/index.html")
    
    return result.wasSuccessful()

def setup_test_environment():
    """テスト環境セットアップ"""
    print("🔧 テスト環境セットアップ中...")
    
    # テスト用ディレクトリ作成
    test_dirs = [
        Path(__file__).parent / "temp_data",
        Path(__file__).parent / "test_results"
    ]
    
    for test_dir in test_dirs:
        test_dir.mkdir(exist_ok=True)
    
    # テスト用環境変数設定
    os.environ['TESTING'] = 'True'
    os.environ['TEST_MODE'] = 'True'
    
    print("✅ テスト環境セットアップ完了")

def cleanup_test_environment():
    """テスト環境クリーンアップ"""
    print("\n🧹 テスト環境クリーンアップ中...")
    
    # テスト用ファイル削除
    test_files = [
        "test_execution_logs.db",
        "test_analysis.db",
        "test_*.pkl.gz"
    ]
    
    import glob
    for pattern in test_files:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"削除: {file_path}")
            except Exception as e:
                print(f"削除失敗 {file_path}: {e}")
    
    # 環境変数クリア
    test_env_vars = ['TESTING', 'TEST_MODE']
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]
    
    print("✅ クリーンアップ完了")

def generate_test_report(results):
    """テスト結果レポート生成"""
    report_file = Path(__file__).parent / "test_results" / f"test_report_{sys.version_info.major}_{sys.version_info.minor}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("Long Trader テスト実行レポート\n")
        f.write("=" * 50 + "\n")
        f.write(f"実行日時: {__import__('datetime').datetime.now()}\n")
        f.write(f"Python バージョン: {sys.version}\n")
        f.write("\n")
        
        if hasattr(results, 'testsRun'):
            f.write(f"実行テスト数: {results.testsRun}\n")
            f.write(f"失敗: {len(results.failures)}\n")
            f.write(f"エラー: {len(results.errors)}\n")
            f.write(f"成功率: {((results.testsRun - len(results.failures) - len(results.errors)) / results.testsRun * 100):.1f}%\n")
            
            if results.failures:
                f.write("\n失敗したテスト:\n")
                for test, traceback in results.failures:
                    f.write(f"- {test}\n")
                    f.write(f"  {traceback}\n")
            
            if results.errors:
                f.write("\nエラーが発生したテスト:\n")
                for test, traceback in results.errors:
                    f.write(f"- {test}\n")
                    f.write(f"  {traceback}\n")
    
    print(f"📄 テストレポート保存: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='Long Trader テスト実行スクリプト')
    parser.add_argument('--unit', action='store_true', help='単体テストのみ実行')
    parser.add_argument('--integration', action='store_true', help='統合テストのみ実行')
    parser.add_argument('--coverage', action='store_true', help='カバレッジ付きテスト実行')
    parser.add_argument('--verbose', action='store_true', help='詳細出力')
    parser.add_argument('--no-cleanup', action='store_true', help='クリーンアップをスキップ')
    
    args = parser.parse_args()
    
    print("🚀 Long Trader テストスイート")
    print("=" * 60)
    
    # テスト環境セットアップ
    setup_test_environment()
    
    success = True
    results = None
    
    try:
        if args.coverage:
            success = run_with_coverage()
        elif args.unit:
            results = run_unit_tests()
            success = results.wasSuccessful()
        elif args.integration:
            success = run_integration_tests()
        else:
            # 全テスト実行
            print("📋 全テスト実行モード")
            results = run_unit_tests()
            unit_success = results.wasSuccessful()
            
            integration_success = run_integration_tests()
            
            success = unit_success and integration_success
        
        # テスト結果サマリー
        print("\n" + "=" * 60)
        print("📊 テスト実行結果")
        print("=" * 60)
        
        if results:
            print(f"実行テスト数: {results.testsRun}")
            print(f"失敗: {len(results.failures)}")
            print(f"エラー: {len(results.errors)}")
            success_rate = ((results.testsRun - len(results.failures) - len(results.errors)) / results.testsRun * 100) if results.testsRun > 0 else 0
            print(f"成功率: {success_rate:.1f}%")
            
            generate_test_report(results)
        
        if success:
            print("\n✅ 全テストが成功しました！")
            exit_code = 0
        else:
            print("\n❌ 一部テストが失敗しました")
            exit_code = 1
        
        # 推奨事項
        print("\n💡 次のステップ:")
        if not success:
            print("1. 失敗したテストを確認し修正")
            print("2. 詳細ログを確認 (--verbose オプション)")
        print("3. カバレッジレポートを確認 (--coverage オプション)")
        print("4. 新機能追加時はテストも追加")
        
    finally:
        # クリーンアップ
        if not args.no_cleanup:
            cleanup_test_environment()
    
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)