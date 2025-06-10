#!/usr/bin/env python3
"""
既存銘柄マイグレーションシステム
旧設定から新しい管理システムへの安全な移行
"""

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sys
import os

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from real_time_system.utils.colored_log import get_colored_logger
from hyperliquid_validator import HyperliquidValidator, ValidationContext, ValidationResult
from execution_log_database import ExecutionLogDatabase, ExecutionType, ExecutionStatus


class MigrationStatus(Enum):
    """マイグレーション状況"""
    PENDING = "pending"           # 未実行
    RUNNING = "running"           # 実行中
    SUCCESS = "success"           # 成功
    PARTIAL_SUCCESS = "partial"   # 部分成功
    FAILED = "failed"             # 失敗
    CANCELLED = "cancelled"       # キャンセル


@dataclass
class LegacySymbolConfig:
    """旧設定の銘柄情報"""
    symbol: str
    timeframe: str = "15m"
    strategy: str = "Conservative_ML"
    enabled: bool = True
    source: str = "config.json"  # 設定元ファイル


@dataclass
class MigrationResult:
    """マイグレーション結果"""
    symbol: str
    status: MigrationStatus
    validation_result: Optional[ValidationResult] = None
    error_message: Optional[str] = None
    migrated_to_new_system: bool = False
    backup_created: bool = False
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class MigrationSummary:
    """マイグレーション全体の結果"""
    total_symbols: int
    successful_migrations: int
    failed_migrations: int
    warnings_count: int
    backup_created: bool
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: List[MigrationResult] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []


