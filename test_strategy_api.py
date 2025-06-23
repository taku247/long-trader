#!/usr/bin/env python3
"""
戦略設定API統合テスト

strategy_config_api.py の動作確認用テストスクリプト
"""

import json
import requests
import time
from threading import Thread
from flask import Flask

# APIサーバー起動用
def start_test_server():
    """テスト用APIサーバーを起動"""
    import tempfile
    import os
    from strategy_config_api import StrategyConfigAPI
    from strategy_config_manager import StrategyConfigManager
    
    # テスト用の一時DBを作成
    test_db_dir = tempfile.mkdtemp(prefix="test_strategy_api_")
    test_db_path = os.path.join(test_db_dir, "test_analysis.db")
    
    print(f"🧪 Using test database: {test_db_path}")
    
    # テスト用DBでマネージャーを作成
    os.environ['TEST_STRATEGY_DB_PATH'] = test_db_path
    
    app = Flask(__name__)
    api = StrategyConfigAPI(app)
    
    # CORS設定
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    try:
        app.run(debug=False, port=5002, use_reloader=False)
    finally:
        # テスト後にクリーンアップ
        import shutil
        if os.path.exists(test_db_dir):
            shutil.rmtree(test_db_dir)
            print(f"🧹 Cleaned up test database: {test_db_dir}")

