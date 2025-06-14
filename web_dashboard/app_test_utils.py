#!/usr/bin/env python3
"""
Web Dashboard テスト用ユーティリティ

テスト用Flaskアプリの作成とテスト環境設定
"""

import os
import tempfile
import sys
from pathlib import Path

def create_test_app():
    """テスト用Flaskアプリケーションを作成"""
    
    # テスト環境設定
    os.environ['TESTING'] = 'True'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    # テスト用の一時ディレクトリ
    test_temp_dir = tempfile.mkdtemp(prefix="test_dashboard_")
    os.environ['TEST_DATA_DIR'] = test_temp_dir
    
    # appモジュールをインポート（テスト用設定で）
    from app import app
    
    # テスト用設定を適用
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'DEBUG': False
    })
    
    return app

def setup_test_database():
    """テスト用データベースをセットアップ"""
    import sqlite3
    
    test_db_path = "test_execution_logs.db"
    
    # テーブル作成SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS execution_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_id TEXT UNIQUE NOT NULL,
        execution_type TEXT NOT NULL,
        symbol TEXT,
        status TEXT DEFAULT 'PENDING',
        triggered_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT,
        results TEXT,
        error_message TEXT,
        progress_percentage REAL DEFAULT 0.0,
        current_operation TEXT
    );
    """
    
    conn = sqlite3.connect(test_db_path)
    conn.execute(create_table_sql)
    conn.commit()
    conn.close()
    
    return test_db_path

def cleanup_test_environment():
    """テスト環境をクリーンアップ"""
    
    # テスト用ファイルを削除
    test_files = [
        "test_execution_logs.db",
        "test_analysis.db"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # テスト用ディレクトリをクリーンアップ
    test_data_dir = os.environ.get('TEST_DATA_DIR')
    if test_data_dir and os.path.exists(test_data_dir):
        import shutil
        shutil.rmtree(test_data_dir, ignore_errors=True)
    
    # 環境変数をクリア
    test_env_vars = ['TESTING', 'DATABASE_URL', 'TEST_DATA_DIR']
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]

class MockAPIClient:
    """テスト用モックAPIクライアント"""
    
    def __init__(self, mock_responses=None):
        self.mock_responses = mock_responses or {}
    
    async def validate_symbol_real(self, symbol):
        """モック銘柄バリデーション"""
        if symbol in self.mock_responses:
            return self.mock_responses[symbol]
        
        # デフォルトレスポンス
        if symbol.startswith('VALID'):
            return {'valid': True, 'symbol': symbol, 'exchange': 'gateio'}
        else:
            return {'valid': False, 'error': 'Symbol not found'}
    
    async def get_ohlcv_data_with_period(self, symbol, timeframe, days):
        """モックOHLCVデータ取得"""
        import pandas as pd
        from datetime import datetime, timedelta
        
        # 充分なテストデータを生成
        periods = days * 24 if timeframe == '1h' else days * 24 * 4 if timeframe == '15m' else 1500
        
        return pd.DataFrame({
            'timestamp': pd.date_range(
                start=datetime.now() - timedelta(days=days),
                periods=periods,
                freq='1H'
            ),
            'open': [100.0 + i * 0.1 for i in range(periods)],
            'high': [105.0 + i * 0.1 for i in range(periods)],
            'low': [95.0 + i * 0.1 for i in range(periods)],
            'close': [102.0 + i * 0.1 for i in range(periods)],
            'volume': [1000000.0] * periods
        })

class TestDataGenerator:
    """テスト用データ生成器"""
    
    @staticmethod
    def create_mock_execution_log(execution_id="test_exec_001", 
                                symbol="TEST", 
                                status="COMPLETED"):
        """モック実行ログを作成"""
        return {
            'execution_id': execution_id,
            'execution_type': 'SYMBOL_ADDITION',
            'symbol': symbol,
            'status': status,
            'triggered_by': 'unit_test',
            'created_at': '2024-01-01 12:00:00',
            'updated_at': '2024-01-01 12:30:00',
            'metadata': '{"test": true}',
            'results': '{"total_patterns": 18, "best_sharpe": 2.5}',
            'progress_percentage': 100.0
        }
    
    @staticmethod
    def create_mock_analysis_result(symbol="TEST", strategy="Conservative_ML"):
        """モック分析結果を作成"""
        return {
            'symbol': symbol,
            'timeframe': '1h',
            'strategy': strategy,
            'leverage': 5.0,
            'confidence': 75.0,
            'current_price': 100.0,
            'entry_price': 100.0,
            'target_price': 105.0,
            'stop_loss': 95.0,
            'risk_reward_ratio': 1.0,
            'timestamp': '2024-01-01T12:00:00Z',
            'position_size': 100.0,
            'risk_level': 25.0
        }
    
    @staticmethod
    def create_mock_trade_data(symbol="TEST", num_trades=50):
        """モックトレードデータを作成"""
        import random
        
        trades = []
        base_price = 100.0
        
        for i in range(num_trades):
            entry_price = base_price + random.uniform(-5, 5)
            trades.append({
                'entry_price': entry_price,
                'exit_price': entry_price + random.uniform(-2, 8),
                'take_profit_price': entry_price * 1.05,
                'stop_loss_price': entry_price * 0.95,
                'position_size': 100.0,
                'pnl': random.uniform(-10, 20),
                'trade_duration': random.randint(60, 3600),
                'timestamp': f"2024-01-{i+1:02d}T12:00:00Z"
            })
        
        return trades

if __name__ == "__main__":
    # テストユーティリティの動作確認
    print("🧪 Web Dashboard テストユーティリティ")
    print("=" * 50)
    
    # テスト用アプリ作成確認
    try:
        app = create_test_app()
        print("✅ テスト用Flaskアプリ作成成功")
    except Exception as e:
        print(f"❌ テスト用Flaskアプリ作成失敗: {e}")
    
    # テスト用DB作成確認
    try:
        db_path = setup_test_database()
        print(f"✅ テスト用DB作成成功: {db_path}")
    except Exception as e:
        print(f"❌ テスト用DB作成失敗: {e}")
    
    # モックデータ生成確認
    try:
        mock_data = TestDataGenerator.create_mock_analysis_result()
        print(f"✅ モックデータ生成成功: {mock_data['symbol']}")
    except Exception as e:
        print(f"❌ モックデータ生成失敗: {e}")
    
    # クリーンアップ
    cleanup_test_environment()
    print("✅ テスト環境クリーンアップ完了")