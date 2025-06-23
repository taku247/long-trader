#!/usr/bin/env python3
"""
戦略カスタマイズ機能 - 全テスト実行スクリプト

戦略カスタマイズ機能の全テストケースを順序実行する統合テストランナー
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

def main():
    """全戦略カスタマイズテストの実行"""
    print("🚀 戦略カスタマイズ機能 - 全テスト実行開始")
    print("=" * 80)
    print(f"開始時刻: {datetime.now()}")
    print()
    
    # テスト実行順序の定義
    test_modules = [
        {
            'name': '戦略設定テーブル基本機能',
            'module': 'test_strategy_configurations',
            'description': 'strategy_configurations テーブルのCRUD操作とバリデーション'
        },
        {
            'name': 'パラメータバリデーション',
            'module': 'test_parameter_validation',
            'description': '戦略パラメータの妥当性検証機能'
        },
        {
            'name': '選択的実行機能',
            'module': 'test_selective_execution',
            'description': '指定戦略・時間足のみでの実行機能'
        },
        {
            'name': '統合テスト',
            'module': 'test_integration',
            'description': 'エンドツーエンドの戦略カスタマイズワークフロー'
        }
    ]
    
    # 結果記録
    test_results = []
    total_start_time = time.time()
    
    for i, test_info in enumerate(test_modules, 1):
        print(f"📋 テスト {i}/{len(test_modules)}: {test_info['name']}")
        print(f"   説明: {test_info['description']}")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            # テストモジュールの動的インポートと実行
            module_name = test_info['module']
            
            if module_name == 'test_strategy_configurations':
                from test_strategy_configurations import run_strategy_configuration_tests
                success = run_strategy_configuration_tests()
                
            elif module_name == 'test_parameter_validation':
                from test_parameter_validation import run_parameter_validation_tests
                success = run_parameter_validation_tests()
                
            elif module_name == 'test_selective_execution':
                from test_selective_execution import run_selective_execution_tests
                success = run_selective_execution_tests()
                
            elif module_name == 'test_integration':
                from test_integration import run_integration_tests
                success = run_integration_tests()
                
            else:
                print(f"❌ 未知のテストモジュール: {module_name}")
                success = False
            
        except ImportError as e:
            print(f"❌ テストモジュールのインポートエラー: {e}")
            success = False
        except Exception as e:
            print(f"❌ テスト実行エラー: {e}")
            success = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 結果記録
        test_results.append({
            'name': test_info['name'],
            'module': module_name,
            'success': success,
            'duration': duration
        })
        
        # 結果表示
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"\n{status} - {test_info['name']} ({duration:.2f}秒)")
        print()
        
        # 失敗時の処理
        if not success:
            print("⚠️ テストが失敗しました。続行しますか？")
            if '--continue-on-failure' not in sys.argv:
                user_input = input("続行する場合は 'y' を入力してください [y/N]: ")
                if user_input.lower() not in ['y', 'yes']:
                    print("テスト実行を中断しました。")
                    break
            else:
                print("--continue-on-failure オプションにより続行します。")
    
    # 全体結果サマリー
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    print("=" * 80)
    print("🎯 戦略カスタマイズ機能テスト - 全体結果サマリー")
    print("=" * 80)
    print(f"総実行時間: {total_duration:.2f}秒")
    print(f"実行テスト数: {len(test_results)}")
    
    successful_tests = [r for r in test_results if r['success']]
    failed_tests = [r for r in test_results if not r['success']]
    
    print(f"成功: {len(successful_tests)}")
    print(f"失敗: {len(failed_tests)}")
    
    # 詳細結果表示
    if successful_tests:
        print(f"\n✅ 成功したテスト:")
        for result in successful_tests:
            print(f"   - {result['name']} ({result['duration']:.2f}秒)")
    
    if failed_tests:
        print(f"\n❌ 失敗したテスト:")
        for result in failed_tests:
            print(f"   - {result['name']} ({result['duration']:.2f}秒)")
    
    # 全体成功判定
    overall_success = len(failed_tests) == 0
    
    if overall_success:
        print(f"\n🎉 全テスト成功!")
        print("戦略カスタマイズ機能の実装準備が完了しました。")
        print("\n📋 次のステップ:")
        print("1. データベーススキーマの実装")
        print("2. 戦略管理API の実装")
        print("3. Web UI での戦略カスタマイズ画面")
        print("4. 銘柄追加時の選択的実行機能")
        
    else:
        print(f"\n⚠️ 一部テストが失敗しました。")
        print("失敗したテストを確認して、問題を解決してください。")
    
    print(f"\n終了時刻: {datetime.now()}")
    
    return overall_success

def show_help():
    """ヘルプ表示"""
    print("戦略カスタマイズ機能テストランナー")
    print()
    print("使用方法:")
    print("  python run_all_strategy_tests.py [オプション]")
    print()
    print("オプション:")
    print("  --continue-on-failure    テスト失敗時も続行する")
    print("  --help                   このヘルプを表示")
    print()
    print("テスト内容:")
    print("1. 戦略設定テーブル基本機能")
    print("   - strategy_configurations テーブルのCRUD操作")
    print("   - 戦略設定の作成・更新・削除・クエリ")
    print()
    print("2. パラメータバリデーション")
    print("   - 戦略パラメータの型チェック")
    print("   - 値の範囲検証")
    print("   - 必須パラメータの確認")
    print()
    print("3. 選択的実行機能")
    print("   - 指定戦略・時間足のみでの実行")
    print("   - 処理時間短縮効果の確認")
    print("   - 既存データとの互換性")
    print()
    print("4. 統合テスト")
    print("   - エンドツーエンドワークフロー")
    print("   - 戦略比較機能")
    print("   - アラートトレーサビリティ")

if __name__ == "__main__":
    if '--help' in sys.argv:
        show_help()
        sys.exit(0)
    
    success = main()
    sys.exit(0 if success else 1)