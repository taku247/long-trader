#!/usr/bin/env python3
"""
実データ利用PreparedDataクラスのテストケース

TDDアプローチで実装前にテストを作成し、要件を明確化する
"""

import unittest
import tempfile
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# BaseTestを継承してテスト環境の安全性を確保
try:
    from tests_organized.base_test import BaseTest
    USE_BASE_TEST = True
except ImportError:
    USE_BASE_TEST = False
    print("⚠️ BaseTestが利用できません。標準のunittestを使用します。")


class TestRealPreparedData(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """実データ利用PreparedDataクラスのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        if USE_BASE_TEST:
            super().setUp()
        
        # テスト用の一時ディレクトリ
        self.test_dir = tempfile.mkdtemp()
        
        # テスト用のOHLCVデータ生成
        self.test_ohlcv_data = self._create_test_ohlcv_data()
        
        # 評価時点
        self.test_evaluation_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    
    def tearDown(self):
        """テスト後清理"""
        if USE_BASE_TEST:
            super().tearDown()
        
        # 一時ディレクトリの削除
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_ohlcv_data(self):
        """テスト用OHLCVデータ生成（1分足、1000本）"""
        base_time = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        base_price = 50000.0
        
        data = []
        for i in range(1000):
            timestamp = base_time + timedelta(minutes=i)
            
            # 価格変動をシミュレート（サイン波 + ノイズ）
            price_variation = np.sin(i * 0.01) * 500 + np.random.normal(0, 50)
            close_price = base_price + price_variation
            
            # OHLCを生成
            open_price = close_price + np.random.normal(0, 10)
            high_price = max(open_price, close_price) + abs(np.random.normal(0, 20))
            low_price = min(open_price, close_price) - abs(np.random.normal(0, 20))
            
            # ボリューム（時間帯による変動）
            hour = timestamp.hour
            base_volume = 10000000  # ベースボリュームを増やす
            if 9 <= hour <= 17:  # 活発な時間帯
                volume = base_volume * np.random.uniform(1.5, 3.0)
            else:
                volume = base_volume * np.random.uniform(0.8, 1.2)
            
            data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def test_real_prepared_data_creation(self):
        """RealPreparedDataクラスの生成テスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        # 基本属性の確認
        self.assertIsNotNone(prepared_data)
        self.assertEqual(len(prepared_data.ohlcv_data), 1000)
        self.assertIn('timestamp', prepared_data.ohlcv_data.columns)
        self.assertIn('close', prepared_data.ohlcv_data.columns)
    
    def test_get_price_at(self):
        """特定時点の価格取得テスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        # 1. 正確な時点での価格取得
        exact_time = self.test_ohlcv_data.iloc[100]['timestamp']
        expected_price = self.test_ohlcv_data.iloc[100]['close']
        actual_price = prepared_data.get_price_at(exact_time)
        self.assertAlmostEqual(actual_price, expected_price, places=2)
        
        # 2. 補間が必要な時点での価格取得（2つのキャンドルの間）
        between_time = exact_time + timedelta(seconds=30)
        interpolated_price = prepared_data.get_price_at(between_time)
        self.assertIsNotNone(interpolated_price)
        self.assertIsInstance(interpolated_price, float)
        
        # 3. データ範囲外の時点（エラーハンドリング）
        future_time = self.test_ohlcv_data.iloc[-1]['timestamp'] + timedelta(hours=1)
        with self.assertRaises(ValueError):
            prepared_data.get_price_at(future_time)
    
    def test_get_volume_at(self):
        """特定時点のボリューム取得テスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        # 正確な時点でのボリューム取得
        exact_time = self.test_ohlcv_data.iloc[200]['timestamp']
        expected_volume = self.test_ohlcv_data.iloc[200]['volume']
        actual_volume = prepared_data.get_volume_at(exact_time)
        self.assertAlmostEqual(actual_volume, expected_volume, places=2)
    
    def test_get_ohlcv_until(self):
        """指定時点までのOHLCV一覧取得テスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        # 1. 通常の取得（過去100本）
        eval_time = self.test_ohlcv_data.iloc[500]['timestamp']
        historical_data = prepared_data.get_ohlcv_until(eval_time, lookback_periods=100)
        
        self.assertEqual(len(historical_data), 100)
        self.assertTrue(all(row['timestamp'] <= eval_time for row in historical_data))
        
        # 2. データ不足時の処理（最初の方で100本取れない場合）
        early_time = self.test_ohlcv_data.iloc[50]['timestamp']
        limited_data = prepared_data.get_ohlcv_until(early_time, lookback_periods=100)
        
        self.assertLessEqual(len(limited_data), 51)  # 0-50の51本
        self.assertTrue(all(row['timestamp'] <= early_time for row in limited_data))
        
        # 3. データ形式の確認
        self.assertIsInstance(historical_data, list)
        self.assertIsInstance(historical_data[0], dict)
        self.assertIn('timestamp', historical_data[0])
        self.assertIn('close', historical_data[0])
        self.assertIn('volume', historical_data[0])
    
    def test_get_ohlcv_range(self):
        """指定期間範囲のOHLCV取得テスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        # 1時間分のデータ取得
        start_time = self.test_ohlcv_data.iloc[100]['timestamp']
        end_time = start_time + timedelta(hours=1)
        
        range_data = prepared_data.get_ohlcv_range(start_time, end_time)
        
        # 1分足なので約60本
        self.assertGreater(len(range_data), 55)
        self.assertLess(len(range_data), 65)
        
        # 時間範囲の確認
        self.assertTrue(all(start_time <= row['timestamp'] <= end_time for row in range_data))
    
    def test_get_recent_ohlcv(self):
        """最近のOHLCV取得テスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        # 過去30分のデータ取得
        eval_time = self.test_ohlcv_data.iloc[300]['timestamp']
        recent_data = prepared_data.get_recent_ohlcv(eval_time, minutes=30)
        
        # 約30本のデータ
        self.assertGreater(len(recent_data), 25)
        self.assertLess(len(recent_data), 35)
        
        # 最新データが評価時点に近いことを確認
        latest_timestamp = recent_data[-1]['timestamp']
        time_diff = (eval_time - latest_timestamp).total_seconds()
        self.assertLess(time_diff, 60)  # 1分以内
    
    def test_technical_indicators(self):
        """テクニカル指標計算のテスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        # 1. 移動平均
        eval_time = self.test_ohlcv_data.iloc[100]['timestamp']
        ma20 = prepared_data.get_moving_average(eval_time, period=20)
        self.assertIsInstance(ma20, float)
        self.assertGreater(ma20, 0)
        
        # 2. RSI
        rsi = prepared_data.get_rsi(eval_time, period=14)
        self.assertIsInstance(rsi, float)
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)
        
        # 3. ボリューム加重平均価格（VWAP）
        vwap = prepared_data.get_vwap(eval_time, period=20)
        self.assertIsInstance(vwap, float)
        self.assertGreater(vwap, 0)
    
    def test_spread_calculation(self):
        """スプレッド計算のテスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        eval_time = self.test_ohlcv_data.iloc[200]['timestamp']
        spread = prepared_data.get_spread_at(eval_time)
        
        # スプレッドは0-1%程度と仮定
        self.assertIsInstance(spread, float)
        self.assertGreaterEqual(spread, 0)
        self.assertLess(spread, 0.01)
    
    def test_liquidity_score(self):
        """流動性スコア計算のテスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        eval_time = self.test_ohlcv_data.iloc[300]['timestamp']
        liquidity_score = prepared_data.get_liquidity_score_at(eval_time)
        
        # スコアは0-1の範囲
        self.assertIsInstance(liquidity_score, float)
        self.assertGreaterEqual(liquidity_score, 0)
        self.assertLessEqual(liquidity_score, 1)
    
    def test_volatility_calculation(self):
        """ボラティリティ計算のテスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        eval_time = self.test_ohlcv_data.iloc[400]['timestamp']
        
        # 1. 通常のボラティリティ
        volatility = prepared_data.get_volatility_at(eval_time)
        self.assertIsInstance(volatility, float)
        self.assertGreater(volatility, 0)
        self.assertLess(volatility, 1)  # 100%未満
        
        # 2. ATR (Average True Range)
        atr = prepared_data.get_atr_at(eval_time)
        self.assertIsInstance(atr, float)
        self.assertGreater(atr, 0)
    
    def test_data_quality_checks(self):
        """データ品質チェックのテスト"""
        from engines.data_preparers import RealPreparedData
        
        prepared_data = RealPreparedData(self.test_ohlcv_data)
        
        eval_time = self.test_ohlcv_data.iloc[500]['timestamp']
        
        # 1. 欠損データチェック
        has_missing = prepared_data.has_missing_data_around(eval_time, window_minutes=60)
        self.assertIsInstance(has_missing, bool)
        self.assertFalse(has_missing)  # テストデータには欠損なし
        
        # 2. 価格異常チェック
        has_anomaly = prepared_data.has_price_anomaly_at(eval_time)
        self.assertIsInstance(has_anomaly, bool)
        
        # 3. データ有効性
        is_valid = prepared_data.is_valid()
        self.assertTrue(is_valid)
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        from engines.data_preparers import RealPreparedData
        
        # 1. 空のデータフレーム
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError):
            RealPreparedData(empty_df)
        
        # 2. 必須カラムの欠如
        incomplete_df = pd.DataFrame({'timestamp': [datetime.now()], 'close': [100]})
        with self.assertRaises(ValueError):
            RealPreparedData(incomplete_df)
        
        # 3. 時系列順序の乱れ
        disordered_df = self.test_ohlcv_data.sample(frac=1)  # シャッフル
        prepared_data = RealPreparedData(disordered_df)
        # 内部で自動ソートされることを確認
        self.assertTrue(prepared_data.ohlcv_data['timestamp'].is_monotonic_increasing)
    
    def test_performance(self):
        """パフォーマンステスト"""
        from engines.data_preparers import RealPreparedData
        import time
        
        # 大規模データ（10000本）を生成
        large_data = self._create_large_test_data(10000)
        prepared_data = RealPreparedData(large_data)
        
        eval_time = large_data.iloc[5000]['timestamp']
        
        # 1. 単一時点取得の速度
        start_time = time.time()
        for _ in range(1000):
            prepared_data.get_price_at(eval_time)
        single_access_time = time.time() - start_time
        self.assertLess(single_access_time, 0.1)  # 1000回で0.1秒以内
        
        # 2. 範囲取得の速度
        start_time = time.time()
        prepared_data.get_ohlcv_until(eval_time, 1000)
        range_access_time = time.time() - start_time
        self.assertLess(range_access_time, 0.01)  # 0.01秒以内
    
    def _create_large_test_data(self, size):
        """大規模テストデータ生成"""
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        data = []
        
        for i in range(size):
            timestamp = base_time + timedelta(minutes=i)
            price = 50000 + np.random.normal(0, 100)
            
            data.append({
                'timestamp': timestamp,
                'open': price + np.random.normal(0, 10),
                'high': price + abs(np.random.normal(0, 20)),
                'low': price - abs(np.random.normal(0, 20)),
                'close': price,
                'volume': 1000000 * np.random.uniform(0.5, 2.0)
            })
        
        return pd.DataFrame(data)


class TestRealPreparedDataIntegration(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """RealPreparedDataとFilteringFrameworkの統合テスト"""
    
    def setUp(self):
        """テスト前準備"""
        if USE_BASE_TEST:
            super().setUp()
        
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """テスト後清理"""
        if USE_BASE_TEST:
            super().tearDown()
        
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_filtering_with_real_data(self):
        """実データを使用したフィルタリングテスト"""
        from engines.filtering_framework import FilteringFramework
        from engines.data_preparers import RealPreparedData
        
        # OHLCVデータ準備
        test_case = TestRealPreparedData()
        test_case.setUp()
        ohlcv_data = test_case.test_ohlcv_data
        
        # RealPreparedDataの作成
        prepared_data = RealPreparedData(ohlcv_data)
        
        # モック戦略（フィルター通過しやすいように設定）
        mock_strategy = Mock()
        mock_strategy.name = "TestStrategy"
        mock_strategy.min_volume_threshold = 100000  # 低めに設定
        mock_strategy.max_spread_threshold = 0.1     # 高めに設定
        mock_strategy.min_liquidity_score = 0.3      # 低めに設定
        
        # FilteringFrameworkの初期化
        framework = FilteringFramework(
            prepared_data_factory=lambda: prepared_data,
            strategy_factory=lambda: mock_strategy
        )
        
        # フィルタリング実行
        evaluation_times = [ohlcv_data.iloc[i]['timestamp'] for i in range(100, 110)]
        results = framework.execute_filtering(evaluation_times)
        
        # 結果の確認
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        
        # 統計情報の確認
        stats = framework.get_statistics()
        self.assertEqual(stats.total_evaluations, 10)
        
        test_case.tearDown()
    
    def test_scalable_analysis_integration(self):
        """ScalableAnalysisSystemとの統合テスト"""
        # このテストは実際のシステム統合後に実装
        self.assertTrue(True, "統合テストのプレースホルダー")


class TestDataConsistency(BaseTest if USE_BASE_TEST else unittest.TestCase):
    """データ一貫性のテスト"""
    
    def test_concurrent_data_access(self):
        """並行データアクセスのテスト"""
        from engines.data_preparers import RealPreparedData
        import threading
        
        # テストデータ
        test_case = TestRealPreparedData()
        test_case.setUp()
        prepared_data = RealPreparedData(test_case.test_ohlcv_data)
        
        results = []
        eval_time = test_case.test_ohlcv_data.iloc[100]['timestamp']
        
        def access_data():
            price = prepared_data.get_price_at(eval_time)
            results.append(price)
        
        # 10スレッドで同時アクセス
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_data)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 全て同じ値を返すことを確認
        self.assertEqual(len(set(results)), 1)
        
        test_case.tearDown()


if __name__ == '__main__':
    # テスト実行時のログ出力
    print("🧪 実データ利用PreparedDataテスト開始")
    print("📋 TDDアプローチによる包括的テスト")
    
    # BaseTestの使用状況を表示
    if USE_BASE_TEST:
        print("✅ BaseTest使用: 本番DB保護確認済み")
    else:
        print("⚠️ BaseTest未使用: 標準unittestで実行")
    
    # テストスイート実行
    unittest.main(verbosity=2)