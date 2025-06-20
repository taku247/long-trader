#!/usr/bin/env python3
"""
DB統一のためのマイグレーションスクリプト
安全にweb_dashboard/execution_logs.dbのデータをルートDBに統合する
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
import json

def backup_databases():
    """データベースをバックアップ"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path(f"backups/migration_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    root_db = Path("execution_logs.db")
    web_db = Path("web_dashboard/execution_logs.db")
    
    backups = {}
    
    if root_db.exists():
        backup_root = backup_dir / "execution_logs_root_backup.db"
        shutil.copy2(root_db, backup_root)
        backups['root'] = str(backup_root)
        print(f"✅ ルートDBバックアップ: {backup_root}")
    
    if web_db.exists():
        backup_web = backup_dir / "execution_logs_web_backup.db"
        shutil.copy2(web_db, backup_web)
        backups['web'] = str(backup_web)
        print(f"✅ WebDBバックアップ: {backup_web}")
    
    # バックアップ情報を記録
    backup_info = {
        'timestamp': timestamp,
        'backup_dir': str(backup_dir),
        'backups': backups,
        'original_root_exists': root_db.exists(),
        'original_web_exists': web_db.exists()
    }
    
    info_file = backup_dir / "backup_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(backup_info, f, indent=2, ensure_ascii=False)
    
    return backup_info

