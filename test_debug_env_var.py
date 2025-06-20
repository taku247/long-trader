#!/usr/bin/env python3
"""
環境変数デバッグテスト
"""

import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

def test_environment_variable_debug():
    """環境変数の詳細デバッグ"""
    
    print("🔍 環境変数デバッグテスト")
    print("=" * 50)
    
    # 1. support_resistance_ml.pyの関数確認
    try:
        from support_resistance_ml import get_current_execution_id
        current_id = get_current_execution_id()
        print(f"📋 get_current_execution_id(): '{current_id}'")
        print(f"📋 型: {type(current_id)}")
        print(f"📋 真偽値: {bool(current_id)}")
    except Exception as e:
        print(f"❌ import エラー: {e}")
        return False
    
    # 2. 環境変数設定
    import uuid
    test_id = f"debug_test_{uuid.uuid4().hex[:8]}"
    os.environ['CURRENT_EXECUTION_ID'] = test_id
    print(f"\n🔧 環境変数設定: '{test_id}'")
    
    # 3. os.environ確認
    env_value = os.environ.get('CURRENT_EXECUTION_ID')
    print(f"📋 os.environ取得: '{env_value}'")
    
    # 4. 関数による動的取得テスト
    try:
        current_id_after = get_current_execution_id()
        print(f"📋 環境変数設定後の関数呼び出し: '{current_id_after}'")
        print(f"📋 真偽値: {bool(current_id_after)}")
        
        if current_id_after == test_id:
            print("✅ 動的取得成功: 環境変数と一致")
        else:
            print("❌ 動的取得失敗: 環境変数と不一致")
        
    except Exception as e:
        print(f"❌ 動的取得エラー: {e}")
    
    # 5. 直接関数テスト
    try:
        from support_resistance_ml import check_cancellation_requested
        
        # DB記録作成
        from execution_log_database import ExecutionLogDatabase, ExecutionType, ExecutionStatus
        db = ExecutionLogDatabase()
        
        db.create_execution_with_id(
            test_id,
            ExecutionType.SYMBOL_ADDITION,
            symbol="DEBUG_TEST"
        )
        
        db.update_execution_status(test_id, ExecutionStatus.CANCELLED)
        print(f"📝 DB記録作成: {test_id} (CANCELLED)")
        
        # キャンセル確認
        result = check_cancellation_requested()
        print(f"🔍 キャンセル確認結果: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ 関数テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # クリーンアップ
        if 'CURRENT_EXECUTION_ID' in os.environ:
            del os.environ['CURRENT_EXECUTION_ID']

if __name__ == "__main__":
    success = test_environment_variable_debug()
    print(f"\n結果: {'成功' if success else '失敗'}")