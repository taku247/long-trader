#!/usr/bin/env python3
"""
強制Early Exit発生テスト - Discord通知確認用
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from scalable_analysis_system import ScalableAnalysisSystem
from engines.analysis_result import AnalysisResult, AnalysisStage, ExitReason
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_forced_early_exit():
    """強制的にEarly Exitを発生させてDiscord通知をテスト"""
    logger.info("🧪 強制Early Exitテスト開始")
    
    # ScalableAnalysisSystemを初期化
    system = ScalableAnalysisSystem()
    
    # 環境変数読み込み
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        logger.error("❌ DISCORD_WEBHOOK_URL環境変数が設定されていません")
        return False
    
    # AnalysisResultを作成（Early Exit状態）
    test_scenarios = [
        {
            "symbol": "TEST_INSUFFICIENT_DATA",
            "stage": AnalysisStage.DATA_FETCH,
            "reason": ExitReason.INSUFFICIENT_DATA,
            "error": "テスト用: データ不足によるEarly Exit"
        },
        {
            "symbol": "TEST_NO_SUPPORT_RESISTANCE", 
            "stage": AnalysisStage.SUPPORT_RESISTANCE,
            "reason": ExitReason.NO_SUPPORT_RESISTANCE,
            "error": "テスト用: サポート・レジスタンスレベル検出失敗"
        },
        {
            "symbol": "TEST_ML_FAILURE",
            "stage": AnalysisStage.ML_PREDICTION,
            "reason": ExitReason.ML_PREDICTION_FAILED,
            "error": "テスト用: ML予測システムエラー"
        }
    ]
    
    success_count = 0
    
    for i, scenario in enumerate(test_scenarios, 1):
        logger.info(f"📡 テストシナリオ {i}/{len(test_scenarios)}: {scenario['symbol']}")
        
        # AnalysisResult作成
        result = AnalysisResult(
            symbol=scenario['symbol'],
            timeframe="1h",
            strategy="Conservative_ML-1h",
            execution_id=f"test_early_exit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
        )
        
        # Early Exitをマーク
        result.mark_early_exit(
            stage=scenario['stage'],
            reason=scenario['reason'],
            error_message=scenario['error']
        )
        
        # Discord通知送信
        try:
            notification_success = system._send_discord_notification_sync(
                symbol=scenario['symbol'],
                timeframe="1h",
                strategy="Conservative_ML-1h",
                execution_id=result.execution_id,
                result=result,
                webhook_url=webhook_url
            )
            
            if notification_success:
                logger.info(f"✅ {scenario['symbol']}: Discord通知送信成功")
                success_count += 1
            else:
                logger.error(f"❌ {scenario['symbol']}: Discord通知送信失敗")
                
        except Exception as e:
            logger.error(f"❌ {scenario['symbol']}: Discord通知エラー - {e}")
    
    # 結果レポート
    logger.info("=" * 60)
    logger.info("🏁 強制Early Exit Discord通知テスト結果:")
    logger.info(f"   成功: {success_count}/{len(test_scenarios)} シナリオ")
    
    if success_count == len(test_scenarios):
        logger.info("🎉 すべてのEarly Exitシナリオで通知が成功しました！")
        logger.info("💬 Discordチャンネルを確認してください")
        return True
    else:
        logger.error("⚠️ 一部のシナリオで通知が失敗しました")
        return False

if __name__ == "__main__":
    success = test_forced_early_exit()
    sys.exit(0 if success else 1)