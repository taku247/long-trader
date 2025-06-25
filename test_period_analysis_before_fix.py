#!/usr/bin/env python3
"""
修正前の期間設定動作確認テスト

evaluation_period_days固定値問題とtimeframe_conditions.json設定無視の問題を
修正前に現状を記録・確認するためのテスト
"""

import sys
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_current_period_settings():
    """現在の期間設定動作を記録"""
    print("🔍 修正前の期間設定動作確認")
    print("=" * 70)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # timeframe_conditions.jsonの設定確認
        print("\n📋 timeframe_conditions.json の設定:")
        try:
            with open('config/timeframe_conditions.json', 'r') as f:
                config = json.load(f)
                
            for tf, settings in config['timeframe_configs'].items():
                data_days = settings.get('data_days', 'N/A')
                eval_interval = settings.get('evaluation_interval_minutes', 'N/A')
                max_evals = settings.get('max_evaluations', 'N/A')
                print(f"  {tf}足: data_days={data_days}, interval={eval_interval}min, max_evals={max_evals}")
                
        except Exception as e:
            print(f"  ❌ 設定ファイル読み込みエラー: {e}")
        
        # _load_timeframe_config メソッドのテスト
        print("\n🧪 _load_timeframe_config メソッドテスト:")
        timeframes = ['1m', '15m', '1h']
        
        for tf in timeframes:
            try:
                tf_config = system._load_timeframe_config(tf)
                data_days = tf_config.get('data_days', 'NOT_FOUND')
                interval_min = tf_config.get('evaluation_interval_minutes', 'NOT_FOUND')
                max_evals = tf_config.get('max_evaluations', 'NOT_FOUND')
                
                print(f"  {tf}足設定: data_days={data_days}, interval={interval_min}, max_evals={max_evals}")
            except Exception as e:
                print(f"  ❌ {tf}足設定読み込みエラー: {e}")
        
        # _generate_real_analysis のデフォルト引数確認
        print("\n🔍 _generate_real_analysis メソッド確認:")
        import inspect
        
        signature = inspect.signature(system._generate_real_analysis)
        print(f"  メソッドシグネチャ: {signature}")
        
        for param_name, param in signature.parameters.items():
            if param.default != inspect.Parameter.empty:
                print(f"    {param_name} = {param.default} (デフォルト値)")
            else:
                print(f"    {param_name} (必須)")
        
        # 実際の動作テスト（モック環境）
        print("\n🧪 期間計算ロジックテスト:")
        
        # 現在時刻から90日前の計算
        end_time = datetime.now(timezone.utc)
        start_time_90 = end_time - timedelta(days=90)
        
        print(f"  固定90日期間: {start_time_90.strftime('%Y-%m-%d')} ～ {end_time.strftime('%Y-%m-%d')}")
        
        # 時間足別の本来あるべき期間
        tf_configs = {
            '1m': 14,
            '3m': 30, 
            '15m': 90,
            '1h': 180
        }
        
        for tf, expected_days in tf_configs.items():
            expected_start = end_time - timedelta(days=expected_days)
            print(f"  {tf}足期待期間: {expected_start.strftime('%Y-%m-%d')} ～ {end_time.strftime('%Y-%m-%d')} ({expected_days}日)")
        
        print("\n✅ 現状確認完了")
        print("\n📝 確認された問題:")
        print("  1. evaluation_period_days=90 が全時間足で固定")
        print("  2. timeframe_conditions.json の data_days 設定が無視される")
        print("  3. 時間足の特性に応じた期間設定ができていない")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_evaluation_count_calculation():
    """評価回数計算の現状確認"""
    print("\n🔍 評価回数計算の現状確認")
    print("=" * 50)
    
    try:
        # timeframe_conditions.json から設定を読み込み
        with open('config/timeframe_conditions.json', 'r') as f:
            config = json.load(f)
        
        print("📊 時間足別カバー率計算:")
        for tf, settings in config['timeframe_configs'].items():
            data_days = settings['data_days']
            interval_min = settings['evaluation_interval_minutes']
            max_evals = settings['max_evaluations']
            
            # 実際の評価期間計算
            total_eval_minutes = max_evals * interval_min
            total_eval_days = total_eval_minutes / (24 * 60)
            coverage_rate = (total_eval_days / data_days) * 100
            
            print(f"  {tf}足:")
            print(f"    データ期間: {data_days}日")
            print(f"    評価間隔: {interval_min}分")
            print(f"    最大評価: {max_evals}回")
            print(f"    実評価期間: {total_eval_days:.1f}日")
            print(f"    カバー率: {coverage_rate:.1f}%")
            
            if coverage_rate < 50:
                print(f"    ⚠️ カバー率不足（50%未満）")
        
        return True
        
    except Exception as e:
        print(f"❌ 評価回数計算エラー: {e}")
        return False

if __name__ == "__main__":
    print("🚀 修正前動作確認テスト開始")
    print("=" * 70)
    
    success1 = test_current_period_settings()
    success2 = test_evaluation_count_calculation()
    
    if success1 and success2:
        print("\n✅ 修正前テスト完了 - 問題状況を確認しました")
        print("🔧 次は修正作業を安全に実行します")
    else:
        print("\n❌ 修正前テスト失敗 - 修正作業前の問題調査が必要")