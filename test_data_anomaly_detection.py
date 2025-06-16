#!/usr/bin/env python3
"""
データ異常検知専用テストスイート

今回発見されたデータ異常の検知・防止メカニズムをテスト:
1. 非現実的利益率の検知
2. 価格参照整合性の確認
3. 損切り・利確ロジックの妥当性
4. 時間軸妥当性の確認
5. 異常値自動検出システム
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import warnings

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class DataAnomalyDetector:
    """データ異常検知クラス"""
    
    @staticmethod
    def detect_unrealistic_profit_rate(entry_price: float, exit_price: float, 
                                       duration_minutes: int, threshold_annual_rate: float = 1000.0) -> tuple:
        """非現実的利益率の検知"""
        if entry_price <= 0 or exit_price <= 0 or duration_minutes <= 0:
            return True, "価格または期間が無効です"
        
        profit_rate = (exit_price - entry_price) / entry_price
        profit_percentage = profit_rate * 100
        
        # 年利換算
        minutes_per_year = 365 * 24 * 60
        annual_rate_percentage = profit_percentage * (minutes_per_year / duration_minutes)
        
        # 短期間での高利益率を検知
        anomalies = []
        
        if duration_minutes < 60 and profit_percentage > 20:
            anomalies.append(f"1時間未満で{profit_percentage:.1f}%の利益")
        
        if duration_minutes < 120 and profit_percentage > 40:
            anomalies.append(f"2時間未満で{profit_percentage:.1f}%の利益")
        
        if duration_minutes < 1440 and profit_percentage > 100:  # 24時間未満で100%超
            anomalies.append(f"24時間未満で{profit_percentage:.1f}%の利益")
        
        if annual_rate_percentage > threshold_annual_rate:
            anomalies.append(f"年利換算{annual_rate_percentage:.0f}%")
        
        is_anomaly = len(anomalies) > 0
        message = "; ".join(anomalies) if anomalies else "正常"
        
        return is_anomaly, message
    
    @staticmethod
    def validate_long_position_logic(entry_price: float, stop_loss_price: float, 
                                   take_profit_price: float) -> tuple:
        """ロングポジションの論理妥当性検証"""
        errors = []
        
        if stop_loss_price >= entry_price:
            errors.append(f"損切り価格({stop_loss_price:.2f})がエントリー価格({entry_price:.2f})以上")
        
        if take_profit_price <= entry_price:
            errors.append(f"利確価格({take_profit_price:.2f})がエントリー価格({entry_price:.2f})以下")
        
        if stop_loss_price >= take_profit_price:
            errors.append(f"損切り価格({stop_loss_price:.2f})が利確価格({take_profit_price:.2f})以上")
        
        # 異常に大きな価格差の検知
        loss_percentage = ((entry_price - stop_loss_price) / entry_price) * 100
        profit_percentage = ((take_profit_price - entry_price) / entry_price) * 100
        
        if loss_percentage > 50:
            errors.append(f"損切り幅が異常に大きい({loss_percentage:.1f}%)")
        
        if profit_percentage > 200:
            errors.append(f"利確幅が異常に大きい({profit_percentage:.1f}%)")
        
        is_valid = len(errors) == 0
        message = "; ".join(errors) if errors else "正常"
        
        return is_valid, message
    
    @staticmethod
    def check_price_reference_consistency(current_price: float, entry_price: float, 
                                        tolerance_percentage: float = 5.0) -> tuple:
        """価格参照の整合性確認"""
        if current_price <= 0 or entry_price <= 0:
            return False, "価格が無効です"
        
        price_diff_percentage = abs(current_price - entry_price) / entry_price * 100
        
        if price_diff_percentage > tolerance_percentage:
            return False, f"current_price({current_price:.2f})とentry_price({entry_price:.2f})の差が{price_diff_percentage:.1f}%で許容範囲({tolerance_percentage}%)を超過"
        
        return True, "整合性あり"
    
    @staticmethod
    def validate_time_sequence(entry_time: datetime, exit_time: datetime, 
                             market_data_start: datetime, market_data_end: datetime) -> tuple:
        """時系列データの妥当性確認"""
        errors = []
        
        if exit_time <= entry_time:
            errors.append("エグジット時刻がエントリー時刻以前")
        
        if entry_time < market_data_start:
            errors.append("エントリー時刻が市場データ開始前")
        
        if exit_time > market_data_end:
            errors.append("エグジット時刻が市場データ終了後")
        
        # 異常に短い取引時間
        duration = exit_time - entry_time
        if duration.total_seconds() < 60:  # 1分未満
            errors.append(f"取引時間が異常に短い({duration.total_seconds():.0f}秒)")
        
        is_valid = len(errors) == 0
        message = "; ".join(errors) if errors else "正常"
        
        return is_valid, message


class TestUnrealisticProfitDetection(unittest.TestCase):
    """非現実的利益率検知のテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.detector = DataAnomalyDetector()
    
    def test_eth_anomaly_case(self):
        """実際のETH異常ケースの検知テスト"""
        # 実際に発見された異常ケース
        entry_price = 1932.0
        exit_price = 2812.0
        duration_minutes = 50
        
        is_anomaly, message = self.detector.detect_unrealistic_profit_rate(
            entry_price, exit_price, duration_minutes
        )
        
        self.assertTrue(is_anomaly, "ETH異常ケースが検知されない")
        self.assertIn("45", message, "利益率45%が検知されない")
        self.assertIn("時間未満", message, "短時間高利益が検知されない")
        
        # 利益率の計算確認
        profit_rate = (exit_price - entry_price) / entry_price
        self.assertAlmostEqual(profit_rate * 100, 45.5, delta=0.1, 
                              msg="利益率計算が正しくない")
        
        print(f"✅ ETH異常ケース検知: {message}")
    
    def test_normal_profit_cases(self):
        """正常な利益ケースのテスト"""
        normal_cases = [
            {
                'name': '1日で5%利益',
                'entry_price': 50000,
                'exit_price': 52500,
                'duration_minutes': 1440  # 24時間
            },
            {
                'name': '1週間で20%利益',
                'entry_price': 50000,
                'exit_price': 60000,
                'duration_minutes': 7 * 1440  # 1週間
            },
            {
                'name': '1時間で3%利益',
                'entry_price': 50000,
                'exit_price': 51500,
                'duration_minutes': 60
            }
        ]
        
        for case in normal_cases:
            with self.subTest(case=case['name']):
                is_anomaly, message = self.detector.detect_unrealistic_profit_rate(
                    case['entry_price'], case['exit_price'], case['duration_minutes']
                )
                
                self.assertFalse(is_anomaly, f"{case['name']}が異常と判定された: {message}")
                
                print(f"✅ 正常ケース: {case['name']}")
    
    def test_extreme_anomaly_cases(self):
        """極端な異常ケースのテスト"""
        extreme_cases = [
            {
                'name': '10分で100%利益',
                'entry_price': 50000,
                'exit_price': 100000,
                'duration_minutes': 10,
                'expected_keywords': ['10', '100%', '分未満']
            },
            {
                'name': '1時間で200%利益',
                'entry_price': 50000,
                'exit_price': 150000,
                'duration_minutes': 60,
                'expected_keywords': ['200%', '時間未満']
            },
            {
                'name': '30分で50%利益',
                'entry_price': 1000,
                'exit_price': 1500,
                'duration_minutes': 30,
                'expected_keywords': ['50%', '分未満']
            }
        ]
        
        for case in extreme_cases:
            with self.subTest(case=case['name']):
                is_anomaly, message = self.detector.detect_unrealistic_profit_rate(
                    case['entry_price'], case['exit_price'], case['duration_minutes']
                )
                
                self.assertTrue(is_anomaly, f"{case['name']}が検知されない")
                
                # 期待されるキーワードの確認
                for keyword in case['expected_keywords']:
                    self.assertIn(keyword, message, 
                                f"{case['name']}のメッセージに'{keyword}'が含まれない: {message}")
                
                print(f"✅ 極端異常ケース検知: {case['name']} - {message}")
    
    def test_annual_rate_calculation(self):
        """年利換算計算の確認"""
        # 50分で45%の場合
        entry_price = 1932.0
        exit_price = 2812.0
        duration_minutes = 50
        
        profit_rate = (exit_price - entry_price) / entry_price
        minutes_per_year = 365 * 24 * 60
        annual_rate = profit_rate * (minutes_per_year / duration_minutes)
        
        # 年利が異常に高いことを確認
        self.assertGreater(annual_rate, 10, "年利換算が10倍(1000%)未満")
        
        # 実際には約468倍(46,800%)になるはず
        expected_annual_rate = 0.455 * (525600 / 50)
        self.assertAlmostEqual(annual_rate, expected_annual_rate, delta=0.1,
                              msg="年利換算計算が正しくない")
        
        print(f"✅ 年利換算: {annual_rate:.0f}倍({annual_rate*100:.0f}%)")
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        edge_cases = [
            {
                'name': 'ゼロ価格',
                'entry_price': 0,
                'exit_price': 100,
                'duration_minutes': 60,
                'should_be_anomaly': True
            },
            {
                'name': '負の価格',
                'entry_price': -100,
                'exit_price': 100,
                'duration_minutes': 60,
                'should_be_anomaly': True
            },
            {
                'name': 'ゼロ期間',
                'entry_price': 100,
                'exit_price': 200,
                'duration_minutes': 0,
                'should_be_anomaly': True
            },
            {
                'name': '損失ケース',
                'entry_price': 100,
                'exit_price': 50,
                'duration_minutes': 60,
                'should_be_anomaly': False  # 損失は異常ではない
            }
        ]
        
        for case in edge_cases:
            with self.subTest(case=case['name']):
                is_anomaly, message = self.detector.detect_unrealistic_profit_rate(
                    case['entry_price'], case['exit_price'], case['duration_minutes']
                )
                
                if case['should_be_anomaly']:
                    self.assertTrue(is_anomaly, f"{case['name']}が異常として検知されない")
                else:
                    self.assertFalse(is_anomaly, f"{case['name']}が異常として誤検知された")
                
                print(f"✅ エッジケース: {case['name']} - {message}")


