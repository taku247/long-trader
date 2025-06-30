#!/usr/bin/env python3
"""
Discord通知システムテスト
ProcessPoolExecutor環境でのDiscord通知機能を検証
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from scalable_analysis_system import ScalableAnalysisSystem
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_discord_notifications():
    """Discord通知機能のテスト"""
    logger.info("🧪 Discord通知システムテスト開始")
    
    # ScalableAnalysisSystemを初期化
    system = ScalableAnalysisSystem()
    
    # 1. シンプル通知テスト
    logger.info("📡 テスト1: シンプル通知")
    result1 = system.test_discord_notification(test_type="simple")
    
    if result1:
        logger.info("✅ シンプル通知テスト成功")
    else:
        logger.error("❌ シンプル通知テスト失敗")
    
    # 2. Early Exit通知テスト
    logger.info("📡 テスト2: Early Exit通知")
    result2 = system.test_discord_notification(test_type="early_exit")
    
    if result2:
        logger.info("✅ Early Exit通知テスト成功")
    else:
        logger.error("❌ Early Exit通知テスト失敗")
    
    # 結果サマリー
    logger.info("=" * 50)
    logger.info("🏁 Discord通知テスト結果:")
    logger.info(f"   シンプル通知: {'✅ 成功' if result1 else '❌ 失敗'}")
    logger.info(f"   Early Exit通知: {'✅ 成功' if result2 else '❌ 失敗'}")
    
    if result1 and result2:
        logger.info("🎉 すべてのテストが成功しました！")
        return True
    else:
        logger.error("⚠️ 一部またはすべてのテストが失敗しました")
        return False

if __name__ == "__main__":
    success = test_discord_notifications()
    sys.exit(0 if success else 1)