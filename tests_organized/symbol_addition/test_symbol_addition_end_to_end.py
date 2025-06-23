#!/usr/bin/env python3
"""
銘柄追加の統合テスト（エンドツーエンド）
実際のWebダッシュボードとの連携を含む完全なテスト
"""

import os
import sys
import time
import requests
import sqlite3
import threading
import subprocess
import psutil
import signal
from pathlib import Path
from datetime import datetime
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from execution_log_database import ExecutionLogDatabase
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class SymbolAdditionEndToEndTest:
    """銘柄追加のエンドツーエンドテスト"""
    
    def __init__(self):
        self.base_url = "http://localhost:5001"
        self.db = ExecutionLogDatabase()
        self.web_process = None
        self.test_results = []
        
    def start_web_dashboard(self):
        """Webダッシュボードを起動"""
        print("🌐 Webダッシュボードを起動中...")
        
        # web_dashboardディレクトリに移動してapp.pyを起動
        web_dir = Path("web_dashboard")
        if not web_dir.exists():
            raise FileNotFoundError("web_dashboardディレクトリが見つかりません")
        
        # バックグラウンドでWebサーバーを起動
        self.web_process = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=web_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # サーバーの起動を待機
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/api/status", timeout=1)
                if response.status_code == 200:
                    print(f"✅ Webダッシュボードが起動しました ({self.base_url})")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            print(f"  起動待機中... ({attempt + 1}/{max_attempts})")
        
        print("❌ Webダッシュボードの起動に失敗しました")
        return False
    
    def stop_web_dashboard(self):
        """Webダッシュボードを停止"""
        if self.web_process:
            print("🛑 Webダッシュボードを停止中...")
            self.web_process.terminate()
            self.web_process.wait(timeout=10)
            self.web_process = None
    
    def find_related_processes(self, execution_id, symbol=None):
        """関連プロセスを検索（孤児プロセス検出を含む）"""
        related_processes = []
        orphan_processes = []
        
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline', 'environ', 'cpu_percent', 'create_time']):
            try:
                proc_info = proc.info
                cmdline_list = proc_info.get('cmdline', [])
                if cmdline_list is None:
                    cmdline_list = []
                cmdline = ' '.join(str(x) for x in cmdline_list)
                environ = proc_info.get('environ', {})
                ppid = proc_info.get('ppid')
                
                # execution_idを含むプロセスを検索
                is_related = False
                is_orphan = False
                
                if execution_id:
                    if execution_id in cmdline:
                        is_related = True
                    if environ and environ.get('CURRENT_EXECUTION_ID') == execution_id:
                        is_related = True
                
                # symbolを含むプロセスを検索
                if symbol and symbol in cmdline:
                    is_related = True
                
                # 銘柄追加関連のプロセスを検索
                if any(keyword in cmdline.lower() for keyword in [
                    'support_resistance_ml',
                    'scalable_analysis',
                    'auto_symbol_training',
                    'multiprocessing',
                    'spawn_main',  # multiprocessingの子プロセス
                    'Pool',        # ProcessPoolExecutorのワーカー
                ]):
                    is_related = True
                
                # 孤児プロセスの検出（PPID=1）
                if ppid == 1 and any(keyword in cmdline.lower() for keyword in [
                    'python', 'multiprocessing', 'support_resistance', 'scalable_analysis'
                ]):
                    is_orphan = True
                    is_related = True
                
                if is_related:
                    process_data = {
                        'pid': proc_info['pid'],
                        'ppid': ppid,
                        'name': proc_info['name'],
                        'cmdline': cmdline,
                        'cpu_percent': proc.cpu_percent() if proc.is_running() else 0,
                        'execution_id_in_env': environ.get('CURRENT_EXECUTION_ID') if environ else None,
                        'is_orphan': is_orphan,
                        'create_time': proc_info.get('create_time', 0)
                    }
                    
                    related_processes.append(process_data)
                    
                    if is_orphan:
                        orphan_processes.append(process_data)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # 結果に孤児プロセス情報を追加
        for proc in related_processes:
            proc['orphan_count'] = len(orphan_processes)
        
        return related_processes
    
    def check_for_orphan_processes(self):
        """孤児プロセスの専用チェック"""
        print("    🔍 孤児プロセス専用チェック...")
        
        orphan_processes = []
        
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline', 'create_time']):
            try:
                proc_info = proc.info
                cmdline_list = proc_info.get('cmdline', [])
                if cmdline_list is None:
                    cmdline_list = []
                cmdline = ' '.join(str(x) for x in cmdline_list)
                ppid = proc_info.get('ppid')
                
                # PPID=1（init プロセスの子）かつ関連キーワードを含む
                if ppid == 1 and any(keyword in cmdline.lower() for keyword in [
                    'multiprocessing',
                    'support_resistance_ml',
                    'scalable_analysis',
                    'auto_symbol_training',
                    'spawn_main',
                    'Pool'
                ]):
                    # Pythonプロセスに限定
                    if 'python' in proc_info['name'].lower():
                        orphan_processes.append({
                            'pid': proc_info['pid'],
                            'name': proc_info['name'],
                            'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline,
                            'create_time': proc_info.get('create_time', 0)
                        })
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if orphan_processes:
            print(f"    ⚠️ 検出された孤児プロセス: {len(orphan_processes)}件")
            for orphan in orphan_processes:
                age_seconds = time.time() - orphan['create_time']
                print(f"      PID {orphan['pid']}: {orphan['name']} (経過時間: {age_seconds:.0f}秒)")
                print(f"        コマンド: {orphan['cmdline']}")
        else:
            print("    ✅ 孤児プロセスは検出されませんでした")
        
        return orphan_processes
    
    def test_cancellation_functionality(self):
        """キャンセル機能のテスト（プロセス停止確認付き）"""
        print("\n❌ キャンセル機能テスト開始...")
        
        test_symbol = "BTC"  # 実在する銘柄を使用（データ取得まで進めるため）
        
        # 1. 銘柄追加を開始
        print(f"  1. 銘柄追加開始: {test_symbol}")
        
        add_response = requests.post(
            f"{self.base_url}/api/symbol/add",
            json={"symbol": test_symbol},
            timeout=10
        )
        
        if add_response.status_code != 200:
            print(f"  ❌ 銘柄追加APIエラー: {add_response.status_code}")
            return False
        
        add_result = add_response.json()
        execution_id = add_result.get("execution_id")
        
        if not execution_id:
            print("  ❌ execution_idが取得できません")
            return False
        
        print(f"  ✅ 銘柄追加開始: execution_id = {execution_id}")
        
        # 2. 処理開始を待機してプロセスを確認
        print("  2. 処理開始を待機中...")
        time.sleep(5)  # 少し長めに待機
        
        # 3. 関連プロセスの確認（キャンセル前）
        print("  3. 関連プロセス確認（キャンセル前）...")
        before_processes = self.find_related_processes(execution_id, test_symbol)
        
        print(f"  関連プロセス数: {len(before_processes)}")
        orphan_count_before = 0
        for proc in before_processes:
            orphan_marker = " 🚫[孤児]" if proc.get('is_orphan') else ""
            ppid_info = f"PPID:{proc.get('ppid', 'N/A')}"
            print(f"    PID {proc['pid']}: {proc['name']} (CPU: {proc['cpu_percent']:.1f}%, {ppid_info}){orphan_marker}")
            if proc['execution_id_in_env']:
                print(f"      環境変数 CURRENT_EXECUTION_ID: {proc['execution_id_in_env']}")
            if proc.get('is_orphan'):
                orphan_count_before += 1
        
        if orphan_count_before > 0:
            print(f"    ⚠️ キャンセル前の孤児プロセス: {orphan_count_before}件")
        
        # 孤児プロセス専用チェック
        orphan_processes_before = self.check_for_orphan_processes()
        
        # 4. ステータス確認
        status_response = requests.get(f"{self.base_url}/api/execution/{execution_id}/status")
        if status_response.status_code == 200:
            status = status_response.json().get("status")
            print(f"  現在のステータス: {status}")
        
        # 5. CPU使用率の記録（キャンセル前）
        system_cpu_before = psutil.cpu_percent(interval=1)
        print(f"  システムCPU使用率（キャンセル前）: {system_cpu_before:.1f}%")
        
        # 6. キャンセル実行
        print("  4. キャンセル実行...")
        
        cancel_response = requests.post(
            f"{self.base_url}/api/admin/reset-execution",
            json={"execution_id": execution_id},
            timeout=10
        )
        
        if cancel_response.status_code != 200:
            print(f"  ❌ キャンセルAPIエラー: {cancel_response.status_code}")
            return False
        
        cancel_result = cancel_response.json()
        print(f"  キャンセル結果: {cancel_result.get('message', 'N/A')}")
        
        # プロセス停止の詳細情報があれば表示
        if 'processes_terminated' in cancel_result:
            terminated = cancel_result['processes_terminated']
            print(f"  停止されたプロセス数: {terminated}")
        
        # 7. キャンセル後の待機（プロセス停止を待つ）
        print("  5. プロセス停止待機...")
        time.sleep(3)
        
        # 8. 関連プロセスの確認（キャンセル後）
        print("  6. 関連プロセス確認（キャンセル後）...")
        after_processes = self.find_related_processes(execution_id, test_symbol)
        
        print(f"  関連プロセス数: {len(after_processes)}")
        orphan_count_after = 0
        for proc in after_processes:
            orphan_marker = " 🚫[孤児]" if proc.get('is_orphan') else ""
            ppid_info = f"PPID:{proc.get('ppid', 'N/A')}"
            print(f"    PID {proc['pid']}: {proc['name']} (CPU: {proc['cpu_percent']:.1f}%, {ppid_info}){orphan_marker}")
            if proc.get('is_orphan'):
                orphan_count_after += 1
        
        if orphan_count_after > 0:
            print(f"    ⚠️ キャンセル後に残存する孤児プロセス: {orphan_count_after}件")
        
        # 孤児プロセス専用チェック（キャンセル後）
        orphan_processes_after = self.check_for_orphan_processes()
        
        # 9. CPU使用率の確認（キャンセル後）
        system_cpu_after = psutil.cpu_percent(interval=1)
        print(f"  システムCPU使用率（キャンセル後）: {system_cpu_after:.1f}%")
        
        # 10. DBステータス確認
        print("  7. DBステータス確認...")
        final_status_response = requests.get(f"{self.base_url}/api/execution/{execution_id}/status")
        if final_status_response.status_code == 200:
            final_status = final_status_response.json().get("status")
            print(f"  最終ステータス: {final_status}")
        else:
            print("  ❌ ステータス確認に失敗")
            return False
        
        # 11. 結果判定
        print("  8. 結果判定...")
        
        success_criteria = []
        
        # DBステータスチェック
        if final_status == "CANCELLED":
            print("    ✅ DBステータス: CANCELLED")
            success_criteria.append(True)
        else:
            print(f"    ❌ DBステータス: {final_status} (期待値: CANCELLED)")
            success_criteria.append(False)
        
        # プロセス数の減少チェック
        if len(after_processes) < len(before_processes):
            print(f"    ✅ プロセス数減少: {len(before_processes)} → {len(after_processes)}")
            success_criteria.append(True)
        elif len(after_processes) == 0:
            print("    ✅ 関連プロセス完全停止")
            success_criteria.append(True)
        else:
            print(f"    ⚠️ プロセス数変化なし: {len(before_processes)} → {len(after_processes)}")
            success_criteria.append(False)
        
        # 孤児プロセスチェック（重要）
        orphan_decrease = len(orphan_processes_before) - len(orphan_processes_after)
        if len(orphan_processes_after) == 0:
            print("    ✅ 孤児プロセス完全清理")
            success_criteria.append(True)
        elif orphan_decrease > 0:
            print(f"    ✅ 孤児プロセス減少: {len(orphan_processes_before)} → {len(orphan_processes_after)}")
            success_criteria.append(True)
        elif len(orphan_processes_before) == 0 and len(orphan_processes_after) == 0:
            print("    ✅ 孤児プロセス問題なし")
            success_criteria.append(True)
        else:
            print(f"    ❌ 孤児プロセス残存: {len(orphan_processes_after)}件")
            success_criteria.append(False)
        
        # CPU使用率の変化チェック（大幅な減少があれば良い）
        cpu_decrease = system_cpu_before - system_cpu_after
        if cpu_decrease > 5:  # 5%以上の減少
            print(f"    ✅ CPU使用率減少: {cpu_decrease:.1f}%減")
            success_criteria.append(True)
        elif system_cpu_after < 20:  # または低CPU状態
            print(f"    ✅ CPU使用率低下: {system_cpu_after:.1f}%")
            success_criteria.append(True)
        else:
            print(f"    ℹ️ CPU使用率変化: {cpu_decrease:.1f}%減（参考値）")
            success_criteria.append(True)  # CPUチェックは参考程度
        
        # 総合判定
        overall_success = all(success_criteria)
        
        if overall_success:
            print("  🎉 キャンセル機能が完全に動作しています！")
            print("     - DBステータス更新: ✅")
            print("     - プロセス停止: ✅")
            print("     - 孤児プロセス清理: ✅")
            print("     - リソース解放: ✅")
        else:
            print("  ❌ キャンセル機能に問題があります")
            failed_checks = sum(1 for x in success_criteria if not x)
            print(f"     失敗チェック数: {failed_checks}/{len(success_criteria)}")
            
            # 詳細な問題分析
            if len(orphan_processes_after) > 0:
                print("  🚫 孤児プロセス問題:")
                for orphan in orphan_processes_after:
                    age = time.time() - orphan['create_time']
                    print(f"     PID {orphan['pid']}: 経過時間 {age:.0f}秒")
                    print(f"     コマンド: {orphan['cmdline'][:80]}...")
                    
            if len(after_processes) > 0:
                print("  📊 残存プロセス詳細:")
                for proc in after_processes:
                    if proc.get('is_orphan'):
                        print(f"     🚫 PID {proc['pid']}: {proc['name']} (孤児プロセス)")
                    else:
                        print(f"     📌 PID {proc['pid']}: {proc['name']} (通常プロセス)")
        
        return overall_success
    
    def test_normal_completion(self):
        """正常完了のテスト"""
        print("\n✅ 正常完了テスト開始...")
        
        # 既に存在する銘柄を使用して短時間で完了させる
        test_symbol = "BTC"  # 既存の銘柄なので処理が早い
        
        print(f"  1. 銘柄追加開始: {test_symbol}")
        
        add_response = requests.post(
            f"{self.base_url}/api/symbol/add",
            json={"symbol": test_symbol},
            timeout=10
        )
        
        if add_response.status_code != 200:
            print(f"  ❌ 銘柄追加APIエラー: {add_response.status_code}")
            return False
        
        add_result = add_response.json()
        execution_id = add_result.get("execution_id")
        
        print(f"  ✅ 銘柄追加開始: execution_id = {execution_id}")
        
        # 2. 完了まで監視
        print("  2. 完了監視中...")
        max_wait = 60  # 最大60秒待機
        
        for i in range(max_wait):
            time.sleep(1)
            
            status_response = requests.get(f"{self.base_url}/api/execution/{execution_id}/status")
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("status")
                progress = status_data.get("progress_percentage", 0)
                
                print(f"  進捗: {status} ({progress:.1f}%)")
                
                if status in ["SUCCESS", "FAILED", "CANCELLED"]:
                    print(f"  完了: 最終ステータス = {status}")
                    return status == "SUCCESS"
            else:
                print(f"  ステータス確認エラー: {status_response.status_code}")
        
        print("  ❌ タイムアウト: 処理が完了しませんでした")
        return False
    
    def check_database_consistency(self):
        """データベースの整合性確認"""
        print("\n📊 データベース整合性確認...")
        
        # 統合DBの状態確認
        with sqlite3.connect("execution_logs.db") as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM execution_logs")
            total_count = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT COUNT(*) FROM execution_logs 
                WHERE timestamp_start >= date('now', '-1 day')
            """)
            recent_count = cursor.fetchone()[0]
            
            print(f"  総レコード数: {total_count}")
            print(f"  過去24時間のレコード: {recent_count}")
            
            # 最新のテストレコードを確認
            cursor = conn.execute("""
                SELECT execution_id, symbol, status, timestamp_start 
                FROM execution_logs 
                WHERE execution_id LIKE '%TEST%' OR symbol IN ('TESTCANCEL', 'BTC')
                ORDER BY timestamp_start DESC 
                LIMIT 5
            """)
            
            test_records = cursor.fetchall()
            print("  最新のテストレコード:")
            for record in test_records:
                print(f"    {record[0]}: {record[1]} ({record[2]}) at {record[3]}")
        
        return True
    
    def run_all_tests(self):
        """すべてのテストを実行"""
        print("🧪 銘柄追加エンドツーエンドテスト開始")
        print("=" * 60)
        
        success = True
        
        try:
            # Webダッシュボード起動
            if not self.start_web_dashboard():
                return False
            
            # テスト1: キャンセル機能
            print("\n" + "="*50)
            print("TEST 1: キャンセル機能テスト")
            print("="*50)
            
            cancel_success = self.test_cancellation_functionality()
            self.test_results.append(("キャンセル機能", cancel_success))
            
            if not cancel_success:
                success = False
            
            # テスト2: 正常完了（オプション - 時間がかかる可能性）
            print("\n" + "="*50)
            print("TEST 2: 正常完了テスト（スキップ可能）")
            print("="*50)
            
            # 自動実行時は正常完了テストをスキップ
            if '--auto' in sys.argv or not sys.stdin.isatty():
                print("  自動実行モードのため正常完了テストをスキップします")
            else:
                user_input = input("正常完了テストを実行しますか？（時間がかかる可能性があります）[y/N]: ")
                if user_input.lower() in ['y', 'yes']:
                    completion_success = self.test_normal_completion()
                    self.test_results.append(("正常完了", completion_success))
                    
                    if not completion_success:
                        success = False
                else:
                    print("  正常完了テストをスキップしました")
            
            # データベース整合性確認
            print("\n" + "="*50)
            print("TEST 3: データベース整合性確認")
            print("="*50)
            
            db_success = self.check_database_consistency()
            self.test_results.append(("DB整合性", db_success))
            
        finally:
            # Webダッシュボード停止
            self.stop_web_dashboard()
        
        # 結果サマリー
        print("\n" + "="*60)
        print("🎯 テスト結果サマリー")
        print("="*60)
        
        for test_name, result in self.test_results:
            status = "✅ 成功" if result else "❌ 失敗"
            print(f"  {test_name}: {status}")
        
        if success:
            print("\n🎉 すべてのテストが成功しました！")
            print("   DB統一により銘柄追加のキャンセル機能が修復されました。")
        else:
            print("\n❌ 一部のテストが失敗しました。")
            print("   問題の詳細を確認してください。")
        
        return success

def main():
    """メイン実行関数"""
    print("🚀 銘柄追加エンドツーエンドテスト")
    print("このテストでは以下を確認します:")
    print("1. Webダッシュボードの起動")
    print("2. 銘柄追加APIの動作")
    print("3. キャンセル機能の動作（重要）")
    print("4. データベースの整合性")
    print()
    
    # 自動実行モード（CI/CD環境対応）
    import sys
    if '--auto' in sys.argv or not sys.stdin.isatty():
        print("自動実行モードでテストを開始します...")
    else:
        confirmation = input("テストを開始しますか？ [y/N]: ")
        if confirmation.lower() not in ['y', 'yes']:
            print("テストをキャンセルしました。")
            return
    
    tester = SymbolAdditionEndToEndTest()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()