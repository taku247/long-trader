#!/usr/bin/env python3
"""
統一テストランナー
- カテゴリ別テスト実行
- 本番DB保護確認
- 詳細レポート生成
- パフォーマンス測定
"""
import os
import sys
import unittest
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
import sqlite3

class SafeTestRunner:
    """
    安全なテスト実行環境を提供するランナー
    
    機能:
    - 本番DB保護の事前確認
    - カテゴリ別テスト実行
    - 詳細なレポート生成
    - パフォーマンス測定
    - テスト失敗時の詳細分析
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.test_results = {}
        self.start_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
    def verify_production_db_safety(self) -> bool:
        """本番DB保護の事前確認"""
        print("🔒 本番DB保護確認...")
        
        # 本番DBパスのリスト
        production_dbs = [
            os.path.join(os.getcwd(), "execution_logs.db"),
            os.path.join(os.getcwd(), "large_scale_analysis", "analysis.db"),
            os.path.expanduser("~/execution_logs.db")
        ]
        
        safety_issues = []
        
        for db_path in production_dbs:
            if os.path.exists(db_path):
                # 最近のアクセス時間をチェック
                stat = os.stat(db_path)
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                
                # 5分以内に変更されていたら警告
                time_diff = (datetime.now() - last_modified).total_seconds()
                if time_diff < 300:  # 5分
                    safety_issues.append(f"⚠️ {db_path} が最近変更されています ({time_diff:.0f}秒前)")
        
        if safety_issues:
            print("🚨 本番DB安全性の懸念:")
            for issue in safety_issues:
                print(f"  {issue}")
            
            response = input("続行しますか？ (y/N): ")
            return response.lower() == 'y'
        
        print("✅ 本番DB保護確認完了")
        return True
    
    def discover_test_categories(self) -> Dict[str, List[str]]:
        """テストカテゴリの自動発見"""
        categories = {}
        tests_dir = Path(self.base_dir)
        
        # カテゴリディレクトリをスキャン
        for category_dir in tests_dir.iterdir():
            if category_dir.is_dir() and category_dir.name != '__pycache__':
                test_files = []
                for test_file in category_dir.glob("test_*.py"):
                    test_files.append(str(test_file))
                
                if test_files:
                    categories[category_dir.name] = test_files
        
        # ルートディレクトリの単体テストファイル
        root_tests = list(tests_dir.glob("test_*.py"))
        if root_tests:
            categories["root"] = [str(f) for f in root_tests]
        
        return categories
    
    def run_category_tests(self, category: str, test_files: List[str], 
                          verbose: bool = True) -> Dict:
        """カテゴリ別テスト実行"""
        print(f"\n📂 カテゴリ: {category} ({len(test_files)}ファイル)")
        
        category_results = {
            "category": category,
            "total_files": len(test_files),
            "passed_files": 0,
            "failed_files": 0,
            "tests": [],
            "start_time": datetime.now(timezone.utc).isoformat(),
            "duration": 0
        }
        
        category_start = time.time()
        
        for test_file in test_files:
            print(f"  🧪 {os.path.basename(test_file)}...", end="")
            
            file_start = time.time()
            result = self.run_single_test_file(test_file, verbose=verbose)
            file_duration = time.time() - file_start
            
            result["duration"] = file_duration
            category_results["tests"].append(result)
            
            if result["success"]:
                category_results["passed_files"] += 1
                print(f" ✅ ({file_duration:.2f}s)")
            else:
                category_results["failed_files"] += 1
                print(f" ❌ ({file_duration:.2f}s)")
                if verbose and result.get("error"):
                    print(f"    Error: {result['error']}")
        
        category_results["duration"] = time.time() - category_start
        return category_results
    
    def run_single_test_file(self, test_file: str, verbose: bool = False) -> Dict:
        """単一テストファイルの実行"""
        result = {
            "file": os.path.basename(test_file),
            "path": test_file,
            "success": False,
            "tests_run": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "error": None
        }
        
        try:
            # テストスイートをロード
            loader = unittest.TestLoader()
            
            # テストファイルをモジュールとしてロード
            spec = importlib.util.spec_from_file_location("test_module", test_file)
            test_module = importlib.util.module_from_spec(spec)
            sys.modules["test_module"] = test_module
            spec.loader.exec_module(test_module)
            
            # テストスイートを作成
            suite = loader.loadTestsFromModule(test_module)
            
            # テスト実行
            runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'), verbosity=0)
            test_result = runner.run(suite)
            
            # 結果を記録
            result.update({
                "success": test_result.wasSuccessful(),
                "tests_run": test_result.testsRun,
                "failures": len(test_result.failures),
                "errors": len(test_result.errors),
                "skipped": len(test_result.skipped)
            })
            
            # エラー詳細
            if test_result.failures or test_result.errors:
                error_details = []
                for failure in test_result.failures:
                    error_details.append(f"FAIL: {failure[0]} - {failure[1]}")
                for error in test_result.errors:
                    error_details.append(f"ERROR: {error[0]} - {error[1]}")
                result["error"] = "\\n".join(error_details)
            
            # 統計更新
            self.total_tests += result["tests_run"]
            if result["success"]:
                self.passed_tests += result["tests_run"]
            else:
                self.failed_tests += result["failures"] + result["errors"]
            self.skipped_tests += result["skipped"]
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def run_all_tests(self, categories: List[str] = None, verbose: bool = True) -> Dict:
        """全テストの実行"""
        if not self.verify_production_db_safety():
            print("🛑 安全性確認が失敗したため、テストを中止します")
            return {"error": "Safety check failed"}
        
        print("🚀 統一テストランナー開始")
        print(f"📍 ベースディレクトリ: {self.base_dir}")
        
        self.start_time = time.time()
        
        # テストカテゴリを発見
        all_categories = self.discover_test_categories()
        
        if categories:
            # 指定されたカテゴリのみ実行
            selected_categories = {k: v for k, v in all_categories.items() if k in categories}
        else:
            # 全カテゴリ実行
            selected_categories = all_categories
        
        print(f"📊 実行対象カテゴリ: {list(selected_categories.keys())}")
        
        # カテゴリ別実行
        category_results = []
        for category, test_files in selected_categories.items():
            result = self.run_category_tests(category, test_files, verbose)
            category_results.append(result)
        
        # 総合結果
        total_duration = time.time() - self.start_time
        
        overall_results = {
            "summary": {
                "total_categories": len(category_results),
                "total_test_files": sum(r["total_files"] for r in category_results),
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "skipped_tests": self.skipped_tests,
                "success_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0,
                "duration": total_duration,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "categories": category_results
        }
        
        self.generate_report(overall_results)
        return overall_results
    
    def generate_report(self, results: Dict):
        """詳細レポートの生成"""
        summary = results["summary"]
        
        print(f"\n{'='*60}")
        print(f"🎯 テスト実行結果サマリー")
        print(f"{'='*60}")
        print(f"📊 実行統計:")
        print(f"  カテゴリ数: {summary['total_categories']}")
        print(f"  テストファイル数: {summary['total_test_files']}")
        print(f"  総テスト数: {summary['total_tests']}")
        print(f"  成功: {summary['passed_tests']} ✅")
        print(f"  失敗: {summary['failed_tests']} ❌")
        print(f"  スキップ: {summary['skipped_tests']} ⏭️")
        print(f"  成功率: {summary['success_rate']:.1f}%")
        print(f"  実行時間: {summary['duration']:.2f}秒")
        
        # カテゴリ別詳細
        print(f"\n📂 カテゴリ別結果:")
        for category_result in results["categories"]:
            status = "✅" if category_result["failed_files"] == 0 else "❌"
            print(f"  {status} {category_result['category']}: "
                  f"{category_result['passed_files']}/{category_result['total_files']} "
                  f"({category_result['duration']:.2f}s)")
        
        # 失敗したテストの詳細
        failed_tests = []
        for category_result in results["categories"]:
            for test_result in category_result["tests"]:
                if not test_result["success"]:
                    failed_tests.append(test_result)
        
        if failed_tests:
            print(f"\n❌ 失敗したテスト詳細:")
            for failed_test in failed_tests:
                print(f"  📁 {failed_test['file']}")
                if failed_test.get("error"):
                    print(f"    エラー: {failed_test['error'][:200]}...")
        
        # JSONレポート保存
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 詳細レポート保存: {report_file}")


# インポート用のユーティリティ
import importlib.util

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="統一テストランナー")
    parser.add_argument("--categories", nargs='+', help="実行するカテゴリを指定")
    parser.add_argument("--verbose", action='store_true', help="詳細出力")
    parser.add_argument("--quick", action='store_true', help="高速モード（エラー詳細なし）")
    
    args = parser.parse_args()
    
    runner = SafeTestRunner()
    results = runner.run_all_tests(
        categories=args.categories,
        verbose=args.verbose and not args.quick
    )
    
    # 終了コード設定
    if results.get("error"):
        sys.exit(1)
    
    success_rate = results["summary"]["success_rate"]
    if success_rate < 100:
        print(f"\n⚠️  一部テストが失敗しました (成功率: {success_rate:.1f}%)")
        sys.exit(1)
    else:
        print(f"\n🎉 すべてのテストが成功しました！")
        sys.exit(0)


if __name__ == "__main__":
    main()