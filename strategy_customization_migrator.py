#!/usr/bin/env python3
"""
戦略カスタマイズ機能マイグレーター

戦略カスタマイズ機能のためのデータベースマイグレーションを実行
"""

import sys
import os
import sqlite3
import importlib.util
from pathlib import Path
from datetime import datetime, timezone

class StrategyCustomizationMigrator:
    """戦略カスタマイズ機能のマイグレーター"""
    
    def __init__(self, analysis_db_path="large_scale_analysis/analysis.db"):
        self.analysis_db_path = analysis_db_path
        self.migrations_dir = Path("migrations")
        
        # マイグレーション実行履歴を記録するテーブルを作成
        self.ensure_migration_table()
    
    def ensure_migration_table(self):
        """マイグレーション履歴テーブルの作成"""
        with sqlite3.connect(self.analysis_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_id TEXT UNIQUE NOT NULL,
                    migration_name TEXT NOT NULL,
                    description TEXT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 1
                )
            """)
            conn.commit()
    
    def load_migration(self, migration_file):
        """マイグレーションファイルを動的にロード"""
        spec = importlib.util.spec_from_file_location("migration", migration_file)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)
        return migration_module
    
    def get_available_migrations(self):
        """利用可能なマイグレーションファイルを取得"""
        migrations = []
        
        if not self.migrations_dir.exists():
            return migrations
        
        for migration_file in sorted(self.migrations_dir.glob("*.py")):
            if migration_file.name.startswith("__"):
                continue
            
            try:
                migration_module = self.load_migration(migration_file)
                if hasattr(migration_module, 'get_migration_info'):
                    info = migration_module.get_migration_info()
                    migrations.append({
                        'file': migration_file,
                        'module': migration_module,
                        'info': info
                    })
            except Exception as e:
                print(f"⚠️ マイグレーションファイル {migration_file} の読み込みエラー: {e}")
        
        return migrations
    
    def get_executed_migrations(self):
        """実行済みマイグレーションを取得"""
        with sqlite3.connect(self.analysis_db_path) as conn:
            cursor = conn.execute("""
                SELECT migration_id, migration_name, executed_at, success 
                FROM migration_history 
                ORDER BY executed_at
            """)
            return cursor.fetchall()
    
    def is_migration_executed(self, migration_id):
        """マイグレーションが実行済みかチェック"""
        with sqlite3.connect(self.analysis_db_path) as conn:
            cursor = conn.execute("""
                SELECT 1 FROM migration_history 
                WHERE migration_id = ? AND success = 1
            """, (migration_id,))
            return cursor.fetchone() is not None
    
    def record_migration(self, migration_info, success=True):
        """マイグレーション実行を記録"""
        with sqlite3.connect(self.analysis_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO migration_history 
                (migration_id, migration_name, description, success)
                VALUES (?, ?, ?, ?)
            """, (
                migration_info['id'],
                migration_info['name'],
                migration_info['description'],
                success
            ))
            conn.commit()
    
    def run_migration(self, migration, dry_run=False):
        """単一マイグレーションの実行"""
        info = migration['info']
        module = migration['module']
        
        print(f"🔄 Migration {info['id']}: {info['name']}")
        print(f"   説明: {info['description']}")
        
        if dry_run:
            print("   🔍 ドライラン: 実際の変更は行いません")
            return True
        
        if self.is_migration_executed(info['id']):
            print(f"   ℹ️ スキップ: 既に実行済み")
            return True
        
        try:
            # マイグレーション実行
            module.up(self.analysis_db_path)
            
            # 検証
            if hasattr(module, 'verify'):
                success, message = module.verify(self.analysis_db_path)
                if not success:
                    print(f"   ❌ 検証失敗: {message}")
                    self.record_migration(info, success=False)
                    return False
                print(f"   ✅ 検証成功: {message}")
            
            # 実行記録
            self.record_migration(info, success=True)
            print(f"   ✅ Migration {info['id']} 完了")
            return True
            
        except Exception as e:
            print(f"   ❌ Migration {info['id']} 失敗: {e}")
            self.record_migration(info, success=False)
            return False
    
    def migrate_up(self, dry_run=False, target_migration=None):
        """マイグレーション実行"""
        print("🚀 戦略カスタマイズ機能マイグレーション開始")
        print("=" * 60)
        print(f"対象DB: {self.analysis_db_path}")
        
        if dry_run:
            print("🔍 ドライランモード: 実際の変更は行いません")
        
        print()
        
        # 利用可能なマイグレーション取得
        migrations = self.get_available_migrations()
        
        if not migrations:
            print("❌ 利用可能なマイグレーションがありません")
            return False
        
        print(f"📋 利用可能なマイグレーション: {len(migrations)}件")
        
        # マイグレーション実行
        success_count = 0
        failed_count = 0
        
        for migration in migrations:
            info = migration['info']
            
            # 特定マイグレーションのみ実行する場合
            if target_migration and info['id'] != target_migration:
                continue
            
            success = self.run_migration(migration, dry_run=dry_run)
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                print(f"⚠️ Migration {info['id']} が失敗しました。続行しますか？")
                user_input = input("続行する場合は 'y' を入力: ")
                if user_input.lower() != 'y':
                    break
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("🎯 マイグレーション結果")
        print("=" * 60)
        print(f"成功: {success_count}")
        print(f"失敗: {failed_count}")
        
        if failed_count == 0:
            print("\n🎉 すべてのマイグレーションが成功しました！")
            print("戦略カスタマイズ機能のデータベース準備が完了しました。")
        else:
            print(f"\n⚠️ {failed_count}件のマイグレーションが失敗しました。")
        
        return failed_count == 0
    
    def show_status(self):
        """マイグレーション状況表示"""
        print("📊 マイグレーション状況")
        print("=" * 60)
        
        # 利用可能なマイグレーション
        available_migrations = self.get_available_migrations()
        executed_migrations = self.get_executed_migrations()
        
        print(f"利用可能: {len(available_migrations)}件")
        print(f"実行済み: {len(executed_migrations)}件")
        print()
        
        # 詳細表示
        print("📋 詳細状況:")
        
        executed_ids = {migration[0] for migration in executed_migrations}
        
        for migration in available_migrations:
            info = migration['info']
            status = "✅ 実行済み" if info['id'] in executed_ids else "⏳ 未実行"
            print(f"  {info['id']}: {info['name']} - {status}")
            print(f"      {info['description']}")
        
        if executed_migrations:
            print(f"\n📅 実行履歴:")
            for migration_id, name, executed_at, success in executed_migrations:
                status = "✅" if success else "❌"
                print(f"  {status} {migration_id}: {name} ({executed_at})")
    
    def verify_all(self):
        """全マイグレーションの検証"""
        print("🔍 マイグレーション検証開始")
        print("=" * 60)
        
        migrations = self.get_available_migrations()
        
        if not migrations:
            print("❌ 検証するマイグレーションがありません")
            return False
        
        success_count = 0
        failed_count = 0
        
        for migration in migrations:
            info = migration['info']
            module = migration['module']
            
            if not hasattr(module, 'verify'):
                print(f"⚠️ Migration {info['id']}: 検証関数がありません")
                continue
            
            try:
                success, message = module.verify(self.analysis_db_path)
                status = "✅" if success else "❌"
                print(f"{status} Migration {info['id']}: {message}")
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"❌ Migration {info['id']}: 検証エラー - {e}")
                failed_count += 1
        
        print(f"\n📊 検証結果: 成功={success_count}, 失敗={failed_count}")
        return failed_count == 0

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="戦略カスタマイズ機能マイグレーター")
    parser.add_argument("command", choices=["up", "status", "verify"], 
                       help="実行するコマンド")
    parser.add_argument("--db", default="large_scale_analysis/analysis.db",
                       help="データベースファイルパス")
    parser.add_argument("--dry-run", action="store_true",
                       help="ドライラン（実際の変更を行わない）")
    parser.add_argument("--target", 
                       help="特定のマイグレーションIDのみ実行")
    
    args = parser.parse_args()
    
    # データベースファイルの存在確認
    if not Path(args.db).exists():
        print(f"❌ データベースファイルが存在しません: {args.db}")
        # ディレクトリを作成
        Path(args.db).parent.mkdir(parents=True, exist_ok=True)
        print(f"✅ ディレクトリ作成: {Path(args.db).parent}")
    
    migrator = StrategyCustomizationMigrator(args.db)
    
    if args.command == "up":
        success = migrator.migrate_up(dry_run=args.dry_run, target_migration=args.target)
        sys.exit(0 if success else 1)
    elif args.command == "status":
        migrator.show_status()
    elif args.command == "verify":
        success = migrator.verify_all()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()