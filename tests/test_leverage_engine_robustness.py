#!/usr/bin/env python3
"""
レバレッジエンジン堅牢性テスト

NameErrorや他の一般的なエラーを事前に検知し、
システムの安定性を継続的に監視するテストスイート。
"""

import unittest
import sys
import logging
import io
from pathlib import Path
from unittest.mock import Mock, patch

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from engines.leverage_decision_engine import CoreLeverageDecisionEngine
from interfaces.data_types import (
    SupportResistanceLevel, BreakoutPrediction, BTCCorrelationRisk,
    MarketContext, LeverageRecommendation
)

class TestLeverageEngineRobustness(unittest.TestCase):
    """レバレッジエンジン堅牢性テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.engine = CoreLeverageDecisionEngine()
        self.log_capture = io.StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        self.log_handler.setLevel(logging.ERROR)
        
        # ログ監視を設定
        self.logger = logging.getLogger('engines.leverage_decision_engine')
        self.logger.addHandler(self.log_handler)
        
        # 標準的なテストデータ
        self.setup_standard_test_data()
    
    def tearDown(self):
        """テスト後処理"""
        self.logger.removeHandler(self.log_handler)
    
    def setup_standard_test_data(self):
        """標準的なテストデータをセットアップ"""
        from datetime import datetime
        now = datetime.now()
        
        self.support_levels = [
            SupportResistanceLevel(
                price=95.0, strength=0.8, touch_count=3,
                level_type='support', first_touch=now, last_touch=now,
                volume_at_level=1000.0, distance_from_current=5.0
            )
        ]
        
        self.resistance_levels = [
            SupportResistanceLevel(
                price=105.0, strength=0.7, touch_count=2,
                level_type='resistance', first_touch=now, last_touch=now,
                volume_at_level=800.0, distance_from_current=5.0
            )
        ]
        
        self.breakout_predictions = [
            BreakoutPrediction(
                level=self.support_levels[0],
                breakout_probability=0.3, bounce_probability=0.7,
                prediction_confidence=0.8, predicted_price_target=100.0,
                time_horizon_minutes=60, model_name='test_model'
            )
        ]
        
        self.btc_correlation_risk = BTCCorrelationRisk(
            symbol='TEST', btc_drop_scenario=-10.0,
            predicted_altcoin_drop={60: -5.0, 120: -10.0},
            correlation_strength=0.8, risk_level='MEDIUM',
            liquidation_risk={60: 0.1, 120: 0.2}
        )
        
        self.market_context = MarketContext(
            current_price=100.0, volume_24h=1000000.0, volatility=0.02,
            trend_direction='BULLISH', market_phase='MARKUP', timestamp=now
        )
    
    def test_nameerror_regression_detection(self):
        """NameError回帰検知テスト"""
        print("🔍 NameError回帰検知テスト実行中...")
        
        # ログをクリア
        self.log_capture.seek(0)
        self.log_capture.truncate(0)
        
        try:
            result = self.engine.calculate_safe_leverage(
                symbol='NAMEERROR_TEST',
                support_levels=self.support_levels,
                resistance_levels=self.resistance_levels,
                breakout_predictions=self.breakout_predictions,
                btc_correlation_risk=self.btc_correlation_risk,
                market_context=self.market_context
            )
            
            # ログ内容をチェック
            log_content = self.log_capture.getvalue()
            
            # NameErrorの兆候をチェック
            name_error_indicators = [
                "NameError",
                "name 'market_context' is not defined",
                "AttributeError",
                "UnboundLocalError"
            ]
            
            for indicator in name_error_indicators:
                self.assertNotIn(indicator, log_content,
                               f"NameError関連のエラーが検出されました: {indicator}")
            
            # 正常な結果が返されることを確認
            self.assertIsInstance(result, LeverageRecommendation,
                                "LeverageRecommendationが返されませんでした")
            
            print(f"✅ NameError回帰検知テスト完了 - エラーなし")
            
        except NameError as e:
            self.fail(f"NameErrorが再発しました: {e}")
        except Exception as e:
            # 他の例外もチェック
            if "market_context" in str(e):
                self.fail(f"market_context関連のエラーが発生: {e}")
            else:
                raise e
    
    def test_parameter_validation_robustness(self):
        """パラメータ検証堅牢性テスト"""
        print("🔍 パラメータ検証堅牢性テスト実行中...")
        
        from datetime import datetime
        
        # 様々な不正なパラメータでテスト
        test_cases = [
            {
                'name': 'None market_context',
                'market_context': None,
                'expect_fallback': True
            },
            {
                'name': 'Invalid volatility',
                'market_context': MarketContext(
                    current_price=100.0, volume_24h=1000000.0, volatility=-1.0,
                    trend_direction='BULLISH', market_phase='MARKUP', timestamp=datetime.now()
                ),
                'expect_fallback': False  # 負のボラティリティでも計算可能
            },
            {
                'name': 'Zero price',
                'market_context': MarketContext(
                    current_price=0.0, volume_24h=1000000.0, volatility=0.02,
                    trend_direction='BULLISH', market_phase='MARKUP', timestamp=datetime.now()
                ),
                'expect_fallback': True
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case['name']):
                print(f"  - テストケース: {test_case['name']}")
                
                # ログをクリア
                self.log_capture.seek(0)
                self.log_capture.truncate(0)
                
                try:
                    if test_case['market_context'] is None:
                        # Noneの場合はTypeErrorが期待される
                        with self.assertRaises(Exception):
                            self.engine.calculate_safe_leverage(
                                symbol='PARAM_TEST',
                                support_levels=self.support_levels,
                                resistance_levels=self.resistance_levels,
                                breakout_predictions=self.breakout_predictions,
                                btc_correlation_risk=self.btc_correlation_risk,
                                market_context=test_case['market_context']
                            )
                    else:
                        result = self.engine.calculate_safe_leverage(
                            symbol='PARAM_TEST',
                            support_levels=self.support_levels,
                            resistance_levels=self.resistance_levels,
                            breakout_predictions=self.breakout_predictions,
                            btc_correlation_risk=self.btc_correlation_risk,
                            market_context=test_case['market_context']
                        )
                        
                        self.assertIsInstance(result, LeverageRecommendation)
                        
                        if test_case['expect_fallback']:
                            # フォールバック値かチェック
                            self.assertEqual(result.confidence_level, 0.1,
                                           "フォールバック信頼度が設定されていません")
                
                except NameError as e:
                    self.fail(f"NameErrorが発生: {test_case['name']} - {e}")
        
        print(f"✅ パラメータ検証堅牢性テスト完了")
    
    def test_edge_case_robustness(self):
        """エッジケース堅牢性テスト"""
        print("🔍 エッジケース堅牢性テスト実行中...")
        
        from datetime import datetime
        
        edge_cases = [
            {
                'name': '極端に高いボラティリティ',
                'volatility': 1.0,  # 100%ボラティリティ
                'price': 100.0
            },
            {
                'name': '極端に低いボラティリティ',
                'volatility': 0.0001,  # 0.01%ボラティリティ
                'price': 100.0
            },
            {
                'name': '非常に高い価格',
                'volatility': 0.02,
                'price': 1000000.0
            },
            {
                'name': '非常に低い価格',
                'volatility': 0.02,
                'price': 0.0001
            }
        ]
        
        for case in edge_cases:
            with self.subTest(case=case['name']):
                print(f"  - エッジケース: {case['name']}")
                
                edge_market_context = MarketContext(
                    current_price=case['price'],
                    volume_24h=1000000.0,
                    volatility=case['volatility'],
                    trend_direction='SIDEWAYS',
                    market_phase='ACCUMULATION',
                    timestamp=datetime.now()
                )
                
                # ログをクリア
                self.log_capture.seek(0)
                self.log_capture.truncate(0)
                
                try:
                    result = self.engine.calculate_safe_leverage(
                        symbol=f"EDGE_TEST_{case['name'].replace(' ', '_')}",
                        support_levels=self.support_levels,
                        resistance_levels=self.resistance_levels,
                        breakout_predictions=self.breakout_predictions,
                        btc_correlation_risk=self.btc_correlation_risk,
                        market_context=edge_market_context
                    )
                    
                    self.assertIsInstance(result, LeverageRecommendation)
                    
                    # NameError関連のエラーがないことを確認
                    log_content = self.log_capture.getvalue()
                    self.assertNotIn("NameError", log_content)
                    self.assertNotIn("market_context", log_content.lower())
                    
                except NameError as e:
                    self.fail(f"エッジケース {case['name']} でNameError: {e}")
        
        print(f"✅ エッジケース堅牢性テスト完了")
    
    def test_concurrent_access_safety(self):
        """並行アクセス安全性テスト"""
        print("🔍 並行アクセス安全性テスト実行中...")
        
        import threading
        import time
        from datetime import datetime
        
        results = []
        errors = []
        
        def run_analysis(thread_id):
            """スレッドで実行する分析"""
            try:
                context = MarketContext(
                    current_price=100.0 + thread_id,  # 各スレッドで異なる価格
                    volume_24h=1000000.0,
                    volatility=0.02 + (thread_id * 0.01),  # 各スレッドで異なるボラティリティ
                    trend_direction='BULLISH',
                    market_phase='MARKUP',
                    timestamp=datetime.now()
                )
                
                result = self.engine.calculate_safe_leverage(
                    symbol=f'THREAD_TEST_{thread_id}',
                    support_levels=self.support_levels,
                    resistance_levels=self.resistance_levels,
                    breakout_predictions=self.breakout_predictions,
                    btc_correlation_risk=self.btc_correlation_risk,
                    market_context=context
                )
                
                results.append((thread_id, result))
                
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 複数スレッドで同時実行
        threads = []
        for i in range(5):
            thread = threading.Thread(target=run_analysis, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 結果を検証
        self.assertEqual(len(results), 5, "全てのスレッドが成功していません")
        self.assertEqual(len(errors), 0, f"エラーが発生しました: {errors}")
        
        # NameError関連のエラーがないことを確認
        for thread_id, error in errors:
            self.assertNotIn("NameError", error)
            self.assertNotIn("market_context", error)
        
        print(f"✅ 並行アクセス安全性テスト完了 - {len(results)}スレッド成功")

def run_robustness_tests():
    """堅牢性テストの実行"""
    print("🔧 レバレッジエンジン堅牢性テスト開始")
    print("=" * 60)
    
    # テストスイートを作成
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLeverageEngineRobustness)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📋 堅牢性テスト結果:")
    print(f"   実行テスト数: {result.testsRun}")
    print(f"   失敗: {len(result.failures)}")
    print(f"   エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ 全ての堅牢性テストに合格しました！")
        print("   システムは安定動作しています。")
    else:
        print("❌ 一部のテストが失敗しました。")
        print("   システムの安定性に問題がある可能性があります。")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    run_robustness_tests()