class TestPositionLogicValidation(unittest.TestCase):
    """ポジション論理妥当性のテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.detector = DataAnomalyDetector()
    
    def test_eth_anomaly_position_logic(self):
        """ETH異常ケースのポジション論理テスト"""
        # 実際に発見された異常ケース
        entry_price = 1932.0
        stop_loss_price = 2578.0  # エントリーより33%高い（異常）
        take_profit_price = 2782.0  # エントリーより44%高い
        
        is_valid, message = self.detector.validate_long_position_logic(
            entry_price, stop_loss_price, take_profit_price
        )
        
        self.assertFalse(is_valid, "ETH異常ポジション論理が検知されない")
        self.assertIn("損切り価格", message, "損切り価格の異常が検知されない")
        self.assertIn("以上", message, "価格関係の異常が検知されない")
        
        print(f"✅ ETH異常ポジション論理検知: {message}")
    
    def test_valid_long_position_logic(self):
        """正常なロングポジション論理のテスト"""
        valid_cases = [
            {
                'name': '標準的なロングポジション',
                'entry_price': 50000,
                'stop_loss_price': 47500,  # 5%下
                'take_profit_price': 55000  # 10%上
            },
            {
                'name': '保守的なロングポジション',
                'entry_price': 50000,
                'stop_loss_price': 48500,  # 3%下
                'take_profit_price': 52500  # 5%上
            },
            {
                'name': '積極的なロングポジション',
                'entry_price': 50000,
                'stop_loss_price': 45000,  # 10%下
                'take_profit_price': 60000  # 20%上
            }
        ]
        
        for case in valid_cases:
            with self.subTest(case=case['name']):
                is_valid, message = self.detector.validate_long_position_logic(
                    case['entry_price'], case['stop_loss_price'], case['take_profit_price']
                )
                
                self.assertTrue(is_valid, f"{case['name']}が無効と判定された: {message}")
                self.assertEqual(message, "正常", f"{case['name']}のメッセージが正常でない")
                
                print(f"✅ 正常ポジション論理: {case['name']}")
    
    def test_invalid_position_logic_cases(self):
        """無効なポジション論理のテスト"""
        invalid_cases = [
            {
                'name': '損切りがエントリーより上',
                'entry_price': 50000,
                'stop_loss_price': 52000,  # エントリーより上（異常）
                'take_profit_price': 55000,
                'expected_keyword': '損切り価格'
            },
            {
                'name': '利確がエントリーより下',
                'entry_price': 50000,
                'stop_loss_price': 47000,
                'take_profit_price': 48000,  # エントリーより下（異常）
                'expected_keyword': '利確価格'
            },
            {
                'name': '損切りが利確より上',
                'entry_price': 50000,
                'stop_loss_price': 52000,
                'take_profit_price': 51000,  # 損切りより下（異常）
                'expected_keyword': '損切り価格'
            },
            {
                'name': '異常に大きな損切り幅',
                'entry_price': 50000,
                'stop_loss_price': 20000,  # 60%下（異常）
                'take_profit_price': 55000,
                'expected_keyword': '損切り幅'
            },
            {
                'name': '異常に大きな利確幅',
                'entry_price': 50000,
                'stop_loss_price': 47000,
                'take_profit_price': 200000,  # 300%上（異常）
                'expected_keyword': '利確幅'
            }
        ]
        
        for case in invalid_cases:
            with self.subTest(case=case['name']):
                is_valid, message = self.detector.validate_long_position_logic(
                    case['entry_price'], case['stop_loss_price'], case['take_profit_price']
                )
                
                self.assertFalse(is_valid, f"{case['name']}が有効と判定された")
                self.assertIn(case['expected_keyword'], message, 
                            f"{case['name']}のメッセージに'{case['expected_keyword']}'が含まれない: {message}")
                
                print(f"✅ 無効ポジション論理検知: {case['name']} - {message}")


class TestPriceReferenceConsistency(unittest.TestCase):
    """価格参照整合性のテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.detector = DataAnomalyDetector()
    
    def test_eth_price_inconsistency(self):
        """ETH価格不整合ケースのテスト"""
        # 実際のケースをシミュレート
        current_price = 3950.0  # 分析時の価格
        entry_price = 3970.0    # 実際の市場価格
        
        is_consistent, message = self.detector.check_price_reference_consistency(
            current_price, entry_price, tolerance_percentage=2.0
        )
        
        # この場合は許容範囲内（差は約0.5%）
        self.assertTrue(is_consistent, f"ETH価格整合性テストが失敗: {message}")
        
        print(f"✅ ETH価格整合性（許容範囲内）: {message}")
    
    def test_severe_price_inconsistency(self):
        """深刻な価格不整合のテスト"""
        inconsistent_cases = [
            {
                'name': '10%の価格差',
                'current_price': 50000,
                'entry_price': 55000,
                'tolerance': 5.0,
                'should_be_inconsistent': True
            },
            {
                'name': '50%の価格差',
                'current_price': 50000,
                'entry_price': 75000,
                'tolerance': 5.0,
                'should_be_inconsistent': True
            },
            {
                'name': '許容範囲内の価格差',
                'current_price': 50000,
                'entry_price': 51000,
                'tolerance': 5.0,
                'should_be_inconsistent': False
            }
        ]
        
        for case in inconsistent_cases:
            with self.subTest(case=case['name']):
                is_consistent, message = self.detector.check_price_reference_consistency(
                    case['current_price'], case['entry_price'], case['tolerance']
                )
                
                if case['should_be_inconsistent']:
                    self.assertFalse(is_consistent, f"{case['name']}の不整合が検知されない")
                    self.assertIn("超過", message, f"{case['name']}のエラーメッセージが不適切")
                else:
                    self.assertTrue(is_consistent, f"{case['name']}が不整合と誤判定された")
                
                print(f"✅ 価格整合性ケース: {case['name']} - {message}")
    
    def test_extreme_price_differences(self):
        """極端な価格差のテスト"""
        # ETHの異常クローズ価格ケース
        current_price = 3950.0
        close_price = 5739.36
        
        is_consistent, message = self.detector.check_price_reference_consistency(
            current_price, close_price, tolerance_percentage=5.0
        )
        
        self.assertFalse(is_consistent, "極端な価格差が検知されない")
        
        # 価格差を計算
        price_diff_pct = abs(current_price - close_price) / close_price * 100
        self.assertGreater(price_diff_pct, 30, "価格差が期待値より小さい")
        
        print(f"✅ 極端価格差検知: {message}")


