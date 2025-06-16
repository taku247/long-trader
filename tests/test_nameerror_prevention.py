#!/usr/bin/env python3
"""
NameErrorバグ再発防止テスト

engines/leverage_decision_engine.pyでのNameError: name 'market_context' is not defined
の再発を防ぐための包括的テストスイート。
"""

import unittest
import sys
import inspect
from pathlib import Path
from unittest.mock import Mock, patch

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from engines.leverage_decision_engine import CoreLeverageDecisionEngine
from interfaces.data_types import (
    SupportResistanceLevel, BreakoutPrediction, BTCCorrelationRisk,
    MarketContext, LeverageRecommendation
)

class TestNameErrorPrevention(unittest.TestCase):
    """NameError再発防止テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.engine = CoreLeverageDecisionEngine()
        
        # モックデータの準備
        from datetime import datetime
        now = datetime.now()
        
        self.mock_support_levels = [
            SupportResistanceLevel(
                price=100.0, strength=0.8, touch_count=3, 
                level_type='support', first_touch=now, last_touch=now, 
                volume_at_level=1000.0, distance_from_current=5.0
            )
        ]
        
        self.mock_resistance_levels = [
            SupportResistanceLevel(
                price=110.0, strength=0.7, touch_count=2,
                level_type='resistance', first_touch=now, last_touch=now,
                volume_at_level=800.0, distance_from_current=5.0
            )
        ]
        
        self.mock_breakout_predictions = [
            BreakoutPrediction(
                level=self.mock_support_levels[0], 
                breakout_probability=0.3, bounce_probability=0.7,
                prediction_confidence=0.8, predicted_price_target=105.0,
                time_horizon_minutes=60, model_name='test_model'
            )
        ]
        
        self.mock_btc_correlation_risk = BTCCorrelationRisk(
            symbol='TEST', btc_drop_scenario=-10.0,
            predicted_altcoin_drop={60: -5.0, 120: -10.0}, 
            correlation_strength=0.8, risk_level='MEDIUM',
            liquidation_risk={60: 0.1, 120: 0.2}
        )
        
        self.mock_market_context = MarketContext(
            current_price=105.0, volume_24h=1000000.0, volatility=0.02,
            trend_direction='BULLISH', market_phase='MARKUP', timestamp=now
        )
    
    def test_calculate_final_leverage_method_signature(self):
        """_calculate_final_leverageメソッドのシグネチャ検証"""
        method = getattr(self.engine, '_calculate_final_leverage')
        signature = inspect.signature(method)
        
        # 必要なパラメータが存在することを確認
        expected_params = [
            'downside_analysis', 'upside_analysis', 'btc_risk_analysis',
            'market_risk_factor', 'current_price', 'reasoning', 'market_context'
        ]
        
        actual_params = list(signature.parameters.keys())[1:]  # selfを除く
        
        print(f"   実際のパラメータ: {actual_params}")
        
        for param in expected_params:
            self.assertIn(param, actual_params,
                         f"必須パラメータ '{param}' がメソッドシグネチャに存在しません")
        
        print(f"✅ _calculate_final_leverageメソッドシグネチャ検証完了")
        print(f"   パラメータ: {actual_params}")
    
    def test_market_context_parameter_usage(self):
        """market_contextパラメータが正しく使用されることを確認"""
        
        # モックデータを使用してテスト実行
        try:
            result = self.engine.calculate_safe_leverage(
                symbol='TEST',
                support_levels=self.mock_support_levels,
                resistance_levels=self.mock_resistance_levels,
                breakout_predictions=self.mock_breakout_predictions,
                btc_correlation_risk=self.mock_btc_correlation_risk,
                market_context=self.mock_market_context
            )
            
            # エラーが発生せずにLeverageRecommendationが返されることを確認
            self.assertIsInstance(result, LeverageRecommendation)
            print(f"✅ market_contextパラメータ使用テスト完了")
            print(f"   レバレッジ: {result.recommended_leverage}")
            print(f"   信頼度: {result.confidence_level}")
            
        except NameError as e:
            if "'market_context' is not defined" in str(e):
                self.fail(f"NameError再発！: {e}")
            else:
                raise e
    
    def test_method_call_parameter_passing(self):
        """メソッド呼び出し時にmarket_contextが正しく渡されることを確認"""
        
        # calculate_safe_leverageメソッドをパッチして呼び出しを監視
        with patch.object(self.engine, '_calculate_final_leverage') as mock_method:
            mock_method.return_value = {
                'recommended_leverage': 2.0,
                'max_safe_leverage': 4.0,
                'risk_reward_ratio': 1.5,
                'confidence': 0.8
            }
            
            # メソッド実行
            self.engine.calculate_safe_leverage(
                symbol='TEST',
                support_levels=self.mock_support_levels,
                resistance_levels=self.mock_resistance_levels,
                breakout_predictions=self.mock_breakout_predictions,
                btc_correlation_risk=self.mock_btc_correlation_risk,
                market_context=self.mock_market_context
            )
            
            # _calculate_final_leverageが正しい引数で呼ばれたことを確認
            mock_method.assert_called_once()
            call_args = mock_method.call_args
            
            # market_contextが最後の引数として渡されていることを確認
            self.assertEqual(len(call_args[0]), 7,  # 7つの位置引数
                           "_calculate_final_leverageの引数数が正しくありません")
            
            # 最後の引数がmarket_contextであることを確認
            passed_market_context = call_args[0][6]  # 7番目の引数（0ベース）
            self.assertEqual(passed_market_context, self.mock_market_context,
                           "market_contextが正しく渡されていません")
            
            print(f"✅ メソッド呼び出しパラメータ渡しテスト完了")
    
    def test_market_context_volatility_access(self):
        """market_context.volatilityへのアクセスが正常に動作することを確認"""
        
        # volatilityアクセスを直接テスト
        from datetime import datetime
        test_context = MarketContext(
            current_price=100.0, volume_24h=1000000.0, volatility=0.05,
            trend_direction='SIDEWAYS', market_phase='ACCUMULATION', timestamp=datetime.now()
        )
        
        # volatilityに正常にアクセスできることを確認
        volatility_value = test_context.volatility
        self.assertEqual(volatility_value, 0.05, "volatilityアクセスが失敗しました")
        
        # 計算で使用されるパターンをテスト
        market_conservatism = 0.5 + (test_context.volatility * 0.3)
        expected_value = 0.5 + (0.05 * 0.3)
        self.assertEqual(market_conservatism, expected_value,
                        "market_context.volatilityを使った計算が失敗しました")
        
        print(f"✅ market_context.volatilityアクセステスト完了")
        print(f"   volatility値: {volatility_value}")
        print(f"   計算結果: {market_conservatism}")
    
    def test_exception_handling_robustness(self):
        """例外処理の堅牢性テスト"""
        
        # 不正なデータでテストして例外処理を確認
        from datetime import datetime
        invalid_market_context = MarketContext(
            current_price=0.0,  # 不正な価格
            volume_24h=0.0, volatility=float('inf'),  # 無限大のボラティリティ
            trend_direction='INVALID', market_phase='INVALID', timestamp=datetime.now()
        )
        
        try:
            result = self.engine.calculate_safe_leverage(
                symbol='INVALID_TEST',
                support_levels=self.mock_support_levels,
                resistance_levels=self.mock_resistance_levels,
                breakout_predictions=self.mock_breakout_predictions,
                btc_correlation_risk=self.mock_btc_correlation_risk,
                market_context=invalid_market_context
            )
            
            # フォールバック値が返されることを確認
            self.assertIsInstance(result, LeverageRecommendation)
            self.assertEqual(result.confidence_level, 0.1,  # フォールバック信頼度
                           "例外時のフォールバック値が正しくありません")
            
            print(f"✅ 例外処理堅牢性テスト完了")
            print(f"   フォールバック信頼度: {result.confidence_level}")
            
        except NameError as e:
            if "'market_context' is not defined" in str(e):
                self.fail(f"例外処理中にNameError再発！: {e}")
            else:
                raise e
    
    def test_regression_prevention_complete(self):
        """包括的回帰テスト - NameErrorが発生しないことを確認"""
        
        from datetime import datetime
        
        # 複数のシナリオでテスト実行
        test_scenarios = [
            {
                'name': '通常の市場条件',
                'volatility': 0.02,
                'price': 100.0,
                'trend': 'BULLISH'
            },
            {
                'name': '高ボラティリティ',
                'volatility': 0.1,
                'price': 50.0,
                'trend': 'BEARISH'
            },
            {
                'name': '低ボラティリティ',
                'volatility': 0.001,
                'price': 1000.0,
                'trend': 'SIDEWAYS'
            }
        ]
        
        for scenario in test_scenarios:
            with self.subTest(scenario=scenario['name']):
                test_context = MarketContext(
                    current_price=scenario['price'],
                    volume_24h=1000000.0,
                    volatility=scenario['volatility'],
                    trend_direction=scenario['trend'],
                    market_phase='MARKUP',
                    timestamp=datetime.now()
                )
                
                try:
                    result = self.engine.calculate_safe_leverage(
                        symbol=f"TEST_{scenario['name'].replace(' ', '_')}",
                        support_levels=self.mock_support_levels,
                        resistance_levels=self.mock_resistance_levels,
                        breakout_predictions=self.mock_breakout_predictions,
                        btc_correlation_risk=self.mock_btc_correlation_risk,
                        market_context=test_context
                    )
                    
                    self.assertIsInstance(result, LeverageRecommendation,
                                        f"{scenario['name']}でLeverageRecommendationが返されませんでした")
                    
                    print(f"✅ シナリオ '{scenario['name']}' テスト完了")
                    
                except NameError as e:
                    if "'market_context' is not defined" in str(e):
                        self.fail(f"シナリオ '{scenario['name']}' でNameError再発！: {e}")
                    else:
                        raise e

def run_nameerror_prevention_tests():
    """NameError再発防止テストの実行"""
    print("🔍 NameError再発防止テスト開始")
    print("=" * 60)
    
    # テストスイートを作成
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNameErrorPrevention)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー:")
    print(f"   実行テスト数: {result.testsRun}")
    print(f"   失敗: {len(result.failures)}")
    print(f"   エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ 全てのNameError再発防止テストに合格しました！")
        print("   修正されたバグが再発する可能性は低いです。")
    else:
        print("❌ 一部のテストが失敗しました。")
        print("   NameErrorバグが再発する可能性があります。")
        
        if result.failures:
            print("\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
                
        if result.errors:
            print("\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    run_nameerror_prevention_tests()