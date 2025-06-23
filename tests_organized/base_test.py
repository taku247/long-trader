#!/usr/bin/env python3
"""
統一テスト基底クラス
- 本番DBへの影響を完全に防ぐ
- テスト用データベースの自動管理
- 共通のセットアップ・クリーンアップ処理
- 標準的なテストパターンの提供
"""
import os
import sqlite3
import tempfile
import shutil
import unittest
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import json

class BaseTest(unittest.TestCase):
    """
    すべてのテストクラスの基底クラス
    
    機能:
    - テスト用一時ディレクトリの自動作成・削除
    - テスト用DBの標準テーブル作成
    - 本番DBとの分離保証
    - 共通のアサートメソッド提供
    """
    
    def setUp(self):
        """テスト前のセットアップ処理"""
        # テスト用一時ディレクトリ作成
        self.test_dir = tempfile.mkdtemp(prefix=f"test_{self.__class__.__name__}_")
        self.test_start_time = datetime.now(timezone.utc)
        
        # デバッグ用ログ
        print(f"\n🧪 {self.__class__.__name__} テスト開始")
        print(f"   📁 テスト用ディレクトリ: {self.test_dir}")
        print(f"   ⏰ 開始時刻: {self.test_start_time.strftime('%H:%M:%S')}")
        
        # 標準的なテスト用DBパスを設定
        self.setup_test_databases()
        
        # テスト固有のセットアップ
        self.custom_setup()
    
    def tearDown(self):
        """テスト後のクリーンアップ処理"""
        try:
            # テスト固有のクリーンアップ
            self.custom_teardown()
            
            # テスト用ディレクトリの削除
            if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
                
            # テスト完了ログ
            test_duration = (datetime.now(timezone.utc) - self.test_start_time).total_seconds()
            print(f"   ✅ テスト完了 (実行時間: {test_duration:.2f}秒)")
            print(f"   🧹 テスト用ディレクトリ削除: {self.test_dir}")
            
        except Exception as e:
            print(f"   ⚠️ クリーンアップエラー: {e}")
    
    def setup_test_databases(self):
        """標準的なテスト用データベースを作成"""
        # execution_logs.db
        self.execution_logs_db = os.path.join(self.test_dir, "execution_logs.db")
        
        # analysis.db
        analysis_dir = os.path.join(self.test_dir, "large_scale_analysis")
        os.makedirs(analysis_dir)
        self.analysis_db = os.path.join(analysis_dir, "analysis.db")
        
        # 基本テーブル作成
        self.create_execution_logs_table()
        self.create_analyses_table()
        
        print(f"   📊 execution_logs DB: {self.execution_logs_db}")
        print(f"   📊 analysis DB: {self.analysis_db}")
    
    def create_execution_logs_table(self):
        """execution_logsテーブルの作成"""
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("""
                CREATE TABLE execution_logs (
                    execution_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # インデックス作成
            conn.execute("CREATE INDEX idx_execution_logs_symbol ON execution_logs(symbol)")
            conn.execute("CREATE INDEX idx_execution_logs_status ON execution_logs(status)")
    
    def create_analyses_table(self):
        """analysesテーブルの作成"""
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                CREATE TABLE analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    config TEXT NOT NULL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    total_return REAL,
                    win_rate REAL,
                    total_trades INTEGER,
                    compressed_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (execution_id) REFERENCES execution_logs(execution_id)
                )
            """)
            
            # インデックス作成
            conn.execute("CREATE INDEX idx_analyses_symbol ON analyses(symbol)")
            conn.execute("CREATE INDEX idx_analyses_execution_id ON analyses(execution_id)")
            conn.execute("CREATE INDEX idx_analyses_config ON analyses(config)")
    
    def insert_test_execution_log(self, execution_id: str, symbol: str, 
                                  status: str = "SUCCESS") -> str:
        """テスト用execution_logレコードを挿入"""
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("""
                INSERT INTO execution_logs 
                (execution_id, symbol, status, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
            """, (
                execution_id, symbol, status,
                self.test_start_time.isoformat(),
                datetime.now(timezone.utc).isoformat()
            ))
        return execution_id
    
    def insert_test_analysis(self, execution_id: str, symbol: str, 
                           timeframe: str, config: str,
                           sharpe_ratio: float = 1.0,
                           max_drawdown: float = -0.1,
                           total_return: float = 0.15) -> int:
        """テスト用analysisレコードを挿入"""
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                INSERT INTO analyses 
                (execution_id, symbol, timeframe, config, sharpe_ratio, max_drawdown, total_return)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (execution_id, symbol, timeframe, config, sharpe_ratio, max_drawdown, total_return))
            return cursor.lastrowid
    
    def create_test_symbol_data(self, symbol: str, num_patterns: int = 5) -> List[str]:
        """指定銘柄のテストデータセットを作成"""
        execution_ids = []
        strategies = ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']
        timeframes = ['30m', '1h']
        
        pattern_count = 0
        for strategy in strategies:
            for timeframe in timeframes:
                if pattern_count >= num_patterns:
                    break
                
                execution_id = f"test_{symbol}_{strategy}_{timeframe}_{pattern_count}"
                
                # execution_log作成
                self.insert_test_execution_log(execution_id, symbol)
                
                # analysis作成
                self.insert_test_analysis(
                    execution_id, symbol, timeframe, strategy,
                    sharpe_ratio=1.0 + (pattern_count * 0.1),
                    max_drawdown=-0.1 - (pattern_count * 0.01),
                    total_return=0.15 + (pattern_count * 0.02)
                )
                
                execution_ids.append(execution_id)
                pattern_count += 1
                
            if pattern_count >= num_patterns:
                break
        
        print(f"   📈 {symbol}テストデータ作成: {len(execution_ids)}パターン")
        return execution_ids
    
    def assert_db_isolated(self):
        """本番DBとの分離を確認"""
        # 本番DBパスに触れていないことを確認
        production_paths = [
            'execution_logs.db',
            'large_scale_analysis/analysis.db',
            os.path.expanduser('~/execution_logs.db')
        ]
        
        for path in production_paths:
            abs_path = os.path.abspath(path)
            test_path = os.path.abspath(self.test_dir)
            
            # テスト用ディレクトリ外のDBファイルに触れていないことを確認
            self.assertFalse(
                abs_path.startswith(test_path.rstrip('/test_')),
                f"本番DB({abs_path})に触れる可能性があります"
            )
    
    def assert_test_data_exists(self, symbol: str, min_records: int = 1):
        """テストデータの存在確認"""
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM analyses WHERE symbol = ?", (symbol,)
            )
            count = cursor.fetchone()[0]
            self.assertGreaterEqual(
                count, min_records,
                f"{symbol}のテストデータが不足: {count} < {min_records}"
            )
    
    def get_analysis_count(self, symbol: str = None) -> int:
        """分析レコード数を取得"""
        with sqlite3.connect(self.analysis_db) as conn:
            if symbol:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM analyses WHERE symbol = ?", (symbol,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM analyses")
            return cursor.fetchone()[0]
    
    def get_execution_logs_count(self, symbol: str = None, status: str = None) -> int:
        """実行ログレコード数を取得"""
        with sqlite3.connect(self.execution_logs_db) as conn:
            query = "SELECT COUNT(*) FROM execution_logs WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]
    
    # カスタマイズ用のフック
    def custom_setup(self):
        """各テストクラスでオーバーライド可能なセットアップ処理"""
        pass
    
    def custom_teardown(self):
        """各テストクラスでオーバーライド可能なクリーンアップ処理"""
        pass


