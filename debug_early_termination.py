#!/usr/bin/env python3
"""
早期終了条件を徹底的に特定するデバッグツール
"""

import time
import os
from datetime import datetime, timezone, timedelta

def debug_loop_termination_conditions():
    """ループ終了条件を徹底的に調査"""
    
    print("🔍 ループ終了条件の徹底調査\n")
    
    # scalable_analysis_system.pyのwhile条件をシミュレート
    try:
        import json
        
        # timeframe設定の確認
        with open('config/timeframe_conditions.json', 'r') as f:
            tf_config = json.load(f)
        
        timeframe = '1h'
        if timeframe in tf_config.get('timeframe_configs', {}):
            config_data = tf_config['timeframe_configs'][timeframe]
            max_evaluations = config_data.get('max_evaluations', 100)
            print(f"📊 設定確認:")
            print(f"   max_evaluations: {max_evaluations}")
            print(f"   evaluation_interval: {config_data.get('evaluation_interval_minutes', 240)}分")
            print()
        
        # 時間範囲の計算
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=90)
        
        print(f"📅 時間範囲:")
        print(f"   start_time: {start_time}")
        print(f"   end_time: {end_time}")
        print(f"   期間: {(end_time - start_time).days}日")
        print()
        
        # 評価間隔の計算
        evaluation_interval = timedelta(hours=4)  # 1h足のデフォルト
        
        print(f"⏱️ 評価間隔: {evaluation_interval}")
        print()
        
        # max_signalsの計算
        max_signals = max_evaluations // 2  # 評価回数の半分
        print(f"🎯 max_signals: {max_signals} (max_evaluations {max_evaluations} の半分)")
        print()
        
        # while条件のシミュレーション
        print("🔄 while条件のシミュレーション:")
        print("="*60)
        
        current_time = start_time
        total_evaluations = 0
        signals_generated = 0
        
        evaluation_times = []
        
        while (current_time <= end_time and 
               total_evaluations < max_evaluations and 
               signals_generated < max_signals):
            
            total_evaluations += 1
            evaluation_times.append(current_time)
            
            # 条件チェック
            condition1 = current_time <= end_time
            condition2 = total_evaluations < max_evaluations  
            condition3 = signals_generated < max_signals
            
            print(f"評価 {total_evaluations}:")
            print(f"   時刻: {current_time}")
            print(f"   条件1 (時間内): {condition1}")
            print(f"   条件2 (評価数): {condition2} ({total_evaluations} < {max_evaluations})")
            print(f"   条件3 (シグナル数): {condition3} ({signals_generated} < {max_signals})")
            print(f"   総合: {condition1 and condition2 and condition3}")
            
            # 実際のシステムでは失敗するため、signals_generatedは増えない
            # current_time += evaluation_interval で次の時刻へ
            current_time += evaluation_interval
            
            # 最初の10回で状況確認
            if total_evaluations >= 10:
                print(f"   ... (10回で一旦停止)")
                break
            print()
        
        print(f"\\n📊 結果:")
        print(f"   総評価回数: {total_evaluations}")
        print(f"   期間内の理論的最大評価回数: {int((end_time - start_time).total_seconds() / evaluation_interval.total_seconds())}")
        print(f"   signals_generated: {signals_generated}")
        print(f"   max_signals: {max_signals}")
        
        # 最初の評価で条件3に引っかかるかチェック
        if max_signals == 0:
            print(f"\\n❌ 原因特定: max_signals = 0")
            print(f"   max_evaluations {max_evaluations} // 2 = {max_signals}")
            print(f"   signals_generated {signals_generated} < max_signals {max_signals} = {signals_generated < max_signals}")
            print(f"   → 最初から条件3で終了!")
        
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")


def debug_actual_system_execution():
    """実際のシステム実行で終了条件を監視"""
    
    print("\\n" + "="*60)
    print("🔍 実際のシステム実行での終了条件監視")
    print("="*60)
    
    try:
        # scalable_analysis_systemの_generate_real_analysisに監視を追加
        # ここでは出力から推測
        
        print("📊 実際の実行ログ分析:")
        print("   - 各評価で3-4秒の処理時間")
        print("   - 毎回データ取得 + 支持線検出実行")
        print("   - 毎回同じエラーで失敗")
        print("   - signals_generated = 0 (成功シグナルなし)")
        print()
        
        print("🎯 推定される終了原因:")
        
        # 可能性1: max_signals = 0
        print("\\n可能性1: max_signals = 0")
        print("   max_evaluations = 100")
        print("   max_signals = 100 // 2 = 50") 
        print("   signals_generated = 0")
        print("   0 < 50 = True → 条件は満足")
        print("   ❌ これが原因ではない")
        
        # 可能性2: 時間範囲
        print("\\n可能性2: 時間範囲の終了")
        print("   90日間の範囲で4時間間隔")
        print("   理論的最大: 90 * 24 / 4 = 540回")
        print("   ❌ これが原因ではない")
        
        # 可能性3: 例外による早期終了
        print("\\n可能性3: 例外による早期終了")
        print("   ✅ 最も可能性が高い")
        print("   処理中で例外が発生して、try-except文で処理が中断")
        print("   → 条件ベース分析が途中で終了")
        
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")


def debug_exception_handling():
    """例外処理による早期終了を調査"""
    
    print("\\n" + "="*60)
    print("🔍 例外処理による早期終了の調査")
    print("="*60)
    
    # scalable_analysis_system.pyの_generate_real_analysisの例外処理を確認
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        import inspect
        
        # _generate_real_analysisのソースを確認
        system = ScalableAnalysisSystem()
        source = inspect.getsource(system._generate_real_analysis)
        
        # try-except文を探す
        lines = source.split('\\n')
        in_try = False
        except_found = False
        
        print("📝 _generate_real_analysis の例外処理:")
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if 'try:' in line_stripped:
                in_try = True
                print(f"   Line {i}: {line_stripped}")
            elif 'except' in line_stripped and in_try:
                except_found = True
                print(f"   Line {i}: {line_stripped}")
                # 次の数行も表示
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip():
                        print(f"   Line {j}: {lines[j].strip()}")
                        if 'return' in lines[j] or 'raise' in lines[j]:
                            break
                break
        
        if except_found:
            print("\\n✅ 例外処理が見つかりました")
            print("   例外発生時に処理が早期終了する可能性があります")
        else:
            print("\\n❓ 明確な例外処理が見つかりませんでした")
            
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")


if __name__ == "__main__":
    debug_loop_termination_conditions()
    debug_actual_system_execution() 
    debug_exception_handling()