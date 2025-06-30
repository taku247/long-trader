#!/usr/bin/env python3
"""
MEW銘柄の監視システム総合レポート
"""

import sys
import os
from pathlib import Path
import sqlite3
import json
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_mew_current_status():
    """MEWの現在の状況確認"""
    logger.info("📊 MEW銘柄の現在の状況")
    
    try:
        # execution_logs.dbからMEWの状況確認
        with sqlite3.connect("execution_logs.db") as conn:
            cursor = conn.cursor()
            
            # MEWの最新実行ログ
            cursor.execute("""
                SELECT execution_id, status, timestamp_start, timestamp_end, 
                       current_operation, progress_percentage, errors, metadata
                FROM execution_logs 
                WHERE symbol = 'MEW' 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            
            results = cursor.fetchall()
            
            if results:
                logger.info("🔍 MEW実行履歴 (最新3件):")
                for i, row in enumerate(results, 1):
                    execution_id, status, start, end, operation, progress, errors, metadata = row
                    logger.info(f"【{i}】実行ID: {execution_id}")
                    logger.info(f"   ステータス: {status}")
                    logger.info(f"   開始時刻: {start}")
                    logger.info(f"   終了時刻: {end}")
                    logger.info(f"   進捗: {progress}%")
                    logger.info(f"   操作: {operation}")
                    
                    if errors and errors != "[]":
                        logger.info(f"   エラー: {errors}")
                    
                    if metadata:
                        try:
                            meta = json.loads(metadata)
                            logger.info(f"   メタデータ: {meta}")
                        except:
                            logger.info(f"   メタデータ: {metadata}")
                    
                    logger.info("   " + "-" * 50)
                
                # 最新実行の詳細
                latest = results[0]
                logger.info(f"📋 最新実行状況:")
                logger.info(f"   MEWは {latest[1]} ステータスです")
                if latest[1] == "SUCCESS":
                    logger.info("   ✅ MEWの分析は正常に完了しています")
                elif latest[1] == "RUNNING":
                    logger.info("   🔄 MEWの分析が実行中です")
                else:
                    logger.info(f"   ⚠️ MEWの分析ステータス: {latest[1]}")
                    
            else:
                logger.info("ℹ️ MEWの実行ログが見つかりません")
    
    except Exception as e:
        logger.error(f"❌ MEWステータス確認エラー: {e}")

def check_early_exit_logs():
    """Early Exitログファイルの確認"""
    logger.info("🔍 Early Exitログファイル確認")
    
    # /tmpディレクトリのanalysis_logファイルを確認
    tmp_dir = Path("/tmp")
    early_exit_logs = []
    
    for log_file in tmp_dir.glob("analysis_log_*.json"):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
                if log_data.get('early_exit'):
                    early_exit_logs.append((log_file, log_data))
        except Exception as e:
            continue
    
    if early_exit_logs:
        logger.info(f"📋 Early Exit検出: {len(early_exit_logs)}件")
        for log_file, log_data in early_exit_logs[-5:]:  # 最新5件
            logger.info(f"   ファイル: {log_file.name}")
            logger.info(f"   銘柄: {log_data.get('symbol')}")
            logger.info(f"   タイムフレーム: {log_data.get('timeframe')}")
            logger.info(f"   ステージ: {log_data.get('stage')}")
            logger.info(f"   理由: {log_data.get('reason')}")
            logger.info(f"   時刻: {log_data.get('timestamp')}")
            logger.info("   " + "-" * 40)
    else:
        logger.info("ℹ️ 現在、Early Exitログは見つかりません")

def test_discord_connectivity():
    """Discord通知接続性テスト"""
    logger.info("📡 Discord通知接続性テスト")
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # シンプル通知テスト
        result = system.test_discord_notification(test_type="simple")
        
        if result:
            logger.info("✅ Discord通知システムは正常に動作しています")
            logger.info("   MEWでEarly Exitが発生した場合、自動でDiscord通知が送信されます")
            return True
        else:
            logger.error("❌ Discord通知システムに問題があります")
            return False
            
    except Exception as e:
        logger.error(f"❌ Discord接続テストエラー: {e}")
        return False

def monitoring_instructions():
    """監視方法の説明"""
    logger.info("📋 MEW監視継続のための方法")
    logger.info("")
    logger.info("【1】リアルタイム監視方法:")
    logger.info("   - Webダッシュボード: http://localhost:5001")
    logger.info("   - 進捗確認: http://localhost:5001/analysis-progress")
    logger.info("   - 銘柄管理: http://localhost:5001/symbols-enhanced")
    logger.info("")
    logger.info("【2】Early Exit確認方法:")
    logger.info("   - 一時ファイル: ls -la /tmp/analysis_log_*.json")
    logger.info("   - このスクリプト実行: python mew_monitoring_summary.py")
    logger.info("")
    logger.info("【3】Discord通知確認:")
    logger.info("   - 手動テスト: python test_discord_notification.py")
    logger.info("   - シンプルテスト: python simple_early_exit_test.py")
    logger.info("")
    logger.info("【4】MEW新規分析実行方法:")
    logger.info("   - Webから: http://localhost:5001 の「銘柄追加」")
    logger.info("   - APIから: curl -X POST http://localhost:5001/api/symbol/add -d '{\"symbol\":\"MEW\"}'")
    logger.info("")
    logger.info("【5】Early Exit強制テスト:")
    logger.info("   - 実行: python test_early_exit_with_bad_symbol.py")
    logger.info("   - 存在しない銘柄でEarly Exitを誘発してDiscord通知をテスト")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🎯 MEW銘柄監視システム総合レポート")
    logger.info("=" * 60)
    
    # 1. MEW現在の状況確認
    logger.info("【1】MEW現在の状況")
    check_mew_current_status()
    
    print("\n" + "=" * 60)
    
    # 2. Early Exitログ確認
    logger.info("【2】Early Exitログ状況")
    check_early_exit_logs()
    
    print("\n" + "=" * 60)
    
    # 3. Discord通知テスト
    logger.info("【3】Discord通知システム確認")
    discord_ok = test_discord_connectivity()
    
    print("\n" + "=" * 60)
    
    # 4. 監視方法の説明
    logger.info("【4】継続監視の方法")
    monitoring_instructions()
    
    logger.info("=" * 60)
    logger.info("🏁 監視レポート完了")
    if discord_ok:
        logger.info("✅ Discord通知システムは正常動作中")
        logger.info("📡 MEWでEarly Exitが発生した場合、自動通知されます")
    else:
        logger.warning("⚠️ Discord通知システムに問題がある可能性があります")
    logger.info("=" * 60)