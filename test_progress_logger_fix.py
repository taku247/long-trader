#!/usr/bin/env python3
"""
進捗ロガー修正テスト

問題: total_processed=0の場合（シグナルなし）でも「失敗」と表示される
修正: analysis_attempted基準での成功判定に変更
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from scalable_analysis_system import ScalableAnalysisSystem
from progress_logger import SymbolProgressLogger

def test_progress_logger_no_signal_success():
    """シグナルなしでも成功表示されるかテスト"""
    print("🧪 進捗ロガー修正テスト: シグナルなし = 成功")
    
    # 一時DBセットアップ
    temp_dir = tempfile.mkdtemp()
    temp_db = Path(temp_dir) / "test_analysis.db"
    
    with sqlite3.connect(temp_db) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timeframe TEXT,
                config TEXT,
                execution_id TEXT,
                task_status TEXT DEFAULT 'pending',
                status TEXT DEFAULT 'running'
            )
        ''')
        conn.commit()
    
    try:
        # ScalableAnalysisSystemインスタンス作成（テスト用DB使用）
        with patch.object(ScalableAnalysisSystem, '__init__', 
                        lambda self, base_dir: setattr(self, 'db_path', temp_db)):
            
            system = ScalableAnalysisSystem("test_dir")
            
            # バッチ設定（2つの戦略）
            batch_configs = [
                {'symbol': 'HYPE', 'timeframe': '15m', 'strategy': 'Aggressive_ML'},
                {'symbol': 'HYPE', 'timeframe': '15m', 'strategy': 'Balanced'}
            ]
            
            # 進捗ロガーのログ出力をキャプチャ
            captured_logs = []
            
            def mock_log(message):
                captured_logs.append(message)
                print(f"📋 ProgressLogger: {message}")
            
            # ProgressLoggerのログ出力をモック化
            with patch.object(SymbolProgressLogger, '_log', side_effect=mock_log):
                # generate_batch_analysisメソッドをモック化（total_processed=0を返す）
                with patch.object(system, '_process_chunk', return_value=0):
                    
                    # 進捗ロガー有効でgenerate_batch_analysis実行
                    total_processed = system.generate_batch_analysis(
                        batch_configs, 
                        symbol="HYPE", 
                        execution_id="test_execution_id"
                    )
                    
                    print(f"📊 total_processed: {total_processed}")
                    
                    # ログ内容を確認
                    log_text = " ".join(captured_logs)
                    
                    if "🎉 HYPE 銘柄追加完了！" in log_text:
                        print("✅ 成功: シグナルなしでも「完了」と表示された")
                        return True
                    elif "❌ HYPE 銘柄追加失敗" in log_text:
                        print("❌ 失敗: まだ「失敗」と表示されている")
                        return False
                    else:
                        print("⚠️ 不明: 成功/失敗メッセージが見つからない")
                        return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_success_criteria_change():
    """成功判定ロジック変更の確認"""
    print("\n🔧 成功判定ロジック変更確認")
    
    try:
        # scalable_analysis_system.pyファイル内容確認
        with open('/Users/moriwakikeita/tools/long-trader/scalable_analysis_system.py', 'r') as f:
            content = f.read()
        
        # 修正前のロジック（total_processed > 0）が残っていないか確認
        if 'progress_logger.log_final_summary(total_processed > 0)' in content:
            print("❌ 修正前のロジックが残っている")
            return False
        
        # 修正後のロジック（analysis_attempted）があるか確認
        if 'analysis_attempted = len(batch_configs) > 0' in content and \
           'progress_logger.log_final_summary(analysis_attempted)' in content:
            print("✅ 成功判定ロジックが修正済み")
            return True
        else:
            print("❌ 修正後のロジックが見つからない")
            return False
            
    except Exception as e:
        print(f"❌ ファイル確認エラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 進捗ロガー修正テスト")
    print("=" * 50)
    
    # テスト1: 成功判定ロジック変更確認
    success1 = test_success_criteria_change()
    
    # テスト2: 実際の動作確認
    success2 = test_progress_logger_no_signal_success()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ 進捗ロガー修正完了")
        print("\n📋 修正内容:")
        print("  - 修正前: total_processed > 0 （シグナル数基準）")
        print("  - 修正後: len(batch_configs) > 0 （分析実行基準）")
        print("\n🎯 これで「シグナルなし」でも「完了」と表示されます")
        return 0
    else:
        print("❌ 修正が不完全")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)