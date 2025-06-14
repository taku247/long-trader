#!/usr/bin/env python3
"""
実在のシンボルでの分析テスト

修正されたコードで実在のシンボル（HYPE）を分析し、
ハードコード値が発生しないことを確認
"""

import sys
import os
import pandas as pd
from datetime import datetime, timezone, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_real_symbol_analysis():
    """実在のシンボル（HYPE）で分析をテスト"""
    print("🔍 実在シンボル（HYPE）での分析テスト")
    print("=" * 50)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # HYPEの分析を1件だけ実行
        print("\n📊 HYPE_1h_Conservative_ML の分析を実行...")
        
        try:
            # 正しいメソッド呼び出し（strategyは引数にない）
            result = system._generate_single_analysis(
                symbol="HYPE",
                timeframe="1h", 
                config="Conservative_ML"
            )
            
            print("✅ 分析結果:")
            print(f"   結果の型: {type(result)}")
            
            if isinstance(result, list):
                print(f"   件数: {len(result)}")
                if result:
                    first_trade = result[0]
                    print(f"   最初のトレード keys: {list(first_trade.keys())}")
                    
                    if 'entry_price' in first_trade:
                        entry_price = first_trade['entry_price']
                        print(f"   🎯 entry_price: {entry_price}")
                        
                        # ハードコード値チェック
                        hardcoded_values = [100.0, 1000.0, 105.0, 97.62]
                        is_hardcoded = any(abs(entry_price - hv) < 0.001 for hv in hardcoded_values)
                        
                        if is_hardcoded:
                            print(f"   ❌ ハードコード値を検出: {entry_price}")
                        else:
                            print(f"   ✅ 動的価格を確認: {entry_price}")
                    
                    if 'take_profit_price' in first_trade:
                        tp_price = first_trade.get('take_profit_price', 'N/A')
                        print(f"   🎯 take_profit_price: {tp_price}")
                    
                    if 'stop_loss_price' in first_trade:
                        sl_price = first_trade.get('stop_loss_price', 'N/A')
                        print(f"   🎯 stop_loss_price: {sl_price}")
                    
                    # 価格の多様性をチェック
                    entry_prices = [trade.get('entry_price') for trade in result[:10]]
                    unique_prices = len(set(entry_prices))
                    print(f"   📊 最初の10件のユニーク価格数: {unique_prices}")
                    
                    if unique_prices > 1:
                        print("   ✅ 価格変動を確認")
                    else:
                        print("   ❌ 価格が固定されています")
            
        except Exception as e:
            print(f"❌ 分析エラー: {e}")
            print(f"   エラータイプ: {type(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ システム初期化エラー: {e}")

def check_existing_hype_data():
    """既存のHYPEデータをチェック"""
    print("\n🔍 既存のHYPEデータファイルチェック")
    print("=" * 50)
    
    import glob
    import pickle
    import gzip
    
    hype_files = glob.glob("large_scale_analysis/compressed/HYPE_*.pkl.gz")
    
    if not hype_files:
        print("❓ HYPEのデータファイルが見つかりません")
        return
    
    print(f"📁 HYPEファイル数: {len(hype_files)}")
    
    # 最初のファイルを詳細チェック
    first_file = hype_files[0]
    print(f"\n📊 詳細チェック: {first_file}")
    
    try:
        with gzip.open(first_file, 'rb') as f:
            trades_data = pickle.load(f)
        
        if isinstance(trades_data, list):
            df = pd.DataFrame(trades_data)
        elif isinstance(trades_data, dict):
            df = pd.DataFrame(trades_data)
        else:
            df = trades_data
        
        print(f"   レコード数: {len(df)}")
        print(f"   カラム: {list(df.columns)}")
        
        if 'entry_price' in df.columns:
            entry_prices = df['entry_price']
            print(f"   エントリー価格:")
            print(f"     ユニーク値数: {len(entry_prices.unique())}")
            print(f"     最小値: {entry_prices.min():.4f}")
            print(f"     最大値: {entry_prices.max():.4f}")
            print(f"     平均値: {entry_prices.mean():.4f}")
            print(f"     標準偏差: {entry_prices.std():.4f}")
            
            # ハードコード値チェック
            hardcoded_values = [100.0, 1000.0, 105.0, 97.62]
            hardcoded_count = 0
            
            for hv in hardcoded_values:
                matching = sum(abs(price - hv) < 0.001 for price in entry_prices)
                if matching > 0:
                    hardcoded_count += matching
                    print(f"     ❌ ハードコード値 {hv}: {matching}件")
            
            if hardcoded_count == 0:
                print("     ✅ ハードコード値なし")
            else:
                print(f"     ❌ ハードコード値合計: {hardcoded_count}件")
                
    except Exception as e:
        print(f"   ❌ ファイル読み込みエラー: {e}")

def check_recent_files():
    """最近作成されたファイルをチェック"""
    print("\n🔍 最近作成されたファイルチェック")
    print("=" * 50)
    
    import glob
    import os
    from datetime import datetime
    
    all_files = glob.glob("large_scale_analysis/compressed/*.pkl.gz")
    
    # 作成日時でソート（新しい順）
    files_with_time = []
    for file_path in all_files:
        try:
            mtime = os.path.getmtime(file_path)
            files_with_time.append((file_path, mtime))
        except:
            continue
    
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    print(f"📁 総ファイル数: {len(files_with_time)}")
    print("📅 最新の10ファイル:")
    
    for i, (file_path, mtime) in enumerate(files_with_time[:10]):
        dt = datetime.fromtimestamp(mtime)
        print(f"   {i+1}. {os.path.basename(file_path)} - {dt.strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """メイン実行関数"""
    print("🔍 実在シンボルでの分析テスト")
    print("=" * 60)
    
    # 1. 実在シンボル（HYPE）での新規分析テスト
    test_real_symbol_analysis()
    
    # 2. 既存のHYPEデータをチェック
    check_existing_hype_data()
    
    # 3. 最近作成されたファイルをチェック
    check_recent_files()
    
    print("\n" + "=" * 60)
    print("✅ テスト完了")
    print("=" * 60)

if __name__ == '__main__':
    main()