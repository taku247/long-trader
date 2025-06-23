#!/usr/bin/env python3
"""
EarlyFail データベース接続性チェックのテストコード
"""

import asyncio
import sqlite3
import tempfile
import os
from pathlib import Path
from symbol_early_fail_validator import SymbolEarlyFailValidator, FailReason

async def test_db_connectivity():
    """DB接続性チェックの簡易テスト"""
    
    # 一時ディレクトリでテスト
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. DB不存在ケース
        validator = SymbolEarlyFailValidator()
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            result = await validator._check_database_connectivity("TEST")
            print(f"❌ DB不存在: {result.passed} - {result.error_message}")
            assert not result.passed
            assert result.fail_reason == FailReason.DATABASE_CONNECTION_FAILED
            
            # 2. 正常ケース
            # execution_logs.db作成
            exec_db = temp_path / "execution_logs.db"
            with sqlite3.connect(exec_db) as conn:
                conn.execute("""
                    CREATE TABLE execution_logs (
                        execution_id TEXT PRIMARY KEY,
                        status TEXT
                    )
                """)
                conn.execute("INSERT INTO execution_logs VALUES ('test1', 'SUCCESS')")
            
            # analysis.db作成
            analysis_dir = temp_path / "large_scale_analysis"
            analysis_dir.mkdir()
            analysis_db = analysis_dir / "analysis.db"
            with sqlite3.connect(analysis_db) as conn:
                conn.execute("""
                    CREATE TABLE analyses (
                        id INTEGER PRIMARY KEY,
                        symbol TEXT
                    )
                """)
                conn.execute("INSERT INTO analyses VALUES (1, 'BTC')")
            
            result = await validator._check_database_connectivity("TEST")
            print(f"✅ 正常ケース: {result.passed}")
            assert result.passed
            assert "database_status" in result.metadata
            
            # 3. テーブル不存在ケース
            os.remove(exec_db)
            with sqlite3.connect(exec_db) as conn:
                conn.execute("CREATE TABLE wrong_table (id INTEGER)")
            
            result = await validator._check_database_connectivity("TEST")
            print(f"❌ テーブル不存在: {result.passed} - {result.error_message}")
            assert not result.passed
            
        finally:
            os.chdir(original_dir)
    
    print("🎯 全テスト完了")

if __name__ == "__main__":
    asyncio.run(test_db_connectivity())