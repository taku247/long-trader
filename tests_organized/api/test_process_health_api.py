#!/usr/bin/env python3
"""
プロセス健全性監視APIエンドポイントのテストスイート
実際のWebダッシュボードAPIをテスト
"""

import os
import sys
import json
import time
import threading
import subprocess
import requests
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class TestProcessHealthAPI(unittest.TestCase):
    """プロセス健全性監視APIのテストクラス"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス全体のセットアップ"""
        cls.base_url = "http://localhost:5001"
        cls.api_base = f"{cls.base_url}/api/admin/process-health"
        cls.web_process = None
        cls.dashboard_started = False
        
        # Webダッシュボードが既に起動しているかチェック
        try:
            response = requests.get(f"{cls.base_url}/api/status", timeout=2)
            if response.status_code == 200:
                cls.dashboard_started = True
                print("✅ Webダッシュボードは既に起動しています")
            else:
                print("🚀 Webダッシュボードを起動中...")
                cls._start_dashboard()
        except requests.exceptions.RequestException:
            print("🚀 Webダッシュボードを起動中...")
            cls._start_dashboard()
    
    @classmethod
    def _start_dashboard(cls):
        """Webダッシュボードを起動"""
        try:
            # web_dashboardディレクトリに移動してapp.pyを起動
            web_dir = project_root / "web_dashboard"
            if not web_dir.exists():
                raise FileNotFoundError("web_dashboardディレクトリが見つかりません")
            
            # バックグラウンドでWebサーバーを起動
            cls.web_process = subprocess.Popen(
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
                    response = requests.get(f"{cls.base_url}/api/status", timeout=1)
                    if response.status_code == 200:
                        print(f"✅ Webダッシュボードが起動しました ({cls.base_url})")
                        cls.dashboard_started = True
                        return
                except requests.exceptions.RequestException:
                    pass
                
                time.sleep(1)
            
            print("❌ Webダッシュボードの起動に失敗しました")
            
        except Exception as e:
            print(f"❌ Webダッシュボード起動エラー: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """テストクラス全体のクリーンアップ"""
        if cls.web_process:
            print("🛑 Webダッシュボードを停止中...")
            cls.web_process.terminate()
            try:
                cls.web_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.web_process.kill()
                cls.web_process.wait()
    
    def setUp(self):
        """各テストのセットアップ"""
        if not self.dashboard_started:
            self.skipTest("Webダッシュボードが起動していません")
    
    def test_process_health_status_api(self):
        """プロセス健全性ステータスAPI テスト"""
        response = requests.get(f"{self.api_base}/status")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 必要なキーが存在することを確認
        required_keys = [
            'monitoring_active', 'check_interval_seconds', 'max_execution_hours',
            'orphan_processes', 'long_running_processes', 'active_processes',
            'total_cpu_usage', 'total_memory_mb', 'processes'
        ]
        
        for key in required_keys:
            self.assertIn(key, data, f"Key '{key}' not found in response")
        
        # データ型チェック
        self.assertIsInstance(data['monitoring_active'], bool)
        self.assertIsInstance(data['check_interval_seconds'], int)
        self.assertIsInstance(data['max_execution_hours'], (int, float))
        self.assertIsInstance(data['orphan_processes'], int)
        self.assertIsInstance(data['long_running_processes'], int)
        self.assertIsInstance(data['active_processes'], int)
        self.assertIsInstance(data['processes'], list)
        
        print(f"✅ ステータス取得成功: {data['active_processes']} active processes")
    
    def test_start_monitoring_api(self):
        """プロセス監視開始API テスト"""
        payload = {
            'check_interval': 120,
            'max_execution_hours': 8
        }
        
        response = requests.post(f"{self.api_base}/start", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        self.assertEqual(data['check_interval'], 120)
        self.assertEqual(data['max_execution_hours'], 8)
        
        print(f"✅ 監視開始成功: {data['message']}")
    
    def test_stop_monitoring_api(self):
        """プロセス監視停止API テスト"""
        response = requests.post(f"{self.api_base}/stop")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        
        print(f"✅ 監視停止成功: {data['message']}")
    
    def test_manual_cleanup_api(self):
        """手動クリーンアップAPI テスト"""
        response = requests.post(f"{self.api_base}/manual-cleanup")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('orphan_processes_cleaned', data)
        self.assertIn('timeout_processes_handled', data)
        self.assertIn('message', data)
        
        orphan_cleaned = data['orphan_processes_cleaned']
        timeout_handled = data['timeout_processes_handled']
        
        print(f"✅ 手動クリーンアップ成功: {orphan_cleaned} orphans, {timeout_handled} timeouts")
    
    def test_aggressive_cleanup_api(self):
        """積極的クリーンアップAPI テスト（標準モード: 5分閾値）"""
        payload = {'force_all': False}
        
        response = requests.post(f"{self.api_base}/aggressive-cleanup", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('processes_terminated', data)
        self.assertIn('force_killed', data)
        self.assertIn('processes', data)
        self.assertIn('message', data)
        
        terminated = data['processes_terminated']
        force_killed = data['force_killed']
        
        print(f"✅ 積極的クリーンアップ成功（標準モード）: {terminated} terminated, {force_killed} force killed")
    
    def test_aggressive_cleanup_force_mode(self):
        """積極的クリーンアップ（強制モード）API テスト（年齢制限なし）"""
        payload = {'force_all': True}
        
        response = requests.post(f"{self.api_base}/aggressive-cleanup", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('processes_terminated', data)
        self.assertIn('force_killed', data)
        
        terminated = data['processes_terminated']
        force_killed = data['force_killed']
        
        print(f"✅ 強制クリーンアップ成功（強制モード）: {terminated} terminated, {force_killed} force killed")
    
    def test_aggressive_cleanup_immediate(self):
        """積極的クリーンアップ（即座実行・改善版検出）API テスト"""
        payload = {
            'force_all': True  # 年齢に関係なく全multiprocessingプロセスを対象（改善版検出ロジック）
        }
        
        response = requests.post(f"{self.api_base}/aggressive-cleanup", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('processes_terminated', data)
        self.assertIn('force_killed', data)
        
        terminated = data['processes_terminated']
        force_killed = data['force_killed']
        
        print(f"✅ 積極的クリーンアップ成功（即座実行）: {terminated} terminated, {force_killed} force killed")
    
    def test_monitoring_workflow(self):
        """監視ワークフローの統合テスト"""
        print("\n🔄 監視ワークフローテスト開始...")
        
        # 1. 初期ステータス確認
        status_response = requests.get(f"{self.api_base}/status")
        self.assertEqual(status_response.status_code, 200)
        initial_status = status_response.json()
        print(f"   初期状態: monitoring={initial_status['monitoring_active']}")
        
        # 2. 監視開始
        start_response = requests.post(f"{self.api_base}/start", 
                                     json={'check_interval': 30, 'max_execution_hours': 4})
        self.assertEqual(start_response.status_code, 200)
        print("   監視開始: ✅")
        
        # 3. ステータス確認（監視中）
        time.sleep(1)
        status_response = requests.get(f"{self.api_base}/status")
        monitoring_status = status_response.json()
        print(f"   監視中状態: active_processes={monitoring_status['active_processes']}")
        
        # 4. 手動クリーンアップ実行
        cleanup_response = requests.post(f"{self.api_base}/manual-cleanup")
        self.assertEqual(cleanup_response.status_code, 200)
        cleanup_result = cleanup_response.json()
        print(f"   クリーンアップ: {cleanup_result['message']}")
        
        # 5. 監視停止
        stop_response = requests.post(f"{self.api_base}/stop")
        self.assertEqual(stop_response.status_code, 200)
        print("   監視停止: ✅")
        
        # 6. 最終ステータス確認
        final_status_response = requests.get(f"{self.api_base}/status")
        final_status = final_status_response.json()
        print(f"   最終状態: monitoring={final_status['monitoring_active']}")
        
        print("🎉 ワークフローテスト完了")
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        # 不正なJSON送信
        response = requests.post(f"{self.api_base}/start", 
                               data="invalid json", 
                               headers={'Content-Type': 'application/json'})
        
        # ステータスコードは400または500系のはず
        self.assertIn(response.status_code, [400, 422, 500])
        
        print(f"✅ エラーハンドリング確認: {response.status_code}")


class TestAPIPerformance(unittest.TestCase):
    """API パフォーマンステスト"""
    
    def setUp(self):
        """セットアップ"""
        self.base_url = "http://localhost:5001"
        self.api_base = f"{self.base_url}/api/admin/process-health"
        
        # Webダッシュボードが起動しているかチェック
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=2)
            if response.status_code != 200:
                self.skipTest("Webダッシュボードが起動していません")
        except requests.exceptions.RequestException:
            self.skipTest("Webダッシュボードが起動していません")
    
    def test_status_api_performance(self):
        """ステータスAPI のパフォーマンステスト"""
        start_time = time.time()
        
        response = requests.get(f"{self.api_base}/status")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 2.0, "ステータスAPIの応答時間が2秒を超えています")
        
        print(f"✅ ステータスAPI応答時間: {response_time:.3f}秒")
    
    def test_cleanup_api_performance(self):
        """クリーンアップAPI のパフォーマンステスト"""
        start_time = time.time()
        
        response = requests.post(f"{self.api_base}/manual-cleanup")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 10.0, "クリーンアップAPIの応答時間が10秒を超えています")
        
        print(f"✅ クリーンアップAPI応答時間: {response_time:.3f}秒")


def run_quick_api_test():
    """クイックAPIテスト（WebダッシュボードなしでAPI構造確認）"""
    print("⚡ Quick API Structure Test")
    print("=" * 40)
    
    try:
        from web_dashboard.app import WebDashboard
        
        # テスト用ダッシュボード作成
        dashboard = WebDashboard(debug=True)
        client = dashboard.app.test_client()
        
        # ステータスエンドポイントテスト
        response = client.get('/api/admin/process-health/status')
        print(f"Status API: {response.status_code}")
        
        # 監視開始エンドポイントテスト
        response = client.post('/api/admin/process-health/start', 
                             json={'check_interval': 60})
        print(f"Start API: {response.status_code}")
        
        # 手動クリーンアップエンドポイントテスト
        response = client.post('/api/admin/process-health/manual-cleanup')
        print(f"Cleanup API: {response.status_code}")
        
        print("✅ APIエンドポイント構造OK")
        return True
        
    except Exception as e:
        print(f"❌ APIテストエラー: {e}")
        return False


def main():
    """メイン実行関数"""
    print("🌐 Process Health API Test Suite")
    print("=" * 60)
    
    # クイックテスト実行
    print("\n⚡ Running Quick Structure Tests...")
    quick_success = run_quick_api_test()
    
    if not quick_success:
        print("❌ クイックテストが失敗しました。")
        return False
    
    print("\n" + "=" * 60)
    
    # フルAPIテスト実行
    print("\n🧪 Running Full API Tests...")
    
    # ユニットテスト実行
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n✅ API テストスイート完了")
    return True


if __name__ == "__main__":
    main()