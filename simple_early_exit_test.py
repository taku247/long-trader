#!/usr/bin/env python3
"""
シンプルなEarly Exit & Discord通知テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_analysis_result_directly():
    """AnalysisResultとDiscord通知を直接テスト"""
    logger.info("🧪 AnalysisResult & Discord通知直接テスト")
    
    try:
        from engines.analysis_result import AnalysisResult, AnalysisStage, ExitReason
        from scalable_analysis_system import ScalableAnalysisSystem
        from datetime import datetime
        
        # AnalysisResultでEarly Exitを作成
        result = AnalysisResult(
            symbol="TESTCOIN",
            timeframe="1h",
            strategy="Conservative_ML",
            execution_id=f"test_early_exit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        # Early Exitをマーク
        result.mark_early_exit(
            stage=AnalysisStage.SUPPORT_RESISTANCE,
            reason=ExitReason.NO_SUPPORT_RESISTANCE,
            error_message="テスト用Early Exit - 支持線・抵抗線が検出されませんでした"
        )
        
        logger.info(f"✅ AnalysisResult作成完了:")
        logger.info(f"   early_exit: {result.early_exit}")
        logger.info(f"   exit_stage: {result.exit_stage}")
        logger.info(f"   exit_reason: {result.exit_reason}")
        logger.info(f"   詳細メッセージ: {result.get_detailed_log_message()}")
        logger.info(f"   ユーザー向けメッセージ: {result.get_user_friendly_message()}")
        
        # ScalableAnalysisSystemを使ってDiscord通知
        system = ScalableAnalysisSystem()
        
        # Discord通知を直接呼び出し
        logger.info("📡 Discord通知テスト実行")
        
        system._handle_discord_notification_for_result(
            result=result,
            symbol="TESTCOIN",
            timeframe="1h", 
            config="Conservative_ML",
            execution_id=result.execution_id
        )
        
        logger.info("✅ Discord通知処理完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ テストエラー: {e}")
        import traceback
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        return False

def test_manual_discord_only():
    """手動Discord通知のみテスト"""
    logger.info("🔔 手動Discord通知のみテスト")
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # Early Exit通知テスト
        result1 = system.test_discord_notification(test_type="early_exit")
        logger.info(f"   Early Exit通知: {'✅ 成功' if result1 else '❌ 失敗'}")
        
        # シンプル通知テスト
        result2 = system.test_discord_notification(test_type="simple")
        logger.info(f"   シンプル通知: {'✅ 成功' if result2 else '❌ 失敗'}")
        
        return result1 and result2
        
    except Exception as e:
        logger.error(f"❌ 手動Discord通知エラー: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🎯 シンプルEarly Exit & Discord通知テスト")
    logger.info("=" * 50)
    
    # 1. 手動Discord通知テスト（確実に動作）
    logger.info("【1】手動Discord通知テスト")
    manual_result = test_manual_discord_only()
    
    print("\n" + "=" * 50)
    
    # 2. AnalysisResult経由のDiscord通知テスト
    logger.info("【2】AnalysisResult経由Discord通知テスト")
    analysis_result = test_analysis_result_directly()
    
    logger.info("=" * 50)
    logger.info("🏁 テスト結果:")
    logger.info(f"   手動Discord通知: {'✅ 成功' if manual_result else '❌ 失敗'}")
    logger.info(f"   AnalysisResult通知: {'✅ 成功' if analysis_result else '❌ 失敗'}")
    logger.info("📡 Discordチャンネルで通知を確認してください！")
    logger.info("=" * 50)
    
    sys.exit(0 if (manual_result and analysis_result) else 1)