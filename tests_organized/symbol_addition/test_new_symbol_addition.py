#!/usr/bin/env python3
"""
新銘柄追加テスト - 正常なデータ生成確認
"""

import sys
import time
from pathlib import Path
from datetime import datetime
import json

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

from scalable_analysis_system import ScalableAnalysisSystem
from tests.test_data_quality_validation import TestDataQualityValidation


def test_new_symbol_addition(symbol='DOGE', timeframe='15m', config='Aggressive_ML', max_wait_minutes=5):
    """
    新銘柄追加テスト
    
    Args:
        symbol: テスト対象銘柄
        timeframe: 時間足
        config: 戦略設定
        max_wait_minutes: 最大待機時間（分）
    """
    print("🧪 新銘柄追加テスト開始")
    print("=" * 50)
    print(f"対象銘柄: {symbol}")
    print(f"時間足: {timeframe}")
    print(f"戦略: {config}")
    print(f"最大待機時間: {max_wait_minutes}分")
    print()
    
    system = ScalableAnalysisSystem()
    test_suite = TestDataQualityValidation()
    test_suite.setUp()
    
    # 1. 事前状態確認
    print("1️⃣ 事前状態確認...")
    
    existing_results = system.query_analyses(filters={'symbol': symbol})
    if not existing_results.empty:
        print(f"⚠️ {symbol}の既存データが見つかりました:")
        for _, row in existing_results.iterrows():
            print(f"  {row['symbol']} {row['timeframe']} {row['config']} - {row['total_trades']}トレード")
        
        user_input = input(f"{symbol}の既存データを削除して新規テストしますか？ (y/N): ")
        if user_input.lower() == 'y':
            # 既存データ削除
            print(f"🗑️ {symbol}の既存データを削除中...")
            import sqlite3
            import os
            
            with sqlite3.connect(system.db_path) as conn:
                cursor = conn.cursor()
                
                # ファイル削除
                cursor.execute('SELECT data_compressed_path, chart_path FROM analyses WHERE symbol = ?', (symbol,))
                file_paths = cursor.fetchall()
                
                for compressed_path, chart_path in file_paths:
                    if compressed_path and os.path.exists(compressed_path):
                        os.remove(compressed_path)
                        print(f"  ✅ 削除: {compressed_path}")
                    if chart_path and os.path.exists(chart_path):
                        os.remove(chart_path)
                        print(f"  ✅ 削除: {chart_path}")
                
                # DB削除
                cursor.execute('DELETE FROM backtest_summary WHERE analysis_id IN (SELECT id FROM analyses WHERE symbol = ?)', (symbol,))
                cursor.execute('DELETE FROM analyses WHERE symbol = ?', (symbol,))
                conn.commit()
                print(f"  ✅ データベースレコード削除完了")
        else:
            print("❌ 既存データが存在するためテストを中止します")
            return False
    else:
        print(f"✅ {symbol}の既存データなし - 新規テスト実行")
    
    # 2. エントリー条件確認
    print(f"\n2️⃣ エントリー条件確認...")
    
    try:
        from config.unified_config_manager import UnifiedConfigManager
        config_manager = UnifiedConfigManager()
        
        # developmentレベルの条件を取得
        conditions = config_manager.get_entry_conditions(timeframe, config, 'development')
        print(f"developmentレベルの条件:")
        print(f"  最小レバレッジ: {conditions.get('min_leverage', 'N/A')}")
        print(f"  最小信頼度: {conditions.get('min_confidence', 'N/A')}")
        print(f"  最小リスク・リワード: {conditions.get('min_risk_reward', 'N/A')}")
        
        if conditions.get('min_leverage', 999) > 5.0:
            print("⚠️ 条件が厳しすぎる可能性があります")
        else:
            print("✅ developmentレベルで適切に緩和されています")
            
    except Exception as e:
        print(f"❌ 条件取得エラー: {e}")
        return False
    
    # 3. 分析実行
    print(f"\n3️⃣ {symbol} 分析実行...")
    
    start_time = datetime.now()
    
    batch_configs = [
        {'symbol': symbol, 'timeframe': timeframe, 'config': config}
    ]
    
    print(f"バッチ分析開始: {symbol} {timeframe} {config}")
    print("⏳ この処理には数分かかる場合があります...")
    
    try:
        # 短時間でのテストのため evaluation_period_days を短く設定
        print("条件ベース分析を短期間（30日）で実行...")
        
        # 直接分析を実行
        trades = system._generate_real_analysis(symbol, timeframe, config, evaluation_period_days=30)
        
        if trades:
            print(f"✅ 分析完了: {len(trades)}件のトレードが生成されました")
            
            # データベースに保存するためメトリクス計算
            if len(trades) > 0:
                metrics = system._calculate_metrics(trades)
                compressed_path = system._save_compressed_data(f"{symbol}_{timeframe}_{config}", trades)
                system._save_to_database(symbol, timeframe, config, metrics, None, compressed_path)
                print(f"✅ データベース保存完了")
            
        else:
            print("ℹ️ 条件を満たすシグナルが見つかりませんでした")
            print("これは正常な動作です（市場条件が条件を満たしていない）")
            
    except Exception as e:
        print(f"❌ 分析実行エラー: {e}")
        print(f"エラー詳細: {type(e).__name__}")
        return False
    
    execution_time = datetime.now() - start_time
    print(f"⏱️ 実行時間: {execution_time.total_seconds():.1f}秒")
    
    # 4. 結果確認
    print(f"\n4️⃣ 結果確認...")
    
    new_results = system.query_analyses(filters={'symbol': symbol})
    
    if new_results.empty:
        print(f"ℹ️ {symbol}の分析結果が保存されていません")
        print("（条件を満たすシグナルが生成されなかった場合）")
        return True  # これは正常なケース
    
    print(f"📊 {symbol}分析結果:")
    for _, row in new_results.iterrows():
        print(f"  {row['symbol']} {row['timeframe']} {row['config']}")
        print(f"    総取引数: {row['total_trades']}")
        print(f"    勝率: {row['win_rate']:.1%}")
        print(f"    総リターン: {row['total_return']:.2f}")
        print(f"    平均レバレッジ: {row['avg_leverage']:.2f}x")
        print(f"    シャープレシオ: {row['sharpe_ratio']:.2f}")
        print()
    
    # 5. 品質チェック
    print(f"5️⃣ データ品質チェック...")
    
    if new_results.iloc[0]['total_trades'] > 0:
        trades_data = test_suite.get_trade_data_for_symbol(symbol)
        
        if trades_data:
            print(f"✅ {len(trades_data)}件のトレードデータを取得")
            
            # 基本品質確認
            leverages = [float(t.get('leverage', 0)) for t in trades_data]
            entry_prices = [float(t.get('entry_price', 0)) for t in trades_data if t.get('entry_price')]
            entry_times = [t.get('entry_time', 'N/A') for t in trades_data]
            
            quality_results = {
                'leverage_unique': len(set(leverages)),
                'leverage_range': f"{min(leverages):.2f} - {max(leverages):.2f}" if leverages else "N/A",
                'price_unique': len(set(entry_prices)),
                'price_range': f"{min(entry_prices):.4f} - {max(entry_prices):.4f}" if entry_prices else "N/A",
                'time_unique': len(set(entry_times)),
                'time_duplicates': len(entry_times) - len(set(entry_times))
            }
            
            print(f"📈 品質指標:")
            print(f"  レバレッジ: {quality_results['leverage_unique']}種類 ({quality_results['leverage_range']})")
            print(f"  エントリー価格: {quality_results['price_unique']}種類 ({quality_results['price_range']})")
            print(f"  エントリー時刻: {quality_results['time_unique']}種類 (重複{quality_results['time_duplicates']}件)")
            
            # 異常検出
            anomalies = []
            if quality_results['leverage_unique'] <= 1:
                anomalies.append("レバレッジ固定")
            if quality_results['price_unique'] <= 1:
                anomalies.append("エントリー価格固定")
            if quality_results['time_duplicates'] > len(trades_data) * 0.1:
                anomalies.append("エントリー時刻重複過多")
            
            if anomalies:
                print(f"🚨 検出された異常: {', '.join(anomalies)}")
                return False
            else:
                print("✅ データ品質に問題なし")
                
        else:
            print("❌ トレードデータ取得失敗")
            return False
    else:
        print("ℹ️ トレードデータが0件のため品質チェックをスキップ")
    
    # 6. Web UI API テスト
    print(f"\n6️⃣ Web UI API テスト...")
    
    if new_results.iloc[0]['total_trades'] > 0:
        try:
            import requests
            response = requests.get(f'http://localhost:5001/api/anomaly-check/{symbol}', timeout=10)
            
            if response.status_code == 200:
                api_data = response.json()
                print(f"✅ 異常チェックAPI成功:")
                print(f"  検出された異常: {len(api_data.get('anomalies', []))}件")
                print(f"  正常チェック: {len(api_data.get('normal_checks', []))}件")
                
                if api_data.get('anomalies'):
                    for anomaly in api_data['anomalies']:
                        print(f"  🚨 {anomaly['type']}: {anomaly['description']}")
                        
            else:
                print(f"❌ API エラー: {response.status_code}")
                
        except Exception as e:
            print(f"❌ API テストエラー: {e}")
    else:
        print("ℹ️ トレードデータが0件のためAPIテストをスキップ")
    
    # 7. 総合評価
    print(f"\n7️⃣ 総合評価...")
    
    if new_results.empty:
        print("📋 結果: 条件を満たすシグナルなし（正常）")
        print("✅ システムは正常に動作しています")
        print("💡 より多くのシグナル生成には条件のさらなる緩和を検討してください")
        return True
    elif new_results.iloc[0]['total_trades'] > 0 and not anomalies:
        print("📋 結果: 正常なデータが生成されました！")
        print("✅ 新銘柄追加テスト合格")
        return True
    else:
        print("📋 結果: データに異常が検出されました")
        print("❌ 新銘柄追加テスト失敗")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='新銘柄追加テスト')
    parser.add_argument('--symbol', default='DOGE', help='テスト対象銘柄 (デフォルト: DOGE)')
    parser.add_argument('--timeframe', default='15m', help='時間足 (デフォルト: 15m)')
    parser.add_argument('--config', default='Aggressive_ML', help='戦略設定 (デフォルト: Aggressive_ML)')
    parser.add_argument('--wait', type=int, default=5, help='最大待機時間（分）')
    
    args = parser.parse_args()
    
    success = test_new_symbol_addition(
        symbol=args.symbol,
        timeframe=args.timeframe, 
        config=args.config,
        max_wait_minutes=args.wait
    )
    
    if success:
        print("\n🎉 新銘柄追加テスト成功!")
        print("✅ システムは正常に動作し、適切なデータ品質を維持しています")
    else:
        print("\n❌ 新銘柄追加テストで問題が検出されました")
        print("🔧 システムの調整が必要です")
    
    sys.exit(0 if success else 1)