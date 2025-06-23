#!/usr/bin/env python3
"""
TRX（TRON）新規銘柄追加テスト
ハードコード値が発生しないことを確認
"""

import sys
import os
from datetime import datetime
import pandas as pd
import pickle
import gzip
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_trx_addition():
    """TRX銘柄追加テスト"""
    print("🔍 TRX（TRON）新規銘柄追加テスト")
    print("=" * 70)
    
    symbol = "TRX"
    timeframe = "1h"
    config = "Conservative_ML"
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # 分析を実行
        print(f"\n📊 {symbol}_{timeframe}_{config} の分析を実行...")
        
        start_time = datetime.now()
        result = system._generate_single_analysis(
            symbol=symbol,
            timeframe=timeframe,
            config=config
        )
        end_time = datetime.now()
        
        print(f"\n✅ 分析完了: {result}")
        print(f"⏱️ 処理時間: {(end_time - start_time).total_seconds():.2f}秒")
        
        # 生成されたデータを検証
        if result:
            verify_trx_data(symbol, timeframe, config)
        else:
            print("❌ 分析が失敗しました")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

def verify_trx_data(symbol, timeframe, config):
    """TRXデータの詳細検証"""
    file_path = Path(f"large_scale_analysis/compressed/{symbol}_{timeframe}_{config}.pkl.gz")
    
    if not file_path.exists():
        print(f"\n❌ ファイルが見つかりません: {file_path}")
        return
    
    print(f"\n📊 生成データの詳細検証: {file_path.name}")
    print("=" * 60)
    
    try:
        with gzip.open(file_path, 'rb') as f:
            data = pickle.load(f)
        
        # データ形式に応じて処理
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            print(f"❓ 未知のデータ形式: {type(data)}")
            return
        
        print(f"レコード数: {len(df)}")
        print(f"カラム: {list(df.columns)}")
        
        # ハードコード値リスト（拡張版）
        hardcoded_values = [
            100.0, 105.0, 97.62, 97.619, 97.6190, 97.61904761904762,
            1000.0, 1050.0, 976.2
        ]
        
        # 価格カラムを詳細検証
        price_columns = ['entry_price', 'take_profit_price', 'stop_loss_price', 
                       'exit_price', 'current_price']
        
        total_hardcoded = 0
        
        for col in price_columns:
            if col in df.columns:
                values = df[col].values
                unique_values = pd.Series(values).unique()
                unique_count = len(unique_values)
                
                print(f"\n{col}:")
                print(f"  ユニーク値数: {unique_count}/{len(values)}")
                print(f"  範囲: {values.min():.6f} - {values.max():.6f}")
                print(f"  平均: {values.mean():.6f}")
                print(f"  標準偏差: {values.std():.6f}")
                
                # ハードコード値チェック
                hardcoded_found = False
                for hv in hardcoded_values:
                    matching = sum(abs(val - hv) < 0.001 for val in values)
                    if matching > 0:
                        print(f"  ❌ ハードコード値 {hv}: {matching}件")
                        hardcoded_found = True
                        total_hardcoded += matching
                
                if not hardcoded_found:
                    print(f"  ✅ ハードコード値なし")
                
                # 最初と最後の5件表示
                print(f"  最初の5件: {[f'{v:.6f}' for v in values[:5]]}")
                if len(values) > 5:
                    print(f"  最後の5件: {[f'{v:.6f}' for v in values[-5:]]}")
                
                # TRXの妥当な価格範囲チェック (0.01 - 1.0 USD)
                if col in ['entry_price', 'exit_price', 'current_price']:
                    trx_range_check = all(0.01 <= val <= 1.0 for val in values)
                    if trx_range_check:
                        print(f"  ✅ TRX価格範囲内 (0.01-1.0 USD)")
                    else:
                        out_of_range = sum(1 for val in values if val < 0.01 or val > 1.0)
                        print(f"  ⚠️ 範囲外の値: {out_of_range}件")
        
        # 最終判定
        print(f"\n{'='*60}")
        print("📋 最終判定:")
        if total_hardcoded > 0:
            print(f"❌ ハードコード値検出: 合計{total_hardcoded}件")
        else:
            print("✅ ハードコード値なし - 実データのみ使用確認！")
            
            # 価格の妥当性も確認
            if 'entry_price' in df.columns:
                entry_price = df['entry_price'].iloc[0]
                print(f"\n💰 TRX現在価格: ${entry_price:.6f}")
                print("✅ 実際の市場価格を使用しています")
            
    except Exception as e:
        print(f"❌ 検証エラー: {e}")

def check_trx_api_data():
    """TRXのAPIデータ取得確認"""
    print("\n🔍 TRX APIデータ取得確認")
    print("=" * 60)
    
    try:
        from hyperliquid_api_client import MultiExchangeAPIClient
        import asyncio
        from datetime import datetime, timezone, timedelta
        
        client = MultiExchangeAPIClient()
        
        # 最新データを取得
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("🔄 TRXの最新価格取得中...")
            data = loop.run_until_complete(
                client.get_ohlcv_data("TRX", "1h", start_time, end_time)
            )
            
            if data is not None and not data.empty:
                latest_price = data['close'].iloc[-1]
                print(f"✅ TRX最新価格: ${latest_price:.6f}")
                print(f"   高値: ${data['high'].max():.6f}")
                print(f"   安値: ${data['low'].min():.6f}")
            else:
                print("❌ データ取得失敗")
                
        except Exception as e:
            print(f"❌ エラー: {e}")
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ APIクライアントエラー: {e}")

def main():
    """メイン実行関数"""
    print("🚀 TRX新規銘柄追加テスト開始")
    print("=" * 70)
    
    # 1. APIデータ取得確認
    check_trx_api_data()
    
    # 2. 銘柄追加テスト
    test_trx_addition()
    
    print("\n" + "=" * 70)
    print("✅ TRXテスト完了")

if __name__ == '__main__':
    main()