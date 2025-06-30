#!/usr/bin/env python3
"""
実際のEarly Exit発生テスト - ProcessPoolExecutor環境
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加  
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

import subprocess
import time
import sqlite3
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_with_problematic_symbol():
    """問題のある銘柄でProcessPoolExecutor環境でのEarly Exit確認"""
    
    # 存在しない銘柄でテスト（Early Fail段階）
    invalid_symbols = ["XXXINVALID", "NOTEXIST", "BADCOIN"]
    
    # 短時間足で意図的に条件を厳しくしてEarly Exit発生を誘発
    problematic_conditions = [
        {"symbol": "TEST123", "description": "存在しない銘柄"},
        {"symbol": "INVALID", "description": "無効なシンボル"}
    ]
    
    logger.info("🔍 実際のEarly Exit発生テスト開始")
    logger.info("📊 ProcessPoolExecutor環境でのDiscord通知確認")
    
    for test_case in problematic_conditions:
        symbol = test_case["symbol"]
        desc = test_case["description"]
        
        logger.info(f"📡 テスト実行: {symbol} ({desc})")
        
        try:
            # auto_symbol_training.pyを実行（タイムアウト30秒）
            result = subprocess.run([
                "python", "auto_symbol_training.py", 
                "--symbol", symbol
            ], capture_output=True, text=True, timeout=30)
            
            logger.info(f"✅ {symbol}: 実行完了 (exit_code: {result.returncode})")
            
            if result.returncode != 0:
                logger.info(f"⚠️ {symbol}: エラー終了（期待通り）")
                logger.info(f"   stdout: {result.stdout[-200:]}")
                logger.info(f"   stderr: {result.stderr[-200:]}")
            
        except subprocess.TimeoutExpired:
            logger.warning(f"⏰ {symbol}: タイムアウト（30秒）")
        except Exception as e:
            logger.error(f"❌ {symbol}: 実行エラー - {e}")
        
        # 短時間待機
        time.sleep(2)
    
    logger.info("🔍 Discord通知確認:")
    logger.info("   Discordチャンネルでテスト通知を確認してください")
    logger.info("   期待される通知:")
    logger.info("   - Early Exit詳細情報")
    logger.info("   - 銘柄名・実行ID・エラー理由")
    logger.info("   - 改善提案")
    
    return True

if __name__ == "__main__":
    test_with_problematic_symbol()