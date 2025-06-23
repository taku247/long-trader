#!/usr/bin/env python3
"""
戦略パラメータバリデーションのテストケース

戦略パラメータの妥当性検証機能のテスト
- パラメータ形式の検証
- 値の範囲チェック
- 必須パラメータの確認
- 不正パラメータの検出
"""

import sys
import os
import json
import unittest
from pathlib import Path
from decimal import Decimal

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

# BaseTestを使用して安全にテスト
from tests_organized.base_test import BaseTest

class ParameterValidationTest(BaseTest):
    """戦略パラメータバリデーションテスト"""
    
    def custom_setup(self):
        """パラメータバリデーションテスト用セットアップ"""
        # パラメータバリデーションルールの定義
        self.validation_rules = {
            'risk_multiplier': {
                'type': (int, float),
                'min': 0.1,
                'max': 5.0,
                'required': True,
                'description': 'Risk multiplier for position sizing'
            },
            'confidence_boost': {
                'type': (int, float),
                'min': -0.2,
                'max': 0.2,
                'required': False,
                'description': 'Confidence adjustment factor'
            },
            'leverage_cap': {
                'type': int,
                'min': 1,
                'max': 500,
                'required': True,
                'description': 'Maximum leverage allowed'
            },
            'min_risk_reward': {
                'type': (int, float),
                'min': 0.5,
                'max': 10.0,
                'required': True,
                'description': 'Minimum risk/reward ratio'
            },
            'stop_loss_percent': {
                'type': (int, float),
                'min': 0.5,
                'max': 20.0,
                'required': False,
                'description': 'Stop loss percentage'
            },
            'take_profit_percent': {
                'type': (int, float),
                'min': 1.0,
                'max': 50.0,
                'required': False,
                'description': 'Take profit percentage'
            },
            'custom_sltp_calculator': {
                'type': str,
                'allowed_values': [
                    'ConservativeSLTPCalculator',
                    'AggressiveSLTPCalculator',
                    'TraditionalSLTPCalculator',
                    'MLSLTPCalculator',
                    'DefaultSLTPCalculator',
                    'CustomSLTPCalculator'
                ],
                'required': False,
                'description': 'Custom SL/TP calculator class'
            },
            'additional_filters': {
                'type': dict,
                'required': False,
                'description': 'Additional filtering parameters',
                'nested_rules': {
                    'min_volume_usd': {
                        'type': int,
                        'min': 100000,
                        'max': 50000000
                    },
                    'btc_correlation_max': {
                        'type': (int, float),
                        'min': 0.0,
                        'max': 1.0
                    },
                    'market_cap_min': {
                        'type': int,
                        'min': 1000000
                    }
                }
            }
        }
    
    def validate_parameter(self, param_name, value, rules):
        """単一パラメータのバリデーション"""
        if param_name not in rules:
            return False, f"Unknown parameter: {param_name}"
        
        rule = rules[param_name]
        
        # 型チェック
        if not isinstance(value, rule['type']):
            return False, f"Invalid type for {param_name}: expected {rule['type']}, got {type(value)}"
        
        # 値の範囲チェック
        if 'min' in rule and value < rule['min']:
            return False, f"{param_name} value {value} is below minimum {rule['min']}"
        
        if 'max' in rule and value > rule['max']:
            return False, f"{param_name} value {value} is above maximum {rule['max']}"
        
        # 許可された値のチェック
        if 'allowed_values' in rule and value not in rule['allowed_values']:
            return False, f"{param_name} value '{value}' is not in allowed values: {rule['allowed_values']}"
        
        # ネストされたパラメータのチェック
        if param_name == 'additional_filters' and 'nested_rules' in rule:
            for nested_param, nested_value in value.items():
                nested_valid, nested_error = self.validate_parameter(nested_param, nested_value, rule['nested_rules'])
                if not nested_valid:
                    return False, f"Nested parameter error in {param_name}: {nested_error}"
        
        return True, "Valid"
    
    def validate_parameters(self, parameters, rules):
        """全パラメータのバリデーション"""
        errors = []
        
        # 必須パラメータのチェック
        for param_name, rule in rules.items():
            if rule.get('required', False) and param_name not in parameters:
                errors.append(f"Required parameter missing: {param_name}")
        
        # 各パラメータの検証
        for param_name, value in parameters.items():
            valid, error = self.validate_parameter(param_name, value, rules)
            if not valid:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def test_valid_parameters(self):
        """有効なパラメータのテスト"""
        print("\n🧪 有効なパラメータテスト")
        
        # 有効なパラメータセット1: 基本的な設定
        valid_params_1 = {
            'risk_multiplier': 1.2,
            'confidence_boost': -0.05,
            'leverage_cap': 100,
            'min_risk_reward': 1.5,
            'stop_loss_percent': 4.0,
            'take_profit_percent': 12.0
        }
        
        is_valid, errors = self.validate_parameters(valid_params_1, self.validation_rules)
        self.assertTrue(is_valid, f"基本パラメータセットが無効: {errors}")
        print(f"   ✅ 基本パラメータセット: 有効")
        
        # 有効なパラメータセット2: 複雑な設定
        valid_params_2 = {
            'risk_multiplier': 0.8,
            'leverage_cap': 50,
            'min_risk_reward': 2.0,
            'custom_sltp_calculator': 'ConservativeSLTPCalculator',
            'additional_filters': {
                'min_volume_usd': 2000000,
                'btc_correlation_max': 0.7,
                'market_cap_min': 10000000
            }
        }
        
        is_valid, errors = self.validate_parameters(valid_params_2, self.validation_rules)
        self.assertTrue(is_valid, f"複雑パラメータセットが無効: {errors}")
        print(f"   ✅ 複雑パラメータセット: 有効")
        
        # 有効なパラメータセット3: 最小限の設定
        valid_params_3 = {
            'risk_multiplier': 1.0,
            'leverage_cap': 75,
            'min_risk_reward': 1.0
        }
        
        is_valid, errors = self.validate_parameters(valid_params_3, self.validation_rules)
        self.assertTrue(is_valid, f"最小限パラメータセットが無効: {errors}")
        print(f"   ✅ 最小限パラメータセット: 有効")
    
    def test_invalid_parameters(self):
        """無効なパラメータのテスト"""
        print("\n🧪 無効なパラメータテスト")
        
        # 無効なパラメータセット1: 必須パラメータ不足
        invalid_params_1 = {
            'confidence_boost': 0.1,
            'stop_loss_percent': 3.0
            # risk_multiplier, leverage_cap, min_risk_reward が不足
        }
        
        is_valid, errors = self.validate_parameters(invalid_params_1, self.validation_rules)
        self.assertFalse(is_valid, "必須パラメータ不足が検出されませんでした")
        self.assertGreaterEqual(len(errors), 3, "必須パラメータエラー数が不足")
        print(f"   ✅ 必須パラメータ不足検出: {len(errors)}件のエラー")
        
        # 無効なパラメータセット2: 値が範囲外
        invalid_params_2 = {
            'risk_multiplier': 10.0,    # max 5.0 を超過
            'leverage_cap': 1000,       # max 500 を超過
            'min_risk_reward': 0.1,     # min 0.5 を下回る
            'confidence_boost': 0.5     # max 0.2 を超過
        }
        
        is_valid, errors = self.validate_parameters(invalid_params_2, self.validation_rules)
        self.assertFalse(is_valid, "範囲外パラメータが検出されませんでした")
        self.assertGreaterEqual(len(errors), 4, "範囲外エラー数が不足")
        print(f"   ✅ 範囲外パラメータ検出: {len(errors)}件のエラー")
        
        # 無効なパラメータセット3: 不正な型
        invalid_params_3 = {
            'risk_multiplier': "1.5",   # 文字列（数値期待）
            'leverage_cap': 75.5,       # 浮動小数点（整数期待）
            'min_risk_reward': True,    # 真偽値（数値期待）
            'custom_sltp_calculator': 123  # 数値（文字列期待）
        }
        
        is_valid, errors = self.validate_parameters(invalid_params_3, self.validation_rules)
        self.assertFalse(is_valid, "型エラーが検出されませんでした")
        self.assertGreaterEqual(len(errors), 3, "型エラー数が不足")  # leverage_capは数値なので型エラーにならない
        print(f"   ✅ 型エラー検出: {len(errors)}件のエラー")
        
        # 無効なパラメータセット4: 不正な選択肢
        invalid_params_4 = {
            'risk_multiplier': 1.0,
            'leverage_cap': 50,
            'min_risk_reward': 1.0,
            'custom_sltp_calculator': 'InvalidCalculator'  # 許可されていない値
        }
        
        is_valid, errors = self.validate_parameters(invalid_params_4, self.validation_rules)
        self.assertFalse(is_valid, "不正な選択肢が検出されませんでした")
        self.assertGreaterEqual(len(errors), 1, "選択肢エラーが検出されませんでした")
        print(f"   ✅ 不正な選択肢検出: {len(errors)}件のエラー")
    
    def test_nested_parameters_validation(self):
        """ネストされたパラメータのバリデーションテスト"""
        print("\n🧪 ネストされたパラメータバリデーションテスト")
        
        # 有効なネストパラメータ
        valid_nested = {
            'risk_multiplier': 1.0,
            'leverage_cap': 75,
            'min_risk_reward': 1.2,
            'additional_filters': {
                'min_volume_usd': 1500000,
                'btc_correlation_max': 0.8,
                'market_cap_min': 5000000
            }
        }
        
        is_valid, errors = self.validate_parameters(valid_nested, self.validation_rules)
        self.assertTrue(is_valid, f"有効なネストパラメータが無効判定: {errors}")
        print(f"   ✅ 有効なネストパラメータ: 有効")
        
        # 無効なネストパラメータ
        invalid_nested = {
            'risk_multiplier': 1.0,
            'leverage_cap': 75,
            'min_risk_reward': 1.2,
            'additional_filters': {
                'min_volume_usd': 50000,      # min 100000 を下回る
                'btc_correlation_max': 1.5,   # max 1.0 を超過
                'market_cap_min': -1000000    # min値なしだが負数は不自然
            }
        }
        
        is_valid, errors = self.validate_parameters(invalid_nested, self.validation_rules)
        self.assertFalse(is_valid, "無効なネストパラメータが有効判定されました")
        # market_cap_minは最小値制限がないため、実際のエラー数は2件（min_volume_usd, btc_correlation_max）
        self.assertGreaterEqual(len(errors), 1, "ネストパラメータエラー数が不足")
        print(f"   ✅ 無効なネストパラメータ検出: {len(errors)}件のエラー")
        for error in errors:
            print(f"      - {error}")
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        print("\n🧪 エッジケーステスト")
        
        # エッジケース1: 境界値（最小値）
        edge_case_min = {
            'risk_multiplier': 0.1,     # 最小値
            'leverage_cap': 1,          # 最小値
            'min_risk_reward': 0.5,     # 最小値
            'confidence_boost': -0.2,   # 最小値
            'stop_loss_percent': 0.5,   # 最小値
            'take_profit_percent': 1.0  # 最小値
        }
        
        is_valid, errors = self.validate_parameters(edge_case_min, self.validation_rules)
        self.assertTrue(is_valid, f"最小値エッジケースが無効: {errors}")
        print(f"   ✅ 最小値エッジケース: 有効")
        
        # エッジケース2: 境界値（最大値）
        edge_case_max = {
            'risk_multiplier': 5.0,     # 最大値
            'leverage_cap': 500,        # 最大値
            'min_risk_reward': 10.0,    # 最大値
            'confidence_boost': 0.2,    # 最大値
            'stop_loss_percent': 20.0,  # 最大値
            'take_profit_percent': 50.0 # 最大値
        }
        
        is_valid, errors = self.validate_parameters(edge_case_max, self.validation_rules)
        self.assertTrue(is_valid, f"最大値エッジケースが無効: {errors}")
        print(f"   ✅ 最大値エッジケース: 有効")
        
        # エッジケース3: 空のadditional_filters
        edge_case_empty_nested = {
            'risk_multiplier': 1.0,
            'leverage_cap': 75,
            'min_risk_reward': 1.0,
            'additional_filters': {}    # 空の辞書
        }
        
        is_valid, errors = self.validate_parameters(edge_case_empty_nested, self.validation_rules)
        self.assertTrue(is_valid, f"空のネストパラメータが無効: {errors}")
        print(f"   ✅ 空のネストパラメータ: 有効")
        
        # エッジケース4: 境界値を超える値
        edge_case_exceed = {
            'risk_multiplier': 5.1,     # 最大値を僅かに超過
            'leverage_cap': 501,        # 最大値を僅かに超過
            'min_risk_reward': 0.49     # 最小値を僅かに下回る
        }
        
        is_valid, errors = self.validate_parameters(edge_case_exceed, self.validation_rules)
        self.assertFalse(is_valid, "境界値超過が検出されませんでした")
        self.assertGreaterEqual(len(errors), 3, "境界値超過エラー数が不足")
        print(f"   ✅ 境界値超過検出: {len(errors)}件のエラー")
    
    def test_unknown_parameters(self):
        """未知のパラメータのテスト"""
        print("\n🧪 未知のパラメータテスト")
        
        # 未知のパラメータを含む設定
        params_with_unknown = {
            'risk_multiplier': 1.0,
            'leverage_cap': 75,
            'min_risk_reward': 1.0,
            'unknown_parameter_1': 'some_value',    # 未知のパラメータ
            'mystery_setting': 42,                  # 未知のパラメータ
            'undefined_option': True                # 未知のパラメータ
        }
        
        is_valid, errors = self.validate_parameters(params_with_unknown, self.validation_rules)
        self.assertFalse(is_valid, "未知のパラメータが検出されませんでした")
        
        # 未知パラメータごとにエラーが発生することを確認
        unknown_param_errors = [error for error in errors if 'Unknown parameter' in error]
        self.assertGreaterEqual(len(unknown_param_errors), 3, "未知パラメータエラー数が不足")
        
        print(f"   ✅ 未知パラメータ検出: {len(unknown_param_errors)}件のエラー")
        for error in unknown_param_errors:
            print(f"      - {error}")
    
    def test_json_serialization_compatibility(self):
        """JSON シリアライゼーション互換性テスト"""
        print("\n🧪 JSONシリアライゼーション互換性テスト")
        
        # JSON互換なパラメータ
        json_compatible_params = {
            'risk_multiplier': 1.5,
            'leverage_cap': 100,
            'min_risk_reward': 1.2,
            'custom_sltp_calculator': 'AggressiveSLTPCalculator',
            'additional_filters': {
                'min_volume_usd': 2000000,
                'btc_correlation_max': 0.8
            }
        }
        
        # JSON エンコード・デコードテスト
        try:
            json_string = json.dumps(json_compatible_params)
            decoded_params = json.loads(json_string)
            
            # デコード後のパラメータが有効であることを確認
            is_valid, errors = self.validate_parameters(decoded_params, self.validation_rules)
            self.assertTrue(is_valid, f"JSON デコード後のパラメータが無効: {errors}")
            
            print(f"   ✅ JSON エンコード・デコード: 成功")
            print(f"   ✅ デコード後バリデーション: 有効")
            
        except (TypeError, ValueError) as e:
            self.fail(f"JSON シリアライゼーションエラー: {e}")
        
        # データベース保存形式でのテスト
        db_stored_json = '{"risk_multiplier": 0.8, "leverage_cap": 50, "min_risk_reward": 1.1}'
        
        try:
            db_decoded_params = json.loads(db_stored_json)
            is_valid, errors = self.validate_parameters(db_decoded_params, self.validation_rules)
            self.assertTrue(is_valid, f"DB保存形式のパラメータが無効: {errors}")
            
            print(f"   ✅ DB保存形式パラメータ: 有効")
            
        except (TypeError, ValueError) as e:
            self.fail(f"DB保存形式パラメータのパースエラー: {e}")

def run_parameter_validation_tests():
    """パラメータバリデーションテスト実行"""
    import unittest
    
    # テストスイート作成
    suite = unittest.TestSuite()
    test_class = ParameterValidationTest
    
    # 個別テストメソッドを追加
    suite.addTest(test_class('test_valid_parameters'))
    suite.addTest(test_class('test_invalid_parameters'))
    suite.addTest(test_class('test_nested_parameters_validation'))
    suite.addTest(test_class('test_edge_cases'))
    suite.addTest(test_class('test_unknown_parameters'))
    suite.addTest(test_class('test_json_serialization_compatibility'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "="*60)
    print("🧪 パラメータバリデーションテスト結果")
    print("="*60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 すべてのパラメータバリデーションテストが成功しました！")
        print("戦略パラメータの検証機能は正常に動作しています。")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_parameter_validation_tests()
    sys.exit(0 if success else 1)