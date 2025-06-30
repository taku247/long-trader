#!/usr/bin/env python3
"""
Early Exit発生プロセスのデバッグ
子プロセスで何が起こっているかを詳細に調査
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from scalable_analysis_system import ScalableAnalysisSystem
import logging

# ログ設定（詳細モード）
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_early_exit_process():
    """Early Exit発生プロセスのデバッグ"""
    logger.info("🔍 Early Exit発生プロセスのデバッグ開始")
    
    # ScalableAnalysisSystemを初期化
    system = ScalableAnalysisSystem()
    
    # 直接_generate_single_analysisを呼び出してEarly Exitを確認
    logger.info("📊 _generate_single_analysis直接呼び出しテスト")
    
    try:
        from datetime import datetime
        execution_id = f"debug_early_exit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 存在しない銘柄で直接分析実行
        test_symbol = "NONEXISTENT_DEBUG"
        test_timeframe = "1h"
        test_config = "Conservative_ML"
        
        logger.info(f"🎯 直接分析実行: {test_symbol} {test_timeframe} {test_config}")
        
        # 環境変数にexecution_idを設定
        os.environ['CURRENT_EXECUTION_ID'] = execution_id
        
        result = system._generate_single_analysis(
            symbol=test_symbol,
            timeframe=test_timeframe,
            config=test_config,
            execution_id=execution_id
        )
        
        logger.info(f"📋 分析結果: {result}")
        logger.info(f"   結果タイプ: {type(result)}")
        
        # AnalysisResultの場合
        from engines.analysis_result import AnalysisResult
        if isinstance(result, AnalysisResult):
            logger.info(f"   AnalysisResult詳細:")
            logger.info(f"     completed: {result.completed}")
            logger.info(f"     early_exit: {result.early_exit}")
            logger.info(f"     exit_stage: {result.exit_stage}")
            logger.info(f"     exit_reason: {result.exit_reason}")
            logger.info(f"     error_details: {result.error_details}")
            
            if result.early_exit:
                logger.info("🎯 Early Exit検出！")
                logger.info(f"   詳細メッセージ: {result.get_detailed_log_message()}")
                logger.info(f"   ユーザー向けメッセージ: {result.get_user_friendly_message()}")
                logger.info("📡 この時点でDiscord通知が送信されるはずです")
            else:
                logger.info("ℹ️ Early Exitなし")
        else:
            logger.info("⚠️ AnalysisResult以外の結果")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ デバッグ実行エラー: {e}")
        import traceback
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        return False

def test_data_fetch_directly():
    """データ取得を直接テストしてEarly Exitを確認"""
    logger.info("📡 データ取得直接テスト")
    
    try:
        from data_fetcher import DataFetcher
        from datetime import datetime, timedelta
        
        # データフェッチャー初期化
        fetcher = DataFetcher()
        
        # 存在しない銘柄でデータ取得試行
        test_symbol = "NONEXISTENT_DIRECT"
        timeframe = "1h"
        
        # 90日分のデータを要求
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        logger.info(f"🎯 データ取得テスト: {test_symbol}")
        logger.info(f"   期間: {start_date} - {end_date}")
        logger.info(f"   タイムフレーム: {timeframe}")
        
        try:
            data = fetcher.fetch_ohlcv(
                symbol=test_symbol,
                timeframe=timeframe,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if data is None or data.empty:
                logger.info("🎯 データ取得失敗 - Early Exit候補")
                logger.info("   この状況でEarly Exitが発生するはずです")
                return "DATA_EMPTY"
            else:
                logger.info(f"📊 データ取得成功: {len(data)}行")
                return "DATA_SUCCESS"
                
        except Exception as data_error:
            logger.info(f"🎯 データ取得例外 - Early Exit候補: {data_error}")
            logger.info("   この例外でEarly Exitが発生するはずです")
            return "DATA_ERROR"
        
    except Exception as e:
        logger.error(f"❌ データ取得テストエラー: {e}")
        return "TEST_ERROR"

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔍 Early Exit発生プロセス詳細デバッグ")
    logger.info("=" * 60)
    
    # 1. データ取得直接テスト
    logger.info("【1】データ取得直接テスト")
    data_result = test_data_fetch_directly()
    logger.info(f"   結果: {data_result}")
    
    print("\n" + "=" * 60)
    
    # 2. 分析プロセス直接テスト
    logger.info("【2】分析プロセス直接テスト")
    analysis_result = debug_early_exit_process()
    logger.info(f"   結果: {'✅ 成功' if analysis_result else '❌ 失敗'}")
    
    logger.info("=" * 60)
    logger.info("🏁 デバッグ完了")
    logger.info("=" * 60)