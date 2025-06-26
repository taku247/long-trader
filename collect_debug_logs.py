#!/usr/bin/env python3
"""
Support/Resistance Debug Log Collector
並列プロセスで生成されたデバッグログファイルを収集・表示するツール
"""

import os
import glob
import sys
from datetime import datetime

def collect_debug_logs():
    """
    /tmp/sr_debug_*.logファイルを収集して表示
    """
    print("🔍 Support/Resistance Debug Log Collector")
    print("=" * 60)
    
    # デバッグログファイルを検索
    log_pattern = "/tmp/sr_debug_*.log"
    log_files = glob.glob(log_pattern)
    
    if not log_files:
        print("❌ デバッグログファイルが見つかりません")
        print(f"検索パターン: {log_pattern}")
        print("\n💡 使用方法:")
        print("1. 環境変数を設定: export SUPPORT_RESISTANCE_DEBUG=true")
        print("2. 分析を実行")
        print("3. このスクリプトでログを確認")
        return
    
    print(f"📁 {len(log_files)}個のデバッグログファイルを発見")
    log_files.sort()
    
    for log_file in log_files:
        pid = log_file.split('_')[-1].replace('.log', '')
        file_size = os.path.getsize(log_file)
        
        print(f"\n📄 プロセス {pid} のログ ({file_size} bytes)")
        print("-" * 40)
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content)
        except Exception as e:
            print(f"❌ ログ読み込みエラー: {e}")
    
    print("\n🧹 ログファイルクリーンアップ")
    cleanup_choice = input("デバッグログファイルを削除しますか? (y/N): ").lower()
    
    if cleanup_choice == 'y':
        for log_file in log_files:
            try:
                os.remove(log_file)
                print(f"✅ 削除: {log_file}")
            except Exception as e:
                print(f"❌ 削除失敗: {log_file} - {e}")
    else:
        print("ℹ️  ログファイルは保持されました")

def enable_debug_mode():
    """
    デバッグモードを有効化するための手順を表示
    """
    print("🔧 Support/Resistance Debug Mode Setup")
    print("=" * 50)
    print("\n1. 環境変数を設定:")
    print("   export SUPPORT_RESISTANCE_DEBUG=true")
    print("\n2. 分析を実行:")
    print("   python auto_symbol_training.py")
    print("   または")
    print("   cd web_dashboard && python app.py")
    print("\n3. ログを確認:")
    print("   python collect_debug_logs.py")
    print("\n4. 無効化:")
    print("   export SUPPORT_RESISTANCE_DEBUG=false")
    print("   または")
    print("   unset SUPPORT_RESISTANCE_DEBUG")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        enable_debug_mode()
        return
    
    # 現在のデバッグモード状態をチェック
    debug_mode = os.environ.get('SUPPORT_RESISTANCE_DEBUG', 'false').lower() == 'true'
    
    print(f"🔍 デバッグモード状態: {'有効' if debug_mode else '無効'}")
    
    if not debug_mode:
        print("\n⚠️  デバッグモードが無効です")
        print("有効化するには: python collect_debug_logs.py --setup")
        print("または直接: export SUPPORT_RESISTANCE_DEBUG=true")
        print("\n既存のログファイルを確認しますか? (y/N): ", end="")
        
        choice = input().lower()
        if choice != 'y':
            return
    
    collect_debug_logs()

if __name__ == "__main__":
    main()