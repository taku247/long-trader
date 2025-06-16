#!/usr/bin/env python3
"""
今回のバグ・実装漏れ防止テストスイート マスター実行プログラム

今回実装した全てのテストを統合実行:
1. 包括的バグ防止テスト
2. Level 1厳格バリデーション専用テスト
3. 支持線・抵抗線検出システム専用テスト
4. アダプターパターン互換性専用テスト
5. データ異常検知専用テスト
6. 統合テスト
7. 総合評価とレポート生成
"""

import unittest
import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Any
import argparse

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 個別テストスイートのインポート
from test_comprehensive_bug_prevention import run_comprehensive_tests
from test_level1_strict_validation import run_level1_validation_tests
from test_support_resistance_detection import run_support_resistance_detection_tests
from test_adapter_pattern_compatibility import run_adapter_pattern_tests
from test_data_anomaly_detection import run_data_anomaly_detection_tests


class TestSuiteManager:
    """テストスイート管理クラス"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
        self.total_duration = 0
        
    def run_all_tests(self, verbose: bool = True, fast_mode: bool = False) -> Dict[str, Any]:
        """全テストスイートの実行"""
        self.start_time = time.time()
        
        print("🧪 今回のバグ・実装漏れ防止テストスイート マスター実行")
        print("=" * 100)
        print(f"実行開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"モード: {'高速モード' if fast_mode else '完全モード'}")
        print("=" * 100)
        
        # テストスイート定義
        test_suites = [
            {
                'name': '包括的バグ防止テスト',
                'function': run_comprehensive_tests,
                'priority': 'critical',
                'description': '今回のバグ・実装漏れの包括的防止確認'
            },
            {
                'name': 'Level 1厳格バリデーション',
                'function': run_level1_validation_tests,
                'priority': 'critical',
                'description': '空配列検出時の完全失敗機能確認'
            },
            {
                'name': '支持線・抵抗線検出システム',
                'function': run_support_resistance_detection_tests,
                'priority': 'high',
                'description': '実際のデータ検出機能確認'
            },
            {
                'name': 'アダプターパターン互換性',
                'function': run_adapter_pattern_tests,
                'priority': 'high',
                'description': 'プロバイダー差し替えアーキテクチャ確認'
            },
            {
                'name': 'データ異常検知',
                'function': run_data_anomaly_detection_tests,
                'priority': 'critical',
                'description': '非現実的データの自動検知確認'
            }
        ]
        
        # 高速モードでは重要度の高いテストのみ実行
        if fast_mode:
            test_suites = [suite for suite in test_suites if suite['priority'] == 'critical']
            print("🚀 高速モード: 重要度 'critical' のテストのみ実行")
            print()
        
        # 各テストスイートの実行
        for i, suite in enumerate(test_suites, 1):
            print(f"\n📋 [{i}/{len(test_suites)}] {suite['name']} 実行中...")
            print(f"説明: {suite['description']}")
            print("-" * 80)
            
            suite_start_time = time.time()
            
            try:
                success = suite['function']()
                suite_end_time = time.time()
                suite_duration = suite_end_time - suite_start_time
                
                self.results[suite['name']] = {
                    'success': success,
                    'duration': suite_duration,
                    'priority': suite['priority'],
                    'description': suite['description'],
                    'status': '✅ 成功' if success else '❌ 失敗'
                }
                
                print(f"\n⏱️ {suite['name']} 完了: {suite_duration:.2f}秒")
                
            except Exception as e:
                suite_end_time = time.time()
                suite_duration = suite_end_time - suite_start_time
                
                self.results[suite['name']] = {
                    'success': False,
                    'duration': suite_duration,
                    'priority': suite['priority'],
                    'description': suite['description'],
                    'status': f'💥 エラー: {str(e)}',
                    'error': str(e)
                }
                
                print(f"\n💥 {suite['name']} エラー: {str(e)}")
                
            print("=" * 80)
        
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time
        
        return self._generate_final_report()
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """最終レポートの生成"""
        total_suites = len(self.results)
        successful_suites = sum(1 for result in self.results.values() if result['success'])
        failed_suites = total_suites - successful_suites
        
        success_rate = (successful_suites / total_suites * 100) if total_suites > 0 else 0
        
        # 重要度別の結果
        critical_results = [result for result in self.results.values() if result['priority'] == 'critical']
        critical_success_count = sum(1 for result in critical_results if result['success'])
        critical_success_rate = (critical_success_count / len(critical_results) * 100) if critical_results else 100
        
        report = {
            'summary': {
                'total_suites': total_suites,
                'successful_suites': successful_suites,
                'failed_suites': failed_suites,
                'success_rate': success_rate,
                'critical_success_rate': critical_success_rate,
                'total_duration': self.total_duration,
                'execution_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'detailed_results': self.results,
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """推奨事項の生成"""
        recommendations = []
        
        # 失敗したテストスイートの分析
        failed_critical = [name for name, result in self.results.items() 
                          if not result['success'] and result['priority'] == 'critical']
        
        if failed_critical:
            recommendations.append(
                f"🚨 重要: 以下の重要テストが失敗しています: {', '.join(failed_critical)}"
            )
            recommendations.append("即座に修正が必要です。")
        
        failed_high = [name for name, result in self.results.items() 
                      if not result['success'] and result['priority'] == 'high']
        
        if failed_high:
            recommendations.append(
                f"⚠️ 高優先度: 以下のテストが失敗しています: {', '.join(failed_high)}"
            )
            recommendations.append("次のリリース前に修正を検討してください。")
        
        # 成功時の推奨事項
        success_rate = self.summary['success_rate'] if hasattr(self, 'summary') else 0
        if success_rate == 100:
            recommendations.append("✅ 全テストが成功! 実装品質が高く保たれています。")
            recommendations.append("定期的にこのテストスイートを実行して品質を維持してください。")
        elif success_rate >= 80:
            recommendations.append("👍 テストの大部分が成功しています。")
            recommendations.append("失敗したテストの修正を優先してください。")
        else:
            recommendations.append("⚠️ テスト成功率が低いです。")
            recommendations.append("実装の見直しが必要かもしれません。")
        
        # パフォーマンス推奨事項
        if self.total_duration > 300:  # 5分超
            recommendations.append("⏱️ テスト実行時間が長いです。高速モードの使用を検討してください。")
        
        return recommendations
    
    def print_final_report(self, report: Dict[str, Any]):
        """最終レポートの表示"""
        print("\n" + "🏁 最終テスト結果レポート" + "=" * 70)
        print(f"実行時刻: {report['summary']['execution_time']}")
        print(f"総実行時間: {report['summary']['total_duration']:.2f}秒")
        print("=" * 100)
        
        # サマリー
        summary = report['summary']
        print("📊 テストサマリー")
        print("-" * 50)
        print(f"総テストスイート数: {summary['total_suites']}")
        print(f"成功: {summary['successful_suites']}")
        print(f"失敗: {summary['failed_suites']}")
        print(f"成功率: {summary['success_rate']:.1f}%")
        print(f"重要テスト成功率: {summary['critical_success_rate']:.1f}%")
        
        # 詳細結果
        print("\n📋 詳細結果")
        print("-" * 50)
        for name, result in report['detailed_results'].items():
            duration_str = f"{result['duration']:.2f}s"
            priority_icon = "🔥" if result['priority'] == 'critical' else "⚡" if result['priority'] == 'high' else "📝"
            print(f"{priority_icon} {result['status']} {name} ({duration_str})")
            if 'error' in result:
                print(f"    エラー詳細: {result['error']}")
        
        # 推奨事項
        print("\n💡 推奨事項")
        print("-" * 50)
        for i, recommendation in enumerate(report['recommendations'], 1):
            print(f"{i}. {recommendation}")
        
        # 総合判定
        print("\n🎯 総合判定")
        print("-" * 50)
        if summary['critical_success_rate'] == 100:
            if summary['success_rate'] == 100:
                print("🏆 完璧! 全テストが成功しています。")
                print("システムの品質が非常に高く保たれています。")
            else:
                print("✅ 良好! 重要なテストは全て成功しています。")
                print("残りのテストの修正を進めてください。")
        else:
            print("⚠️ 注意! 重要なテストに失敗があります。")
            print("システムの根幹部分に問題がある可能性があります。")
        
        print("=" * 100)
    
    def save_report_to_file(self, report: Dict[str, Any], filename: str = None):
        """レポートをファイルに保存"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"test_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 テストレポートを保存しました: {filename}")
            
        except Exception as e:
            print(f"\n❌ レポート保存に失敗: {str(e)}")


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description='今回のバグ・実装漏れ防止テストスイート',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python test_master_suite.py                    # 全テスト実行
  python test_master_suite.py --fast            # 重要テストのみ実行
  python test_master_suite.py --save-report     # レポート保存
  python test_master_suite.py --fast --save-report --quiet  # 高速・保存・簡潔モード
        """
    )
    
    parser.add_argument('--fast', action='store_true', 
                       help='高速モード（重要テストのみ実行）')
    parser.add_argument('--save-report', action='store_true',
                       help='テストレポートをJSONファイルに保存')
    parser.add_argument('--quiet', action='store_true',
                       help='簡潔な出力モード')
    parser.add_argument('--output', type=str,
                       help='レポート保存ファイル名')
    
    args = parser.parse_args()
    
    # テストスイート管理インスタンス
    manager = TestSuiteManager()
    
    try:
        # 全テスト実行
        report = manager.run_all_tests(
            verbose=not args.quiet,
            fast_mode=args.fast
        )
        
        # レポート表示
        if not args.quiet:
            manager.print_final_report(report)
        else:
            # 簡潔モードでは結果のみ表示
            summary = report['summary']
            print(f"テスト結果: {summary['successful_suites']}/{summary['total_suites']} 成功 "
                  f"({summary['success_rate']:.1f}%) - {summary['total_duration']:.1f}秒")
        
        # レポート保存
        if args.save_report:
            manager.save_report_to_file(report, args.output)
        
        # 終了コード決定
        critical_success_rate = report['summary']['critical_success_rate']
        if critical_success_rate == 100:
            exit_code = 0  # 重要テストが全て成功
        else:
            exit_code = 1  # 重要テストに失敗がある
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n⚠️ テスト実行が中断されました")
        sys.exit(2)
    except Exception as e:
        print(f"\n💥 予期しないエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()