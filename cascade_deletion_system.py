#!/usr/bin/env python3
"""
カスケード削除システム
execution_logs削除時に関連するanalysesレコードを自動的に削除
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Optional, Tuple

class CascadeDeletionSystem:
    """カスケード削除システムクラス"""
    
    def __init__(self, execution_db_path=None, analysis_db_path=None):
        self.execution_db_path = Path(execution_db_path or "execution_logs.db")
        self.analysis_db_path = Path(analysis_db_path or "web_dashboard/large_scale_analysis/analysis.db")
        
        if not self.execution_db_path.exists():
            raise FileNotFoundError(f"execution_logs.db not found: {self.execution_db_path}")
        if not self.analysis_db_path.exists():
            raise FileNotFoundError(f"analysis.db not found: {self.analysis_db_path}")
    
    def analyze_deletion_impact(self, execution_ids: List[str]) -> Dict:
        """削除の影響範囲を分析"""
        print("📊 削除影響範囲分析")
        print("-" * 40)
        
        impact_analysis = {
            'execution_logs': {
                'total_found': 0,
                'records': []
            },
            'analyses': {
                'total_affected': 0,
                'records': [],
                'by_symbol': {},
                'by_config': {}
            },
            'file_artifacts': {
                'chart_files': [],
                'compressed_files': [],
                'total_size': 0
            },
            'warnings': []
        }
        
        # execution_logs の確認
        with sqlite3.connect(self.execution_db_path) as exec_conn:
            exec_conn.row_factory = sqlite3.Row
            
            placeholders = ','.join(['?' for _ in execution_ids])
            cursor = exec_conn.execute(f"""
                SELECT execution_id, execution_type, symbol, status, timestamp_start, timestamp_end
                FROM execution_logs 
                WHERE execution_id IN ({placeholders})
            """, execution_ids)
            
            exec_records = cursor.fetchall()
            impact_analysis['execution_logs']['total_found'] = len(exec_records)
            impact_analysis['execution_logs']['records'] = [dict(row) for row in exec_records]
        
        # 存在しないexecution_idを警告
        found_ids = {record['execution_id'] for record in impact_analysis['execution_logs']['records']}
        missing_ids = set(execution_ids) - found_ids
        if missing_ids:
            impact_analysis['warnings'].append(f"存在しないexecution_id: {missing_ids}")
        
        # analyses の影響確認
        if found_ids:
            with sqlite3.connect(self.analysis_db_path) as analysis_conn:
                analysis_conn.row_factory = sqlite3.Row
                
                placeholders = ','.join(['?' for _ in found_ids])
                cursor = analysis_conn.execute(f"""
                    SELECT id, symbol, timeframe, config, chart_path, compressed_path, 
                           execution_id, generated_at
                    FROM analyses 
                    WHERE execution_id IN ({placeholders})
                """, list(found_ids))
                
                analysis_records = cursor.fetchall()
                impact_analysis['analyses']['total_affected'] = len(analysis_records)
                impact_analysis['analyses']['records'] = [dict(row) for row in analysis_records]
                
                # 統計集計
                for record in analysis_records:
                    symbol = record['symbol']
                    config = record['config']
                    
                    if symbol not in impact_analysis['analyses']['by_symbol']:
                        impact_analysis['analyses']['by_symbol'][symbol] = 0
                    impact_analysis['analyses']['by_symbol'][symbol] += 1
                    
                    if config not in impact_analysis['analyses']['by_config']:
                        impact_analysis['analyses']['by_config'][config] = 0
                    impact_analysis['analyses']['by_config'][config] += 1
                    
                    # ファイルアーティファクトの確認
                    if record['chart_path']:
                        chart_path = Path(record['chart_path'])
                        if chart_path.exists():
                            impact_analysis['file_artifacts']['chart_files'].append(str(chart_path))
                            impact_analysis['file_artifacts']['total_size'] += chart_path.stat().st_size
                    
                    if record['compressed_path']:
                        compressed_path = Path(record['compressed_path'])
                        if compressed_path.exists():
                            impact_analysis['file_artifacts']['compressed_files'].append(str(compressed_path))
                            impact_analysis['file_artifacts']['total_size'] += compressed_path.stat().st_size
        
        # 結果表示
        print(f"📋 実行ログ: {impact_analysis['execution_logs']['total_found']}件が削除対象")
        for record in impact_analysis['execution_logs']['records'][:5]:
            print(f"   - {record['execution_id']}: {record['symbol']} ({record['status']})")
        if len(impact_analysis['execution_logs']['records']) > 5:
            print(f"   ... 他 {len(impact_analysis['execution_logs']['records']) - 5}件")
        
        print(f"\n📊 分析結果: {impact_analysis['analyses']['total_affected']}件が削除対象")
        if impact_analysis['analyses']['by_symbol']:
            print("   銘柄別:")
            for symbol, count in sorted(impact_analysis['analyses']['by_symbol'].items()):
                print(f"     {symbol}: {count}件")
        
        if impact_analysis['analyses']['by_config']:
            print("   戦略別:")
            for config, count in sorted(impact_analysis['analyses']['by_config'].items()):
                print(f"     {config}: {count}件")
        
        file_count = len(impact_analysis['file_artifacts']['chart_files']) + len(impact_analysis['file_artifacts']['compressed_files'])
        if file_count > 0:
            size_mb = impact_analysis['file_artifacts']['total_size'] / (1024 * 1024)
            print(f"\n💾 関連ファイル: {file_count}件 ({size_mb:.1f}MB)")
        
        if impact_analysis['warnings']:
            print(f"\n⚠️ 警告:")
            for warning in impact_analysis['warnings']:
                print(f"   {warning}")
        
        return impact_analysis
    
    def backup_before_deletion(self, execution_ids: List[str]) -> Dict:
        """削除前のバックアップ作成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = Path(f"backups/cascade_deletion_{timestamp}")
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
            'backups': backups,
            'target_execution_ids': execution_ids,
            'original_execution_size': self.execution_db_path.stat().st_size,
            'original_analysis_size': self.analysis_db_path.stat().st_size
        }
        
        info_file = backup_dir / "backup_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        return backup_info
    
    def execute_cascade_deletion(self, execution_ids: List[str], 
                                impact_analysis: Dict, 
                                backup_info: Dict,
                                dry_run: bool = True,
                                delete_files: bool = False) -> Dict:
        """カスケード削除を実行"""
        print(f"\n🗑️ カスケード削除実行 {'(DRY RUN)' if dry_run else ''}")
        print("-" * 40)
        
        deletion_summary = {
            'execution_logs_deleted': 0,
            'analyses_deleted': 0,
            'files_deleted': 0,
            'files_size_freed': 0,
            'errors': []
        }
        
        if impact_analysis['execution_logs']['total_found'] == 0:
            print("✅ 削除対象のexecution_logsがありません")
            return deletion_summary
        
        try:
            # 1. 分析結果削除
            if impact_analysis['analyses']['total_affected'] > 0:
                if dry_run:
                    print(f"🔍 [DRY RUN] 分析結果削除予定: {impact_analysis['analyses']['total_affected']}件")
                else:
                    with sqlite3.connect(self.analysis_db_path) as analysis_conn:
                        found_ids = [record['execution_id'] for record in impact_analysis['execution_logs']['records']]
                        placeholders = ','.join(['?' for _ in found_ids])
                        
                        cursor = analysis_conn.execute(f"""
                            DELETE FROM analyses WHERE execution_id IN ({placeholders})
                        """, found_ids)
                        
                        deletion_summary['analyses_deleted'] = cursor.rowcount
                        analysis_conn.commit()
                        print(f"✅ 分析結果削除: {deletion_summary['analyses_deleted']}件")
            
            # 2. 関連ファイル削除
            if delete_files and impact_analysis['file_artifacts']['total_size'] > 0:
                all_files = (impact_analysis['file_artifacts']['chart_files'] + 
                            impact_analysis['file_artifacts']['compressed_files'])
                
                if dry_run:
                    size_mb = impact_analysis['file_artifacts']['total_size'] / (1024 * 1024)
                    print(f"🔍 [DRY RUN] ファイル削除予定: {len(all_files)}件 ({size_mb:.1f}MB)")
                else:
                    deleted_files = 0
                    deleted_size = 0
                    
                    for file_path in all_files:
                        try:
                            path = Path(file_path)
                            if path.exists():
                                file_size = path.stat().st_size
                                path.unlink()
                                deleted_files += 1
                                deleted_size += file_size
                        except Exception as e:
                            deletion_summary['errors'].append(f"ファイル削除エラー {file_path}: {e}")
                    
                    deletion_summary['files_deleted'] = deleted_files
                    deletion_summary['files_size_freed'] = deleted_size
                    size_mb = deleted_size / (1024 * 1024)
                    print(f"✅ ファイル削除: {deleted_files}件 ({size_mb:.1f}MB)")
            
            # 3. 実行ログ削除（最後に実行）
            if dry_run:
                print(f"🔍 [DRY RUN] 実行ログ削除予定: {impact_analysis['execution_logs']['total_found']}件")
            else:
                with sqlite3.connect(self.execution_db_path) as exec_conn:
                    found_ids = [record['execution_id'] for record in impact_analysis['execution_logs']['records']]
                    placeholders = ','.join(['?' for _ in found_ids])
                    
                    cursor = exec_conn.execute(f"""
                        DELETE FROM execution_logs WHERE execution_id IN ({placeholders})
                    """, found_ids)
                    
                    deletion_summary['execution_logs_deleted'] = cursor.rowcount
                    exec_conn.commit()
                    print(f"✅ 実行ログ削除: {deletion_summary['execution_logs_deleted']}件")
                    
                    # VACUUM でデータベース最適化
                    print("🔧 データベース最適化中...")
                    exec_conn.execute("VACUUM")
                    print("✅ データベース最適化完了")
        
        except Exception as e:
            deletion_summary['errors'].append(str(e))
            print(f"❌ カスケード削除エラー: {e}")
        
        return deletion_summary
    
    def safe_cascade_delete(self, execution_ids: List[str], 
                          dry_run: bool = True,
                          delete_files: bool = False,
                          skip_backup: bool = False) -> bool:
        """安全なカスケード削除（全体フロー）"""
        print("🗑️ 安全カスケード削除システム")
        print("=" * 50)
        
        if not execution_ids:
            print("❌ 削除対象のexecution_idが指定されていません")
            return False
        
        try:
            # ステップ1: 影響範囲分析
            print("\n📊 ステップ1: 削除影響範囲分析")
            impact_analysis = self.analyze_deletion_impact(execution_ids)
            
            if impact_analysis['execution_logs']['total_found'] == 0:
                print("⚠️ 指定されたexecution_idは存在しません")
                return False
            
            # ステップ2: バックアップ作成
            if not skip_backup and not dry_run:
                print("\n📁 ステップ2: バックアップ作成")
                backup_info = self.backup_before_deletion(execution_ids)
            else:
                backup_info = {'backup_dir': 'スキップ', 'backups': {}}
            
            # ステップ3: 削除確認
            total_impact = (impact_analysis['execution_logs']['total_found'] + 
                          impact_analysis['analyses']['total_affected'])
            
            print(f"\n🔍 ステップ3: 削除確認")
            print(f"削除対象: execution_logs {impact_analysis['execution_logs']['total_found']}件 + "
                  f"analyses {impact_analysis['analyses']['total_affected']}件 = 計{total_impact}件")
            
            if not dry_run:
                print("⚠️ 実際の削除が実行されます")
            
            # ステップ4: カスケード削除実行
            print(f"\n🗑️ ステップ4: カスケード削除実行")
            deletion_summary = self.execute_cascade_deletion(
                execution_ids, impact_analysis, backup_info, dry_run, delete_files
            )
            
            # ステップ5: 結果レポート
            self._generate_deletion_report(impact_analysis, deletion_summary, backup_info, dry_run)
            
            return len(deletion_summary['errors']) == 0
            
        except Exception as e:
            print(f"❌ カスケード削除エラー: {e}")
            return False
    
    def _generate_deletion_report(self, impact_analysis, deletion_summary, backup_info, dry_run):
        """削除レポートを生成"""
        print(f"\n📋 カスケード削除レポート")
        print("=" * 50)
        
        if dry_run:
            print("🔍 DRY RUN 結果:")
            print(f"  削除予定 execution_logs: {impact_analysis['execution_logs']['total_found']}件")
            print(f"  削除予定 analyses: {impact_analysis['analyses']['total_affected']}件")
            if impact_analysis['file_artifacts']['total_size'] > 0:
                size_mb = impact_analysis['file_artifacts']['total_size'] / (1024 * 1024)
                file_count = (len(impact_analysis['file_artifacts']['chart_files']) + 
                            len(impact_analysis['file_artifacts']['compressed_files']))
                print(f"  削除予定ファイル: {file_count}件 ({size_mb:.1f}MB)")
        else:
            print("実行結果:")
            print(f"  削除済み execution_logs: {deletion_summary['execution_logs_deleted']}件")
            print(f"  削除済み analyses: {deletion_summary['analyses_deleted']}件")
            if deletion_summary['files_deleted'] > 0:
                size_mb = deletion_summary['files_size_freed'] / (1024 * 1024)
                print(f"  削除済みファイル: {deletion_summary['files_deleted']}件 ({size_mb:.1f}MB)")
            
            if backup_info['backup_dir'] != 'スキップ':
                print(f"\nバックアップ:")
                print(f"  場所: {backup_info['backup_dir']}")
        
        if deletion_summary['errors']:
            print(f"\nエラー:")
            for error in deletion_summary['errors']:
                print(f"  ❌ {error}")

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='カスケード削除システム')
    parser.add_argument('execution_ids', nargs='+', 
                       help='削除するexecution_idのリスト')
    parser.add_argument('--dry-run', action='store_true',
                       help='実際の削除を行わず、削除予定のみを表示')
    parser.add_argument('--delete-files', action='store_true',
                       help='関連ファイル（チャート、圧縮データ）も削除')
    parser.add_argument('--skip-backup', action='store_true',
                       help='バックアップをスキップ')
    parser.add_argument('--analysis-only', action='store_true',
                       help='影響範囲分析のみ実行')
    
    args = parser.parse_args()
    
    print("🗑️ カスケード削除システム")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN モード - 実際の削除は行いません")
    
    try:
        cascade_system = CascadeDeletionSystem()
        
        if args.analysis_only:
            print("\n📊 影響範囲分析のみ実行")
            cascade_system.analyze_deletion_impact(args.execution_ids)
            return
        
        success = cascade_system.safe_cascade_delete(
            execution_ids=args.execution_ids,
            dry_run=args.dry_run,
            delete_files=args.delete_files,
            skip_backup=args.skip_backup
        )
        
        if success:
            if args.dry_run:
                print("\n🔍 DRY RUN 完了 - --dry-run フラグを外して実際の削除を実行してください")
            else:
                print("\n✅ カスケード削除が正常に完了しました")
        else:
            print("\n❌ カスケード削除でエラーが発生しました")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()