class StrategyAPITester:
    """戦略設定API統合テスト"""
    
    def __init__(self, base_url="http://localhost:5002"):
        self.base_url = base_url
        self.test_strategy_id = None
    
    def test_options_endpoint(self):
        """設定オプション取得テスト"""
        print("🔍 Testing /api/strategy-configs/options")
        
        response = requests.get(f"{self.base_url}/api/strategy-configs/options")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Options endpoint success")
            print(f"   Base strategies: {len(data['data']['base_strategies'])}")
            print(f"   Timeframes: {len(data['data']['timeframes'])}")
            print(f"   Parameter rules: {len(data['data']['parameter_rules'])}")
            return True
        else:
            print(f"❌ Options endpoint failed: {response.status_code}")
            return False
    
    def test_create_strategy(self):
        """戦略作成テスト"""
        print("\n🔍 Testing POST /api/strategy-configs")
        
        test_strategy = {
            "name": "Test_Conservative_30m",
            "base_strategy": "Conservative_ML",
            "timeframe": "30m",
            "parameters": {
                "risk_multiplier": 1.5,
                "leverage_cap": 50,
                "min_risk_reward": 1.2,
                "confidence_boost": 0.1,
                "stop_loss_percent": 3.0,
                "take_profit_percent": 6.0
            },
            "description": "Test strategy for Conservative ML 30m timeframe",
            "created_by": "api_tester"
        }
        
        response = requests.post(
            f"{self.base_url}/api/strategy-configs",
            json=test_strategy,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            data = response.json()
            self.test_strategy_id = data['data']['id']
            print("✅ Strategy creation success")
            print(f"   Created strategy ID: {self.test_strategy_id}")
            print(f"   Strategy name: {data['data']['name']}")
            return True
        else:
            print(f"❌ Strategy creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_list_strategies(self):
        """戦略一覧取得テスト"""
        print("\n🔍 Testing GET /api/strategy-configs")
        
        # 全戦略取得
        response = requests.get(f"{self.base_url}/api/strategy-configs")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Strategy list success")
            print(f"   Total strategies: {data['count']}")
            
            # フィルタテスト
            response = requests.get(
                f"{self.base_url}/api/strategy-configs?base_strategy=Conservative_ML&include_stats=true"
            )
            
            if response.status_code == 200:
                filtered_data = response.json()
                print(f"   Conservative_ML strategies: {filtered_data['count']}")
                if filtered_data['count'] > 0:
                    print(f"   First strategy has stats: {'usage_stats' in filtered_data['data'][0]}")
                return True
            else:
                print(f"❌ Strategy filtering failed: {response.status_code}")
                return False
        else:
            print(f"❌ Strategy list failed: {response.status_code}")
            return False
    
    def test_get_strategy_detail(self):
        """戦略詳細取得テスト"""
        if not self.test_strategy_id:
            print("\n⚠️ Skipping strategy detail test (no test strategy ID)")
            return False
        
        print(f"\n🔍 Testing GET /api/strategy-configs/{self.test_strategy_id}")
        
        response = requests.get(f"{self.base_url}/api/strategy-configs/{self.test_strategy_id}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Strategy detail success")
            print(f"   Strategy name: {data['data']['name']}")
            print(f"   Parameters count: {len(data['data']['parameters'])}")
            print(f"   Usage stats included: {'usage_stats' in data['data']}")
            return True
        else:
            print(f"❌ Strategy detail failed: {response.status_code}")
            return False
    
    def test_update_strategy(self):
        """戦略更新テスト"""
        if not self.test_strategy_id:
            print("\n⚠️ Skipping strategy update test (no test strategy ID)")
            return False
        
        print(f"\n🔍 Testing PUT /api/strategy-configs/{self.test_strategy_id}")
        
        update_data = {
            "description": "Updated test strategy description",
            "parameters": {
                "risk_multiplier": 2.0,
                "leverage_cap": 75,
                "min_risk_reward": 1.5,
                "confidence_boost": 0.15
            }
        }
        
        response = requests.put(
            f"{self.base_url}/api/strategy-configs/{self.test_strategy_id}",
            json=update_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Strategy update success")
            print(f"   Updated description: {data['data']['description']}")
            print(f"   New risk_multiplier: {data['data']['parameters']['risk_multiplier']}")
            return True
        else:
            print(f"❌ Strategy update failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_duplicate_strategy(self):
        """戦略複製テスト"""
        if not self.test_strategy_id:
            print("\n⚠️ Skipping strategy duplicate test (no test strategy ID)")
            return False
        
        print(f"\n🔍 Testing POST /api/strategy-configs/{self.test_strategy_id}/duplicate")
        
        duplicate_data = {
            "name": "Test_Conservative_30m_Copy",
            "created_by": "api_tester"
        }
        
        response = requests.post(
            f"{self.base_url}/api/strategy-configs/{self.test_strategy_id}/duplicate",
            json=duplicate_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            data = response.json()
            duplicate_id = data['data']['id']
            print("✅ Strategy duplicate success")
            print(f"   Duplicate strategy ID: {duplicate_id}")
            print(f"   Duplicate name: {data['data']['name']}")
            
            # 複製した戦略も削除用にマークしておく
            self.cleanup_ids = getattr(self, 'cleanup_ids', [])
            self.cleanup_ids.append(duplicate_id)
            
            return True
        else:
            print(f"❌ Strategy duplicate failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_validate_parameters(self):
        """パラメータバリデーションテスト"""
        print("\n🔍 Testing POST /api/strategy-configs/validate-parameters")
        
        # 正常なパラメータ
        valid_params = {
            "parameters": {
                "risk_multiplier": 1.5,
                "leverage_cap": 50,
                "min_risk_reward": 1.2
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/strategy-configs/validate-parameters",
            json=valid_params,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Parameter validation success")
            print(f"   Valid: {data['data']['valid']}")
            print(f"   Errors: {len(data['data']['errors'])}")
            
            # 無効なパラメータのテスト
            invalid_params = {
                "parameters": {
                    "risk_multiplier": 10.0,  # 範囲外
                    "leverage_cap": -5,  # 範囲外
                    "unknown_param": "test"  # 未知のパラメータ
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/strategy-configs/validate-parameters",
                json=invalid_params,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Invalid params detected: {not data['data']['valid']}")
                print(f"   Error count: {len(data['data']['errors'])}")
                return True
            else:
                print(f"❌ Invalid parameter validation failed: {response.status_code}")
                return False
        else:
            print(f"❌ Parameter validation failed: {response.status_code}")
            return False
    
    def test_stats_endpoint(self):
        """統計情報取得テスト"""
        print("\n🔍 Testing GET /api/strategy-configs/stats")
        
        response = requests.get(f"{self.base_url}/api/strategy-configs/stats")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Stats endpoint success")
            print(f"   Total strategies: {data['data']['total_strategies']}")
            print(f"   Base strategy types: {len(data['data']['base_strategy_distribution'])}")
            print(f"   Timeframe types: {len(data['data']['timeframe_distribution'])}")
            return True
        else:
            print(f"❌ Stats endpoint failed: {response.status_code}")
            return False
    
    def test_search_strategies(self):
        """戦略検索テスト"""
        print("\n🔍 Testing GET /api/strategy-configs?search=Test")
        
        response = requests.get(f"{self.base_url}/api/strategy-configs?search=Test")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Strategy search success")
            print(f"   Search results: {data['count']}")
            return True
        else:
            print(f"❌ Strategy search failed: {response.status_code}")
            return False
    
    def cleanup_test_data(self):
        """テストデータのクリーンアップ"""
        print("\n🧹 Cleaning up test data")
        
        cleanup_ids = [self.test_strategy_id] + getattr(self, 'cleanup_ids', [])
        
        for strategy_id in cleanup_ids:
            if strategy_id:
                response = requests.delete(f"{self.base_url}/api/strategy-configs/{strategy_id}")
                if response.status_code == 200:
                    print(f"   ✅ Deleted strategy {strategy_id}")
                else:
                    print(f"   ⚠️ Failed to delete strategy {strategy_id}")
    
    def run_all_tests(self):
        """すべてのテストを実行"""
        print("🚀 戦略設定API統合テスト開始")
        print("=" * 60)
        
        tests = [
            self.test_options_endpoint,
            self.test_create_strategy,
            self.test_list_strategies,
            self.test_get_strategy_detail,
            self.test_update_strategy,
            self.test_duplicate_strategy,
            self.test_validate_parameters,
            self.test_stats_endpoint,
            self.test_search_strategies
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} error: {e}")
                failed += 1
            
            time.sleep(0.5)  # API呼び出し間隔を空ける
        
        # クリーンアップ
        self.cleanup_test_data()
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("🎯 テスト結果")
        print("=" * 60)
        print(f"成功: {passed}")
        print(f"失敗: {failed}")
        
        if failed == 0:
            print("\n🎉 すべてのテストが成功しました！")
            print("戦略設定APIが正常に動作しています。")
        else:
            print(f"\n⚠️ {failed}件のテストが失敗しました。")
        
        return failed == 0

def main():
    """メイン実行関数"""
    # APIサーバーをバックグラウンドで起動
    print("🔧 Starting test API server...")
    server_thread = Thread(target=start_test_server, daemon=True)
    server_thread.start()
    
    # サーバー起動待機
    time.sleep(3)
    
    # テスト実行
    tester = StrategyAPITester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())