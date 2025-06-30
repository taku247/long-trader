#!/usr/bin/env python3
"""
Discord子プロセス可視化通知システム - 全テスト実行スクリプト

実装したDiscord通知システムの包括的テスト
"""

import sys
import subprocess
from pathlib import Path

def run_test_file(test_file):
    """個別テストファイルを実行"""
    print(f"\n{'='*60}")
    print(f"🧪 実行中: {test_file}")
    print('='*60)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return False

def main():
    """全Discord通知テストの実行"""
    print("🚀 Discord子プロセス可視化通知システム - 全テスト実行")
    print("=" * 70)
    
    # テストファイルリスト
    test_files = [
        "test_discord_child_process_notifications.py",
        "test_discord_integration_with_scalable_system.py", 
        "test_discord_end_to_end.py",
        "test_discord_bug_prevention.py"  # バグ防止テスト追加
    ]
    
    results = {}
    all_passed = True
    
    for test_file in test_files:
        if Path(test_file).exists():
            success = run_test_file(test_file)
            results[test_file] = success
            if not success:
                all_passed = False
        else:
            print(f"⚠️ テストファイルが見つかりません: {test_file}")
            results[test_file] = False
            all_passed = False
    
    # 最終結果サマリー
    print("\n" + "=" * 70)
    print("📊 全テスト結果サマリー")
    print("=" * 70)
    
    for test_file, passed in results.items():
        status = "✅ 成功" if passed else "❌ 失敗"
        print(f"   {status}: {test_file}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 全テスト成功！Discord子プロセス可視化通知システムは完全に実装・検証されました。")
        print("\n📋 実装完了内容:")
        print("   ✅ discord_notifier.py - シンプル1行通知システム")
        print("   ✅ scalable_analysis_system.py - 子プロセス通知統合")
        print("   ✅ 単体テスト - Discord通知機能の基本動作")
        print("   ✅ 統合テスト - scalable_analysis_systemとの連携")
        print("   ✅ エンドツーエンドテスト - 本番環境シミュレーション")
        print("   ✅ バグ防止テスト - 既存分析通知スキップバグの防止")
        print("\n🔄 通知例:")
        print("   🔄 子プロセス開始: SOL Conservative_ML - 1h")
        print("   ✅ 子プロセス完了: SOL Conservative_ML - 1h (180秒)")
        print("   ⏩ 子プロセススキップ: SOL Conservative_ML - 1h (既存分析)")
        print("   ❌ 子プロセス失敗: SOL Conservative_ML - 1h - データ不足エラー")
        print("\n🎯 解決した問題:")
        print("   ✅ ProcessPoolExecutor環境での子プロセス進捗が見えない問題")
        print("   ✅ STEP2-6の詳細ログが親プロセスに反映されない問題")
        print("   ✅ 子プロセスの開始・完了タイミングが不明な問題")
        print("   ✅ 既存分析でDiscord通知がスキップされるバグ")
        return 0
    else:
        print("❌ 一部のテストが失敗しました。実装を確認してください。")
        return 1

if __name__ == '__main__':
    sys.exit(main())