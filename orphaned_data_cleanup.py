#!/usr/bin/env python3
"""
孤立分析結果クリーンアップスクリプト
データベース間の参照整合性を修復し、不要データを安全に削除
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
import argparse

class OrphanedDataCleanup:
    """孤立データクリーンアップクラス"""
    
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
        backup_dir = Path(f"backups/orphaned_cleanup_{timestamp}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backups = {}
        
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
            'original_analysis_size': self.analysis_db_path.stat().st_size if self.analysis_db_path.exists() else 0
        }
        
        info_file = backup_dir / "backup_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        return backup_info
    
    def analyze_orphaned_data(self):
        """孤立データを分析"""
        print("📊 孤立データ分析")
        print("-" * 40)
        
        analysis = {
            'total_analyses': 0,
            'null_execution_id': 0,
            'empty_execution_id': 0,
            'invalid_execution_id': 0,
            'valid_execution_id': 0,
            'orphaned_records': [],
            'old_records': [],
            'valid_execution_ids': set(),
            'size_info': {
                'analysis_db_size': 0,
                'potential_savings': 0
            }
        }
        
        # analysis.db のサイズ情報
        analysis['size_info']['analysis_db_size'] = self.analysis_db_path.stat().st_size
        
        # 有効なexecution_idのリストを取得
        with sqlite3.connect(self.execution_db_path) as exec_conn:
            cursor = exec_conn.execute("SELECT execution_id FROM execution_logs")
            analysis['valid_execution_ids'] = {row[0] for row in cursor.fetchall()}
        
        # analyses の詳細分析
        with sqlite3.connect(self.analysis_db_path) as analysis_conn:
            # 総数
            cursor = analysis_conn.execute("SELECT COUNT(*) FROM analyses")
            analysis['total_analyses'] = cursor.fetchone()[0]
            
            if analysis['total_analyses'] == 0:
                print("📈 分析結果: 0件（クリーンアップ対象なし）")
                return analysis
            
            # NULL execution_id
            cursor = analysis_conn.execute("SELECT COUNT(*) FROM analyses WHERE execution_id IS NULL")
            analysis['null_execution_id'] = cursor.fetchone()[0]
            
            # 空文字 execution_id
            cursor = analysis_conn.execute("SELECT COUNT(*) FROM analyses WHERE execution_id = ''")
            analysis['empty_execution_id'] = cursor.fetchone()[0]
            
            # 無効 execution_id (存在しないもの)
            cursor = analysis_conn.execute("""
                SELECT id, symbol, timeframe, config, execution_id, generated_at
                FROM analyses 
                WHERE execution_id IS NOT NULL AND execution_id != ''
            """)
            
            all_records = cursor.fetchall()
            for record in all_records:
                execution_id = record[4]
                if execution_id not in analysis['valid_execution_ids']:
                    analysis['orphaned_records'].append({
                        'id': record[0],
                        'symbol': record[1],
                        'timeframe': record[2],
                        'config': record[3],
                        'execution_id': execution_id,
                        'generated_at': record[5]
                    })
                    analysis['invalid_execution_id'] += 1
                else:
                    analysis['valid_execution_id'] += 1
            
            # 古いレコード（30日以上前でexecution_idがNULL）の検出
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            cursor = analysis_conn.execute("""
                SELECT id, symbol, timeframe, config, generated_at
                FROM analyses 
                WHERE execution_id IS NULL 
                AND generated_at < ?
                ORDER BY generated_at
            """, (cutoff_date,))
            
            analysis['old_records'] = [
                {
                    'id': row[0],
                    'symbol': row[1],
                    'timeframe': row[2],
                    'config': row[3],
                    'generated_at': row[4]
                }
                for row in cursor.fetchall()
            ]
        
        # 潜在的な容量節約計算
        total_orphaned = analysis['null_execution_id'] + analysis['empty_execution_id'] + analysis['invalid_execution_id']
        if analysis['total_analyses'] > 0:
            savings_ratio = total_orphaned / analysis['total_analyses']
            analysis['size_info']['potential_savings'] = int(analysis['size_info']['analysis_db_size'] * savings_ratio)
        
        # 結果表示
        print(f"📈 総分析結果: {analysis['total_analyses']}件")
        print(f"   - 有効データ: {analysis['valid_execution_id']}件")
        print(f"   - NULL execution_id: {analysis['null_execution_id']}件")
        print(f"   - 空文字 execution_id: {analysis['empty_execution_id']}件")
        print(f"   - 無効 execution_id: {analysis['invalid_execution_id']}件")
        print(f"   - 古い孤立データ(30日以上): {len(analysis['old_records'])}件")
        
        print(f"\n💾 データベースサイズ: {analysis['size_info']['analysis_db_size']:,} bytes")
        if analysis['size_info']['potential_savings'] > 0:
            print(f"💾 潜在的節約容量: {analysis['size_info']['potential_savings']:,} bytes")
        
        if analysis['orphaned_records']:
            print(f"\n⚠️ 無効execution_idを持つレコード（最初の5件）:")
            for record in analysis['orphaned_records'][:5]:
                print(f"   ID:{record['id']} {record['symbol']}-{record['timeframe']}-{record['config']} -> {record['execution_id']}")
            if len(analysis['orphaned_records']) > 5:
                print(f"   ... 他 {len(analysis['orphaned_records']) - 5}件")
        
        if analysis['old_records']:
            print(f"\n📅 古い孤立レコード（最初の5件）:")
            for record in analysis['old_records'][:5]:
                print(f"   ID:{record['id']} {record['symbol']}-{record['timeframe']}-{record['config']} at {record['generated_at']}")
            if len(analysis['old_records']) > 5:
                print(f"   ... 他 {len(analysis['old_records']) - 5}件")
        
        return analysis
    
    def create_cleanup_plan(self, analysis_result):
        """クリーンアップ計画を作成"""
        print(f"\n🗑️ クリーンアップ計画")
        print("-" * 40)
        
        plan = {
            'null_execution_id': analysis_result['null_execution_id'],
            'empty_execution_id': analysis_result['empty_execution_id'],
            'invalid_execution_id': analysis_result['invalid_execution_id'],
            'old_records': len(analysis_result['old_records']),
            'total_to_delete': 0,
            'deletion_strategy': []
        }
        
        plan['total_to_delete'] = (
            plan['null_execution_id'] + 
            plan['empty_execution_id'] + 
            plan['invalid_execution_id']
        )
        
        if plan['null_execution_id'] > 0:
            plan['deletion_strategy'].append(f"1. NULL execution_id レコード削除: {plan['null_execution_id']}件")
        
        if plan['empty_execution_id'] > 0:
            plan['deletion_strategy'].append(f"2. 空文字 execution_id レコード削除: {plan['empty_execution_id']}件")
        
        if plan['invalid_execution_id'] > 0:
            plan['deletion_strategy'].append(f"3. 無効 execution_id レコード削除: {plan['invalid_execution_id']}件")
        
        if plan['total_to_delete'] > 0:
            print("削除予定:")
            for strategy in plan['deletion_strategy']:
                print(f"   {strategy}")
            print(f"\n📊 総削除予定: {plan['total_to_delete']}件")
        else:
            print("✅ 削除対象のレコードはありません")
        
        return plan
    
    def execute_cleanup(self, analysis_result, dry_run=True):
        """クリーンアップを実行"""
        print(f"\n🧹 クリーンアップ実行 {'(DRY RUN)' if dry_run else ''}")
        print("-" * 40)
        
        cleanup_summary = {
            'deleted_null': 0,
            'deleted_empty': 0,
            'deleted_invalid': 0,
            'total_deleted': 0,
            'errors': []
        }
        
        if analysis_result['total_analyses'] == 0:
            print("✅ クリーンアップ対象データがありません")
            return cleanup_summary
        
        try:
            with sqlite3.connect(self.analysis_db_path) as conn:
                if not dry_run:
                    conn.execute("BEGIN TRANSACTION")
                
                # 1. NULL execution_id の削除
                if analysis_result['null_execution_id'] > 0:
                    if dry_run:
                        print(f"🔍 [DRY RUN] NULL execution_id レコード削除予定: {analysis_result['null_execution_id']}件")
                    else:
                        cursor = conn.execute("DELETE FROM analyses WHERE execution_id IS NULL")
                        cleanup_summary['deleted_null'] = cursor.rowcount
                        print(f"✅ NULL execution_id レコード削除: {cleanup_summary['deleted_null']}件")
                
                # 2. 空文字 execution_id の削除
                if analysis_result['empty_execution_id'] > 0:
                    if dry_run:
                        print(f"🔍 [DRY RUN] 空文字 execution_id レコード削除予定: {analysis_result['empty_execution_id']}件")
                    else:
                        cursor = conn.execute("DELETE FROM analyses WHERE execution_id = ''")
                        cleanup_summary['deleted_empty'] = cursor.rowcount
                        print(f"✅ 空文字 execution_id レコード削除: {cleanup_summary['deleted_empty']}件")
                
                # 3. 無効 execution_id の削除
                if analysis_result['invalid_execution_id'] > 0:
                    invalid_ids = [record['execution_id'] for record in analysis_result['orphaned_records']]
                    if dry_run:
                        print(f"🔍 [DRY RUN] 無効 execution_id レコード削除予定: {len(invalid_ids)}件")
                        for i, invalid_id in enumerate(invalid_ids[:5]):
                            print(f"   {i+1}. {invalid_id}")
                        if len(invalid_ids) > 5:
                            print(f"   ... 他 {len(invalid_ids) - 5}件")
                    else:
                        for invalid_id in invalid_ids:
                            cursor = conn.execute("DELETE FROM analyses WHERE execution_id = ?", (invalid_id,))
                            cleanup_summary['deleted_invalid'] += cursor.rowcount
                        print(f"✅ 無効 execution_id レコード削除: {cleanup_summary['deleted_invalid']}件")
                
                if not dry_run:
                    conn.execute("COMMIT")
                    
                    # VACUUM でデータベースサイズを最適化
                    print("🔧 データベース最適化中...")
                    conn.execute("VACUUM")
                    print("✅ データベース最適化完了")
                
                cleanup_summary['total_deleted'] = (
                    cleanup_summary['deleted_null'] + 
                    cleanup_summary['deleted_empty'] + 
                    cleanup_summary['deleted_invalid']
                )
                
        except Exception as e:
            cleanup_summary['errors'].append(str(e))
            print(f"❌ クリーンアップエラー: {e}")
            if not dry_run:
                try:
                    conn.execute("ROLLBACK")
                    print("🔄 ロールバック実行")
                except:
                    pass
        
        return cleanup_summary
    
    def generate_cleanup_report(self, analysis_result, cleanup_summary, backup_info):
        """クリーンアップレポートを生成"""
        print(f"\n📋 クリーンアップレポート")
        print("=" * 50)
        
        # 実行前の状況
        print("実行前の状況:")
        print(f"  総レコード数: {analysis_result['total_analyses']}")
        print(f"  データベースサイズ: {analysis_result['size_info']['analysis_db_size']:,} bytes")
        
        # クリーンアップ結果
        print("\nクリーンアップ結果:")
        if cleanup_summary['total_deleted'] > 0:
            print(f"  削除レコード数: {cleanup_summary['total_deleted']}")
            if cleanup_summary['deleted_null'] > 0:
                print(f"    - NULL execution_id: {cleanup_summary['deleted_null']}件")
            if cleanup_summary['deleted_empty'] > 0:
                print(f"    - 空文字 execution_id: {cleanup_summary['deleted_empty']}件")
            if cleanup_summary['deleted_invalid'] > 0:
                print(f"    - 無効 execution_id: {cleanup_summary['deleted_invalid']}件")
        else:
            print("  削除レコード数: 0")
        
        # 実行後の状況
        if cleanup_summary['total_deleted'] > 0:
            remaining_records = analysis_result['total_analyses'] - cleanup_summary['total_deleted']
            print(f"\n実行後の状況:")
            print(f"  残存レコード数: {remaining_records}")
            
            # サイズ削減効果
            if self.analysis_db_path.exists():
                new_size = self.analysis_db_path.stat().st_size
                size_reduction = analysis_result['size_info']['analysis_db_size'] - new_size
                if size_reduction > 0:
                    print(f"  新データベースサイズ: {new_size:,} bytes")
                    print(f"  削減サイズ: {size_reduction:,} bytes ({size_reduction/analysis_result['size_info']['analysis_db_size']*100:.1f}%)")
        
        # エラー情報
        if cleanup_summary['errors']:
            print(f"\n⚠️ エラー:")
            for error in cleanup_summary['errors']:
                print(f"    {error}")
        
        # バックアップ情報
        print(f"\n📁 バックアップ:")
        print(f"  場所: {backup_info['backup_dir']}")
        print(f"  バックアップファイル: {backup_info['backups']['analysis']}")
        
        # レポートファイル作成
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'analysis_before': analysis_result,
            'cleanup_summary': cleanup_summary,
            'backup_info': backup_info
        }
        
        report_file = Path(backup_info['backup_dir']) / "cleanup_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"  レポートファイル: {report_file}")

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='孤立分析結果クリーンアップスクリプト')
    parser.add_argument('--dry-run', action='store_true',
                       help='実際の削除を行わず、削除予定のみを表示')
    parser.add_argument('--skip-backup', action='store_true',
                       help='バックアップをスキップ')
    parser.add_argument('--analysis-only', action='store_true',
                       help='分析のみ実行（クリーンアップは行わない）')
    
    args = parser.parse_args()
    
    print("🧹 孤立分析結果クリーンアップスクリプト")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN モード - 実際の削除は行いません")
    
    try:
        # クリーンアップマネージャー初期化
        cleanup = OrphanedDataCleanup()
        
        # ステップ1: バックアップ作成
        if not args.skip_backup and not args.analysis_only:
            print("\n📁 ステップ1: バックアップ作成")
            backup_info = cleanup.backup_databases()
        else:
            backup_info = {'backup_dir': 'スキップ', 'backups': {}}
        
        # ステップ2: 孤立データ分析
        print("\n📊 ステップ2: 孤立データ分析")
        analysis_result = cleanup.analyze_orphaned_data()
        
        # ステップ3: クリーンアップ計画
        print("\n🗑️ ステップ3: クリーンアップ計画作成")
        cleanup_plan = cleanup.create_cleanup_plan(analysis_result)
        
        if args.analysis_only:
            print("\n✅ 分析のみ完了しました")
            return
        
        # ステップ4: クリーンアップ実行
        print("\n🧹 ステップ4: クリーンアップ実行")
        cleanup_summary = cleanup.execute_cleanup(analysis_result, dry_run=args.dry_run)
        
        # ステップ5: レポート生成
        if not args.dry_run:
            print("\n📋 ステップ5: レポート生成")
            cleanup.generate_cleanup_report(analysis_result, cleanup_summary, backup_info)
        
        print("\n" + "=" * 60)
        if args.dry_run:
            print("🔍 DRY RUN 完了 - --dry-run フラグを外して実際のクリーンアップを実行してください")
        elif cleanup_summary['total_deleted'] > 0:
            print("✅ 孤立データクリーンアップ完了！")
            print(f"📊 {cleanup_summary['total_deleted']}件のレコードを削除しました")
            if not args.skip_backup:
                print(f"📁 バックアップ場所: {backup_info['backup_dir']}")
        else:
            print("✅ クリーンアップ対象データはありませんでした")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()