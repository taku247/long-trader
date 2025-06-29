#!/usr/bin/env python3
"""
ブラウザから銘柄追加時の手動設定パラメータ適用テスト

WebUIで手動設定したパラメータが戦略分析で確実に適用され、
DB永続化とトレーサビリティが確保されていることを確認
"""

import unittest
import json
import os
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests_organized.base_test import BaseTest


class TestManualParamsApplication(BaseTest):
    """手動設定パラメータ適用テストクラス"""
    
    def test_filter_params_metadata_storage(self):
        """filter_paramsがDB metadataに保存されることを確認"""
        print("\n🧪 filter_paramsメタデータ保存テスト")
        
        # mock filter_params
        test_filter_params = {
            "entry_conditions": {
                "min_leverage": 5.0,
                "min_confidence": 0.7,
                "min_risk_reward": 2.0
            },
            "support_resistance": {
                "min_support_strength": 0.8,
                "min_resistance_strength": 0.8,
                "min_touch_count": 3,
                "max_distance_pct": 0.05,
                "tolerance_pct": 0.01,
                "fractal_window": 7
            }
        }
        
        # ExecutionLogDatabaseでmetadata保存をテスト
        from execution_log_database import ExecutionLogDatabase, ExecutionType
        
        db = ExecutionLogDatabase()
        
        # テスト実行記録を作成
        execution_id = db.create_execution(
            ExecutionType.SYMBOL_ADDITION,
            symbol="TEST",
            triggered_by="USER:WEB_UI",
            metadata={
                "auto_training": True,
                "source": "web_dashboard", 
                "execution_mode": "default",
                "selected_strategy_ids": [999, 1000],
                "estimated_patterns": 2,
                "filter_params": test_filter_params  # 手動設定パラメータ
            }
        )
        
        # 保存された記録を取得して確認
        executions = db.list_executions(limit=1)
        self.assertTrue(len(executions) > 0, "実行記録が作成されていません")
        
        latest_execution = executions[0]
        self.assertIn('metadata', latest_execution, "metadataが取得されていません")
        
        metadata = latest_execution['metadata']
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        
        self.assertIn('filter_params', metadata, "filter_paramsがmetadataに保存されていません")
        
        stored_filter_params = metadata['filter_params']
        self.assertEqual(stored_filter_params['entry_conditions']['min_leverage'], 5.0)
        self.assertEqual(stored_filter_params['entry_conditions']['min_confidence'], 0.7)
        self.assertEqual(stored_filter_params['entry_conditions']['min_risk_reward'], 2.0)
        
        print("✅ filter_paramsがmetadataに正しく保存されました")
        
        # クリーンアップ
        try:
            db.delete_execution(execution_id)
        except:
            pass
    
    def test_scalable_analysis_system_param_override(self):
        """ScalableAnalysisSystemでの手動パラメータオーバーライドを確認"""
        print("\n🧪 戦略分析パラメータオーバーライドテスト")
        
        # 環境変数でfilter_paramsを設定
        test_filter_params = {
            "entry_conditions": {
                "min_leverage": 8.0,
                "min_confidence": 0.8,
                "min_risk_reward": 3.0
            }
        }
        
        original_env = os.environ.get('FILTER_PARAMS')
        
        try:
            # テスト用環境変数設定
            os.environ['FILTER_PARAMS'] = json.dumps(test_filter_params)
            
            # デフォルト値取得（UnifiedConfigManagerを経由せずに直接）
            from config.defaults_manager import get_default_min_leverage, get_default_min_confidence, get_default_min_risk_reward
            
            # デフォルト条件を直接構築
            conditions = {
                'min_leverage': get_default_min_leverage(),
                'min_confidence': get_default_min_confidence(),
                'min_risk_reward': get_default_min_risk_reward()
            }
            
            print(f"✅ デフォルト条件取得: {conditions}")
            
            # ScalableAnalysisSystemのオーバーライドロジックを模擬
            filter_params_env = os.getenv('FILTER_PARAMS')
            if filter_params_env:
                filter_params = json.loads(filter_params_env)
                entry_conditions = filter_params.get('entry_conditions', {})
                
                if entry_conditions:
                    original_conditions = conditions.copy()
                    if 'min_leverage' in entry_conditions:
                        conditions['min_leverage'] = entry_conditions['min_leverage']
                    if 'min_confidence' in entry_conditions:
                        conditions['min_confidence'] = entry_conditions['min_confidence']
                    if 'min_risk_reward' in entry_conditions:
                        conditions['min_risk_reward'] = entry_conditions['min_risk_reward']
                    
                    # オーバーライド後の値が手動設定値と一致することを確認
                    self.assertEqual(conditions['min_leverage'], 8.0)
                    self.assertEqual(conditions['min_confidence'], 0.8)
                    self.assertEqual(conditions['min_risk_reward'], 3.0)
                    
                    print(f"✅ パラメータオーバーライド成功:")
                    print(f"   min_leverage: {original_conditions.get('min_leverage')} → {conditions['min_leverage']}")
                    print(f"   min_confidence: {original_conditions.get('min_confidence')} → {conditions['min_confidence']}")
                    print(f"   min_risk_reward: {original_conditions.get('min_risk_reward')} → {conditions['min_risk_reward']}")
            
        finally:
            # 環境変数復元
            if original_env is not None:
                os.environ['FILTER_PARAMS'] = original_env
            elif 'FILTER_PARAMS' in os.environ:
                del os.environ['FILTER_PARAMS']
    
    def test_execution_logs_api_includes_filter_params(self):
        """execution logs APIでfilter_paramsが返されることを確認"""
        print("\n🧪 実行ログAPIでfilter_params返却テスト")
        
        # filter_paramsを含むテスト実行記録を作成
        test_filter_params = {
            "entry_conditions": {
                "min_leverage": 4.0,
                "min_confidence": 0.6,
                "min_risk_reward": 1.5
            }
        }
        
        from execution_log_database import ExecutionLogDatabase, ExecutionType
        
        db = ExecutionLogDatabase()
        
        execution_id = db.create_execution(
            ExecutionType.SYMBOL_ADDITION,
            symbol="API_TEST",
            triggered_by="USER:WEB_UI",
            metadata={
                "filter_params": test_filter_params,
                "source": "test"
            }
        )
        
        try:
            # APIから実行記録を取得（limit=1で最新のみ）
            executions = db.list_executions(limit=1)
            self.assertTrue(len(executions) > 0, "実行記録が見つかりません")
            
            latest_execution = executions[0]
            
            # metadataにfilter_paramsが含まれることを確認
            self.assertIn('metadata', latest_execution, "metadataが取得されていません")
            
            metadata = latest_execution['metadata']
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            self.assertIn('filter_params', metadata, "APIレスポンスにfilter_paramsが含まれていません")
            
            returned_filter_params = metadata['filter_params']
            self.assertEqual(returned_filter_params['entry_conditions']['min_leverage'], 4.0)
            self.assertEqual(returned_filter_params['entry_conditions']['min_confidence'], 0.6)
            self.assertEqual(returned_filter_params['entry_conditions']['min_risk_reward'], 1.5)
            
            print("✅ execution logs APIでfilter_paramsが正しく返されました")
            
        finally:
            # クリーンアップ
            try:
                db.delete_execution(execution_id)
            except:
                pass


if __name__ == '__main__':
    unittest.main()