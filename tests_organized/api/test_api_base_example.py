#!/usr/bin/env python3
"""
APIテストの実装例
base_test.pyを使用した安全なAPIテストの例
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_test import APITest
import sqlite3

class TestSymbolsAPI(APITest):
    """symbols API のテスト"""
    
    def test_symbols_api_basic_query(self):
        """基本的なsymbols APIクエリのテスト"""
        # DB分離確認
        self.assert_db_isolated()
        
        # 全銘柄クエリ
        results = self.simulate_api_query()
        
        # 結果検証
        self.assertGreater(len(results), 0, "結果が空です")
        
        # 各銘柄のデータ確認
        symbols_found = set(r['symbol'] for r in results)
        self.assertEqual(symbols_found, set(self.test_symbols))
        
        # データ構造確認
        for result in results:
            self.assertIn('symbol', result)
            self.assertIn('timeframe', result)
            self.assertIn('config', result)
            self.assertIn('sharpe_ratio', result)
            self.assertIsInstance(result['sharpe_ratio'], (int, float))
    
    def test_symbols_api_filtered_query(self):
        """特定銘柄フィルタークエリのテスト"""
        test_symbol = 'BTC'
        
        # BTC専用クエリ
        results = self.simulate_api_query(symbol=test_symbol)
        
        # 結果検証
        self.assertGreater(len(results), 0, f"{test_symbol}の結果が空です")
        
        # すべてがBTCであることを確認
        for result in results:
            self.assertEqual(result['symbol'], test_symbol)
    
    def test_symbols_api_without_execution_logs(self):
        """execution_logs JOIN なしのクエリテスト"""
        # JOINなしクエリ
        results = self.simulate_api_query(join_execution_logs=False)
        
        # 結果検証
        self.assertGreater(len(results), 0, "結果が空です")
        
        # execution_logsと同じ件数が返ることを確認
        join_results = self.simulate_api_query(join_execution_logs=True)
        self.assertEqual(len(results), len(join_results))
    
    def test_database_integrity(self):
        """データベース整合性のテスト"""
        # 各銘柄のレコード数確認
        for symbol in self.test_symbols:
            analysis_count = self.get_analysis_count(symbol)
            execution_count = self.get_execution_logs_count(symbol, 'SUCCESS')
            
            # execution_logsとanalysesの件数が一致することを確認
            self.assertEqual(
                analysis_count, execution_count,
                f"{symbol}: analyses({analysis_count}) != execution_logs({execution_count})"
            )


class TestSOLAPI(APITest):
    """SOL API専用テスト"""
    
    def custom_setup(self):
        """SOL専用のテストデータセットアップ"""
        super().custom_setup()
        
        # SOL専用の詳細データを追加
        strategies = ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']
        timeframes = ['30m', '1h', '4h']
        
        for i, strategy in enumerate(strategies):
            for j, timeframe in enumerate(timeframes):
                execution_id = f"sol_detailed_{strategy}_{timeframe}_{i}_{j}"
                
                # execution_log作成
                self.insert_test_execution_log(execution_id, 'SOL')
                
                # analysis作成（詳細データ）
                self.insert_test_analysis(
                    execution_id, 'SOL', timeframe, strategy,
                    sharpe_ratio=1.2 + (i * 0.1) + (j * 0.05),
                    max_drawdown=-0.15 - (i * 0.02),
                    total_return=0.25 + (i * 0.1)
                )
    
    def test_sol_specific_query(self):
        """SOL専用クエリのテスト"""
        results = self.simulate_api_query(symbol='SOL')
        
        # SOLデータが十分に存在することを確認
        self.assertGreaterEqual(len(results), 9, "SOL詳細データが不足")
        
        # すべてSOLデータであることを確認
        for result in results:
            self.assertEqual(result['symbol'], 'SOL')
        
        # シャープレシオでソート済みであることを確認
        sharpe_ratios = [r['sharpe_ratio'] for r in results]
        self.assertEqual(
            sharpe_ratios, sorted(sharpe_ratios, reverse=True),
            "シャープレシオでソートされていません"
        )
    
    def test_sol_timeframe_coverage(self):
        """SOLの時間足カバレッジテスト"""
        results = self.simulate_api_query(symbol='SOL')
        
        # 各時間足のデータが存在することを確認
        timeframes_found = set(r['timeframe'] for r in results)
        expected_timeframes = {'30m', '1h', '4h'}
        
        self.assertTrue(
            expected_timeframes.issubset(timeframes_found),
            f"時間足カバレッジ不足: {expected_timeframes - timeframes_found}"
        )
        
        # 各戦略のデータが存在することを確認
        strategies_found = set(r['config'] for r in results)
        expected_strategies = {'Conservative_ML', 'Aggressive_Traditional', 'Full_ML'}
        
        self.assertTrue(
            expected_strategies.issubset(strategies_found),
            f"戦略カバレッジ不足: {expected_strategies - strategies_found}"
        )


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)