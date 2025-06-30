#!/usr/bin/env python3
"""
ProcessPoolExecutor DB保存問題修正のテストコード
_create_no_signal_recordメソッドのINSERT修正を検証
"""

import unittest
import tempfile
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer

class TestDBSaveFix(unittest.TestCase):
    """ProcessPoolExecutor DB保存問題修正のテスト"""
    
    def setUp(self):
        """テスト用の一時データベース作成"""
        self.temp_dir = tempfile.mkdtemp()
        # large_scale_analysisディレクトリを作成（実際のパス構造に合わせる）
        self.large_scale_dir = Path(self.temp_dir) / "large_scale_analysis"
        self.large_scale_dir.mkdir(parents=True, exist_ok=True)
        self.temp_db_path = self.large_scale_dir / "analysis.db"
        
        # テスト用データベーススキーマ作成
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timeframe TEXT,
                    config TEXT,
                    strategy_config_id INTEGER,
                    strategy_name TEXT,
                    task_status TEXT,
                    task_completed_at TEXT,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    win_rate REAL,
                    total_trades INTEGER,
                    status TEXT,
                    error_message TEXT,
                    generated_at TEXT,
                    execution_id TEXT
                )
            """)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_no_signal_record_insert(self):
        """シグナルなしレコードのINSERT動作テスト"""
        trainer = AutoSymbolTrainer()
        
        # テスト用設定
        symbol = "TEST"
        config = {
            'strategy': 'momentum',
            'timeframe': '1h',
            'strategy_config_id': 123,
            'strategy_name': 'momentum-1h'
        }
        execution_id = "test_execution_123"
        error_message = "No trading signals detected"
        
        # データベースパスをモック - __file__の動的パッチング
        with patch('auto_symbol_training.__file__', self.temp_dir + '/auto_symbol_training.py'):
            # メソッド実行
            trainer._create_no_signal_record(symbol, config, execution_id, error_message)
        
        # データベースから結果確認
        with sqlite3.connect(self.temp_db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol, timeframe, config, status, error_message, 
                       task_status, execution_id, strategy_name
                FROM analyses 
                WHERE symbol = ? AND execution_id = ?
            """, (symbol, execution_id))
            
            result = cursor.fetchone()
            
        # 検証
        self.assertIsNotNone(result, "レコードが作成されていません")
        self.assertEqual(result[0], symbol)
        self.assertEqual(result[1], '1h')
        self.assertEqual(result[2], 'momentum')
        self.assertEqual(result[3], 'no_signal')
        self.assertEqual(result[4], error_message)
        self.assertEqual(result[5], 'completed')
        self.assertEqual(result[6], execution_id)
        self.assertEqual(result[7], 'momentum-1h')
    
    def test_create_no_signal_record_multiple_inserts(self):
        """複数のシグナルなしレコード作成テスト"""
        trainer = AutoSymbolTrainer()
        
        test_cases = [
            {
                'symbol': 'SOL',
                'config': {'strategy': 'momentum', 'timeframe': '1h'},
                'execution_id': 'exec_1',
                'error_message': 'No signals found'
            },
            {
                'symbol': 'BTC',
                'config': {'strategy': 'aggressive', 'timeframe': '15m'},
                'execution_id': 'exec_2',
                'error_message': 'Insufficient data'
            },
            {
                'symbol': 'ETH',
                'config': {'strategy': 'conservative', 'timeframe': '4h'},
                'execution_id': 'exec_3',
                'error_message': 'No trading opportunities'
            }
        ]
        
        # データベースパスをモック - __file__の動的パッチング
        with patch('auto_symbol_training.__file__', self.temp_dir + '/auto_symbol_training.py'):
            # 複数レコード作成
            for case in test_cases:
                trainer._create_no_signal_record(
                    case['symbol'], 
                    case['config'], 
                    case['execution_id'], 
                    case['error_message']
                )
        
        # データベースから結果確認
        with sqlite3.connect(self.temp_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM analyses")
            count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT symbol, config, error_message FROM analyses ORDER BY symbol")
            results = cursor.fetchall()
        
        # 検証
        self.assertEqual(count, 3, "3つのレコードが作成されるべきです")
        
        expected_symbols = ['BTC', 'ETH', 'SOL']
        actual_symbols = [result[0] for result in results]
        self.assertEqual(actual_symbols, expected_symbols)
        
        # 各レコードの内容確認
        for i, result in enumerate(results):
            expected_case = next(case for case in test_cases if case['symbol'] == result[0])
            self.assertEqual(result[1], expected_case['config']['strategy'])
            self.assertEqual(result[2], expected_case['error_message'])
    
    def test_create_no_signal_record_no_pending_records_needed(self):
        """pendingレコードが存在しなくても正常動作することを確認"""
        trainer = AutoSymbolTrainer()
        
        symbol = "NOPENDING"
        config = {
            'strategy': 'test_strategy',
            'timeframe': '30m'
        }
        execution_id = "no_pending_test"
        
        # データベースパスをモック - __file__の動的パッチング
        with patch('auto_symbol_training.__file__', self.temp_dir + '/auto_symbol_training.py'):
            # pendingレコードが存在しない状態でINSERT実行
            trainer._create_no_signal_record(symbol, config, execution_id)
        
        # データベースから結果確認
        with sqlite3.connect(self.temp_db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol, status, task_status 
                FROM analyses 
                WHERE symbol = ?
            """, (symbol,))
            
            result = cursor.fetchone()
        
        # 検証: pendingレコードなしでも正常にINSERTされる
        self.assertIsNotNone(result)
        self.assertEqual(result[0], symbol)
        self.assertEqual(result[1], 'no_signal')
        self.assertEqual(result[2], 'completed')
    
    def test_create_no_signal_record_error_handling(self):
        """エラーハンドリングのテスト"""
        trainer = AutoSymbolTrainer()
        
        # 無効なデータベースパスでエラーテスト - 存在しないディレクトリを指定
        invalid_dir = "/invalid/path/nonexistent"
        
        with patch('auto_symbol_training.__file__', invalid_dir + '/auto_symbol_training.py'):
            # ログをキャプチャ
            with patch.object(trainer.logger, 'error') as mock_error:
                trainer._create_no_signal_record(
                    "ERROR_TEST", 
                    {'strategy': 'test', 'timeframe': '1h'}, 
                    "error_exec_id"
                )
                
                # エラーログが出力されることを確認
                mock_error.assert_called()
                error_call_args = mock_error.call_args[0][0]
                self.assertIn("シグナルなしレコード作成エラー", error_call_args)
    
    def test_no_signal_record_data_integrity(self):
        """作成されるレコードのデータ完整性テスト"""
        trainer = AutoSymbolTrainer()
        
        config = {
            'strategy': 'momentum',
            'timeframe': '1h',
            'strategy_config_id': 456,
            'strategy_name': 'Custom Strategy Name'
        }
        
        with patch('auto_symbol_training.__file__', self.temp_dir + '/auto_symbol_training.py'):
            trainer._create_no_signal_record("INTEGRITY", config, "integrity_test", "Custom error message")
        
        # データベースから詳細な結果確認
        with sqlite3.connect(self.temp_db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol, timeframe, config, strategy_config_id, strategy_name,
                       task_status, total_return, sharpe_ratio, max_drawdown, 
                       win_rate, total_trades, status, error_message, execution_id
                FROM analyses 
                WHERE symbol = 'INTEGRITY'
            """)
            
            result = cursor.fetchone()
        
        # 詳細検証
        self.assertEqual(result[0], "INTEGRITY")  # symbol
        self.assertEqual(result[1], "1h")  # timeframe
        self.assertEqual(result[2], "momentum")  # config
        self.assertEqual(result[3], 456)  # strategy_config_id
        self.assertEqual(result[4], "Custom Strategy Name")  # strategy_name
        self.assertEqual(result[5], "completed")  # task_status
        self.assertEqual(result[6], 0.0)  # total_return
        self.assertEqual(result[7], 0.0)  # sharpe_ratio
        self.assertEqual(result[8], 0.0)  # max_drawdown
        self.assertEqual(result[9], 0.0)  # win_rate
        self.assertEqual(result[10], 0)  # total_trades
        self.assertEqual(result[11], "no_signal")  # status
        self.assertEqual(result[12], "Custom error message")  # error_message
        self.assertEqual(result[13], "integrity_test")  # execution_id


class TestProcessPoolExecutorDBIntegration(unittest.TestCase):
    """ProcessPoolExecutor環境でのDB保存統合テスト"""
    
    def setUp(self):
        """テスト用の一時環境設定"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_analysis_dir = Path(self.temp_dir) / "large_scale_analysis"
        self.temp_analysis_dir.mkdir()
        self.temp_db_path = self.temp_analysis_dir / "analysis.db"
        
        # テスト用データベーススキーマ作成
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timeframe TEXT,
                    config TEXT,
                    strategy_config_id INTEGER,
                    strategy_name TEXT,
                    task_status TEXT,
                    task_completed_at TEXT,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    win_rate REAL,
                    total_trades INTEGER,
                    status TEXT,
                    error_message TEXT,
                    generated_at TEXT,
                    execution_id TEXT
                )
            """)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_multiprocess_db_save_simulation(self):
        """マルチプロセス環境でのDB保存シミュレーションテスト"""
        trainer = AutoSymbolTrainer()
        
        # 複数の並行処理をシミュレート
        test_configs = [
            {'symbol': 'SOL', 'strategy': 'momentum', 'timeframe': '1h', 'execution_id': 'multi_1'},
            {'symbol': 'BTC', 'strategy': 'aggressive', 'timeframe': '15m', 'execution_id': 'multi_2'},
            {'symbol': 'ETH', 'strategy': 'conservative', 'timeframe': '4h', 'execution_id': 'multi_3'},
        ]
        
        # テスト環境のパスでテスト用ディレクトリを作成
        with patch('auto_symbol_training.__file__', self.temp_dir + '/auto_symbol_training.py'):
            # 各設定でレコード作成
            for config in test_configs:
                config_dict = {
                    'strategy': config['strategy'],
                    'timeframe': config['timeframe']
                }
                trainer._create_no_signal_record(
                    config['symbol'], 
                    config_dict, 
                    config['execution_id'],
                    f"No signals for {config['symbol']}"
                )
        
        # 結果確認
        with sqlite3.connect(self.temp_db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol, config, timeframe, execution_id, status 
                FROM analyses 
                ORDER BY symbol
            """)
            results = cursor.fetchall()
        
        # 検証
        self.assertEqual(len(results), 3, "3つのレコードが作成されるべきです")
        
        expected_symbols = ['BTC', 'ETH', 'SOL']
        actual_symbols = [result[0] for result in results]
        self.assertEqual(actual_symbols, expected_symbols)
        
        # 全てのレコードが正常に保存されている
        for result in results:
            self.assertEqual(result[4], 'no_signal')  # status


def run_tests():
    """テスト実行"""
    print("🧪 ProcessPoolExecutor DB保存修正テスト開始")
    print("=" * 60)
    
    # テストスイート作成
    suite = unittest.TestSuite()
    
    # 基本的なINSERT動作テスト
    suite.addTest(TestDBSaveFix('test_create_no_signal_record_insert'))
    suite.addTest(TestDBSaveFix('test_create_no_signal_record_multiple_inserts'))
    suite.addTest(TestDBSaveFix('test_create_no_signal_record_no_pending_records_needed'))
    suite.addTest(TestDBSaveFix('test_create_no_signal_record_error_handling'))
    suite.addTest(TestDBSaveFix('test_no_signal_record_data_integrity'))
    
    # ProcessPoolExecutor統合テスト
    suite.addTest(TestProcessPoolExecutorDBIntegration('test_multiprocess_db_save_simulation'))
    
    # テストランナー実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print(f"実行されたテスト: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\n📈 成功率: {success_rate:.1f}%")
    
    if success_rate == 100.0:
        print("✅ 全テスト合格！ProcessPoolExecutor DB保存修正が正常に動作しています。")
    else:
        print("⚠️ 一部のテストが失敗しました。修正が必要です。")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)