#!/usr/bin/env python3
"""
選択的実行機能テスト

strategy_configs を使った戦略カスタマイズとselected_strategies/selected_timeframesを使った選択実行のテスト
"""

import json
import requests
import time
from strategy_config_manager import StrategyConfigManager

class SelectiveExecutionTester:
    """選択的実行機能テスト"""
    
    def __init__(self, api_base_url="http://localhost:5001"):
        self.api_base_url = api_base_url
        self.manager = StrategyConfigManager()
        self.test_symbol = "TESTCOIN"  # テスト用仮想銘柄
    
    def create_test_strategy_configs(self):
        """テスト用戦略設定を作成"""
        print("🔧 Creating test strategy configurations...")
        
        test_configs = [
            {
                "name": "Test_Conservative_15m",
                "base_strategy": "Conservative_ML",
                "timeframe": "15m",
                "parameters": {
                    "risk_multiplier": 1.2,
                    "leverage_cap": 30,
                    "min_risk_reward": 1.5,
                    "confidence_boost": 0.05
                },
                "description": "Test conservative strategy for 15m"
            },
            {
                "name": "Test_Aggressive_30m", 
                "base_strategy": "Aggressive_ML",
                "timeframe": "30m",
                "parameters": {
                    "risk_multiplier": 2.5,
                    "leverage_cap": 100,
                    "min_risk_reward": 1.0,
                    "confidence_boost": 0.1,
                    "stop_loss_percent": 2.0,
                    "take_profit_percent": 8.0
                },
                "description": "Test aggressive strategy for 30m"
            }
        ]
        
        created_ids = []
        for config in test_configs:
            try:
                strategy_id = self.manager.create_strategy(
                    name=config["name"],
                    base_strategy=config["base_strategy"],
                    timeframe=config["timeframe"],
                    parameters=config["parameters"],
                    description=config["description"],
                    created_by="test_runner"
                )
                created_ids.append(strategy_id)
                print(f"   ✅ Created strategy {config['name']} (ID: {strategy_id})")
            except Exception as e:
                print(f"   ❌ Failed to create {config['name']}: {e}")
        
        return created_ids
    
    def test_selected_strategies_timeframes(self):
        """selected_strategies と selected_timeframes を使った選択的実行テスト"""
        print("\n🔍 Testing selected_strategies + selected_timeframes execution")
        
        payload = {
            "symbol": self.test_symbol,
            "selected_strategies": ["Conservative_ML", "Aggressive_ML"],
            "selected_timeframes": ["15m", "30m"]
        }
        
        print(f"   Request payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.api_base_url}/api/symbol/add",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print("   ✅ Symbol addition request successful")
                print(f"   Execution ID: {result.get('execution_id')}")
                print(f"   Expected combinations: 2 strategies × 2 timeframes = 4 configs")
                return result.get('execution_id')
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Request error: {e}")
            return None
    
    def test_strategy_configs_execution(self, strategy_config_ids):
        """strategy_configs を使ったカスタム戦略実行テスト"""
        print("\n🔍 Testing strategy_configs custom execution")
        
        # 作成した戦略設定を取得
        strategy_configs = []
        for config_id in strategy_config_ids:
            config = self.manager.get_strategy(config_id)
            if config:
                strategy_configs.append(config)
        
        if not strategy_configs:
            print("   ⚠️ No strategy configs available, skipping test")
            return None
        
        payload = {
            "symbol": self.test_symbol + "_CUSTOM",
            "strategy_configs": strategy_configs
        }
        
        print(f"   Using {len(strategy_configs)} custom strategy configurations:")
        for config in strategy_configs:
            print(f"     - {config['name']} ({config['base_strategy']}, {config['timeframe']})")
        
        try:
            response = requests.post(
                f"{self.api_base_url}/api/symbol/add",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print("   ✅ Custom strategy execution request successful")
                print(f"   Execution ID: {result.get('execution_id')}")
                print(f"   Expected custom configs: {len(strategy_configs)}")
                return result.get('execution_id')
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Request error: {e}")
            return None
    
    def test_mixed_execution(self, strategy_config_ids):
        """selected_strategies + strategy_configs 混合実行テスト"""
        print("\n🔍 Testing mixed execution (selected_strategies + strategy_configs)")
        
        # 1つだけカスタム戦略を使用
        custom_config = self.manager.get_strategy(strategy_config_ids[0]) if strategy_config_ids else None
        
        payload = {
            "symbol": self.test_symbol + "_MIXED",
            "selected_strategies": ["Full_ML"],
            "selected_timeframes": ["1h"],
            "strategy_configs": [custom_config] if custom_config else []
        }
        
        print(f"   Request combines:")
        print(f"     - Default: Full_ML × 1h = 1 config")
        print(f"     - Custom: {custom_config['name'] if custom_config else 'None'}")
        print(f"   Expected total: {1 + (1 if custom_config else 0)} configs")
        
        try:
            response = requests.post(
                f"{self.api_base_url}/api/symbol/add",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print("   ✅ Mixed execution request successful")
                print(f"   Execution ID: {result.get('execution_id')}")
                return result.get('execution_id')
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Request error: {e}")
            return None
    
    def test_default_execution(self):
        """デフォルト実行（従来通り）テスト"""
        print("\n🔍 Testing default execution (backward compatibility)")
        
        payload = {
            "symbol": self.test_symbol + "_DEFAULT"
        }
        
        print("   Using default parameters (no selection)")
        print("   Expected: 3 strategies × 6 timeframes = 18 configs")
        
        try:
            response = requests.post(
                f"{self.api_base_url}/api/symbol/add",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print("   ✅ Default execution request successful")
                print(f"   Execution ID: {result.get('execution_id')}")
                return result.get('execution_id')
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Request error: {e}")
            return None
    
    def cleanup_test_data(self, strategy_config_ids):
        """テストデータのクリーンアップ"""
        print("\n🧹 Cleaning up test data...")
        
        for config_id in strategy_config_ids:
            try:
                success = self.manager.delete_strategy(config_id)
                if success:
                    print(f"   ✅ Deleted strategy config {config_id}")
                else:
                    print(f"   ⚠️ Failed to delete strategy config {config_id}")
            except Exception as e:
                print(f"   ❌ Error deleting strategy config {config_id}: {e}")
    
    def run_all_tests(self):
        """すべてのテストを実行"""
        print("🚀 選択的実行機能統合テスト開始")
        print("=" * 60)
        
        # テスト用戦略設定作成
        strategy_config_ids = self.create_test_strategy_configs()
        
        if not strategy_config_ids:
            print("❌ Failed to create test strategy configs, aborting")
            return False
        
        test_results = {}
        
        # 各テストの実行
        try:
            test_results['selected'] = self.test_selected_strategies_timeframes()
            time.sleep(2)
            
            test_results['custom'] = self.test_strategy_configs_execution(strategy_config_ids)
            time.sleep(2)
            
            test_results['mixed'] = self.test_mixed_execution(strategy_config_ids)
            time.sleep(2)
            
            test_results['default'] = self.test_default_execution()
            
        finally:
            # クリーンアップ
            self.cleanup_test_data(strategy_config_ids)
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("🎯 テスト結果サマリー")
        print("=" * 60)
        
        success_count = sum(1 for result in test_results.values() if result is not None)
        total_count = len(test_results)
        
        for test_name, execution_id in test_results.items():
            status = "✅ Success" if execution_id else "❌ Failed"
            print(f"{test_name:15}: {status}")
            if execution_id:
                print(f"                 Execution ID: {execution_id}")
        
        print(f"\n成功: {success_count}/{total_count}")
        
        if success_count == total_count:
            print("\n🎉 すべてのテストが成功しました！")
            print("選択的実行機能が正常に動作しています。")
        else:
            print(f"\n⚠️ {total_count - success_count}件のテストが失敗しました。")
        
        return success_count == total_count

def main():
    """メイン実行関数"""
    print("⚠️ 注意: このテストは実際にバックテスト処理を開始します。")
    print("Web Dashboard (port 5001) が起動している必要があります。")
    
    user_input = input("続行しますか？ [y/N]: ")
    if user_input.lower() != 'y':
        print("テストをキャンセルしました。")
        return 0
    
    tester = SelectiveExecutionTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())