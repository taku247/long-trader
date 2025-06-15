#!/usr/bin/env python3
"""
異常チェック機能の動作テスト
正常データと異常データでテスト
"""

import sys
from pathlib import Path
import pandas as pd
import pickle
import gzip
import os
import sqlite3
from datetime import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

from scalable_analysis_system import ScalableAnalysisSystem


def create_test_data(symbol, data_type='normal'):
    """テスト用のトレードデータを作成"""
    print(f"🧪 {symbol} 用{data_type}データ作成中...")
    
    if data_type == 'normal':
        # 正常なデータ（多様性あり）
        trades = []
        for i in range(50):
            trade = {
                'entry_time': f'2025-06-{15-i//10:02d} {10+i%12:02d}:00:00',
                'exit_time': f'2025-06-{15-i//10:02d} {11+i%12:02d}:00:00',
                'entry_price': 100.0 + (i * 0.5) + (i % 10) * 0.1,  # 多様な価格
                'exit_price': 105.0 + (i * 0.3) + (i % 7) * 0.2,
                'leverage': 2.0 + (i % 8) * 0.5,  # 2.0〜5.5のレバレッジ
                'pnl_pct': 0.05 + (i % 20) * 0.002 - 0.02 if i % 10 != 0 else -0.01,  # 80%勝率
                'is_success': i % 10 != 0,  # 80%勝率
                'confidence': 60 + (i % 30),
                'strategy': 'Aggressive_ML'
            }
            trades.append(trade)
            
    elif data_type == 'anomalous':
        # 異常データ（固定値多数）
        trades = []
        for i in range(100):
            trade = {
                'entry_time': f'2025-06-15 21:46:49 JST' if i < 3 else f'2025-06-{15-i//20:02d} {10+i%12:02d}:46:49 JST',  # 時刻重複
                'exit_time': f'2025-06-15 22:46:49 JST',
                'entry_price': 18.91,  # 固定価格
                'exit_price': 21.5 + (i % 5) * 0.1,
                'leverage': 2.1,  # 固定レバレッジ
                'pnl_pct': 0.3 if i < 94 else -0.2,  # 94%勝率
                'is_success': i < 94,  # 94%勝率
                'confidence': 75,
                'strategy': 'Aggressive_ML'
            }
            trades.append(trade)
    
    return trades


def save_test_data_to_system(symbol, timeframe, config, trades):
    """テストデータをシステムに保存"""
    system = ScalableAnalysisSystem()
    
    # トレードデータをDataFrameに変換
    trades_df = pd.DataFrame(trades)
    
    # 圧縮して保存
    analysis_id = f"{symbol}_{timeframe}_{config}"
    compressed_path = system.compressed_dir / f"{analysis_id}.pkl.gz"
    
    with gzip.open(compressed_path, 'wb') as f:
        pickle.dump(trades_df, f)
    
    # メトリクス計算
    total_trades = len(trades)
    win_count = sum(1 for t in trades if t['is_success'])
    win_rate = win_count / total_trades if total_trades > 0 else 0
    
    leverages = [t['leverage'] for t in trades]
    avg_leverage = sum(leverages) / len(leverages) if leverages else 0
    
    pnl_pcts = [t['pnl_pct'] for t in trades]
    total_return = sum(pnl_pcts)
    
    # データベースに保存
    with sqlite3.connect(system.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO analyses (
                symbol, timeframe, config, generated_at, total_trades,
                win_rate, total_return, sharpe_ratio, max_drawdown,
                avg_leverage, data_compressed_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol, timeframe, config, datetime.now().isoformat(),
            total_trades, win_rate, total_return, 1.5, -0.1,
            avg_leverage, str(compressed_path), 'completed'
        ))
        conn.commit()
    
    print(f"✅ {symbol} テストデータ保存完了: {total_trades}トレード")
    return True


