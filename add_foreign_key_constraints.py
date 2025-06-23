#!/usr/bin/env python3
"""
外部キー制約追加スクリプト - 段階的なデータベース参照整合性強化
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
import json

class ForeignKeyConstraintManager:
    """外部キー制約管理クラス"""
    
    def __init__(self, execution_db_path=None, analysis_db_path=None):
        self.execution_db_path = Path(execution_db_path or "execution_logs.db")
        self.analysis_db_path = Path(analysis_db_path or "web_dashboard/large_scale_analysis/analysis.db")
        
        if not self.execution_db_path.exists():
            raise FileNotFoundError(f"execution_logs.db not found: {self.execution_db_path}")
        if not self.analysis_db_path.exists():
            raise FileNotFoundError(f"analysis.db not found: {self.analysis_db_path}")
    
    def backup_databases(self):
        """データベースをバックアップ"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = Path(f"backups/foreign_key_constraint_{timestamp}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backups = {}
        
        # execution_logs.db バックアップ
        exec_backup = backup_dir / "execution_logs_backup.db"
        shutil.copy2(self.execution_db_path, exec_backup)
        backups['execution'] = str(exec_backup)
        print(f"✅ execution_logs.db バックアップ: {exec_backup}")
        
        # analysis.db バックアップ
        analysis_backup = backup_dir / "analysis_backup.db"
        shutil.copy2(self.analysis_db_path, analysis_backup)
        backups['analysis'] = str(analysis_backup)
        print(f"✅ analysis.db バックアップ: {analysis_backup}")
        
        # バックアップ情報を記録
        backup_info = {
            'timestamp': timestamp,
            'backup_dir': str(backup_dir),
            'backups': backups
        }
        
        info_file = backup_dir / "backup_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        return backup_info
    
    def analyze_current_state(self):
        """現在のデータ状況を分析"""
        print("📊 現在のデータ状況分析")
        print("-" * 40)
        
        analysis = {
            'execution_logs': {'count': 0, 'sample_ids': []},
            'analyses': {'total': 0, 'null_execution_id': 0, 'set_execution_id': 0, 'invalid_execution_id': 0},
            'orphaned_analyses': []
        }
        
        # execution_logs の状況
        with sqlite3.connect(self.execution_db_path) as exec_conn:
            cursor = exec_conn.execute("SELECT COUNT(*) FROM execution_logs")
            analysis['execution_logs']['count'] = cursor.fetchone()[0]
            
            cursor = exec_conn.execute("SELECT execution_id FROM execution_logs ORDER BY timestamp_start DESC LIMIT 5")
            analysis['execution_logs']['sample_ids'] = [row[0] for row in cursor.fetchall()]
        
        # analyses の状況
        with sqlite3.connect(self.analysis_db_path) as analysis_conn:
            # 総数
            cursor = analysis_conn.execute("SELECT COUNT(*) FROM analyses")
            analysis['analyses']['total'] = cursor.fetchone()[0]
            
            # NULL execution_id
            cursor = analysis_conn.execute("SELECT COUNT(*) FROM analyses WHERE execution_id IS NULL")
            analysis['analyses']['null_execution_id'] = cursor.fetchone()[0]
            
            # SET execution_id
            cursor = analysis_conn.execute("SELECT COUNT(*) FROM analyses WHERE execution_id IS NOT NULL")
            analysis['analyses']['set_execution_id'] = cursor.fetchone()[0]
            
            # 無効なexecution_id（孤立レコード）を検出
            analysis_conn.execute(f"ATTACH DATABASE '{self.execution_db_path}' AS exec_db")
            cursor = analysis_conn.execute("""
                SELECT a.id, a.symbol, a.execution_id
                FROM analyses a
                LEFT JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE a.execution_id IS NOT NULL AND e.execution_id IS NULL
            """)
            analysis['orphaned_analyses'] = cursor.fetchall()
            analysis['analyses']['invalid_execution_id'] = len(analysis['orphaned_analyses'])
        
        # 結果表示
        print(f"📈 execution_logs: {analysis['execution_logs']['count']}件")
        print(f"📈 analyses 総数: {analysis['analyses']['total']}件")
        print(f"   - NULL execution_id: {analysis['analyses']['null_execution_id']}件")
        print(f"   - 有効 execution_id: {analysis['analyses']['set_execution_id'] - analysis['analyses']['invalid_execution_id']}件")
        print(f"   - 無効 execution_id: {analysis['analyses']['invalid_execution_id']}件")
        
        if analysis['orphaned_analyses']:
            print("\n⚠️ 孤立した分析結果:")
            for record in analysis['orphaned_analyses'][:5]:
                print(f"   ID:{record[0]} {record[1]} -> {record[2]}")
            if len(analysis['orphaned_analyses']) > 5:
                print(f"   ... 他 {len(analysis['orphaned_analyses']) - 5}件")
        
        return analysis
    
    def cleanup_orphaned_data(self, dry_run=True):
        """孤立データのクリーンアップ"""
        print(f"\n🧹 孤立データクリーンアップ {'(DRY RUN)' if dry_run else ''}")
        print("-" * 40)
        
        cleanup_summary = {
            'orphaned_deleted': 0,
            'null_handled': 0
        }
        
        with sqlite3.connect(self.analysis_db_path) as analysis_conn:
            analysis_conn.execute(f"ATTACH DATABASE '{self.execution_db_path}' AS exec_db")
            
            # 1. 孤立レコードの削除
            cursor = analysis_conn.execute("""
                SELECT COUNT(*)
                FROM analyses a
                LEFT JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                WHERE a.execution_id IS NOT NULL AND e.execution_id IS NULL
            """)
            orphaned_count = cursor.fetchone()[0]
            
            if orphaned_count > 0:
                print(f"🗑️ 孤立レコード削除対象: {orphaned_count}件")
                if not dry_run:
                    cursor = analysis_conn.execute("""
                        DELETE FROM analyses 
                        WHERE id IN (
                            SELECT a.id
                            FROM analyses a
                            LEFT JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                            WHERE a.execution_id IS NOT NULL AND e.execution_id IS NULL
                        )
                    """)
                    cleanup_summary['orphaned_deleted'] = cursor.rowcount
                    print(f"✅ {cleanup_summary['orphaned_deleted']}件の孤立レコードを削除しました")
                else:
                    print(f"🔍 [DRY RUN] {orphaned_count}件の孤立レコードを削除予定")
            else:
                print("✅ 孤立レコードはありません")
            
            # 2. NULL execution_id の処理方針
            cursor = analysis_conn.execute("SELECT COUNT(*) FROM analyses WHERE execution_id IS NULL")
            null_count = cursor.fetchone()[0]
            
            if null_count > 0:
                print(f"\n📋 NULL execution_id レコード: {null_count}件")
                print("処理方針:")
                print("  1. 削除する（推奨）: 古いデータで参照整合性が取れない")
                print("  2. 保持する: execution_id を NULL のまま残す（制約は NULLABLE にする）")
                print("  3. デフォルト値設定: 'LEGACY' などのデフォルト値を設定")
                
                # ここでは削除方針を採用（NULL レコードは古いデータのため）
                if not dry_run:
                    cursor = analysis_conn.execute("DELETE FROM analyses WHERE execution_id IS NULL")
                    cleanup_summary['null_handled'] = cursor.rowcount
                    print(f"✅ {cleanup_summary['null_handled']}件のNULLレコードを削除しました")
                else:
                    print(f"🔍 [DRY RUN] {null_count}件のNULLレコードを削除予定")
            else:
                print("✅ NULL execution_id レコードはありません")
            
            if not dry_run:
                analysis_conn.commit()
        
        return cleanup_summary
    
    def add_foreign_key_constraint(self, dry_run=True):
        """外部キー制約を追加"""
        print(f"\n🔗 外部キー制約追加 {'(DRY RUN)' if dry_run else ''}")
        print("-" * 40)
        
        if dry_run:
            print("🔍 [DRY RUN] 以下の手順で制約を追加します:")
            print("1. analyses テーブルの構造変更")
            print("2. 外部キー制約付きの新テーブル作成")
            print("3. データ移行")
            print("4. テーブル置換")
            print("5. 外部キー有効化")
            return True
        
        try:
            with sqlite3.connect(self.analysis_db_path) as conn:
                # 外部キーを有効化
                conn.execute("PRAGMA foreign_keys = ON")
                
                # 1. 既存テーブルをリネーム
                conn.execute("ALTER TABLE analyses RENAME TO analyses_old")
                
                # 2. 外部キー制約付きの新テーブル作成（実際のスキーマに合わせる）
                conn.execute(f"""
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
                        FOREIGN KEY (execution_id) REFERENCES execution_logs(execution_id)
                    )
                """)
                
                # 3. 外部データベースをアタッチしてデータ移行
                conn.execute(f"ATTACH DATABASE '{self.execution_db_path}' AS exec_db")
                
                # 有効なレコードのみ移行
                cursor = conn.execute("""
                    INSERT INTO analyses 
                    SELECT a.* FROM analyses_old a
                    JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                    WHERE a.execution_id IS NOT NULL
                """)
                migrated_count = cursor.rowcount
                
                # 4. 古いテーブルを削除
                conn.execute("DROP TABLE analyses_old")
                
                # 5. インデックス作成
                conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_execution_id ON analyses(execution_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_symbol ON analyses(symbol)")
                
                conn.commit()
                
                print(f"✅ 外部キー制約追加完了")
                print(f"✅ {migrated_count}件のレコードを移行しました")
                
                return True
                
        except Exception as e:
            print(f"❌ 外部キー制約追加エラー: {e}")
            return False
    
    def verify_constraints(self):
        """制約の動作確認"""
        print("\n🧪 外部キー制約動作確認")
        print("-" * 40)
        
        try:
            with sqlite3.connect(self.analysis_db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute(f"ATTACH DATABASE '{self.execution_db_path}' AS exec_db")
                
                # 1. 有効なexecution_idでの挿入テスト
                cursor = conn.execute("SELECT execution_id FROM exec_db.execution_logs LIMIT 1")
                valid_execution_id = cursor.fetchone()
                
                if valid_execution_id:
                    valid_id = valid_execution_id[0]
                    try:
                        conn.execute("""
                            INSERT INTO analyses 
                            (symbol, timeframe, config, total_trades, execution_id)
                            VALUES ('CONSTRAINT_TEST', '1h', 'Test', 1, ?)
                        """, (valid_id,))
                        print("✅ 有効execution_idでの挿入: 成功")
                        
                        # テストレコードを削除
                        conn.execute("DELETE FROM analyses WHERE symbol = 'CONSTRAINT_TEST'")
                    except Exception as e:
                        print(f"❌ 有効execution_idでの挿入: 失敗 - {e}")
                
                # 2. 無効なexecution_idでの挿入テスト
                try:
                    conn.execute("""
                        INSERT INTO analyses 
                        (symbol, timeframe, config, total_trades, execution_id)
                        VALUES ('CONSTRAINT_TEST_INVALID', '1h', 'Test', 1, 'invalid_execution_id')
                    """)
                    print("❌ 無効execution_idでの挿入: 成功してしまいました（制約が効いていない）")
                    return False
                except sqlite3.IntegrityError:
                    print("✅ 無効execution_idでの挿入: 正しく拒否されました")
                
                # 3. 制約情報の確認
                cursor = conn.execute("PRAGMA foreign_key_list(analyses)")
                constraints = cursor.fetchall()
                
                print(f"✅ 外部キー制約: {len(constraints)}件")
                for constraint in constraints:
                    print(f"   {constraint}")
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ 制約確認エラー: {e}")
            return False

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='外部キー制約追加スクリプト')
    parser.add_argument('--dry-run', action='store_true', 
                       help='実際の変更を行わず、変更予定のみを表示')
    parser.add_argument('--cleanup-only', action='store_true',
                       help='データクリーンアップのみ実行')
    parser.add_argument('--skip-backup', action='store_true',
                       help='バックアップをスキップ')
    
    args = parser.parse_args()
    
    print("🔗 外部キー制約追加スクリプト")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN モード - 実際の変更は行いません")
    
    try:
        # マネージャー初期化
        manager = ForeignKeyConstraintManager()
        
        # ステップ1: バックアップ作成
        if not args.skip_backup:
            print("\n📁 ステップ1: バックアップ作成")
            backup_info = manager.backup_databases()
        
        # ステップ2: 現状分析
        print("\n📊 ステップ2: データ状況分析")
        analysis = manager.analyze_current_state()
        
        # ステップ3: データクリーンアップ
        print("\n🧹 ステップ3: データクリーンアップ")
        cleanup_summary = manager.cleanup_orphaned_data(dry_run=args.dry_run)
        
        if args.cleanup_only:
            print("✅ データクリーンアップのみ完了しました")
            return
        
        # ステップ4: 外部キー制約追加
        print("\n🔗 ステップ4: 外部キー制約追加")
        constraint_success = manager.add_foreign_key_constraint(dry_run=args.dry_run)
        
        if not constraint_success:
            print("❌ 外部キー制約追加に失敗しました")
            return
        
        # ステップ5: 制約動作確認
        if not args.dry_run:
            print("\n🧪 ステップ5: 制約動作確認")
            verify_success = manager.verify_constraints()
            
            if not verify_success:
                print("❌ 制約動作確認に失敗しました")
                return
        
        print("\n" + "=" * 50)
        if args.dry_run:
            print("🔍 DRY RUN 完了 - --dry-run フラグを外して実際の変更を実行してください")
        else:
            print("✅ 外部キー制約追加完了！")
            if not args.skip_backup:
                print(f"📁 バックアップ場所: {backup_info['backup_dir']}")
            print("\n次のステップ:")
            print("1. アプリケーションの動作確認")
            print("2. 制約が正常に機能することの確認")
            print("3. パフォーマンスの監視")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()