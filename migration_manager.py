#!/usr/bin/env python3
"""
データベースマイグレーション管理システム
- スキーマバージョン管理
- 順次マイグレーション実行
- ロールバック機能
- ドライラン対応
"""
import os
import sqlite3
import json
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import shutil
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Migration:
    """個別マイグレーション定義"""
    
    def __init__(self, version: int, name: str, component: str):
        self.version = version
        self.name = name
        self.component = component
        self.description = ""
        
    def up(self, db_path: str) -> None:
        """マイグレーション適用"""
        raise NotImplementedError("up() method must be implemented")
    
    def down(self, db_path: str) -> None:
        """マイグレーション巻き戻し（オプション）"""
        raise NotImplementedError("down() method not implemented")
    
    def validate(self, db_path: str) -> bool:
        """マイグレーション適用後の検証"""
        return True


class MigrationManager:
    """マイグレーション管理メインクラス"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.migrations_dir = self.project_root / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        
        # データベース設定
        self.databases = {
            'execution_logs': self.project_root / 'execution_logs.db',
            'analysis': self.project_root / 'large_scale_analysis' / 'analysis.db',
            'alert_history': self.project_root / 'alert_history_system' / 'data' / 'alert_history.db'
        }
        
        # 全DBでスキーマバージョンテーブルを確保
        self.ensure_schema_version_tables()
        
    def ensure_schema_version_tables(self):
        """全データベースにスキーマバージョンテーブルを作成"""
        for db_name, db_path in self.databases.items():
            # ディレクトリ作成
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_versions (
                        component TEXT PRIMARY KEY,
                        version INTEGER NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT,
                        migration_file TEXT
                    )
                """)
                
                # 初期バージョン設定（未設定の場合）
                cursor = conn.execute(
                    "SELECT version FROM schema_versions WHERE component = ?", 
                    (db_name,)
                )
                if not cursor.fetchone():
                    conn.execute("""
                        INSERT INTO schema_versions 
                        (component, version, description, migration_file)
                        VALUES (?, 0, 'Initial state', 'baseline')
                    """, (db_name,))
                    
            logger.info(f"✅ Schema version table ensured for {db_name}: {db_path}")
    
    def get_current_version(self, component: str) -> int:
        """指定コンポーネントの現在バージョンを取得"""
        db_path = self.databases.get(component)
        if not db_path or not db_path.exists():
            return 0
            
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute(
                "SELECT version FROM schema_versions WHERE component = ?",
                (component,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def set_version(self, component: str, version: int, description: str = "", 
                   migration_file: str = ""):
        """バージョン更新"""
        db_path = self.databases[component]
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO schema_versions 
                (component, version, applied_at, description, migration_file)
                VALUES (?, ?, ?, ?, ?)
            """, (component, version, datetime.now(timezone.utc).isoformat(), 
                  description, migration_file))
                  
        logger.info(f"📊 {component} version updated: {version} - {description}")
    
    def discover_migrations(self, component: str = None) -> List[Tuple[str, int, str]]:
        """マイグレーションファイルの自動発見"""
        migrations = []
        
        # 対象コンポーネント決定
        components = [component] if component else self.databases.keys()
        
        for comp in components:
            comp_dir = self.migrations_dir / comp
            if not comp_dir.exists():
                continue
                
            # 001_migration_name.py のパターンでファイル発見
            for migration_file in comp_dir.glob("[0-9][0-9][0-9]_*.py"):
                try:
                    # ファイル名からバージョン番号抽出
                    version_str = migration_file.stem[:3]
                    version = int(version_str)
                    name = migration_file.stem[4:]  # 001_ を除去
                    
                    migrations.append((comp, version, str(migration_file)))
                    
                except ValueError:
                    logger.warning(f"⚠️ Invalid migration file format: {migration_file}")
                    
        # バージョン順でソート
        migrations.sort(key=lambda x: (x[0], x[1]))
        return migrations
    
    def load_migration(self, migration_file: str) -> Migration:
        """マイグレーションファイルの動的ロード"""
        spec = importlib.util.spec_from_file_location("migration", migration_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Migrationクラスを期待
        if hasattr(module, 'migration'):
            return module.migration
        else:
            raise ValueError(f"Migration file {migration_file} must define 'migration' variable")
    
    def migrate(self, component: str = None, target_version: int = None, 
               dry_run: bool = False, backup: bool = True) -> bool:
        """マイグレーション実行"""
        try:
            if backup and not dry_run:
                self.backup_databases()
            
            migrations = self.discover_migrations(component)
            applied_count = 0
            
            for comp, version, migration_file in migrations:
                current_version = self.get_current_version(comp)
                
                # 適用判定
                if version <= current_version:
                    continue
                    
                if target_version and version > target_version:
                    continue
                
                logger.info(f"🔄 Applying migration: {comp} v{version}")
                
                if dry_run:
                    logger.info(f"   [DRY RUN] Would apply: {migration_file}")
                    continue
                
                # マイグレーション実行
                migration = self.load_migration(migration_file)
                db_path = str(self.databases[comp])
                
                migration.up(db_path)
                
                # 検証
                if not migration.validate(db_path):
                    raise Exception(f"Migration validation failed: {migration_file}")
                
                # バージョン更新
                self.set_version(comp, version, migration.description, 
                               Path(migration_file).name)
                
                applied_count += 1
                logger.info(f"✅ Migration applied: {comp} v{version}")
            
            if applied_count == 0:
                logger.info("📊 All migrations already applied")
            else:
                logger.info(f"🎉 Applied {applied_count} migrations successfully")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def backup_databases(self) -> Dict[str, str]:
        """データベースバックアップ"""
        backup_dir = self.project_root / "db_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_info = {}
        
        for db_name, db_path in self.databases.items():
            if db_path.exists():
                backup_path = backup_dir / f"{db_name}.db"
                shutil.copy2(str(db_path), str(backup_path))
                backup_info[db_name] = str(backup_path)
                logger.info(f"💾 Backup created: {db_name} -> {backup_path}")
        
        # バックアップ情報をJSONで保存
        with open(backup_dir / "backup_info.json", 'w') as f:
            json.dump({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'databases': backup_info
            }, f, indent=2)
        
        return backup_info
    
    def status(self, component: str = None) -> Dict[str, Dict]:
        """マイグレーション状況確認"""
        status_info = {}
        
        components = [component] if component else self.databases.keys()
        
        for comp in components:
            current_version = self.get_current_version(comp)
            available_migrations = self.discover_migrations(comp)
            
            # 該当コンポーネントのマイグレーション
            comp_migrations = [m for m in available_migrations if m[0] == comp]
            latest_version = max([m[1] for m in comp_migrations], default=0)
            
            status_info[comp] = {
                'current_version': current_version,
                'latest_version': latest_version,
                'pending_migrations': len([m for m in comp_migrations if m[1] > current_version]),
                'database_path': str(self.databases[comp]),
                'database_exists': self.databases[comp].exists()
            }
        
        return status_info
    
    def create_migration_template(self, component: str, name: str) -> str:
        """新規マイグレーションテンプレート作成"""
        comp_dir = self.migrations_dir / component
        comp_dir.mkdir(exist_ok=True)
        
        # 次のバージョン番号計算
        existing_migrations = self.discover_migrations(component)
        comp_migrations = [m for m in existing_migrations if m[0] == component]
        next_version = max([m[1] for m in comp_migrations], default=0) + 1
        
        # ファイル名生成
        filename = f"{next_version:03d}_{name}.py"
        migration_file = comp_dir / filename
        
        # テンプレート内容
        template = f'''#!/usr/bin/env python3
"""
{component} Migration: {name}
Version: {next_version}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
import sqlite3
from migration_manager import Migration


class {name.title().replace('_', '')}Migration(Migration):
    """
    {name} マイグレーション
    
    TODO: マイグレーション内容を実装してください
    """
    
    def __init__(self):
        super().__init__(
            version={next_version},
            name="{name}",
            component="{component}"
        )
        self.description = "TODO: マイグレーションの説明を記載"
    
    def up(self, db_path: str) -> None:
        """マイグレーション適用"""
        with sqlite3.connect(db_path) as conn:
            # TODO: マイグレーション処理を実装
            # 例:
            # conn.execute("""
            #     ALTER TABLE table_name ADD COLUMN new_column TEXT
            # """)
            pass
    
    def down(self, db_path: str) -> None:
        """マイグレーション巻き戻し（オプション）"""
        with sqlite3.connect(db_path) as conn:
            # TODO: ロールバック処理を実装（必要に応じて）
            pass
    
    def validate(self, db_path: str) -> bool:
        """マイグレーション適用後の検証"""
        with sqlite3.connect(db_path) as conn:
            # TODO: マイグレーション成功の検証
            # 例: テーブルやカラムの存在確認
            return True


# インスタンス作成（マイグレーションマネージャーが使用）
migration = {name.title().replace('_', '')}Migration()
'''
        
        with open(migration_file, 'w', encoding='utf-8') as f:
            f.write(template)
        
        logger.info(f"📝 Migration template created: {migration_file}")
        return str(migration_file)


def main():
    """CLI エントリーポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration Manager")
    parser.add_argument("--component", help="Target component (execution_logs, analysis, alert_history)")
    parser.add_argument("--target-version", type=int, help="Target migration version")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--no-backup", action="store_true", help="Skip database backup")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--create", help="Create new migration template (format: component:name)")
    
    args = parser.parse_args()
    
    manager = MigrationManager()
    
    if args.status:
        # ステータス表示
        status = manager.status(args.component)
        print("\n📊 Migration Status:")
        print("=" * 60)
        
        for comp, info in status.items():
            print(f"\n🗄️  {comp.upper()}")
            print(f"   Current Version: {info['current_version']}")
            print(f"   Latest Version:  {info['latest_version']}")
            print(f"   Pending:         {info['pending_migrations']} migrations")
            print(f"   Database:        {info['database_path']}")
            print(f"   Exists:          {'✅' if info['database_exists'] else '❌'}")
    
    elif args.create:
        # 新規マイグレーション作成
        try:
            component, name = args.create.split(':', 1)
            manager.create_migration_template(component, name)
        except ValueError:
            print("❌ Invalid format. Use: --create component:migration_name")
    
    else:
        # マイグレーション実行
        success = manager.migrate(
            component=args.component,
            target_version=args.target_version,
            dry_run=args.dry_run,
            backup=not args.no_backup
        )
        
        if success:
            print("\n🎉 Migration completed successfully!")
        else:
            print("\n❌ Migration failed!")
            exit(1)


if __name__ == "__main__":
    main()