def analyze_databases():
    """両方のデータベースを分析して統合計画を立てる"""
    root_db = Path("execution_logs.db")
    web_db = Path("web_dashboard/execution_logs.db")
    
    analysis = {
        'root_db': {'exists': False, 'count': 0, 'sample_records': []},
        'web_db': {'exists': False, 'count': 0, 'sample_records': []},
        'conflicts': [],
        'merge_plan': {}
    }
    
    # ルートDB分析
    if root_db.exists():
        with sqlite3.connect(root_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            count = cursor.fetchone()[0]
            analysis['root_db'] = {
                'exists': True,
                'count': count,
                'sample_records': []
            }
            
            # サンプルレコード取得
            cursor = conn.execute("""
                SELECT execution_id, execution_type, symbol, status, timestamp_start 
                FROM execution_logs 
                ORDER BY timestamp_start DESC 
                LIMIT 5
            """)
            analysis['root_db']['sample_records'] = [
                dict(zip([col[0] for col in cursor.description], row))
                for row in cursor.fetchall()
            ]
    
    # WebDB分析
    if web_db.exists():
        with sqlite3.connect(web_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            count = cursor.fetchone()[0]
            analysis['web_db'] = {
                'exists': True,
                'count': count,
                'sample_records': []
            }
            
            # サンプルレコード取得
            cursor = conn.execute("""
                SELECT execution_id, execution_type, symbol, status, timestamp_start 
                FROM execution_logs 
                ORDER BY timestamp_start DESC 
                LIMIT 5
            """)
            analysis['web_db']['sample_records'] = [
                dict(zip([col[0] for col in cursor.description], row))
                for row in cursor.fetchall()
            ]
    
    # 競合検出
    if analysis['root_db']['exists'] and analysis['web_db']['exists']:
        with sqlite3.connect(web_db) as web_conn:
            web_conn.execute(f"ATTACH DATABASE '{root_db}' AS root_db")
            
            # 重複するexecution_idを検索
            cursor = web_conn.execute("""
                SELECT w.execution_id, w.status as web_status, r.status as root_status,
                       w.timestamp_start as web_time, r.timestamp_start as root_time
                FROM execution_logs w
                JOIN root_db.execution_logs r ON w.execution_id = r.execution_id
            """)
            
            conflicts = []
            for row in cursor.fetchall():
                conflicts.append({
                    'execution_id': row[0],
                    'web_status': row[1],
                    'root_status': row[2],
                    'web_timestamp': row[3],
                    'root_timestamp': row[4]
                })
            
            analysis['conflicts'] = conflicts
    
    return analysis

def migrate_data(dry_run=True):
    """データを安全に統合"""
    root_db = Path("execution_logs.db")
    web_db = Path("web_dashboard/execution_logs.db")
    
    if not web_db.exists():
        print("❌ WebダッシュボードDBが存在しません")
        return False
    
    if not root_db.exists():
        print("ℹ️ ルートDBが存在しないため、WebDBをコピーします")
        if not dry_run:
            shutil.copy2(web_db, root_db)
            print(f"✅ {web_db} を {root_db} にコピーしました")
        else:
            print(f"🔍 [DRY RUN] {web_db} を {root_db} にコピーする予定")
        return True
    
    # 両方のDBが存在する場合の統合
    print("🔄 両方のDBが存在するため、データを統合します...")
    
    if not dry_run:
        with sqlite3.connect(web_db) as web_conn:
            web_conn.execute(f"ATTACH DATABASE '{root_db}' AS root_db")
            
            # 新しいレコードのみを追加（重複は無視）
            cursor = web_conn.execute("""
                INSERT OR IGNORE INTO root_db.execution_logs 
                SELECT * FROM execution_logs 
                WHERE execution_id NOT IN (
                    SELECT execution_id FROM root_db.execution_logs
                )
            """)
            
            inserted_count = cursor.rowcount
            print(f"✅ {inserted_count}件の新しいレコードを統合しました")
            
            # 統合後の確認
            cursor = web_conn.execute("SELECT COUNT(*) FROM root_db.execution_logs")
            total_count = cursor.fetchone()[0]
            print(f"📊 統合後の総レコード数: {total_count}")
            
            return True
    else:
        # ドライラン：統合される予定のレコードを表示
        with sqlite3.connect(web_db) as web_conn:
            web_conn.execute(f"ATTACH DATABASE '{root_db}' AS root_db")
            
            cursor = web_conn.execute("""
                SELECT execution_id, symbol, status, timestamp_start
                FROM execution_logs 
                WHERE execution_id NOT IN (
                    SELECT execution_id FROM root_db.execution_logs
                )
                ORDER BY timestamp_start DESC
            """)
            
            new_records = cursor.fetchall()
            print(f"🔍 [DRY RUN] {len(new_records)}件の新しいレコードが統合される予定:")
            for record in new_records[:10]:  # 最初の10件を表示
                print(f"  - {record[0]}: {record[1]} ({record[2]}) at {record[3]}")
            
            if len(new_records) > 10:
                print(f"  ... 他 {len(new_records) - 10}件")
            
            return True

def update_web_dashboard_config(dry_run=True):
    """WebダッシュボードがルートDBを参照するよう設定を更新"""
    app_py_path = Path("web_dashboard/app.py")
    
    if not app_py_path.exists():
        print(f"❌ {app_py_path} が存在しません")
        return False
    
    # ファイルを読み込み
    with open(app_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修正対象を検索
    target_line = "exec_db_path = 'execution_logs.db'"
    replacement_line = "exec_db_path = '../execution_logs.db'  # ルートディレクトリのDBを参照"
    
    if target_line in content:
        if not dry_run:
            new_content = content.replace(target_line, replacement_line)
            
            # バックアップを作成
            backup_path = app_py_path.with_suffix('.py.backup')
            shutil.copy2(app_py_path, backup_path)
            print(f"📁 バックアップ作成: {backup_path}")
            
            # ファイルを更新
            with open(app_py_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ {app_py_path} を更新しました")
            print(f"   変更: {target_line}")
            print(f"   →   {replacement_line}")
        else:
            print(f"🔍 [DRY RUN] {app_py_path} を更新する予定:")
            print(f"  変更: {target_line}")
            print(f"  →   {replacement_line}")
        return True
    else:
        print(f"⚠️ {app_py_path} に対象の行が見つかりませんでした")
        print(f"   検索対象: {target_line}")
        return False

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DB統一マイグレーション')
    parser.add_argument('--dry-run', action='store_true', 
                       help='実際の変更を行わず、変更予定のみを表示')
    parser.add_argument('--backup-only', action='store_true',
                       help='バックアップのみ実行')
    
    args = parser.parse_args()
    
    print("🔧 DB統一マイグレーションスクリプト")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN モード - 実際の変更は行いません")
    
    # ステップ1: バックアップ作成
    print("\n📁 ステップ1: バックアップ作成")
    backup_info = backup_databases()
    
    if args.backup_only:
        print("✅ バックアップのみ完了しました")
        return
    
    # ステップ2: データベース分析
    print("\n📊 ステップ2: データベース分析")
    analysis = analyze_databases()
    
    print(f"ルートDB: {analysis['root_db']['count']}件のレコード")
    print(f"WebDB: {analysis['web_db']['count']}件のレコード")
    
    if analysis['conflicts']:
        print(f"⚠️ 競合レコード: {len(analysis['conflicts'])}件")
        for conflict in analysis['conflicts'][:5]:
            print(f"  - {conflict['execution_id']}: Web({conflict['web_status']}) vs Root({conflict['root_status']})")
    else:
        print("✅ 競合なし")
    
    # ステップ3: データマイグレーション
    print("\n🔄 ステップ3: データマイグレーション")
    success = migrate_data(dry_run=args.dry_run)
    
    if not success:
        print("❌ マイグレーションに失敗しました")
        return
    
    # ステップ4: Webダッシュボード設定更新
    print("\n⚙️ ステップ4: Webダッシュボード設定更新")
    config_success = update_web_dashboard_config(dry_run=args.dry_run)
    
    if not config_success:
        print("❌ 設定更新に失敗しました")
        return
    
    print("\n" + "=" * 50)
    if args.dry_run:
        print("🔍 DRY RUN 完了 - --dry-run フラグを外して実際の変更を実行してください")
    else:
        print("✅ DB統一マイグレーション完了！")
        print(f"📁 バックアップ場所: {backup_info['backup_dir']}")
        print("\n次のステップ:")
        print("1. Webダッシュボードを再起動")
        print("2. 銘柄追加のキャンセル機能をテスト")
        print("3. 全体的な動作確認")

if __name__ == "__main__":
    main()