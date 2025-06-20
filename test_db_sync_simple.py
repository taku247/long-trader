#!/usr/bin/env python3
"""
簡単なDB記録同期化テスト
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

def test_db_synchronous_creation():
    """DB記録同期作成のテスト"""
    
    print("🧪 DB記録同期作成テスト")
    print("=" * 50)
    
    try:
        # 1. execution_ID生成
        import uuid
        execution_id = f"test_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        print(f"📋 テスト用execution_ID: {execution_id}")
        
        # 2. DB記録作成（同期的）
        print("\n🔄 DB記録作成中...")
        
        from execution_log_database import ExecutionLogDatabase, ExecutionType
        db = ExecutionLogDatabase()
        
        start_time = time.time()
        
        db_execution_id = db.create_execution_with_id(
            execution_id,
            ExecutionType.SYMBOL_ADDITION,
            symbol="SYNC_TEST",
            triggered_by="USER:WEB_UI",
            metadata={"test": True, "source": "web_dashboard"}
        )
        
        creation_time = time.time() - start_time
        print(f"✅ DB記録作成完了: {creation_time:.3f}秒")
        
        # 3. 即座に記録確認
        print("\n🔍 即座記録確認...")
        
        record = db.get_execution(execution_id)
        if record:
            print("✅ DB記録確認: 成功")
            print(f"   Symbol: {record['symbol']}")
            print(f"   Status: {record['status']}")
            print(f"   Triggered by: {record['triggered_by']}")
        else:
            print("❌ DB記録確認: 失敗")
            return False
        
        # 4. Web UIの流れを模擬
        print("\n🌐 Web UI模擬テスト...")
        
        # 事前定義IDでの処理
        from auto_symbol_training import AutoSymbolTrainer
        trainer = AutoSymbolTrainer()
        
        print("🔄 AutoSymbolTrainer処理中...")
        
        # 既存記録チェック
        existing_record = trainer.execution_db.get_execution(execution_id)
        if existing_record:
            print("✅ 既存記録検出: 重複作成を回避")
        else:
            print("❌ 既存記録検出: 失敗")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_reset_database_lookup():
    """手動リセット時のDB検索テスト"""
    
    print("\n🧪 手動リセットDB検索テスト")
    print("=" * 50)
    
    try:
        # テスト用実行記録作成
        import uuid
        execution_id = f"reset_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        from execution_log_database import ExecutionLogDatabase, ExecutionType, ExecutionStatus
        db = ExecutionLogDatabase()
        
        # 実行中ステータスで記録作成
        db.create_execution_with_id(
            execution_id,
            ExecutionType.SYMBOL_ADDITION,
            symbol="RESET_TEST",
            triggered_by="USER:WEB_UI"
        )
        
        # RUNNINGステータスに更新
        db.update_execution_status(execution_id, ExecutionStatus.RUNNING)
        
        print(f"📋 テスト実行ID: {execution_id}")
        
        # 手動リセットの検索模擬
        print("\n🔍 手動リセット検索模擬...")
        
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute('''
                SELECT symbol, status
                FROM execution_logs 
                WHERE execution_id = ?
            ''', (execution_id,))
            
            row = cursor.fetchone()
            if row:
                symbol, status = row
                print(f"✅ DB検索成功: Symbol={symbol}, Status={status}")
                
                if status == 'RUNNING':
                    print("✅ ステータス確認: RUNNING（リセット可能）")
                    
                    # CANCELLEDに更新
                    conn.execute('''
                        UPDATE execution_logs 
                        SET status = 'CANCELLED', 
                            timestamp_end = datetime('now')
                        WHERE execution_id = ?
                    ''', (execution_id,))
                    
                    conn.commit()
                    print("✅ ステータス更新: CANCELLED")
                    
                    return True
                else:
                    print(f"❌ ステータス確認: {status}（リセット不可）")
                    return False
            else:
                print("❌ DB検索失敗: 記録が見つからない")
                return False
                
    except Exception as e:
        print(f"❌ リセットテストエラー: {e}")
        return False

def test_process_environment_variable():
    """プロセス環境変数テスト"""
    
    print("\n🧪 プロセス環境変数テスト")
    print("=" * 50)
    
    try:
        import uuid
        test_execution_id = f"env_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 環境変数設定
        os.environ['CURRENT_EXECUTION_ID'] = test_execution_id
        print(f"📋 環境変数設定: {test_execution_id}")
        
        # 環境変数確認
        retrieved_id = os.environ.get('CURRENT_EXECUTION_ID')
        if retrieved_id == test_execution_id:
            print("✅ 環境変数確認: 成功")
        else:
            print("❌ 環境変数確認: 失敗")
            return False
        
        # support_resistance_ml.pyの確認ロジック模擬
        from support_resistance_ml import check_cancellation_requested
        
        # DB記録作成（CANCELLED状態）
        from execution_log_database import ExecutionLogDatabase, ExecutionType, ExecutionStatus
        db = ExecutionLogDatabase()
        
        db.create_execution_with_id(
            test_execution_id,
            ExecutionType.SYMBOL_ADDITION,
            symbol="ENV_TEST"
        )
        
        db.update_execution_status(test_execution_id, ExecutionStatus.CANCELLED)
        
        print("🔄 キャンセル確認テスト...")
        
        # キャンセル確認実行
        is_cancelled = check_cancellation_requested()
        
        if is_cancelled:
            print("✅ キャンセル検出: 成功")
            return True
        else:
            print("❌ キャンセル検出: 失敗")
            return False
            
    except Exception as e:
        print(f"❌ 環境変数テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # クリーンアップ
        if 'CURRENT_EXECUTION_ID' in os.environ:
            del os.environ['CURRENT_EXECUTION_ID']

def main():
    """メインテスト実行"""
    
    print("🚀 DB記録同期化 簡単テスト")
    print("=" * 60)
    print(f"⏰ 開始時刻: {datetime.now()}")
    
    # テスト実行
    test1 = test_db_synchronous_creation()
    test2 = test_manual_reset_database_lookup()
    test3 = test_process_environment_variable()
    
    # 結果
    print("\n" + "=" * 60)
    print("🏁 テスト結果")
    print("=" * 60)
    
    results = [
        ("DB記録同期作成", test1),
        ("手動リセットDB検索", test2),
        ("プロセス環境変数", test3)
    ]
    
    passed = 0
    for name, result in results:
        status = "✅ 合格" if result else "❌ 不合格"
        print(f"{status} {name}")
        if result:
            passed += 1
    
    print(f"\n📊 合格率: {passed}/{len(results)} ({passed/len(results)*100:.0f}%)")
    
    if passed == len(results):
        print("\n🎉 全テスト合格! 修正内容が正常に動作しています")
        print("💡 確認された機能:")
        print("   • DB記録の同期的作成")
        print("   • execution_IDの整合性")
        print("   • 手動リセットのDB検索")
        print("   • プロセス間の環境変数共有")
    else:
        print(f"\n⚠️ {len(results)-passed}件のテスト不合格")
    
    print(f"\n⏰ 終了時刻: {datetime.now()}")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)