class TestTimeSequenceValidation(unittest.TestCase):
    """時系列妥当性のテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.detector = DataAnomalyDetector()
        
        # 基準時刻設定
        self.market_start = datetime(2024, 1, 1, 9, 0, 0)
        self.market_end = datetime(2024, 1, 1, 17, 0, 0)
    
    def test_valid_time_sequence(self):
        """正常な時系列のテスト"""
        entry_time = datetime(2024, 1, 1, 10, 0, 0)
        exit_time = datetime(2024, 1, 1, 11, 30, 0)  # 1.5時間後
        
        is_valid, message = self.detector.validate_time_sequence(
            entry_time, exit_time, self.market_start, self.market_end
        )
        
        self.assertTrue(is_valid, f"正常な時系列が無効と判定された: {message}")
        self.assertEqual(message, "正常")
        
        print("✅ 正常時系列確認")
    
    def test_invalid_time_sequences(self):
        """無効な時系列のテスト"""
        invalid_cases = [
            {
                'name': 'エグジットがエントリーより前',
                'entry_time': datetime(2024, 1, 1, 11, 0, 0),
                'exit_time': datetime(2024, 1, 1, 10, 0, 0),
                'expected_keyword': 'エグジット時刻'
            },
            {
                'name': 'エントリーが市場開始前',
                'entry_time': datetime(2024, 1, 1, 8, 0, 0),
                'exit_time': datetime(2024, 1, 1, 10, 0, 0),
                'expected_keyword': 'エントリー時刻'
            },
            {
                'name': 'エグジットが市場終了後',
                'entry_time': datetime(2024, 1, 1, 16, 0, 0),
                'exit_time': datetime(2024, 1, 1, 18, 0, 0),
                'expected_keyword': 'エグジット時刻'
            },
            {
                'name': '異常に短い取引時間',
                'entry_time': datetime(2024, 1, 1, 10, 0, 0),
                'exit_time': datetime(2024, 1, 1, 10, 0, 30),  # 30秒
                'expected_keyword': '異常に短い'
            }
        ]
        
        for case in invalid_cases:
            with self.subTest(case=case['name']):
                is_valid, message = self.detector.validate_time_sequence(
                    case['entry_time'], case['exit_time'], 
                    self.market_start, self.market_end
                )
                
                self.assertFalse(is_valid, f"{case['name']}が有効と判定された")
                self.assertIn(case['expected_keyword'], message,
                            f"{case['name']}のメッセージに'{case['expected_keyword']}'が含まれない: {message}")
                
                print(f"✅ 無効時系列検知: {case['name']} - {message}")


class TestIntegratedAnomalyDetection(unittest.TestCase):
    """統合異常検知のテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.detector = DataAnomalyDetector()
    
    def test_eth_complete_anomaly_analysis(self):
        """ETHケースの完全異常分析テスト"""
        # ETHの実際の異常ケースの全要素
        entry_price = 1932.0
        exit_price = 2812.0
        stop_loss_price = 2578.0
        take_profit_price = 2782.0
        duration_minutes = 50
        current_price = 3950.0
        
        # 1. 利益率異常検知
        profit_anomaly, profit_msg = self.detector.detect_unrealistic_profit_rate(
            entry_price, exit_price, duration_minutes
        )
        
        # 2. ポジション論理異常検知
        position_valid, position_msg = self.detector.validate_long_position_logic(
            entry_price, stop_loss_price, take_profit_price
        )
        
        # 3. 価格参照整合性（entry vs exit）
        price_consistent, price_msg = self.detector.check_price_reference_consistency(
            entry_price, exit_price, tolerance_percentage=5.0
        )
        
        # 結果の確認
        self.assertTrue(profit_anomaly, "利益率異常が検知されない")
        self.assertFalse(position_valid, "ポジション論理異常が検知されない")
        self.assertFalse(price_consistent, "価格整合性異常が検知されない")
        
        # 統合分析結果
        total_anomalies = sum([profit_anomaly, not position_valid, not price_consistent])
        
        print("✅ ETH完全異常分析:")
        print(f"  利益率異常: {profit_msg}")
        print(f"  ポジション論理: {position_msg}")
        print(f"  価格整合性: {price_msg}")
        print(f"  合計異常数: {total_anomalies}/3")
        
        self.assertEqual(total_anomalies, 3, "すべての異常が検知されていない")
    
    def test_anomaly_detection_performance(self):
        """異常検知性能テスト"""
        import time
        
        # 大量のテストケース生成
        test_cases = []
        np.random.seed(42)
        
        for _ in range(1000):
            entry_price = np.random.uniform(1000, 100000)
            profit_rate = np.random.uniform(-0.5, 2.0)  # -50%から200%
            exit_price = entry_price * (1 + profit_rate)
            duration_minutes = np.random.randint(1, 1440)  # 1分から24時間
            
            test_cases.append((entry_price, exit_price, duration_minutes))
        
        # 処理時間測定
        start_time = time.time()
        
        anomaly_count = 0
        for entry_price, exit_price, duration_minutes in test_cases:
            is_anomaly, _ = self.detector.detect_unrealistic_profit_rate(
                entry_price, exit_price, duration_minutes
            )
            if is_anomaly:
                anomaly_count += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 性能要件確認
        self.assertLess(processing_time, 1.0, f"処理時間が長すぎます: {processing_time:.3f}秒")
        
        # 異常検知率の妥当性確認
        anomaly_rate = anomaly_count / len(test_cases)
        self.assertGreater(anomaly_rate, 0.01, "異常検知率が低すぎます")
        self.assertLess(anomaly_rate, 0.5, "異常検知率が高すぎます")
        
        print(f"✅ 性能テスト: {len(test_cases)}ケースを{processing_time:.3f}秒で処理")
        print(f"  異常検知率: {anomaly_rate:.1%} ({anomaly_count}件)")


