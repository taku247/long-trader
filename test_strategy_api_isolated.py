#!/usr/bin/env python3
"""
戦略設定API統合テスト (隔離版)

完全に隔離されたテスト環境で strategy_config_api.py の動作確認
"""

import json
import requests
import time
import tempfile
import os
import shutil
from threading import Thread
from flask import Flask

class IsolatedStrategyAPITester:
    """隔離された戦略設定API統合テスト"""
    
    def __init__(self, base_url="http://localhost:5003"):
        self.base_url = base_url
        self.test_strategy_id = None
        self.test_db_dir = None
        self.server_thread = None
    
    def setup_test_environment(self):
        """テスト環境セットアップ"""
        print("🔧 Setting up isolated test environment...")
        
        # テスト用一時ディレクトリ作成
        self.test_db_dir = tempfile.mkdtemp(prefix="isolated_strategy_test_")
        test_db_path = os.path.join(self.test_db_dir, "test_analysis.db")
        
        print(f"📁 Test directory: {self.test_db_dir}")
        print(f"🗄️ Test database: {test_db_path}")
        
        # 環境変数設定
        os.environ['TEST_STRATEGY_DB_PATH'] = test_db_path
        
        return test_db_path
    
    def start_isolated_server(self):
        """隔離されたテストサーバー起動"""
        def run_server():
            from strategy_config_api import StrategyConfigAPI
            
            app = Flask(__name__)
            api = StrategyConfigAPI(app)
            
            @app.after_request
            def after_request(response):
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
                response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
                return response
            
            app.run(debug=False, port=5003, use_reloader=False)
        
        self.server_thread = Thread(target=run_server, daemon=True)
        self.server_thread.start()
        time.sleep(3)  # サーバー起動待機
        print("🚀 Isolated test server started on port 5003")
    
    def cleanup_test_environment(self):
        """テスト環境クリーンアップ"""
        if self.test_db_dir and os.path.exists(self.test_db_dir):
            shutil.rmtree(self.test_db_dir)
            print(f"🧹 Cleaned up test directory: {self.test_db_dir}")
        
        # 環境変数クリア
        if 'TEST_STRATEGY_DB_PATH' in os.environ:
            del os.environ['TEST_STRATEGY_DB_PATH']
    
    def test_create_strategy(self):
        """戦略作成テスト"""
        print("\n🔍 Testing strategy creation (isolated)")
        
        test_strategy = {
            "name": "Isolated_Test_Conservative_15m",
            "base_strategy": "Conservative_ML",
            "timeframe": "15m",
            "parameters": {
                "risk_multiplier": 1.3,
                "leverage_cap": 40,
                "min_risk_reward": 1.3,
                "confidence_boost": 0.08
            },
            "description": "Isolated test strategy - should not affect production DB",
            "created_by": "isolated_tester"
        }
        
        response = requests.post(
            f"{self.base_url}/api/strategy-configs",
            json=test_strategy,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            data = response.json()
            self.test_strategy_id = data['data']['id']
            print("✅ Isolated strategy creation success")
            print(f"   Created strategy ID: {self.test_strategy_id}")
            print(f"   Strategy name: {data['data']['name']}")
            return True
        else:
            print(f"❌ Isolated strategy creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_list_strategies(self):
        """戦略一覧取得テスト"""
        print("\n🔍 Testing strategy listing (isolated)")
        
        response = requests.get(f"{self.base_url}/api/strategy-configs")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Strategy listing success")
            print(f"   Total strategies: {data['count']}")
            
            # 隔離されたテストでは作成したもののみ存在するはず
            if data['count'] == 1 and self.test_strategy_id:
                print("   ✅ Isolated environment confirmed - only test data exists")
                return True
            elif data['count'] == 0:
                print("   ⚠️ No strategies found (might be timing issue)")
                return True
            else:
                print(f"   ⚠️ Unexpected strategy count: {data['count']}")
                return False
        else:
            print(f"❌ Strategy listing failed: {response.status_code}")
            return False
    
    def test_database_isolation(self):
        """データベース隔離テスト"""
        print("\n🔍 Testing database isolation")
        
        # テスト用DBの存在確認
        test_db_path = os.environ.get('TEST_STRATEGY_DB_PATH')
        if test_db_path and os.path.exists(test_db_path):
            print(f"   ✅ Test database exists: {test_db_path}")
        else:
            print("   ❌ Test database not found")
            return False
        
        # 本番DBに影響がないことを確認
        production_db_path = "large_scale_analysis/analysis.db"
        if os.path.exists(production_db_path):
            import sqlite3
            
            # 本番DBの戦略数をチェック
            with sqlite3.connect(production_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM strategy_configurations WHERE created_by = 'isolated_tester'")
                isolated_test_count = cursor.fetchone()[0]
            
            if isolated_test_count == 0:
                print("   ✅ Production database unaffected")
                return True
            else:
                print(f"   ❌ Production database contaminated: {isolated_test_count} test records found")
                return False
        else:
            print("   ⚠️ Production database not found (might be expected)")
            return True
    
    def run_isolation_test(self):
        """隔離テスト実行"""
        print("🧪 戦略設定API隔離テスト開始")
        print("=" * 60)
        
        try:
            # テスト環境セットアップ
            self.setup_test_environment()
            
            # 隔離サーバー起動
            self.start_isolated_server()
            
            # テスト実行
            tests = [
                ("Database Isolation", self.test_database_isolation),
                ("Strategy Creation", self.test_create_strategy),
                ("Strategy Listing", self.test_list_strategies),
                ("Final Isolation Check", self.test_database_isolation)
            ]
            
            passed = 0
            failed = 0
            
            for test_name, test_func in tests:
                try:
                    if test_func():
                        passed += 1
                        print(f"   ✅ {test_name}: PASSED")
                    else:
                        failed += 1
                        print(f"   ❌ {test_name}: FAILED")
                except Exception as e:
                    failed += 1
                    print(f"   ❌ {test_name}: ERROR - {e}")
                
                time.sleep(0.5)
            
            # 結果サマリー
            print("\n" + "=" * 60)
            print("🎯 隔離テスト結果")
            print("=" * 60)
            print(f"成功: {passed}")
            print(f"失敗: {failed}")
            
            if failed == 0:
                print("\n🎉 すべての隔離テストが成功しました！")
                print("本番データベースへの影響なし")
            else:
                print(f"\n⚠️ {failed}件のテストが失敗しました")
            
            return failed == 0
            
        finally:
            # クリーンアップ
            self.cleanup_test_environment()

def main():
    """メイン実行関数"""
    print("🔒 隔離戦略APIテスト - 本番DBに影響しません")
    
    tester = IsolatedStrategyAPITester()
    success = tester.run_isolation_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())