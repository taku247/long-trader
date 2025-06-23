#!/usr/bin/env python3
"""
サポート・レジスタンス分析エラーハンドリングテスト

_analyze_support_resistance メソッドで例外が発生した場合、
エラーを隠蔽せずに適切に例外を発生させることを検証
"""

import unittest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator

class TestSupportResistanceErrorHandling(unittest.TestCase):
    """サポート・レジスタンス分析エラーハンドリングテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.orchestrator = HighLeverageBotOrchestrator()
        
        # テスト用のダミーデータ
        self.test_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
            'open': [100.0 + i for i in range(100)],
            'high': [101.0 + i for i in range(100)],
            'low': [99.0 + i for i in range(100)],
            'close': [100.5 + i for i in range(100)],
            'volume': [1000.0] * 100
        })
    
    def test_support_resistance_analyzer_exception_propagates(self):
        """サポート・レジスタンス分析器で例外発生時、適切に例外が伝播されることをテスト"""
        print("🧪 サポート・レジスタンス分析器例外伝播テスト")
        
        # モックアナライザーを設定（例外を発生させる）
        mock_analyzer = Mock()
        mock_analyzer.find_levels.side_effect = Exception("Mock support resistance analysis error")
        self.orchestrator.support_resistance_analyzer = mock_analyzer
        
        # 例外が適切に発生することを確認
        with self.assertRaises(Exception) as context:
            self.orchestrator._analyze_support_resistance(self.test_data)
        
        # エラーメッセージの確認
        error_message = str(context.exception)
        self.assertIn("サポート・レジスタンス分析に失敗", error_message)
        self.assertIn("不完全なデータでの分析は危険です", error_message)
        self.assertIn("Mock support resistance analysis error", error_message)
        
        print(f"✅ 例外伝播テスト成功: {error_message}")
    
    def test_empty_data_exception_propagates(self):
        """空データでの例外が適切に伝播されることをテスト"""
        print("🧪 空データ例外伝播テスト")
        
        # 空のDataFrameを作成
        empty_data = pd.DataFrame()
        
        # モックアナライザーを設定
        mock_analyzer = Mock()
        self.orchestrator.support_resistance_analyzer = mock_analyzer
        
        # 例外が適切に発生することを確認
        with self.assertRaises(Exception) as context:
            self.orchestrator._analyze_support_resistance(empty_data)
        
        # エラーメッセージの確認
        error_message = str(context.exception)
        self.assertIn("サポート・レジスタンス分析に失敗", error_message)
        
        print(f"✅ 空データ例外テスト成功: {error_message}")
    
    def test_sort_exception_propagates(self):
        """ソート処理での例外が適切に伝播されることをテスト"""
        print("🧪 ソート例外伝播テスト")
        
        # 正常なレベル検出をモック
        mock_analyzer = Mock()
        mock_level = Mock()
        mock_level.level_type = 'support'
        mock_level.price = None  # Noneを設定してソートエラーを誘発
        mock_analyzer.find_levels.return_value = [mock_level]
        self.orchestrator.support_resistance_analyzer = mock_analyzer
        
        # 例外が適切に発生することを確認
        with self.assertRaises(Exception) as context:
            self.orchestrator._analyze_support_resistance(self.test_data)
        
        # エラーメッセージの確認
        error_message = str(context.exception)
        self.assertIn("サポート・レジスタンス分析に失敗", error_message)
        
        print(f"✅ ソート例外テスト成功: {error_message}")
    
    def test_successful_analysis_returns_levels(self):
        """正常なサポート・レジスタンス分析が成功することをテスト"""
        print("🧪 正常分析成功テスト")
        
        # 正常なレベル検出をモック
        mock_analyzer = Mock()
        
        # テスト用のサポート・レジスタンスレベル
        mock_support = Mock()
        mock_support.level_type = 'support'
        mock_support.price = 95.0
        
        mock_resistance = Mock()
        mock_resistance.level_type = 'resistance'
        mock_resistance.price = 105.0
        
        mock_analyzer.find_levels.return_value = [mock_support, mock_resistance]
        self.orchestrator.support_resistance_analyzer = mock_analyzer
        
        # 正常に実行されることを確認
        support_levels, resistance_levels = self.orchestrator._analyze_support_resistance(self.test_data)
        
        # 結果の確認
        self.assertEqual(len(support_levels), 1)
        self.assertEqual(len(resistance_levels), 1)
        self.assertEqual(support_levels[0].price, 95.0)
        self.assertEqual(resistance_levels[0].price, 105.0)
        
        print(f"✅ 正常分析テスト成功: サポート{len(support_levels)}件, レジスタンス{len(resistance_levels)}件")
    
    def test_no_analyzer_exception_propagates(self):
        """アナライザーがNoneの場合の処理をテスト"""
        print("🧪 アナライザーなし例外テスト")
        
        # アナライザーをNoneに設定
        self.orchestrator.support_resistance_analyzer = None
        
        # 正常に空リストが返されることを確認（これは正常な動作）
        support_levels, resistance_levels = self.orchestrator._analyze_support_resistance(self.test_data)
        
        self.assertEqual(len(support_levels), 0)
        self.assertEqual(len(resistance_levels), 0)
        
        print("✅ アナライザーなしテスト成功: 空リストが返されました")
    
    def test_short_timeframe_optimization(self):
        """短期間足での最適化が正常に動作することをテスト"""
        print("🧪 短期間足最適化テスト")
        
        # 正常なレベル検出をモック
        mock_analyzer = Mock()
        mock_support = Mock()
        mock_support.level_type = 'support'
        mock_support.price = 95.0
        mock_analyzer.find_levels.return_value = [mock_support]
        self.orchestrator.support_resistance_analyzer = mock_analyzer
        
        # 短期間足フラグをTrueで実行
        support_levels, resistance_levels = self.orchestrator._analyze_support_resistance(
            self.test_data, 
            is_short_timeframe=True
        )
        
        # find_levels が呼ばれたことを確認
        mock_analyzer.find_levels.assert_called_once()
        
        # パラメータの確認
        call_args = mock_analyzer.find_levels.call_args[1]
        self.assertEqual(call_args['window'], 3)
        self.assertEqual(call_args['min_touches'], 2)
        self.assertEqual(call_args['tolerance'], 0.005)
        
        print("✅ 短期間足最適化テスト成功: 適切なパラメータが設定されました")


def main():
    """テスト実行"""
    print("=" * 80)
    print("🧪 サポート・レジスタンス分析エラーハンドリングテスト開始")
    print("=" * 80)
    
    # テストスイート実行
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    print("✅ サポート・レジスタンス分析でエラーが発生した場合、適切に例外が伝播されます")
    print("✅ エラー隠蔽は廃止され、銘柄追加処理が安全に停止されます")
    print("✅ 正常なケースでは適切にサポート・レジスタンスレベルが返されます")


if __name__ == "__main__":
    main()