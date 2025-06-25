#!/usr/bin/env python3
"""
ループ終了の正確なメカニズムを徹底的に調査
なぜ数回で終了するのかを完全に特定
"""

import os
import time
import logging
from datetime import datetime, timezone, timedelta

def debug_actual_loop_with_instrumentation():
    """実際のループ実行に計測コードを追加して詳細調査"""
    
    print("🔍 実際のループ実行の徹底調査\n")
    
    try:
        # scalable_analysis_system.pyを直接インポートして調査
        from scalable_analysis_system import ScalableAnalysisSystem
        
        # デバッグ用のシステムインスタンス
        system = ScalableAnalysisSystem()
        
        # テスト設定
        symbol = 'AAVE'
        timeframe = '1h'
        config = 'Conservative_ML'
        
        print(f"テスト対象: {symbol} {timeframe} {config}")
        
        # 環境変数設定
        os.environ['CURRENT_EXECUTION_ID'] = 'DEBUG_DEEP'
        
        # _generate_real_analysisを直接実行して詳細ログ取得
        print("\\n📊 _generate_real_analysis を詳細ログ付きで実行...")
        
        start_time_total = time.time()
        
        try:
            # 実際の関数実行
            result = system._generate_real_analysis(symbol, timeframe, config)
            
            end_time_total = time.time()
            
            print(f"\\n⏱️ 総処理時間: {end_time_total - start_time_total:.2f}秒")
            print(f"📊 結果: {len(result) if result else 0}件のトレードデータ")
            
        except Exception as e:
            end_time_total = time.time()
            print(f"\\n❌ エラー発生: {type(e).__name__}: {e}")
            print(f"⏱️ エラーまでの時間: {end_time_total - start_time_total:.2f}秒")
            
            # エラー詳細分析
            error_message = str(e)
            
            if "条件ベース分析で有効なシグナルが見つかりませんでした" in error_message:
                print("\\n🎯 エラー原因特定:")
                print("   これは while ループ完了後のエラー")
                print("   つまりループは正常に全て実行された")
                print("   問題は最終的にシグナルが0件だったこと")
                
            elif "の分析結果確認中にエラーが発生" in error_message:
                print("\\n🎯 エラー原因特定:")
                print("   これは分析完了後のエラー")
                print("   ループ自体は完了している")
                
            elif "支持線・抵抗線" in error_message:
                print("\\n🎯 エラー原因特定:")
                print("   支持線・抵抗線検出エラー")
                print("   ループ内で例外が発生した可能性")
                
    except Exception as e:
        print(f"❌ 全体エラー: {type(e).__name__}: {e}")


