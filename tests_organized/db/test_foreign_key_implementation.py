#!/usr/bin/env python3
"""
外部キー制約実装テスト - 実際の制約動作を確認
"""

import os
import sys
import sqlite3
from pathlib import Path

def test_foreign_key_constraint():
    """外部キー制約の動作をテストする"""
    print("🧪 外部キー制約動作テスト")
    print("=" * 50)
    
    execution_db = Path("execution_logs.db")
    analysis_db = Path("web_dashboard/large_scale_analysis/analysis.db")
    
    try:
        # 1. テーブル構造に外部キー制約を追加
        with sqlite3.connect(analysis_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # 既存テーブル構造確認
            cursor = conn.execute("PRAGMA table_info(analyses)")
            columns = cursor.fetchall()
            print(f"📊 現在のanalysesテーブル: {len(columns)}カラム")
            
            # 外部キー制約確認
            cursor = conn.execute("PRAGMA foreign_key_list(analyses)")
            constraints = cursor.fetchall()
            print(f"📊 現在の外部キー制約: {len(constraints)}件")
            
            if len(constraints) == 0:
                print("⚠️ 外部キー制約がありません。制約を追加します...")
                
                # テーブルを再作成して制約を追加
                conn.execute("BEGIN TRANSACTION")
                
                # 既存データを保存（現在は0件）
                cursor = conn.execute("SELECT COUNT(*) FROM analyses")
                current_count = cursor.fetchone()[0]
                print(f"📊 現在のレコード数: {current_count}")
                
                # 新しいテーブル作成（外部キー制約付き）
                conn.execute("ALTER TABLE analyses RENAME TO analyses_backup")
                
                # 外部データベースをアタッチしてから制約付きテーブル作成
                conn.execute("ATTACH DATABASE '../../execution_logs.db' AS exec_db")
                
                conn.execute("""
                    CREATE TABLE analyses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        config TEXT NOT NULL,
                        total_trades INTEGER,
                        win_rate REAL,
                        total_return REAL,
                        sharpe_ratio REAL,
                        max_drawdown REAL,
                        avg_leverage REAL,
                        chart_path TEXT,
                        compressed_path TEXT,
                        generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        execution_id TEXT NOT NULL,
                        FOREIGN KEY (execution_id) REFERENCES exec_db.execution_logs(execution_id)
                    )
                """)
                
                # 既存データがあれば移行（現在は0件）
                if current_count > 0:
                    conn.execute("""
                        INSERT INTO analyses 
                        SELECT * FROM analyses_backup
                        WHERE execution_id IS NOT NULL
                    """)
                
                # バックアップテーブル削除
                conn.execute("DROP TABLE analyses_backup")
                
                # インデックス作成
                conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_execution_id ON analyses(execution_id)")
                
                conn.execute("COMMIT")
                print("✅ 外部キー制約を追加しました")
            else:
                print("✅ 既に外部キー制約が設定されています")
                for constraint in constraints:
                    print(f"   {constraint}")
        
        # 2. execution_logs から有効なexecution_idを取得
        with sqlite3.connect(execution_db) as exec_conn:
            cursor = exec_conn.execute("SELECT execution_id FROM execution_logs WHERE status = 'SUCCESS' LIMIT 1")
            valid_execution = cursor.fetchone()
            
            if not valid_execution:
                cursor = exec_conn.execute("SELECT execution_id FROM execution_logs LIMIT 1")
                valid_execution = cursor.fetchone()
        
        if not valid_execution:
            print("❌ テスト用の有効なexecution_idが見つかりません")
            return False
        
        valid_execution_id = valid_execution[0]
        print(f"📋 テスト用execution_id: {valid_execution_id}")
        
        # 3. 制約動作テスト
        with sqlite3.connect(analysis_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            # 外部データベースをアタッチ
            conn.execute("ATTACH DATABASE '../../execution_logs.db' AS exec_db")
            
            print("\n🧪 制約動作テスト実行")
            
            # 3-1. 有効なexecution_idでの挿入テスト
            try:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, total_trades, win_rate, total_return, 
                     sharpe_ratio, max_drawdown, avg_leverage, execution_id)
                    VALUES ('FKTEST', '1h', 'Test', 10, 0.6, 0.15, 1.5, -0.08, 5.0, ?)
                """, (valid_execution_id,))
                print("✅ 有効execution_idでの挿入: 成功")
                
                # 挿入されたレコードを確認
                cursor = conn.execute("SELECT id, symbol, execution_id FROM analyses WHERE symbol = 'FKTEST'")
                test_record = cursor.fetchone()
                if test_record:
                    print(f"   挿入レコード: ID={test_record[0]}, Symbol={test_record[1]}, ExecID={test_record[2]}")
            except Exception as e:
                print(f"❌ 有効execution_idでの挿入: 失敗 - {e}")
                return False
            
            # 3-2. 無効なexecution_idでの挿入テスト
            try:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, total_trades, execution_id)
                    VALUES ('FKTEST_INVALID', '1h', 'Test', 1, 'invalid_execution_id_12345')
                """)
                print("❌ 無効execution_idでの挿入: 成功してしまいました（制約が効いていない）")
                return False
            except sqlite3.IntegrityError as e:
                print("✅ 無効execution_idでの挿入: 正しく拒否されました")
                print(f"   エラーメッセージ: {e}")
            
            # 3-3. NULL execution_idでの挿入テスト
            try:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, total_trades, execution_id)
                    VALUES ('FKTEST_NULL', '1h', 'Test', 1, NULL)
                """)
                print("❌ NULL execution_idでの挿入: 成功してしまいました（NOT NULL制約が効いていない）")
                return False
            except sqlite3.IntegrityError as e:
                print("✅ NULL execution_idでの挿入: 正しく拒否されました")
                print(f"   エラーメッセージ: {e}")
            
            # テストデータをクリーンアップ
            conn.execute("DELETE FROM analyses WHERE symbol LIKE 'FKTEST%'")
            conn.commit()
            
            print("\n✅ すべての制約テストが合格しました")
            return True
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        return False

def verify_constraint_status():
    """制約の現在の状況を確認"""
    print("\n📊 制約状況確認")
    print("-" * 30)
    
    analysis_db = Path("web_dashboard/large_scale_analysis/analysis.db")
    
    with sqlite3.connect(analysis_db) as conn:
        # 外部キー有効状況
        cursor = conn.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        print(f"外部キー有効: {'Yes' if fk_enabled else 'No'}")
        
        # 制約一覧
        cursor = conn.execute("PRAGMA foreign_key_list(analyses)")
        constraints = cursor.fetchall()
        print(f"外部キー制約数: {len(constraints)}")
        
        for i, constraint in enumerate(constraints):
            print(f"制約{i+1}: {constraint}")
        
        # レコード数
        cursor = conn.execute("SELECT COUNT(*) FROM analyses")
        count = cursor.fetchone()[0]
        print(f"現在のレコード数: {count}")

def main():
    """メイン実行"""
    print("🔗 外部キー制約実装テストスイート")
    print("=" * 80)
    
    # 現在の状況確認
    verify_constraint_status()
    
    # 制約動作テスト
    success = test_foreign_key_constraint()
    
    if success:
        print("\n🎉 外部キー制約の実装と動作確認が完了しました！")
        print("✅ 参照整合性が強化されました")
    else:
        print("\n❌ 外部キー制約の実装に問題があります")
    
    # 最終状況確認
    verify_constraint_status()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)