def run_data_anomaly_detection_tests():
    """データ異常検知テストの実行"""
    print("🚨 データ異常検知専用テストスイート")
    print("=" * 80)
    
    # テストスイート作成
    test_suite = unittest.TestSuite()
    
    # テストクラス追加
    test_classes = [
        TestUnrealisticProfitDetection,
        TestPositionLogicValidation,
        TestPriceReferenceConsistency,
        TestTimeSequenceValidation,
        TestIntegratedAnomalyDetection
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 データ異常検知 テスト結果")
    print("=" * 80)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    print(f"スキップ: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback_text in result.failures:
            print(f"  - {test}")
            lines = traceback_text.split('\n')
            for line in lines:
                if 'AssertionError:' in line:
                    print(f"    理由: {line.split('AssertionError: ')[-1]}")
                    break
    
    if result.errors:
        print("\n💥 エラーが発生したテスト:")
        for test, traceback_text in result.errors:
            print(f"  - {test}")
            lines = traceback_text.split('\n')
            for line in reversed(lines):
                if line.strip() and not line.startswith(' '):
                    print(f"    エラー: {line}")
                    break
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0
    print(f"\n成功率: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ データ異常検知の全テストが成功!")
        print("異常検知メカニズムが正常に動作しています。")
        print("\n確認された機能:")
        print("  🚨 非現実的利益率の検知")
        print("  🔍 ポジション論理の妥当性検証")
        print("  📊 価格参照整合性の確認")
        print("  ⏰ 時系列データの妥当性確認")
        print("  🔄 統合異常検知システム")
        print("  ⚡ 高性能な大量データ処理")
    else:
        print("\n⚠️ 一部のデータ異常検知テストが失敗!")
        print("異常検知メカニズムに問題があります。")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_data_anomaly_detection_tests()
    exit(0 if success else 1)