def test_anomaly_detection():
    """異常検知機能をテスト"""
    print("🔍 異常チェック機能テスト開始")
    print("=" * 40)
    
    # 1. 正常データでテスト
    print("\n1️⃣ 正常データテスト")
    normal_trades = create_test_data('TEST_NORMAL', 'normal')
    save_test_data_to_system('TEST_NORMAL', '15m', 'Aggressive_ML', normal_trades)
    
    # 2. 異常データでテスト
    print("\n2️⃣ 異常データテスト")
    anomalous_trades = create_test_data('TEST_ANOMALY', 'anomalous')
    save_test_data_to_system('TEST_ANOMALY', '15m', 'Aggressive_ML', anomalous_trades)
    
    # 3. Web API テスト
    print("\n3️⃣ Web API異常チェックテスト")
    
    import requests
    
    # 正常データのチェック
    try:
        response = requests.get('http://localhost:5001/api/anomaly-check/TEST_NORMAL')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ TEST_NORMAL チェック成功:")
            print(f"   異常検出数: {len(data.get('anomalies', []))}")
            print(f"   正常チェック数: {len(data.get('normal_checks', []))}")
        else:
            print(f"❌ TEST_NORMAL チェック失敗: {response.status_code}")
    except Exception as e:
        print(f"❌ TEST_NORMAL API エラー: {e}")
    
    # 異常データのチェック
    try:
        response = requests.get('http://localhost:5001/api/anomaly-check/TEST_ANOMALY')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ TEST_ANOMALY チェック成功:")
            print(f"   異常検出数: {len(data.get('anomalies', []))}")
            for anomaly in data.get('anomalies', []):
                print(f"   🚨 {anomaly['type']}: {anomaly['description']}")
        else:
            print(f"❌ TEST_ANOMALY チェック失敗: {response.status_code}")
    except Exception as e:
        print(f"❌ TEST_ANOMALY API エラー: {e}")
    
    # 4. 品質テストの実行
    print("\n4️⃣ 品質検証テスト")
    
    from tests.test_data_quality_validation import TestDataQualityValidation
    test_suite = TestDataQualityValidation()
    test_suite.setUp()
    
    try:
        success = test_suite.run_comprehensive_data_quality_check()
        if success:
            print("⚠️ 品質テスト合格（異常データが検出されていない可能性）")
        else:
            print("✅ 品質テスト失敗（異常データが正しく検出されました）")
    except Exception as e:
        print(f"品質テスト実行エラー: {e}")


def cleanup_test_data():
    """テストデータのクリーンアップ"""
    print("\n🧹 テストデータクリーンアップ")
    
    system = ScalableAnalysisSystem()
    
    test_symbols = ['TEST_NORMAL', 'TEST_ANOMALY']
    
    with sqlite3.connect(system.db_path) as conn:
        cursor = conn.cursor()
        
        for symbol in test_symbols:
            # 圧縮ファイル削除
            cursor.execute('SELECT data_compressed_path FROM analyses WHERE symbol = ?', (symbol,))
            results = cursor.fetchall()
            
            for (path,) in results:
                if path and os.path.exists(path):
                    os.remove(path)
                    print(f"  🗑️ ファイル削除: {path}")
            
            # データベースレコード削除
            cursor.execute('DELETE FROM backtest_summary WHERE analysis_id IN (SELECT id FROM analyses WHERE symbol = ?)', (symbol,))
            cursor.execute('DELETE FROM analyses WHERE symbol = ?', (symbol,))
            
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                print(f"  🗑️ {symbol} データベースレコード削除: {deleted_count}件")
        
        conn.commit()
    
    print("✅ クリーンアップ完了")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='異常チェック機能テスト')
    parser.add_argument('--cleanup', action='store_true', help='テストデータをクリーンアップ')
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_data()
    else:
        test_anomaly_detection()
        
        print("\n📋 次のステップ:")
        print("1. ブラウザで http://localhost:5001/symbols にアクセス")
        print("2. TEST_NORMAL と TEST_ANOMALY の詳細を確認")  
        print("3. 異常チェックボタンをテスト")
        print("4. テスト完了後: python test_anomaly_check_functionality.py --cleanup")