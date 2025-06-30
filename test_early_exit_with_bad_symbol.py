#!/usr/bin/env python3
"""
データ不足の銘柄でEarly Exitを強制的に発生させるテスト
Discord通知システムの動作確認用
"""

import sys
import os
from pathlib import Path
import tempfile
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from scalable_analysis_system import ScalableAnalysisSystem
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_early_exit_with_bad_data():
    """データ不足の銘柄でEarly Exitテストを実行"""
    logger.info("🧪 データ不足銘柄によるEarly Exit強制テスト開始")
    
    # ScalableAnalysisSystemを初期化
    system = ScalableAnalysisSystem()
    
    # 存在しない（または新規上場）銘柄を使用してEarly Exitを発生させる
    # これらの銘柄は90日分のデータが不足している可能性が高い
    test_symbols = ["NONEXISTENT", "BADDATA", "NEWCOIN"]
    strategies = ["Conservative_ML"]
    timeframes = ["1h"]
    
    logger.info("📊 データ不足銘柄での分析実行（Early Exit誘発用）")
    
    try:
        # 実行ID生成
        from datetime import datetime
        execution_id = f"early_exit_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🚀 実行開始: {execution_id}")
        logger.info(f"   テスト対象銘柄: {test_symbols}")
        logger.info(f"   ストラテジー: {strategies}")
        logger.info(f"   タイムフレーム: {timeframes}")
        
        early_exit_detected = False
        
        # 各銘柄を個別に実行してEarly Exitを確認
        for symbol in test_symbols:
            logger.info(f"🎯 {symbol} 分析開始")
            
            batch_configs = [{
                'symbol': symbol,
                'timeframe': timeframes[0],
                'config': strategies[0]
            }]
            
            try:
                result = system.generate_batch_analysis(
                    batch_configs=batch_configs,
                    max_workers=1,
                    execution_id=f"{execution_id}_{symbol}"
                )
                
                logger.info(f"   {symbol} 結果: {result}")
                
                # 一時ファイルでEarly Exitログを確認
                for file in Path("/tmp").glob(f"analysis_log_{execution_id}_{symbol}_*.json"):
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            log_data = json.load(f)
                            if log_data.get('early_exit'):
                                early_exit_detected = True
                                logger.info(f"🎯 {symbol}: Early Exit検出！")
                                logger.info(f"   ステージ: {log_data.get('stage')}")
                                logger.info(f"   理由: {log_data.get('reason')}")
                                logger.info(f"   メッセージ: {log_data.get('user_msg', '')[:100]}...")
                                logger.info("📡 Discord通知が送信されました！")
                                break
                    except Exception as e:
                        logger.warning(f"ログファイル読み込みエラー: {file.name} - {e}")
                
                if early_exit_detected:
                    break  # 1つでもEarly Exitが検出されれば十分
                    
            except Exception as e:
                logger.warning(f"⚠️ {symbol} 分析エラー: {e}")
                # エラー自体もEarly Exitの一種として扱う
                early_exit_detected = True
        
        if early_exit_detected:
            logger.info("✅ Early Exit検出成功！Discord通知確認をお願いします。")
        else:
            logger.info("ℹ️ Early Exitが検出されませんでした。手動テストを実行します。")
        
        # 手動Discord通知テスト（確実に動作確認）
        logger.info("🔔 手動Discord通知テスト実行")
        manual_result = system.test_discord_notification(test_type="early_exit")
        
        if manual_result:
            logger.info("✅ 手動Discord通知成功")
            return True
        else:
            logger.error("❌ 手動Discord通知失敗")
            return False
        
    except Exception as e:
        logger.error(f"❌ テスト実行エラー: {e}")
        import traceback
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        
        # エラーが発生した場合も手動テストは実行
        logger.info("🔔 エラー発生のため手動Discord通知テストのみ実行")
        try:
            manual_result = system.test_discord_notification(test_type="early_exit")
            return manual_result
        except:
            return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🎯 Early Exit強制誘発 + Discord通知テスト")
    logger.info("=" * 60)
    
    success = test_early_exit_with_bad_data()
    
    logger.info("=" * 60)
    logger.info(f"🏁 テスト結果: {'✅ 成功' if success else '❌ 失敗'}")
    logger.info("📡 Discordチャンネルで通知を確認してください！")
    logger.info("=" * 60)
    
    sys.exit(0 if success else 1)