#!/usr/bin/env python3
"""
マイグレーションシステムのデモ実行
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from legacy_migration_system import LegacyMigrationSystem


def create_sample_legacy_config():
    """サンプルの旧設定ファイルを作成"""
    sample_config = {
        "monitoring": {
            "symbols": [
                "HYPE",
                "SOL", 
                "PEPE",
                "INVALID_SYMBOL"  # 無効な銘柄も含める
            ],
            "interval_minutes": 15
        },
        "alerts": {
            "leverage_threshold": 10.0,
            "confidence_threshold": 70
        },
        "traded_symbols": [
            "BTC",
            "ETH"
        ]
    }
    
    config_path = Path("config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Sample config created: {config_path}")
    return config_path


async def main():
    """デモ実行"""
    print("=== Long Trader マイグレーションシステム デモ ===\n")
    
    # サンプル設定ファイル作成
    print("📝 Creating sample legacy config...")
    config_path = create_sample_legacy_config()
    
    # マイグレーションシステム初期化
    migration_system = LegacyMigrationSystem()
    
    try:
        # Step 1: ドライラン実行
        print("\n🔍 Running dry-run migration...")
        dry_run_summary = await migration_system.dry_run_migration()
        
        if dry_run_summary.total_symbols > 0:
            print(f"\n✅ Dry-run completed. Found {dry_run_summary.total_symbols} symbols to migrate")
            
            # ユーザー確認
            response = input("\n実際のマイグレーションを実行しますか？ (y/N): ")
            
            if response.lower() == 'y':
                # Step 2: 実際のマイグレーション実行
                print("\n🔄 Running actual migration...")
                actual_summary = await migration_system.run_migration(dry_run=False)
                
                print(f"\n✅ Migration completed!")
                print(f"   Execution ID: {actual_summary.execution_id}")
                print(f"   Successful: {actual_summary.successful_migrations}")
                print(f"   Failed: {actual_summary.failed_migrations}")
                print(f"   Backup created: {actual_summary.backup_created}")
                
                # 生成された新設定ファイルを確認
                if migration_system.new_config_path.exists():
                    print(f"\n📄 New config file generated: {migration_system.new_config_path}")
                
            else:
                print("\n❌ Migration cancelled by user")
        else:
            print("\n📭 No legacy symbols found to migrate")
    
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
    
    finally:
        # サンプル設定ファイルのクリーンアップ
        if config_path.exists():
            config_path.unlink()
            print(f"\n🧹 Cleaned up sample config: {config_path}")


if __name__ == "__main__":
    asyncio.run(main())