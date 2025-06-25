#!/usr/bin/env python3
"""
正確な失敗ポイントを特定するデバッグツール
どのif文でどの条件に引っ掛かっているかを詳細に調査
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

def debug_exact_failure_point():
    """正確な失敗ポイントを特定"""
    
    print("🔍 正確な失敗ポイントの特定\n")
    
    try:
        # 必要なモジュールをインポート
        from scalable_analysis_system import ScalableAnalysisSystem
        from engines import HighLeverageBotOrchestrator
        
        # 設定値を確認
        symbol = 'AAVE'
        timeframe = '1h'
        config = 'Conservative_ML'
        
        print(f"テスト対象: {symbol} {timeframe} {config}")
        
        # Bot初期化
        bot = HighLeverageBotOrchestrator()
        
        # テスト用の時刻設定（90日前から）
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=90)
        test_time = start_time + timedelta(hours=1)  # 最初の評価時刻
        
        print(f"テスト時刻: {test_time}")
        print()
        
        # 1. bot.analyze_symbolの結果を詳細確認
        print("=" * 60)
        print("🔍 Step 1: bot.analyze_symbol の実行")
        print("=" * 60)
        
        try:
            result = bot.analyze_leverage_opportunity(symbol, timeframe, is_backtest=True, target_timestamp=test_time)
            print(f"✅ bot.analyze_symbol 成功")
            print(f"   result type: {type(result)}")
            
            if result:
                print(f"   result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                if isinstance(result, dict):
                    print(f"   current_price: {result.get('current_price', 'NOT FOUND')}")
                    print(f"   leverage: {result.get('leverage', 'NOT FOUND')}")
                    print(f"   confidence: {result.get('confidence', 'NOT FOUND')}")
                    print(f"   risk_reward_ratio: {result.get('risk_reward_ratio', 'NOT FOUND')}")
            else:
                print("   ❌ result is None or False")
                
        except Exception as e:
            print(f"❌ bot.analyze_symbol エラー: {type(e).__name__}: {e}")
            return
        
        # 2. 条件チェック1: result の存在確認
        print("\n" + "=" * 60)
        print("🔍 Step 2: result 存在確認")
        print("=" * 60)
        
        condition1 = not result
        condition2 = 'current_price' not in result if result else True
        
        print(f"   not result: {condition1}")
        print(f"   'current_price' not in result: {condition2}")
        print(f"   総合判定 (result無効): {condition1 or condition2}")
        
        if condition1 or condition2:
            print("   ❌ ここで処理が終了します（Line 598-600）")
            return
        else:
            print("   ✅ 条件1をクリア")
        
        # 3. エントリー条件の評価
        print("\n" + "=" * 60)
        print("🔍 Step 3: エントリー条件評価")
        print("=" * 60)
        
        # ScalableAnalysisSystemのインスタンス作成
        system = ScalableAnalysisSystem()
        
        try:
            should_enter = system._evaluate_entry_conditions(result, timeframe)
            print(f"   _evaluate_entry_conditions: {should_enter}")
            
            if not should_enter:
                print("   ❌ ここで処理が終了します（Line 605-611）")
                
                # エントリー条件の詳細を調査
                print("\n   🔍 エントリー条件の詳細:")
                debug_entry_conditions(result, timeframe)
            else:
                print("   ✅ エントリー条件をクリア")
                
        except Exception as e:
            print(f"   ❌ _evaluate_entry_conditions エラー: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ 全体エラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def debug_entry_conditions(result, timeframe):
    """エントリー条件の詳細デバッグ"""
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        # 実際の条件値を取得
        leverage = result.get('leverage', 0)
        confidence = result.get('confidence', 0)
        risk_reward_ratio = result.get('risk_reward_ratio', 0)
        
        print(f"     実際の値:")
        print(f"       leverage: {leverage}")
        print(f"       confidence: {confidence}")
        print(f"       risk_reward_ratio: {risk_reward_ratio}")
        
        # 設定ファイルから必要な条件を取得
        try:
            import json
            
            # timeframe_conditions.jsonから条件取得
            with open('config/timeframe_conditions.json', 'r') as f:
                tf_config = json.load(f)
            
            if timeframe in tf_config.get('timeframe_configs', {}):
                entry_conditions = tf_config['timeframe_configs'][timeframe].get('entry_conditions', {})
                
                min_leverage = entry_conditions.get('min_leverage', 0)
                min_confidence = entry_conditions.get('min_confidence', 0)
                min_risk_reward = entry_conditions.get('min_risk_reward', 0)
                
                print(f"     必要な条件 ({timeframe}):")
                print(f"       min_leverage: {min_leverage}")
                print(f"       min_confidence: {min_confidence}")
                print(f"       min_risk_reward: {min_risk_reward}")
                
                print(f"     条件判定:")
                print(f"       leverage >= min_leverage: {leverage} >= {min_leverage} = {leverage >= min_leverage}")
                print(f"       confidence >= min_confidence: {confidence} >= {min_confidence} = {confidence >= min_confidence}")
                print(f"       risk_reward >= min_risk_reward: {risk_reward_ratio} >= {min_risk_reward} = {risk_reward_ratio >= min_risk_reward}")
                
                all_conditions_met = (leverage >= min_leverage and 
                                    confidence >= min_confidence and 
                                    risk_reward_ratio >= min_risk_reward)
                
                print(f"     総合判定: {all_conditions_met}")
                
                if not all_conditions_met:
                    failed_conditions = []
                    if leverage < min_leverage:
                        failed_conditions.append(f"leverage不足 ({leverage} < {min_leverage})")
                    if confidence < min_confidence:
                        failed_conditions.append(f"confidence不足 ({confidence} < {min_confidence})")
                    if risk_reward_ratio < min_risk_reward:
                        failed_conditions.append(f"risk_reward不足 ({risk_reward_ratio} < {min_risk_reward})")
                    
                    print(f"     ❌ 失敗理由: {', '.join(failed_conditions)}")
                
            else:
                print(f"     ⚠️ {timeframe}の設定が見つかりません")
                
        except Exception as e:
            print(f"     ❌ 設定ファイル読み込みエラー: {e}")
            
    except Exception as e:
        print(f"     ❌ エントリー条件デバッグエラー: {e}")


if __name__ == "__main__":
    debug_exact_failure_point()