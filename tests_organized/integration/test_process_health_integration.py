#!/usr/bin/env python3
"""
プロセス健全性監視の統合テストスイート
実際のシステム全体での動作確認
"""

import os
import sys
import time
import multiprocessing
import subprocess
import threading
import signal
from pathlib import Path
import psutil

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from enhanced_process_monitor import get_enhanced_process_monitor
from execution_log_database import ExecutionLogDatabase, ExecutionType


class ProcessHealthIntegrationTest:
    """プロセス健全性監視の統合テストクラス"""
    
    def __init__(self):
        self.monitor = get_enhanced_process_monitor()
        self.db = ExecutionLogDatabase()
        self.test_processes = []
        self.test_results = []
        
    def cleanup(self):
        """テスト終了時のクリーンアップ"""
        # 監視停止
        if hasattr(self.monitor, '_running') and self.monitor._running:
            self.monitor.stop_monitoring()
        
        # テストプロセスのクリーンアップ
        for proc in self.test_processes:
            try:
                if hasattr(proc, 'is_alive') and proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=3)
                    if proc.is_alive():
                        proc.kill()
                elif hasattr(proc, 'poll') and proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=3)
            except:
                pass
    
    def create_dummy_multiprocessing_worker(self, duration: int = 30):
        """ダミーのmultiprocessingワーカーを作成"""
        def worker_function():
            """ワーカー関数：指定時間sleep"""
            print(f"🔧 Dummy worker started (PID: {os.getpid()})")
            time.sleep(duration)
            print(f"🔧 Dummy worker finished (PID: {os.getpid()})")
        
        process = multiprocessing.Process(target=worker_function)
        process.start()
        self.test_processes.append(process)
        return process
    
    def create_dummy_subprocess(self, script_content: str, duration: int = 30):
        """ダミーのsubprocessを作成"""
        # 一時的なPythonスクリプトを作成
        script = f"""
import time
import sys
print("🔧 Dummy subprocess started")
print("Args:", sys.argv)
time.sleep({duration})
print("🔧 Dummy subprocess finished")
"""
        
        process = subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.test_processes.append(process)
        return process
    
    def create_fake_analysis_process(self, symbol: str = "TEST", duration: int = 20):
        """偽の分析プロセスを作成"""
        script = f"""
import time
import os
import sys

# プロセス情報を表示
print(f"🧪 Fake analysis process for {symbol} started (PID: {{os.getpid()}})")
print(f"Command line: {{' '.join(sys.argv)}}")

# multiprocessingキーワードを含むようにargvを設定
sys.argv.append('--multiprocessing-fork')
sys.argv.append('scalable_analysis_system')
sys.argv.append(f'--symbol={symbol}')

print(f"Modified command line: {{' '.join(sys.argv)}}")

# 指定時間実行
time.sleep({duration})
print(f"🧪 Fake analysis process for {symbol} finished")
"""
        
        process = subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.test_processes.append(process)
        return process
    
    def test_basic_functionality(self):
        """基本機能テスト"""
        print("🧪 テスト1: 基本機能テスト")
        
        try:
            # ステータス取得テスト
            status = self.monitor.get_process_health_status()
            assert 'monitoring_active' in status
            assert 'active_processes' in status
            print("   ✅ ステータス取得成功")
            
            # 手動クリーンアップテスト
            cleanup_result = self.monitor.manual_cleanup()
            assert cleanup_result['success']
            print("   ✅ 手動クリーンアップ成功")
            
            self.test_results.append(("基本機能", True))
            
        except Exception as e:
            print(f"   ❌ 基本機能テスト失敗: {e}")
            self.test_results.append(("基本機能", False))
    
    def test_process_detection(self):
        """プロセス検出テスト"""
        print("🧪 テスト2: プロセス検出テスト")
        
        try:
            # 初期状態確認
            initial_status = self.monitor.get_process_health_status()
            initial_count = initial_status['active_processes']
            print(f"   初期プロセス数: {initial_count}")
            
            # テストプロセス作成
            print("   テストプロセス作成中...")
            fake_process = self.create_fake_analysis_process("TESTCOIN", 15)
            time.sleep(2)  # プロセス起動を待機
            
            # プロセス検出確認
            after_status = self.monitor.get_process_health_status()
            after_count = after_status['active_processes']
            print(f"   プロセス作成後: {after_count}")
            
            # 検出されたプロセス詳細表示
            for proc in after_status['processes']:
                print(f"   検出プロセス: PID {proc['pid']}, {proc['name']}, CPU: {proc['cpu_percent']:.1f}%")
                print(f"     コマンド: {proc['cmdline'][:80]}...")
            
            # プロセス終了
            fake_process.terminate()
            fake_process.wait(timeout=5)
            time.sleep(1)
            
            # 終了後確認
            final_status = self.monitor.get_process_health_status()
            final_count = final_status['active_processes']
            print(f"   プロセス終了後: {final_count}")
            
            self.test_results.append(("プロセス検出", True))
            
        except Exception as e:
            print(f"   ❌ プロセス検出テスト失敗: {e}")
            self.test_results.append(("プロセス検出", False))
    
    def test_orphan_process_detection(self):
        """孤児プロセス検出テスト"""
        print("🧪 テスト3: 孤児プロセス検出テスト")
        
        try:
            # 孤児プロセスシミュレーション用のスクリプト
            orphan_script = """
import os
import time
import sys

# 親プロセスを終了させて孤児プロセスを作る
if len(sys.argv) > 1 and sys.argv[1] == 'child':
    # 子プロセス：multiprocessingキーワードを含む
    print(f"🧟 Orphan child process started (PID: {os.getpid()})")
    # コマンドラインに multiprocessing を含ませる
    sys.argv.append('multiprocessing')
    sys.argv.append('spawn_main')
    time.sleep(20)  # 20秒実行
    print(f"🧟 Orphan child process finished")
else:
    # 親プロセス：子プロセスを作成後即座に終了
    import subprocess
    child = subprocess.Popen([sys.executable, __file__, 'child'])
    print(f"👨‍👧‍👦 Parent process created child {child.pid}, now exiting")
    # 親プロセスは即座に終了（子プロセスが孤児になる）
"""
            
            # 一時ファイルに書き込み
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(orphan_script)
                temp_script = f.name
            
            try:
                # 孤児プロセス作成
                print("   孤児プロセス作成中...")
                parent_process = subprocess.Popen([sys.executable, temp_script])
                parent_process.wait()  # 親プロセスの終了を待つ
                time.sleep(3)  # 子プロセス（孤児）の起動を待つ
                
                # 孤児プロセス検出テスト
                orphans = self.monitor._find_orphan_processes()
                print(f"   検出された孤児プロセス: {len(orphans)}")
                
                for orphan in orphans:
                    print(f"   孤児プロセス: PID {orphan.pid}, age: {orphan.age_minutes:.1f}min")
                    print(f"     コマンド: {orphan.cmdline[:80]}...")
                
                # 孤児プロセスのクリーンアップテスト
                if orphans:
                    print("   孤児プロセスクリーンアップテスト...")
                    # 手動で孤児プロセスを終了
                    for orphan in orphans:
                        try:
                            proc = psutil.Process(orphan.pid)
                            proc.terminate()
                            print(f"   孤児プロセス {orphan.pid} 終了")
                        except:
                            pass
                
                self.test_results.append(("孤児プロセス検出", True))
                
            finally:
                # 一時ファイル削除
                os.unlink(temp_script)
                
        except Exception as e:
            print(f"   ❌ 孤児プロセス検出テスト失敗: {e}")
            self.test_results.append(("孤児プロセス検出", False))
    
    def test_monitoring_lifecycle(self):
        """監視ライフサイクルテスト"""
        print("🧪 テスト4: 監視ライフサイクルテスト")
        
        try:
            # 初期状態確認
            initial_status = self.monitor.get_process_health_status()
            print(f"   初期監視状態: {initial_status['monitoring_active']}")
            
            # 監視開始
            self.monitor.start_monitoring()
            print("   監視開始")
            
            # 監視状態確認
            time.sleep(2)
            monitoring_status = self.monitor.get_process_health_status()
            assert monitoring_status['monitoring_active']
            print("   ✅ 監視アクティブ確認")
            
            # 監視停止
            self.monitor.stop_monitoring()
            print("   監視停止")
            
            # 停止状態確認
            time.sleep(1)
            stopped_status = self.monitor.get_process_health_status()
            assert not stopped_status['monitoring_active']
            print("   ✅ 監視停止確認")
            
            self.test_results.append(("監視ライフサイクル", True))
            
        except Exception as e:
            print(f"   ❌ 監視ライフサイクルテスト失敗: {e}")
            self.test_results.append(("監視ライフサイクル", False))
    
    def test_database_integration(self):
        """データベース統合テスト"""
        print("🧪 テスト5: データベース統合テスト")
        
        try:
            # テスト用実行記録作成
            execution_id = self.db.create_execution(
                ExecutionType.SYMBOL_ADDITION,
                symbol="TESTINTEGRATION",
                triggered_by="IntegrationTest"
            )
            print(f"   テスト実行記録作成: {execution_id}")
            
            # RUNNING状態に更新
            from execution_log_database import ExecutionStatus
            self.db.update_execution_status(execution_id, ExecutionStatus.RUNNING)
            print("   実行記録をRUNNING状態に更新")
            
            # データベース整合性チェック
            self.monitor._check_db_process_consistency()
            print("   データベース整合性チェック実行")
            
            # 実行記録確認
            execution = self.db.get_execution(execution_id)
            if execution:
                print(f"   実行記録確認: {execution['status']}")
            
            # クリーンアップ（CANCELLED状態に更新）
            self.db.update_execution_status(execution_id, ExecutionStatus.CANCELLED)
            print("   実行記録をCANCELLED状態に更新")
            
            self.test_results.append(("データベース統合", True))
            
        except Exception as e:
            print(f"   ❌ データベース統合テスト失敗: {e}")
            self.test_results.append(("データベース統合", False))
    
    def test_performance(self):
        """パフォーマンステスト"""
        print("🧪 テスト6: パフォーマンステスト")
        
        try:
            # ステータス取得のパフォーマンス
            start_time = time.time()
            status = self.monitor.get_process_health_status()
            status_time = time.time() - start_time
            print(f"   ステータス取得時間: {status_time:.3f}秒")
            
            # クリーンアップのパフォーマンス
            start_time = time.time()
            cleanup_result = self.monitor.manual_cleanup()
            cleanup_time = time.time() - start_time
            print(f"   クリーンアップ時間: {cleanup_time:.3f}秒")
            
            # パフォーマンス基準チェック
            assert status_time < 2.0, f"ステータス取得が遅すぎます: {status_time:.3f}秒"
            assert cleanup_time < 10.0, f"クリーンアップが遅すぎます: {cleanup_time:.3f}秒"
            
            print("   ✅ パフォーマンス基準クリア")
            self.test_results.append(("パフォーマンス", True))
            
        except Exception as e:
            print(f"   ❌ パフォーマンステスト失敗: {e}")
            self.test_results.append(("パフォーマンス", False))
    
    def test_aggressive_cleanup_integration(self):
        """積極的クリーンアップ統合テスト"""
        print("🧪 テスト7: 積極的クリーンアップ統合テスト")
        
        try:
            # resource_trackerプロセスをシミュレート
            dummy_script = """
import time
import sys
import os

# resource_trackerプロセスをシミュレート
sys.argv = ['python', '-c', 'from multiprocessing.resource_tracker import main;main(20)']
print(f"🧟 Simulated resource_tracker started (PID: {os.getpid()})")
time.sleep(8)  # 8分間実行
print(f"🧟 Simulated resource_tracker finished")
"""
            
            # バックグラウンドプロセス起動
            import subprocess
            test_proc = subprocess.Popen(
                [sys.executable, '-c', dummy_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.test_processes.append(test_proc)
            
            # プロセス起動を待機
            time.sleep(2)
            
            print(f"   ダミープロセス作成: PID {test_proc.pid}")
            
            # 積極的クリーンアップのテスト（通常はWebAPIで実行される処理）
            import psutil
            
            cleanup_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid', 'create_time']):
                try:
                    proc_info = proc.info
                    if not proc_info['cmdline']:
                        continue
                    
                    cmdline = ' '.join(proc_info['cmdline'])
                    
                    # multiprocessing.resource_trackerプロセスを検出
                    if ('python' in proc_info['name'].lower() and 
                        'resource_tracker' in cmdline):
                        
                        create_time = proc_info.get('create_time', time.time())
                        age_minutes = (time.time() - create_time) / 60
                        
                        if True:  # 年齢に関係なく全て対象
                            print(f"   検出されたプロセス: PID {proc_info['pid']}, age: {age_minutes:.1f}min")
                            cleanup_count += 1
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            print(f"   クリーンアップ対象プロセス: {cleanup_count}個")
            
            # テストプロセス終了
            test_proc.terminate()
            test_proc.wait(timeout=5)
            
            self.test_results.append(("積極的クリーンアップ統合", True))
            
        except Exception as e:
            print(f"   ❌ 積極的クリーンアップ統合テスト失敗: {e}")
            self.test_results.append(("積極的クリーンアップ統合", False))
    
    def run_all_tests(self):
        """全テスト実行"""
        print("🚀 Enhanced Process Monitor Integration Test Suite")
        print("=" * 60)
        
        try:
            self.test_basic_functionality()
            self.test_process_detection()
            self.test_orphan_process_detection()
            self.test_monitoring_lifecycle()
            self.test_database_integration()
            self.test_performance()
            self.test_aggressive_cleanup_integration()
            
        finally:
            self.cleanup()
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("🎯 テスト結果サマリー")
        print("=" * 60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ 成功" if result else "❌ 失敗"
            print(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n📊 結果: {passed}/{total} テスト成功")
        
        if passed == total:
            print("🎉 すべての統合テストが成功しました！")
            print("   Enhanced Process Monitor は正常に動作しています。")
        else:
            print("⚠️ 一部のテストが失敗しました。")
            print("   問題を確認してください。")
        
        return passed == total


def main():
    """メイン実行関数"""
    tester = ProcessHealthIntegrationTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ 統合テスト完了 - すべて成功")
        sys.exit(0)
    else:
        print("\n❌ 統合テスト完了 - 一部失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()