#!/usr/bin/env python3
"""
単一銘柄追加テスト - ハードコード値検証用

Phase 2クリーンアップ後のシステムで、
実データのみを使用して銘柄追加が正常に動作することを確認
"""

import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_single_symbol_addition(symbol="SOL", timeframe="5m", config="Aggressive_ML"):
    """単一銘柄・単一設定での追加テスト"""
    print(f"🔍 単一銘柄追加テスト: {symbol} {timeframe} {config}")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # 1件だけ分析を実行
        print(f"\n📊 {symbol}_{timeframe}_{config} の分析を実行...")
        
        start_time = datetime.now()
        try:
            # 直接_generate_real_analysisを呼び出してエラーを確認
            trades_data = system._generate_real_analysis(symbol, timeframe, config)
            print(f"✅ リアル分析データ生成: {len(trades_data) if trades_data else 0}件")
            
            # メトリクス計算
            metrics = system._calculate_metrics(trades_data)
            print(f"📊 メトリクス計算完了: {metrics}")
            
            result = True
        except Exception as e:
            print(f"❌ リアル分析エラー: {e}")
            import traceback
            traceback.print_exc()
            result = False
            
        end_time = datetime.now()
        
        print(f"✅ 分析完了: {result}")
        print(f"⏱️ 処理時間: {(end_time - start_time).total_seconds():.2f}秒")
        
        # 生成されたデータを確認
        if result:
            import pandas as pd
            trades_df = system.load_compressed_trades(symbol, timeframe, config)
            
            # リストまたはDataFrameの判定
            if trades_df is not None:
                # リストの場合はDataFrameに変換
                if isinstance(trades_df, list):
                    if len(trades_df) > 0:
                        trades_df = pd.DataFrame(trades_df)
                    else:
                        trades_df = pd.DataFrame()
                
                if not trades_df.empty:
                    print(f"\n📊 生成されたトレードデータ:")
                    print(f"   件数: {len(trades_df)}")
                    print(f"   カラム: {list(trades_df.columns)}")
                    
                    # ハードコード値チェック
                    hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
                    hardcoded_found = False
                    
                    for col in ['entry_price', 'take_profit_price', 'stop_loss_price']:
                        if col in trades_df.columns:
                            values = trades_df[col].values
                            unique_values = pd.Series(values).unique()
                            
                            print(f"\n   {col}:")
                            print(f"     ユニーク値数: {len(unique_values)}")
                            print(f"     最小値: {values.min():.4f}")
                            print(f"     最大値: {values.max():.4f}")
                            print(f"     平均値: {values.mean():.4f}")
                            
                            # ハードコード値チェック
                            for hv in hardcoded_values:
                                matching = sum(abs(val - hv) < 0.001 for val in values)
                                if matching > 0:
                                    print(f"     ❌ ハードコード値 {hv}: {matching}件")
                                    hardcoded_found = True
                            
                            # 最初の5件表示
                            print(f"     最初の5件: {values[:5]}")
                
                    if hardcoded_found:
                        print("\n❌ ハードコード値が検出されました！")
                    else:
                        print("\n✅ ハードコード値なし - 実データのみ使用確認")
                else:
                    print("❌ トレードデータが空です")
        else:
            print("❌ 分析が失敗しました")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

def check_btc_data_availability():
    """BTCのデータ取得可能性をチェック"""
    print("\n🔍 BTCデータ取得可能性チェック")
    print("=" * 60)
    
    try:
        from hyperliquid_api_client import MultiExchangeAPIClient
        import asyncio
        from datetime import datetime, timezone, timedelta
        
        client = MultiExchangeAPIClient()
        
        # 90日間のデータを取得
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=90)
        
        print(f"📅 期間: {start_time} → {end_time}")
        
        # 非同期でデータを取得
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("🔄 BTCのOHLCVデータ取得中...")
            data = loop.run_until_complete(
                client.get_ohlcv_data("BTC", "1h", start_time, end_time)
            )
            
            print("✅ データ取得結果:")
            print(f"   データの型: {type(data)}")
            
            if data is not None and not data.empty:
                print(f"   データ件数: {len(data)}")
                print(f"   最新価格: ${data['close'].iloc[-1]:,.2f}")
                print(f"   価格範囲: ${data['low'].min():,.2f} - ${data['high'].max():,.2f}")
            else:
                print("   ❌ データが空またはNone")
                
        except Exception as e:
            print(f"❌ データ取得エラー: {e}")
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ APIクライアント初期化エラー: {e}")

def main():
    """メイン実行関数"""
    print("🔍 Phase 2クリーンアップ後の銘柄追加テスト")
    print("=" * 70)
    print("目的: フォールバック値を使用せず、実データのみで動作することを確認")
    print("=" * 70)
    
    # 1. BTCデータ取得可能性チェック
    check_btc_data_availability()
    
    # 2. 単一銘柄追加テスト
    print("\n" + "=" * 70)
    test_single_symbol_addition("BTC", "1h", "Conservative_ML")
    
    print("\n" + "=" * 70)
    print("✅ テスト完了")

if __name__ == '__main__':
    main()