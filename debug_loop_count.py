#!/usr/bin/env python3
"""
実際のループ回数と処理時間を詳細に計測
"""

import time
import os
from datetime import datetime, timezone, timedelta

def debug_actual_loop_execution():
    """実際のループ実行回数と時間を計測"""
    
    print("🔍 実際のループ実行回数と時間の計測\n")
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        from engines import HighLeverageBotOrchestrator
        
        # テスト設定
        symbol = 'AAVE'
        timeframe = '1h'  
        config = 'Conservative_ML'
        
        print(f"テスト対象: {symbol} {timeframe} {config}")
        
        # 環境変数設定
        os.environ['CURRENT_EXECUTION_ID'] = 'DEBUG_LOOP_COUNT'
        
        # システム初期化
        system = ScalableAnalysisSystem()
        
        print("📊 _generate_real_analysis を直接実行...")
        
        # 開始時間記録
        start_time = time.time()
        
        try:
            # _generate_real_analysisを直接実行
            result = system._generate_real_analysis(symbol, timeframe, config)
            
            # 終了時間記録
            end_time = time.time()
            
            print(f"\\n⏱️ 処理時間: {end_time - start_time:.2f}秒")
            print(f"📊 結果: {len(result) if result else 0}件のトレードデータ")
            
        except Exception as e:
            end_time = time.time()
            print(f"\\n❌ エラー発生: {type(e).__name__}: {e}")
            print(f"⏱️ エラーまでの時間: {end_time - start_time:.2f}秒")
            
            # エラーの詳細を分析
            error_str = str(e)
            if "条件ベース分析で有効なシグナルが見つかりませんでした" in error_str:
                print("\\n🔍 詳細分析:")
                print("- これは条件ベース分析完了後のエラー")
                print("- つまり100回の評価は実際に実行された")
                print("- 各評価で瞬時に失敗しているため5秒で完了")
            
    except Exception as e:
        print(f"❌ 全体エラー: {type(e).__name__}: {e}")


def debug_single_evaluation_time():
    """単一評価の実行時間を計測"""
    
    print("\\n" + "="*60)
    print("🔍 単一評価の実行時間計測")
    print("="*60)
    
    try:
        from engines import HighLeverageBotOrchestrator
        
        # Bot初期化
        bot = HighLeverageBotOrchestrator()
        
        symbol = 'AAVE'
        timeframe = '1h'
        
        # 90日前の時刻
        test_time = datetime.now(timezone.utc) - timedelta(days=89, hours=1)
        
        print(f"単一評価テスト: {symbol} {timeframe} at {test_time}")
        
        # 単一評価の時間計測
        start_time = time.time()
        
        try:
            result = bot.analyze_leverage_opportunity(
                symbol, timeframe, 
                is_backtest=True, 
                target_timestamp=test_time
            )
            
            end_time = time.time()
            print(f"✅ 単一評価成功: {end_time - start_time:.3f}秒")
            
        except Exception as e:
            end_time = time.time()
            print(f"❌ 単一評価失敗: {end_time - start_time:.3f}秒")
            print(f"   エラー: {type(e).__name__}: {str(e)[:100]}...")
            
            # もし0.1秒未満なら瞬時失敗
            if end_time - start_time < 0.1:
                print("   ⚡ 瞬時失敗 - データ取得すらされていない可能性")
            elif end_time - start_time < 1.0:
                print("   🏃 高速失敗 - 軽い処理で即座に終了")
            else:
                print("   🐌 遅い失敗 - 重い処理後にエラー")
        
        # 計算: 100回実行した場合の推定時間
        single_time = end_time - start_time
        estimated_100_times = single_time * 100
        
        print(f"\\n📊 推定計算:")
        print(f"   単一評価時間: {single_time:.3f}秒")
        print(f"   100回実行時間: {estimated_100_times:.1f}秒")
        print(f"   実際の完了時間: ~5秒")
        
        if estimated_100_times > 10:
            print(f"   ❌ 矛盾: 推定{estimated_100_times:.0f}秒 vs 実際5秒")
        else:
            print(f"   ✅ 整合: 推定時間と実際時間が近い")
        
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")


if __name__ == "__main__":
    debug_actual_loop_execution()
    debug_single_evaluation_time()