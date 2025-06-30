#!/usr/bin/env python3
"""
MEW銘柄でEarly Exitを強制的に発生させるテスト
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

def create_early_exit_test():
    """MEW銘柄でEarly Exitテストを実行"""
    logger.info("🧪 MEW Early Exit強制テスト開始")
    
    # ScalableAnalysisSystemを初期化
    system = ScalableAnalysisSystem()
    
    # 1. MEWの通常分析実行（Discord通知確認のため）
    logger.info("📊 MEW分析実行（Discord通知確認用）")
    
    try:
        # MEW分析を1つのストラテジー、1つのタイムフレームで実行
        # リソース使用量を最小化
        symbols = ["MEW"]
        strategies = ["Conservative_ML"]  # 1つのストラテジーのみ
        timeframes = ["1h"]              # 1つのタイムフレームのみ
        
        # 実行ID生成
        from datetime import datetime
        execution_id = f"mew_early_exit_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🚀 実行開始: {execution_id}")
        logger.info(f"   対象: {symbols}")
        logger.info(f"   ストラテジー: {strategies}")
        logger.info(f"   タイムフレーム: {timeframes}")
        
        # 分析実行（generate_batch_analysisを使用）
        batch_configs = []
        for symbol in symbols:
            for strategy in strategies:
                for timeframe in timeframes:
                    batch_configs.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'config': strategy
                    })
        
        logger.info(f"📋 バッチ設定数: {len(batch_configs)}")
        
        result = system.generate_batch_analysis(
            batch_configs=batch_configs,
            max_workers=1,  # 1プロセスのみで実行
            execution_id=execution_id
        )
        
        logger.info(f"✅ 分析完了: {result}")
        
        # 2. 一時ファイルでEarly Exitログを確認
        logger.info("🔍 Early Exitログファイル確認")
        early_exit_logs = []
        
        for file in Path("/tmp").glob(f"analysis_log_{execution_id}_*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                    if log_data.get('early_exit'):
                        early_exit_logs.append(log_data)
                        logger.info(f"📋 Early Exit発見: {file.name}")
                        logger.info(f"   ステージ: {log_data.get('stage')}")
                        logger.info(f"   理由: {log_data.get('reason')}")
                        logger.info(f"   メッセージ: {log_data.get('user_msg', '')[:100]}...")
            except Exception as e:
                logger.warning(f"ログファイル読み込みエラー: {file.name} - {e}")
        
        if early_exit_logs:
            logger.info(f"🎯 Early Exit検出数: {len(early_exit_logs)}")
            logger.info("📡 Discord通知が送信されたはずです。Discordチャンネルを確認してください。")
        else:
            logger.info("ℹ️ Early Exitは発生しませんでした。MEWの分析が正常に完了した可能性があります。")
        
        # 3. 手動Early Exit通知テスト
        logger.info("🔔 手動Early Exit通知テスト")
        manual_test_result = system.test_discord_notification(test_type="early_exit")
        
        if manual_test_result:
            logger.info("✅ 手動Early Exit通知成功")
        else:
            logger.error("❌ 手動Early Exit通知失敗")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ テスト実行エラー: {e}")
        import traceback
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        return False

def monitor_mew_analysis():
    """MEW分析の監視"""
    logger.info("👀 MEW分析状況監視")
    
    # execution_logs.dbからMEWの状況確認
    import sqlite3
    
    try:
        with sqlite3.connect("execution_logs.db") as conn:
            cursor = conn.cursor()
            
            # MEWの最新実行ログ確認
            cursor.execute("""
                SELECT execution_id, status, timestamp_start, timestamp_end, 
                       current_operation, progress_percentage, errors
                FROM execution_logs 
                WHERE symbol = 'MEW' 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            results = cursor.fetchall()
            
            if results:
                logger.info("📊 MEW実行履歴:")
                for row in results:
                    execution_id, status, start, end, operation, progress, errors = row
                    logger.info(f"   ID: {execution_id}")
                    logger.info(f"   ステータス: {status}")
                    logger.info(f"   開始: {start}")
                    logger.info(f"   終了: {end}")
                    logger.info(f"   進捗: {progress}%")
                    logger.info(f"   現在の操作: {operation}")
                    if errors and errors != "[]":
                        logger.info(f"   エラー: {errors}")
                    logger.info("   " + "-" * 40)
            else:
                logger.info("ℹ️ MEWの実行ログが見つかりません")
    
    except Exception as e:
        logger.error(f"❌ MEW監視エラー: {e}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🎯 MEW Early Exit & Discord通知テスト")
    logger.info("=" * 60)
    
    # 1. MEW分析状況監視
    monitor_mew_analysis()
    
    print("\n" + "=" * 60)
    
    # 2. Early Exitテスト実行
    success = create_early_exit_test()
    
    logger.info("=" * 60)
    logger.info(f"🏁 テスト結果: {'✅ 成功' if success else '❌ 失敗'}")
    logger.info("📡 Discord通知の確認をお忘れなく！")
    logger.info("=" * 60)
    
    sys.exit(0 if success else 1)