class LegacyMigrationSystem:
    """既存銘柄マイグレーションシステム"""
    
    def __init__(self):
        self.logger = get_colored_logger(__name__)
        self.execution_db = ExecutionLogDatabase()
        
        # 設定パス
        self.legacy_config_paths = [
            Path("config.json"),
            Path("settings.json"), 
            Path("real_time_system/config.json"),
            Path("web_dashboard/config.json")
        ]
        
        # バックアップディレクトリ
        self.backup_dir = Path("migration_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # 新システム設定パス
        self.new_config_path = Path("migrated_config.json")
    
    async def run_migration(self, dry_run: bool = False) -> MigrationSummary:
        """
        マイグレーション実行
        
        Args:
            dry_run: True の場合、実際の変更は行わずに確認のみ
        """
        self.logger.info("🔄 Starting legacy symbol migration")
        
        # 実行記録作成
        execution_id = self.execution_db.create_execution(
            ExecutionType.MANUAL_EXECUTION,
            triggered_by="MIGRATION_SYSTEM",
            metadata={
                "migration_type": "legacy_symbols",
                "dry_run": dry_run,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        self.execution_db.update_execution_status(
            execution_id,
            ExecutionStatus.RUNNING,
            current_operation='既存設定の読み込み',
            total_tasks=4
        )
        
        summary = MigrationSummary(
            total_symbols=0,
            successful_migrations=0,
            failed_migrations=0,
            warnings_count=0,
            backup_created=False,
            execution_id=execution_id,
            started_at=datetime.now()
        )
        
        try:
            # Step 1: 既存設定の発見と読み込み
            legacy_symbols = await self._discover_legacy_symbols()
            summary.total_symbols = len(legacy_symbols)
            
            self.execution_db.add_execution_step(
                execution_id,
                "discover_legacy_symbols",
                "SUCCESS",
                result_data={"symbols_found": len(legacy_symbols)}
            )
            
            if not legacy_symbols:
                self.logger.info("📭 No legacy symbols found to migrate")
                summary.status = MigrationStatus.SUCCESS
                summary.completed_at = datetime.now()
                
                self.execution_db.update_execution_status(
                    execution_id,
                    ExecutionStatus.SUCCESS,
                    current_operation='完了（移行対象なし）',
                    progress_percentage=100
                )
                
                return summary
            
            self.logger.info(f"📦 Found {len(legacy_symbols)} legacy symbols to migrate")
            
            # Step 2: バックアップ作成
            if not dry_run:
                backup_success = await self._create_backup()
                summary.backup_created = backup_success
                
                self.execution_db.add_execution_step(
                    execution_id,
                    "create_backup",
                    "SUCCESS" if backup_success else "FAILED",
                    result_data={"backup_created": backup_success}
                )
            
            # Step 3: 各銘柄のマイグレーション
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.RUNNING,
                current_operation='銘柄マイグレーション実行中'
            )
            
            migration_results = []
            for i, symbol_config in enumerate(legacy_symbols):
                self.logger.info(f"🔄 Migrating symbol {i+1}/{len(legacy_symbols)}: {symbol_config.symbol}")
                
                result = await self._migrate_single_symbol(symbol_config, dry_run)
                migration_results.append(result)
                
                if result.status == MigrationStatus.SUCCESS:
                    summary.successful_migrations += 1
                else:
                    summary.failed_migrations += 1
                
                summary.warnings_count += len(result.warnings)
            
            summary.results = migration_results
            
            self.execution_db.add_execution_step(
                execution_id,
                "migrate_symbols",
                "SUCCESS",
                result_data={
                    "total_symbols": summary.total_symbols,
                    "successful": summary.successful_migrations,
                    "failed": summary.failed_migrations
                }
            )
            
            # Step 4: 新設定ファイルの生成
            if not dry_run and summary.successful_migrations > 0:
                await self._generate_new_config(migration_results)
                
                self.execution_db.add_execution_step(
                    execution_id,
                    "generate_new_config",
                    "SUCCESS",
                    result_data={"config_file": str(self.new_config_path)}
                )
            
            # 完了
            summary.completed_at = datetime.now()
            
            if summary.failed_migrations == 0:
                summary_status = ExecutionStatus.SUCCESS
                operation = '完了'
            elif summary.successful_migrations > 0:
                summary_status = ExecutionStatus.PARTIAL_SUCCESS  
                operation = '部分的に完了'
            else:
                summary_status = ExecutionStatus.FAILED
                operation = '失敗'
            
            self.execution_db.update_execution_status(
                execution_id,
                summary_status,
                current_operation=operation,
                progress_percentage=100
            )
            
            self._log_migration_summary(summary, dry_run)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Migration failed: {e}")
            
            self.execution_db.update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                current_operation=f'エラー: {str(e)}'
            )
            
            self.execution_db.add_execution_error(execution_id, {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'step': 'migration_execution'
            })
            
            summary.completed_at = datetime.now()
            raise
    
    async def _discover_legacy_symbols(self) -> List[LegacySymbolConfig]:
        """既存設定ファイルから銘柄を発見"""
        legacy_symbols = []
        
        for config_path in self.legacy_config_paths:
            if not config_path.exists():
                continue
                
            try:
                self.logger.info(f"📖 Reading legacy config: {config_path}")
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 様々な設定形式に対応
                symbols = self._extract_symbols_from_config(config_data, str(config_path))
                legacy_symbols.extend(symbols)
                
                self.logger.info(f"  Found {len(symbols)} symbols in {config_path}")
                
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to read {config_path}: {e}")
        
        # 重複削除
        unique_symbols = {}
        for symbol_config in legacy_symbols:
            key = symbol_config.symbol
            if key not in unique_symbols:
                unique_symbols[key] = symbol_config
            else:
                # より詳細な設定を優先
                existing = unique_symbols[key]
                if (symbol_config.timeframe != "15m" or 
                    symbol_config.strategy != "Conservative_ML"):
                    unique_symbols[key] = symbol_config
        
        return list(unique_symbols.values())
    
    def _extract_symbols_from_config(self, config_data: Dict, source: str) -> List[LegacySymbolConfig]:
        """設定データから銘柄を抽出"""
        symbols = []
        
        # パターン1: monitoring.symbols
        if 'monitoring' in config_data and 'symbols' in config_data['monitoring']:
            for symbol in config_data['monitoring']['symbols']:
                if isinstance(symbol, str):
                    symbols.append(LegacySymbolConfig(
                        symbol=symbol.upper(),
                        source=source
                    ))
                elif isinstance(symbol, dict):
                    symbols.append(LegacySymbolConfig(
                        symbol=symbol.get('name', '').upper(),
                        timeframe=symbol.get('timeframe', '15m'),
                        strategy=symbol.get('strategy', 'Conservative_ML'),
                        enabled=symbol.get('enabled', True),
                        source=source
                    ))
        
        # パターン2: symbols 直接
        if 'symbols' in config_data:
            symbols_data = config_data['symbols']
            if isinstance(symbols_data, list):
                for symbol in symbols_data:
                    if isinstance(symbol, str):
                        symbols.append(LegacySymbolConfig(
                            symbol=symbol.upper(),
                            source=source
                        ))
                    elif isinstance(symbol, dict):
                        symbols.append(LegacySymbolConfig(
                            symbol=symbol.get('name', '').upper(),
                            timeframe=symbol.get('interval', '15m'),
                            strategy=symbol.get('strategy', 'Conservative_ML'),
                            enabled=symbol.get('enabled', True),
                            source=source
                        ))
        
        # パターン3: traded_symbols
        if 'traded_symbols' in config_data:
            for symbol in config_data['traded_symbols']:
                symbols.append(LegacySymbolConfig(
                    symbol=symbol.upper(),
                    source=source
                ))
        
        return symbols
    
    async def _migrate_single_symbol(self, symbol_config: LegacySymbolConfig, dry_run: bool) -> MigrationResult:
        """単一銘柄のマイグレーション"""
        result = MigrationResult(
            symbol=symbol_config.symbol,
            status=MigrationStatus.PENDING
        )
        
        try:
            # バリデーション実行（既存監視用の緩やかな検証）
            async with HyperliquidValidator() as validator:
                validation_result = await validator.validate_symbol(
                    symbol_config.symbol,
                    ValidationContext.MIGRATION
                )
                
                result.validation_result = validation_result
            
            if validation_result.valid:
                if not dry_run:
                    # 新システムに追加
                    success = await self._add_to_new_system(symbol_config)
                    result.migrated_to_new_system = success
                
                if validation_result.warnings:
                    result.warnings.extend(validation_result.warnings)
                    self.logger.warning(f"⚠️ {symbol_config.symbol}: {', '.join(validation_result.warnings)}")
                
                result.status = MigrationStatus.SUCCESS
                self.logger.success(f"✅ {symbol_config.symbol} migrated successfully")
                
            else:
                # バリデーション失敗でも既存は継続（緩やかな移行）
                result.error_message = validation_result.reason
                result.warnings.append(f"Validation failed: {validation_result.reason}")
                
                if validation_result.action == "continue":
                    # 継続推奨の場合は部分成功扱い
                    result.status = MigrationStatus.PARTIAL_SUCCESS
                    if not dry_run:
                        result.migrated_to_new_system = await self._add_to_new_system(symbol_config)
                    self.logger.warning(f"⚠️ {symbol_config.symbol} migrated with warnings")
                else:
                    result.status = MigrationStatus.FAILED
                    self.logger.error(f"❌ {symbol_config.symbol} migration failed: {validation_result.reason}")
                
        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.error_message = str(e)
            self.logger.error(f"❌ {symbol_config.symbol} migration error: {e}")
        
        return result
    
    async def _add_to_new_system(self, symbol_config: LegacySymbolConfig) -> bool:
        """新システムに銘柄を追加"""
        try:
            # TODO: 実際の新システムAPIとの統合
            # 現在はサンプル実装
            
            # AutoSymbolTrainerでの学習実行は必要に応じて
            # from auto_symbol_training import AutoSymbolTrainer
            # trainer = AutoSymbolTrainer()
            # execution_id = await trainer.add_symbol_with_training(symbol_config.symbol)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add {symbol_config.symbol} to new system: {e}")
            return False
    
    async def _create_backup(self) -> bool:
        """設定ファイルのバックアップ作成"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = self.backup_dir / f"migration_{timestamp}"
            backup_subdir.mkdir(exist_ok=True)
            
            backed_up_files = 0
            
            for config_path in self.legacy_config_paths:
                if config_path.exists():
                    backup_path = backup_subdir / f"{config_path.name}.backup"
                    shutil.copy2(config_path, backup_path)
                    backed_up_files += 1
                    self.logger.info(f"📋 Backed up: {config_path} -> {backup_path}")
            
            if backed_up_files > 0:
                # バックアップ情報ファイル作成
                backup_info = {
                    "timestamp": timestamp,
                    "backed_up_files": backed_up_files,
                    "migration_version": "1.0",
                    "original_paths": [str(p) for p in self.legacy_config_paths if p.exists()]
                }
                
                with open(backup_subdir / "backup_info.json", 'w', encoding='utf-8') as f:
                    json.dump(backup_info, f, ensure_ascii=False, indent=2)
                
                self.logger.success(f"✅ Backup created: {backup_subdir}")
                return True
            else:
                self.logger.warning("⚠️ No files to backup")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Backup creation failed: {e}")
            return False
    
    async def _generate_new_config(self, migration_results: List[MigrationResult]):
        """新しい設定ファイルの生成"""
        try:
            successful_symbols = [
                result.symbol for result in migration_results
                if result.status in [MigrationStatus.SUCCESS, MigrationStatus.PARTIAL_SUCCESS]
                and result.migrated_to_new_system
            ]
            
            new_config = {
                "migration_info": {
                    "migrated_at": datetime.now().isoformat(),
                    "migration_version": "1.0",
                    "total_symbols": len(migration_results),
                    "successful_symbols": len(successful_symbols)
                },
                "monitoring": {
                    "symbols": successful_symbols,
                    "interval_minutes": 15
                },
                "alerts": {
                    "leverage_threshold": 10.0,
                    "confidence_threshold": 70,
                    "cooldown_minutes": 60,
                    "max_alerts_hour": 10
                },
                "notifications": {
                    "discord": {
                        "enabled": False,
                        "webhook_url": "",
                        "mention_role": ""
                    },
                    "console": {
                        "level": "INFO"
                    },
                    "file": {
                        "enabled": True
                    }
                }
            }
            
            with open(self.new_config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, ensure_ascii=False, indent=2)
            
            self.logger.success(f"✅ New config generated: {self.new_config_path}")
            
        except Exception as e:
            self.logger.error(f"❌ New config generation failed: {e}")
            raise
    
    def _log_migration_summary(self, summary: MigrationSummary, dry_run: bool):
        """マイグレーション結果のサマリーログ"""
        mode = "DRY RUN" if dry_run else "ACTUAL MIGRATION"
        
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"🔄 MIGRATION SUMMARY ({mode})")
        self.logger.info(f"{'='*50}")
        self.logger.info(f"📊 Total symbols processed: {summary.total_symbols}")
        self.logger.info(f"✅ Successful migrations: {summary.successful_migrations}")
        self.logger.info(f"❌ Failed migrations: {summary.failed_migrations}")
        self.logger.info(f"⚠️ Warnings: {summary.warnings_count}")
        self.logger.info(f"📋 Backup created: {'Yes' if summary.backup_created else 'No'}")
        
        if summary.results:
            self.logger.info(f"\n📋 Detailed Results:")
            for result in summary.results:
                status_icon = {
                    MigrationStatus.SUCCESS: "✅",
                    MigrationStatus.PARTIAL_SUCCESS: "⚠️",
                    MigrationStatus.FAILED: "❌"
                }.get(result.status, "❓")
                
                self.logger.info(f"  {status_icon} {result.symbol}: {result.status.value}")
                if result.warnings:
                    for warning in result.warnings:
                        self.logger.info(f"    ⚠️ {warning}")
        
        self.logger.info(f"{'='*50}")
    
    async def dry_run_migration(self) -> MigrationSummary:
        """ドライランマイグレーション（確認のみ）"""
        self.logger.info("🔍 Starting dry run migration (no actual changes)")
        return await self.run_migration(dry_run=True)
    
    def get_migration_history(self) -> List[Dict]:
        """過去のマイグレーション履歴を取得"""
        try:
            executions = self.execution_db.list_executions(
                limit=20,
                execution_type=ExecutionType.MANUAL_EXECUTION.value
            )
            
            migration_executions = [
                exec for exec in executions
                if exec.get('metadata') and 'migration_type' in exec.get('metadata', '{}')
            ]
            
            return migration_executions
            
        except Exception as e:
            self.logger.error(f"Failed to get migration history: {e}")
            return []


async def main():
    """テスト実行"""
    migration_system = LegacyMigrationSystem()
    
    print("=== Long Trader 既存銘柄マイグレーションシステム ===\n")
    
    # ドライラン実行
    print("🔍 Dry run migration...")
    dry_run_summary = await migration_system.dry_run_migration()
    
    if dry_run_summary.total_symbols > 0:
        response = input(f"\n{dry_run_summary.total_symbols}個の銘柄が見つかりました。実際のマイグレーションを実行しますか？ (y/N): ")
        
        if response.lower() == 'y':
            print("\n🔄 Running actual migration...")
            actual_summary = await migration_system.run_migration(dry_run=False)
            print(f"\n✅ Migration completed. Execution ID: {actual_summary.execution_id}")
        else:
            print("\n❌ Migration cancelled by user")
    else:
        print("\n📭 No legacy symbols found to migrate")


if __name__ == "__main__":
    asyncio.run(main())