class DatabaseTest(BaseTest):
    """データベース操作専用のテスト基底クラス"""
    
    def custom_setup(self):
        """DB操作テスト用の追加セットアップ"""
        # 外部キー制約を有効化
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
        
        with sqlite3.connect(self.execution_logs_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
    
    def test_foreign_key_constraints(self):
        """外部キー制約のテスト"""
        # 存在しないexecution_idでanalysisを作成しようとしてエラーになることを確認
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_test_analysis(
                "nonexistent_id", "TEST", "1h", "Conservative_ML"
            )


class APITest(BaseTest):
    """API操作専用のテスト基底クラス"""
    
    def custom_setup(self):
        """API テスト用の追加セットアップ"""
        # 複数銘柄のテストデータを作成
        self.test_symbols = ['BTC', 'ETH', 'SOL']
        self.test_execution_ids = {}
        
        for symbol in self.test_symbols:
            execution_ids = self.create_test_symbol_data(symbol, num_patterns=6)
            self.test_execution_ids[symbol] = execution_ids
    
    def simulate_api_query(self, symbol: str = None, 
                          join_execution_logs: bool = True) -> List[Dict]:
        """API クエリのシミュレーション"""
        with sqlite3.connect(self.analysis_db) as conn:
            if join_execution_logs:
                # execution_logs.db をアタッチ
                conn.execute(f"ATTACH DATABASE '{self.execution_logs_db}' AS exec_db")
                
                query = """
                    SELECT a.symbol, a.timeframe, a.config, a.sharpe_ratio, a.total_return
                    FROM analyses a
                    INNER JOIN exec_db.execution_logs e ON a.execution_id = e.execution_id
                    WHERE e.status = 'SUCCESS'
                """
                params = []
                
                if symbol:
                    query += " AND a.symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY a.sharpe_ratio DESC"
                
            else:
                query = """
                    SELECT symbol, timeframe, config, sharpe_ratio, total_return
                    FROM analyses WHERE 1=1
                """
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY sharpe_ratio DESC"
            
            cursor = conn.execute(query, params)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            # 辞書形式で返却
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return results


if __name__ == "__main__":
    # テスト基底クラスの動作確認
    class SampleTest(BaseTest):
        def test_basic_functionality(self):
            """基本機能のテスト"""
            # DB分離の確認
            self.assert_db_isolated()
            
            # テストデータ作成
            execution_ids = self.create_test_symbol_data("TEST", 3)
            self.assertEqual(len(execution_ids), 3)
            
            # データ存在確認
            self.assert_test_data_exists("TEST", 3)
            self.assertEqual(self.get_analysis_count("TEST"), 3)
            self.assertEqual(self.get_execution_logs_count("TEST"), 3)
    
    # サンプルテストの実行
    unittest.main(argv=[''], exit=False, verbosity=2)