#!/usr/bin/env python3
"""
時間足別データ分割問題の簡易分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


def analyze_timeframe_issues():
    """時間足別の問題を分析"""
    
    print("=" * 80)
    print("時間足別データ分割・トレード生成問題の分析")
    print("=" * 80)
    
    # 現在の実装の問題点
    current_settings = {
        'num_trades': 50,
        'period_days': 90,
        'train_ratio': 0.6,
        'val_ratio': 0.2,
        'test_ratio': 0.2
    }
    
    # 時間足別の理論値
    timeframe_theoretical = {
        '1m': {
            'intervals_per_day': 1440,
            'recommended_trades_per_day': 20,
            'recommended_days': 14
        },
        '3m': {
            'intervals_per_day': 480,
            'recommended_trades_per_day': 10,
            'recommended_days': 30
        },
        '5m': {
            'intervals_per_day': 288,
            'recommended_trades_per_day': 8,
            'recommended_days': 60
        },
        '15m': {
            'intervals_per_day': 96,
            'recommended_trades_per_day': 4,
            'recommended_days': 90
        },
        '30m': {
            'intervals_per_day': 48,
            'recommended_trades_per_day': 2,
            'recommended_days': 120
        },
        '1h': {
            'intervals_per_day': 24,
            'recommended_trades_per_day': 1,
            'recommended_days': 180
        }
    }
    
    print("\n【現在の実装の問題点】")
    print(f"- 全時間足で一律{current_settings['num_trades']}トレード（90日間）")
    print(f"- トレード間隔: {current_settings['period_days'] / current_settings['num_trades']:.1f}日（約1.8日）")
    print(f"- 短期時間足（1m, 3m, 5m）では非現実的に少ないトレード数")
    
    print("\n【時間足別の分析】")
    for timeframe, config in timeframe_theoretical.items():
        print(f"\n{timeframe}足:")
        
        # 90日間でのデータポイント数
        data_points = config['intervals_per_day'] * current_settings['period_days']
        
        # 現在の設定での問題
        current_trades_per_day = current_settings['num_trades'] / current_settings['period_days']
        gap_ratio = (config['recommended_trades_per_day'] - current_trades_per_day) / config['recommended_trades_per_day']
        
        # 学習データ数
        train_samples = int(data_points * current_settings['train_ratio'])
        
        print(f"  データポイント数（90日）: {data_points:,}")
        print(f"  学習サンプル数: {train_samples:,}")
        print(f"  現在のトレード頻度: {current_trades_per_day:.2f}回/日")
        print(f"  推奨トレード頻度: {config['recommended_trades_per_day']}回/日")
        print(f"  乖離率: {gap_ratio*100:.1f}%")
        
        # 推奨設定
        recommended_trades = config['recommended_trades_per_day'] * config['recommended_days']
        print(f"  推奨設定: {config['recommended_days']}日間で{recommended_trades}トレード")
        
        if gap_ratio > 0.5:
            print(f"  ⚠️ 問題あり: トレード数が大幅に不足")
    
    print("\n【改善案】")
    print("1. scalable_analysis_system.pyの_generate_real_analysis()を修正:")
    print("   - num_tradesを時間足に応じて動的に設定")
    print("   - データ取得期間も時間足に応じて調整")
    
    print("\n2. 時間足別の設定例:")
    print("```python")
    print("TIMEFRAME_CONFIGS = {")
    print("    '1m': {'days': 14, 'trades_per_day': 20},")
    print("    '3m': {'days': 30, 'trades_per_day': 10},")
    print("    '5m': {'days': 60, 'trades_per_day': 8},")
    print("    '15m': {'days': 90, 'trades_per_day': 4},")
    print("    '30m': {'days': 120, 'trades_per_day': 2},")
    print("    '1h': {'days': 180, 'trades_per_day': 1}")
    print("}")
    print("```")
    
    print("\n3. トレード生成の改善:")
    print("   - 均等分散ではなく、取引時間帯を考慮した分布")
    print("   - ボラティリティの高い時間帯に集中")
    print("   - 週末を除外")
    
    # 具体的な数値での影響
    print("\n【1.8日間隔問題の具体的影響】")
    print("例: 1分足でのバックテスト")
    print(f"- 90日間で50トレード = 1.8日に1回")
    print(f"- 実際の1分足トレード = 1日20-50回が一般的")
    print(f"- 結果: 99%以上のトレード機会を見逃している")
    print(f"- ML学習: 極めて疎なデータで学習することになる")
    
    # 結果を保存
    results = {
        'analysis_time': datetime.now().isoformat(),
        'current_issues': {
            'uniform_trades': 50,
            'uniform_days': 90,
            'trade_interval_days': 1.8,
            'problem': 'One-size-fits-all approach ignores timeframe characteristics'
        },
        'recommendations': timeframe_theoretical,
        'impact': {
            '1m': 'Missing 97%+ of trading opportunities',
            '3m': 'Missing 94%+ of trading opportunities', 
            '5m': 'Missing 93%+ of trading opportunities',
            '15m': 'Missing 86%+ of trading opportunities',
            '30m': 'Missing 72%+ of trading opportunities',
            '1h': 'Acceptable but suboptimal'
        }
    }
    
    with open('timeframe_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n分析結果を保存: timeframe_analysis_results.json")


if __name__ == "__main__":
    analyze_timeframe_issues()