#!/usr/bin/env python3
"""
実データ統合テスト

scalable_analysis_system.pyで実際にOHLCVデータを取得して
FilteringFrameworkで使用する統合テストスクリプト
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scalable_analysis_system import ScalableAnalysisSystem
from auto_symbol_training import AutoSymbolTrainer

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_real_data_integration():
    """実データを使用した統合テスト"""
    
    logger.info("🧪 実データ統合テスト開始")
    
    # 1. テスト用のシンボルと設定
    test_symbol = "BTC"  # BTCは確実にデータが存在する
    test_timeframe = "1h"
    test_strategy = "Balanced_Conservative"
    
    # 2. ScalableAnalysisSystemの初期化
    analysis_system = ScalableAnalysisSystem(base_dir="test_real_data_analysis")
    
    # 3. 単一分析の実行（実データ取得含む）
    logger.info(f"📊 {test_symbol} {test_timeframe} {test_strategy} の分析開始")
    
    try:
        # execution_idを設定
        execution_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.environ['CURRENT_EXECUTION_ID'] = execution_id
        
        # 分析実行
        success, metrics = analysis_system._generate_single_analysis(
            symbol=test_symbol,
            timeframe=test_timeframe, 
            config=test_strategy,
            execution_id=execution_id
        )
        
        if success:
            logger.info(f"✅ 分析成功!")
            logger.info(f"   - 総取引数: {metrics.get('total_trades', 0)}")
            logger.info(f"   - シャープレシオ: {metrics.get('sharpe_ratio', 0):.2f}")
            logger.info(f"   - 最大ドローダウン: {metrics.get('max_drawdown', 0):.2%}")
            
            # FilteringFrameworkの統計を確認
            if hasattr(analysis_system, 'filtering_framework') and analysis_system.filtering_framework:
                stats = analysis_system.filtering_framework.get_statistics()
                efficiency = stats.get_efficiency_metrics()
                
                logger.info("📊 フィルタリング統計:")
                logger.info(f"   - 総評価数: {stats.total_evaluations}")
                logger.info(f"   - 有効取引数: {stats.valid_trades}")
                logger.info(f"   - 通過率: {efficiency.get('pass_rate', 0):.2f}%")
                logger.info(f"   - 除外率: {efficiency.get('exclusion_rate', 0):.2f}%")
                
                # フィルター別除外統計
                logger.info("🔍 フィルター別除外数:")
                for filter_name, count in stats.filtering_stats.items():
                    if count > 0:
                        logger.info(f"   - {filter_name}: {count}回")
        else:
            logger.warning(f"⚠️ 分析失敗: {test_symbol} {test_timeframe} {test_strategy}")
            
    except Exception as e:
        logger.error(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        
    # 4. AutoSymbolTrainerを使った統合テスト
    logger.info("\n🤖 AutoSymbolTrainer統合テスト")
    
    training_bot = AutoSymbolTrainer()
    
    try:
        # テスト用の設定で実行
        test_configs = [{
            'symbol': test_symbol,
            'timeframe': test_timeframe,
            'strategy': test_strategy
        }]
        
        # バックテスト実行
        result = await training_bot._run_backtest(test_symbol, test_configs, execution_id)
        
        logger.info(f"✅ バックテスト完了:")
        logger.info(f"   - 成功テスト数: {result['successful_tests']}")
        logger.info(f"   - 失敗テスト数: {result['failed_tests']}")
        
        if result['best_performance']:
            logger.info(f"   - 最高シャープレシオ: {result['best_performance'].get('sharpe_ratio', 0):.2f}")
            
    except Exception as e:
        logger.error(f"❌ AutoSymbolTrainingBotテストエラー: {e}")
        import traceback
        traceback.print_exc()
        
    logger.info("🎉 実データ統合テスト完了")


async def test_filtering_performance():
    """フィルタリングパフォーマンステスト"""
    
    logger.info("⚡ フィルタリングパフォーマンステスト開始")
    
    # 複数の銘柄でテスト
    test_symbols = ["BTC", "ETH", "SOL"]
    timeframes = ["5m", "15m", "1h"]
    
    total_evaluations = 0
    total_valid_trades = 0
    total_time = 0
    
    analysis_system = ScalableAnalysisSystem(base_dir="test_performance_analysis")
    
    for symbol in test_symbols:
        for timeframe in timeframes:
            logger.info(f"\n📊 {symbol} {timeframe} のパフォーマンステスト")
            
            try:
                import time
                start_time = time.time()
                
                # カスタム期間設定（短期間でテスト）
                success, metrics = analysis_system._generate_single_analysis(
                    symbol=symbol,
                    timeframe=timeframe,
                    config="Balanced_Conservative",
                    execution_id=f"perf_test_{symbol}_{timeframe}",
                    custom_period_days=7  # 7日間のみ
                )
                
                elapsed_time = time.time() - start_time
                total_time += elapsed_time
                
                if success and hasattr(analysis_system, 'filtering_framework'):
                    stats = analysis_system.filtering_framework.get_statistics()
                    total_evaluations += stats.total_evaluations
                    total_valid_trades += stats.valid_trades
                    
                    logger.info(f"   - 実行時間: {elapsed_time:.2f}秒")
                    logger.info(f"   - 評価速度: {stats.total_evaluations / elapsed_time:.1f} 評価/秒")
                    
            except Exception as e:
                logger.error(f"❌ {symbol} {timeframe} エラー: {e}")
    
    # 総合統計
    logger.info("\n📊 総合パフォーマンス統計:")
    logger.info(f"   - 総評価数: {total_evaluations:,}")
    logger.info(f"   - 総有効取引数: {total_valid_trades:,}")
    logger.info(f"   - 総実行時間: {total_time:.2f}秒")
    logger.info(f"   - 平均評価速度: {total_evaluations / total_time:.1f} 評価/秒")
    logger.info(f"   - 総通過率: {(total_valid_trades / total_evaluations * 100) if total_evaluations > 0 else 0:.2f}%")


if __name__ == "__main__":
    # 実行選択
    import argparse
    parser = argparse.ArgumentParser(description="実データ統合テスト")
    parser.add_argument("--performance", action="store_true", help="パフォーマンステストを実行")
    args = parser.parse_args()
    
    if args.performance:
        asyncio.run(test_filtering_performance())
    else:
        asyncio.run(test_real_data_integration())