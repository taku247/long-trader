#!/usr/bin/env python3
"""
DB競合仮説検証の統合実行スクリプト
3つのデバッグツールを順次実行して総合分析
"""

import subprocess
import time
import os
import sys
from datetime import datetime

def run_debug_tool(script_name, description):
    """デバッグツールを実行"""
    print(f"\n{'='*70}")
    print(f"🔍 {description}")
    print(f"実行スクリプト: {script_name}")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*70)
    
    start_time = time.time()
    
    try:
        # Pythonスクリプトを実行
        result = subprocess.run([
            sys.executable, script_name
        ], capture_output=True, text=True, timeout=300)  # 5分タイムアウト
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n📊 実行結果:")
        print(f"実行時間: {execution_time:.1f}秒")
        print(f"終了コード: {result.returncode}")
        
        # 標準出力
        if result.stdout:
            print(f"\n📋 標準出力:")
            print(result.stdout)
        
        # エラー出力
        if result.stderr:
            print(f"\n❌ エラー出力:")
            print(result.stderr)
        
        return result.returncode == 0, execution_time
        
    except subprocess.TimeoutExpired:
        print(f"\n⏰ タイムアウト: {script_name} (5分)")
        return False, 300
        
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"\n❌ 実行エラー: {e}")
        return False, execution_time

def main():
    """統合デバッグテスト実行"""
    
    print("🚀 DB競合仮説検証 - 統合デバッグテスト")
    print("="*70)
    print("目的: 5秒完了の真の原因を特定")
    print("検証仮説: SQLite並行処理制限による早期終了")
    print("="*70)
    
    # デバッグツールリスト
    debug_tools = [
        {
            'script': 'debug_sqlite_monitor.py',
            'description': 'SQLite詳細監視 - ロック競合・トランザクション分析'
        },
        {
            'script': 'debug_db_competition.py', 
            'description': 'DB競合検証 - 並行更新テスト・実行監視'
        },
        {
            'script': 'debug_process_timing.py',
            'description': 'プロセス詳細計測 - 実行時間・ボトルネック分析'
        }
    ]
    
    # 実行結果記録
    results = []
    total_start = time.time()
    
    for i, tool in enumerate(debug_tools, 1):
        print(f"\n🎯 テスト {i}/{len(debug_tools)}: {tool['description']}")
        
        # スクリプト存在確認
        if not os.path.exists(tool['script']):
            print(f"❌ スクリプトが見つかりません: {tool['script']}")
            results.append({
                'tool': tool['script'],
                'success': False,
                'execution_time': 0,
                'error': 'スクリプト不存在'
            })
            continue
        
        # 実行
        success, exec_time = run_debug_tool(tool['script'], tool['description'])
        
        results.append({
            'tool': tool['script'],
            'success': success,
            'execution_time': exec_time,
            'description': tool['description']
        })
        
        # 次のテストまで少し待機
        if i < len(debug_tools):
            print(f"\n⏳ 次のテストまで3秒待機...")
            time.sleep(3)
    
    total_end = time.time()
    total_time = total_end - total_start
    
    # 総合結果レポート
    print(f"\n{'='*70}")
    print("📊 統合デバッグテスト - 総合結果レポート")
    print('='*70)
    
    print(f"\n⏱️ 実行サマリー:")
    print(f"総実行時間: {total_time:.1f}秒")
    print(f"実行ツール数: {len(debug_tools)}個")
    
    successful_tests = len([r for r in results if r['success']])
    print(f"成功: {successful_tests}/{len(debug_tools)}個")
    
    print(f"\n📋 個別結果:")
    for result in results:
        status = "✅ 成功" if result['success'] else "❌ 失敗"
        print(f"  {result['tool']}: {status} ({result['execution_time']:.1f}秒)")
    
    # 総合分析
    print(f"\n🔍 総合分析:")
    
    if successful_tests == len(debug_tools):
        print(f"  ✅ 全テスト成功 - 詳細なデータが収集されました")
        print(f"  📊 各ツールの出力を確認して仮説を検証してください")
    elif successful_tests >= len(debug_tools) // 2:
        print(f"  🟡 部分的成功 - 一部のデータが収集されました")
        print(f"  ⚠️ 失敗したテストの原因を確認することが推奨されます")
    else:
        print(f"  🔴 大部分が失敗 - 環境またはスクリプトに問題がある可能性")
        print(f"  🛠️ 依存関係とスクリプトパスを確認してください")
    
    # 次のステップの提案
    print(f"\n💡 次のステップ:")
    print(f"  1. 各ツールの詳細出力を確認")
    print(f"  2. SQLiteロック競合の有無を確認")
    print(f"  3. プロセス実行時間の異常を確認")
    print(f"  4. DB並行更新の競合状況を確認")
    
    # 仮説検証のガイド
    print(f"\n🎯 仮説検証ガイド:")
    print(f"  🔴 SQLite並行処理制限が原因の場合:")
    print(f"    - ロックタイムアウトエラーが多数検出")
    print(f"    - DB更新時間が異常に長い")
    print(f"    - 並行トランザクションで競合発生")
    print(f"  ✅ SQLite以外が原因の場合:")
    print(f"    - ロック競合は少ない")
    print(f"    - プロセス実行時間の別の異常")
    print(f"    - 支持線検出以外のボトルネック")
    
    print('='*70)
    
    return successful_tests == len(debug_tools)

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n🛑 統合テストを中断しました")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 統合テスト実行エラー: {e}")
        sys.exit(1)