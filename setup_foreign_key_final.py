#!/usr/bin/env python3
"""
外部キー制約最終セットアップ - シンプルな実装
"""

import sqlite3
from pathlib import Path

def setup_foreign_key_constraint():
    """外部キー制約を正しく設定"""
    print("🔗 外部キー制約最終セットアップ")
    print("=" * 50)
    
    analysis_db = Path("web_dashboard/large_scale_analysis/analysis.db")
    execution_db = Path("execution_logs.db")
    
    if not execution_db.exists():
        print(f"❌ execution_logs.db が見つかりません: {execution_db}")
        return False
    
    if not analysis_db.exists():
        print(f"❌ analysis.db が見つかりません: {analysis_db}")
        return False
    
    try:
        with sqlite3.connect(analysis_db) as conn:
            # 外部キーを有効化
            conn.execute("PRAGMA foreign_keys = ON")
            
            # 現在のテーブル確認
            cursor = conn.execute("SELECT COUNT(*) FROM analyses")
            current_count = cursor.fetchone()[0]
            print(f"📊 現在のレコード数: {current_count}")
            
            # 現在のデータをバックアップ
            if current_count > 0:
                conn.execute("""
                    CREATE TABLE analyses_backup AS 
                    SELECT * FROM analyses
                """)
                print(f"✅ {current_count}件のデータをバックアップしました")
            
            # 元のテーブルを削除
            conn.execute("DROP TABLE analyses")
            
            # 外部キー制約付きの新テーブル作成
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
                    execution_id TEXT NOT NULL
                )
            """)
            
            # 外部データベースをアタッチ
            conn.execute(f"ATTACH DATABASE '{execution_db.resolve()}' AS exec_db")
            
            # インデックス作成
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_execution_id ON analyses(execution_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_symbol ON analyses(symbol)")
            
            # バックアップデータがあれば、有効なexecution_idのみ復元
            if current_count > 0:
                cursor = conn.execute("""
                    INSERT INTO analyses 
                    SELECT b.* FROM analyses_backup b
                    JOIN exec_db.execution_logs e ON b.execution_id = e.execution_id
                    WHERE b.execution_id IS NOT NULL
                """)
                restored_count = cursor.rowcount
                print(f"✅ {restored_count}件の有効データを復元しました")
                
                # バックアップテーブル削除
                conn.execute("DROP TABLE analyses_backup")
            
            conn.commit()
            print("✅ 外部キー制約付きテーブル作成完了")
            
            # 制約テスト用のトリガー作成（参照整合性チェック）
            conn.execute("""
                CREATE TRIGGER fk_analyses_execution_id
                BEFORE INSERT ON analyses
                FOR EACH ROW
                WHEN NEW.execution_id IS NOT NULL
                BEGIN
                    SELECT CASE
                        WHEN ((SELECT execution_id FROM exec_db.execution_logs WHERE execution_id = NEW.execution_id) IS NULL)
                        THEN RAISE(ABORT, 'Foreign key constraint failed: execution_id not found in execution_logs')
                    END;
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER fk_analyses_execution_id_update
                BEFORE UPDATE ON analyses
                FOR EACH ROW
                WHEN NEW.execution_id IS NOT NULL
                BEGIN
                    SELECT CASE
                        WHEN ((SELECT execution_id FROM exec_db.execution_logs WHERE execution_id = NEW.execution_id) IS NULL)
                        THEN RAISE(ABORT, 'Foreign key constraint failed: execution_id not found in execution_logs')
                    END;
                END
            """)
            
            print("✅ 参照整合性チェックトリガー作成完了")
            
            return True
            
    except Exception as e:
        print(f"❌ セットアップエラー: {e}")
        return False

def test_constraint():
    """制約の動作テスト"""
    print("\n🧪 制約動作テスト")
    print("-" * 30)
    
    analysis_db = Path("web_dashboard/large_scale_analysis/analysis.db")
    execution_db = Path("execution_logs.db")
    
    try:
        # 有効なexecution_idを取得
        with sqlite3.connect(execution_db) as exec_conn:
            cursor = exec_conn.execute("SELECT execution_id FROM execution_logs LIMIT 1")
            valid_execution = cursor.fetchone()
            
            if not valid_execution:
                print("❌ テスト用の有効なexecution_idが見つかりません")
                return False
            
            valid_execution_id = valid_execution[0]
            print(f"📋 テスト用execution_id: {valid_execution_id}")
        
        with sqlite3.connect(analysis_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(f"ATTACH DATABASE '{execution_db.resolve()}' AS exec_db")
            
            # 1. 有効なexecution_idでの挿入テスト
            try:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, total_trades, win_rate, total_return, 
                     sharpe_ratio, max_drawdown, avg_leverage, execution_id)
                    VALUES ('FKTEST', '1h', 'Test', 10, 0.6, 0.15, 1.5, -0.08, 5.0, ?)
                """, (valid_execution_id,))
                print("✅ 有効execution_idでの挿入: 成功")
            except Exception as e:
                print(f"❌ 有効execution_idでの挿入: 失敗 - {e}")
                return False
            
            # 2. 無効なexecution_idでの挿入テスト
            try:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, total_trades, execution_id)
                    VALUES ('FKTEST_INVALID', '1h', 'Test', 1, 'invalid_execution_id_12345')
                """)
                print("❌ 無効execution_idでの挿入: 成功してしまいました（制約が効いていない）")
                return False
            except Exception as e:
                print("✅ 無効execution_idでの挿入: 正しく拒否されました")
                print(f"   エラー: {e}")
            
            # 3. NULL execution_idでの挿入テスト
            try:
                conn.execute("""
                    INSERT INTO analyses 
                    (symbol, timeframe, config, total_trades, execution_id)
                    VALUES ('FKTEST_NULL', '1h', 'Test', 1, NULL)
                """)
                print("❌ NULL execution_idでの挿入: 成功してしまいました（NOT NULL制約が効いていない）")
                return False
            except Exception as e:
                print("✅ NULL execution_idでの挿入: 正しく拒否されました")
                print(f"   エラー: {e}")
            
            # テストデータをクリーンアップ
            conn.execute("DELETE FROM analyses WHERE symbol LIKE 'FKTEST%'")
            conn.commit()
            
            print("✅ すべての制約テストが合格しました")
            return True
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        return False

def verify_final_state():
    """最終状態の確認"""
    print("\n📊 最終状態確認")
    print("-" * 30)
    
    analysis_db = Path("web_dashboard/large_scale_analysis/analysis.db")
    
    with sqlite3.connect(analysis_db) as conn:
        # レコード数
        cursor = conn.execute("SELECT COUNT(*) FROM analyses")
        count = cursor.fetchone()[0]
        print(f"レコード数: {count}")
        
        # トリガー確認
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'fk_%'")
        triggers = cursor.fetchall()
        print(f"参照整合性トリガー: {len(triggers)}件")
        for trigger in triggers:
            print(f"  - {trigger[0]}")
        
        # インデックス確認
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_analyses_%'")
        indexes = cursor.fetchall()
        print(f"インデックス: {len(indexes)}件")
        for index in indexes:
            print(f"  - {index[0]}")

def main():
    """メイン実行"""
    print("🔗 外部キー制約最終セットアップスクリプト")
    print("=" * 80)
    
    # セットアップ実行
    setup_success = setup_foreign_key_constraint()
    
    if not setup_success:
        print("❌ セットアップに失敗しました")
        return False
    
    # 制約テスト
    test_success = test_constraint()
    
    if not test_success:
        print("❌ 制約テストに失敗しました")
        return False
    
    # 最終状態確認
    verify_final_state()
    
    print("\n🎉 外部キー制約の実装が完了しました！")
    print("✅ 参照整合性が強化されました")
    print("✅ 今後のanalysesレコードは有効なexecution_idが必須になります")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)