def debug_loop_instrumentation():
    """ループに直接計測コードを追加"""
    
    print("\\n" + "="*60)
    print("🔍 ループ実行の直接計測")
    print("="*60)
    
    try:
        from engines import HighLeverageBotOrchestrator
        import json
        
        # 設定読み込み
        with open('config/timeframe_conditions.json', 'r') as f:
            tf_config = json.load(f)
        
        timeframe = '1h'
        config_data = tf_config['timeframe_configs'][timeframe]
        max_evaluations = config_data.get('max_evaluations', 100)
        evaluation_interval_minutes = config_data.get('evaluation_interval_minutes', 240)
        
        print(f"📊 設定確認:")
        print(f"   max_evaluations: {max_evaluations}")
        print(f"   evaluation_interval: {evaluation_interval_minutes}分")
        
        # 時間範囲設定
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=90)
        evaluation_interval = timedelta(minutes=evaluation_interval_minutes)
        max_signals = max_evaluations // 2
        
        print(f"\\n⏱️ 時間設定:")
        print(f"   start_time: {start_time}")
        print(f"   end_time: {end_time}")
        print(f"   evaluation_interval: {evaluation_interval}")
        print(f"   max_signals: {max_signals}")
        
        # Bot初期化
        bot = HighLeverageBotOrchestrator()
        symbol = 'AAVE'
        config = 'Conservative_ML'
        
        # ループの手動シミュレーション
        print(f"\\n🔄 while条件のシミュレーション開始:")
        print(f"   while (current_time <= end_time and")
        print(f"          total_evaluations < max_evaluations and")
        print(f"          signals_generated < max_signals):")
        print()
        
        current_time = start_time
        total_evaluations = 0
        signals_generated = 0
        
        loop_start_time = time.time()
        
        while (current_time <= end_time and 
               total_evaluations < max_evaluations and 
               signals_generated < max_signals):
            
            total_evaluations += 1
            iteration_start = time.time()
            
            print(f"📍 評価 {total_evaluations}:")
            print(f"   時刻: {current_time.strftime('%Y-%m-%d %H:%M')}")
            
            # 条件チェック
            condition1 = current_time <= end_time
            condition2 = total_evaluations < max_evaluations
            condition3 = signals_generated < max_signals
            
            print(f"   条件1 (時間内): {condition1}")
            print(f"   条件2 (評価数): {condition2} ({total_evaluations} < {max_evaluations})")
            print(f"   条件3 (シグナル): {condition3} ({signals_generated} < {max_signals})")
            
            try:
                # 実際の分析を実行
                result = bot.analyze_leverage_opportunity(
                    symbol, timeframe, 
                    is_backtest=True, 
                    target_timestamp=current_time
                )
                
                iteration_end = time.time()
                iteration_time = iteration_end - iteration_start
                
                print(f"   ✅ 分析完了: {iteration_time:.2f}秒")
                
                if result and 'current_price' in result:
                    print(f"   📊 結果: price={result.get('current_price')}")
                    # エントリー条件評価（簡易版）
                    leverage = result.get('leverage', 0)
                    confidence = result.get('confidence', 0)
                    rr = result.get('risk_reward_ratio', 0)
                    
                    print(f"   📈 詳細: leverage={leverage}, confidence={confidence}, RR={rr}")
                    
                    # 簡単な条件チェック（実際の_evaluate_entry_conditionsは複雑）
                    if leverage > 0 and confidence > 0 and rr > 0:
                        print(f"   🎯 潜在的エントリー候補")
                else:
                    print(f"   ❌ 結果なし or current_price不足")
                
            except Exception as e:
                iteration_end = time.time()
                iteration_time = iteration_end - iteration_start
                
                print(f"   ❌ 分析エラー: {iteration_time:.2f}秒")
                print(f"   エラー: {type(e).__name__}: {str(e)[:80]}...")
                
                # 特定のエラーで早期終了するかチェック
                error_str = str(e)
                if "支持線・抵抗線" in error_str or "サポートレベル" in error_str:
                    print(f"   🔴 支持線・抵抗線検出エラー")
                elif "データ/設定不足" in error_str:
                    print(f"   🔴 データ/設定不足エラー")
                elif "安全な分析ができません" in error_str:
                    print(f"   🔴 安全性エラー")
            
            # 次の時刻に進む
            current_time += evaluation_interval
            
            # デバッグ用：最初の5回で停止
            if total_evaluations >= 5:
                print(f"\\n⏹️ デバッグ用停止（5回実行）")
                break
            
            print()
        
        loop_end_time = time.time()
        total_loop_time = loop_end_time - loop_start_time
        
        print(f"\\n📊 ループ実行結果:")
        print(f"   実行回数: {total_evaluations}")
        print(f"   総時間: {total_loop_time:.2f}秒")
        print(f"   平均時間/回: {total_loop_time/total_evaluations:.2f}秒")
        print(f"   signals_generated: {signals_generated}")
        
        # 終了条件の確認
        final_condition1 = current_time <= end_time
        final_condition2 = total_evaluations < max_evaluations
        final_condition3 = signals_generated < max_signals
        
        print(f"\\n🏁 終了時の条件:")
        print(f"   条件1 (時間内): {final_condition1}")
        print(f"   条件2 (評価数): {final_condition2}")
        print(f"   条件3 (シグナル): {final_condition3}")
        print(f"   while条件: {final_condition1 and final_condition2 and final_condition3}")
        
        if not (final_condition1 and final_condition2 and final_condition3):
            print(f"\\n✅ while条件がFalseになって正常終了")
        else:
            print(f"\\n❓ while条件はTrueだが何らかの理由で終了")
        
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")


def debug_exception_propagation():
    """例外の伝播とキャッチを詳細調査"""
    
    print("\\n" + "="*60)
    print("🔍 例外の伝播とキャッチの詳細調査")
    print("="*60)
    
    try:
        # scalable_analysis_system.pyの例外処理パターンを確認
        from scalable_analysis_system import ScalableAnalysisSystem
        import inspect
        
        system = ScalableAnalysisSystem()
        
        # _generate_real_analysisの例外処理を解析
        source = inspect.getsource(system._generate_real_analysis)
        lines = source.split('\\n')
        
        print("📝 例外処理パターンの分析:")
        
        try_blocks = []
        except_blocks = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith('try:'):
                try_blocks.append(i)
            elif line_stripped.startswith('except') and ':' in line_stripped:
                except_blocks.append((i, line_stripped))
        
        print(f"   try ブロック: {len(try_blocks)}個")
        print(f"   except ブロック: {len(except_blocks)}個")
        
        for i, (line_num, except_line) in enumerate(except_blocks):
            print(f"   except {i+1}: Line {line_num}: {except_line}")
            
            # 次の数行でどのような処理をしているか確認
            for j in range(line_num + 1, min(line_num + 5, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith('#'):
                    print(f"     → {next_line}")
                    if 'return' in next_line or 'raise' in next_line or 'break' in next_line:
                        break
        
        # 特に重要な例外処理を詳細確認
        print(f"\\n🔍 重要な例外処理の詳細:")
        
        for line_num, except_line in except_blocks:
            if 'Exception' in except_line and 'as e' in except_line:
                print(f"\\n   Line {line_num}: {except_line}")
                
                # この except ブロックの処理内容を確認
                for j in range(line_num + 1, min(line_num + 10, len(lines))):
                    check_line = lines[j].strip()
                    if check_line:
                        print(f"     {check_line}")
                        if ('return' in check_line or 
                            'raise' in check_line or 
                            check_line.startswith('except') or
                            check_line.startswith('def ')):
                            break
        
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")


if __name__ == "__main__":
    debug_actual_loop_with_instrumentation()
    debug_loop_instrumentation()
    debug_exception_propagation()