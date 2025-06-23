#!/usr/bin/env python3
"""
複数銘柄追加テスト - ハードコード値検証用

BTC以外の様々な銘柄で実データのみを使用して
銘柄追加が正常に動作することを確認
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

def test_symbol_addition(symbol, timeframe="1h", config="Conservative_ML"):
    """単一銘柄の追加テストと検証"""
    print(f"\n{'='*60}")
    print(f"🔍 {symbol} 追加テスト")
    print(f"{'='*60}")
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        
        # 分析を実行
        print(f"📊 {symbol}_{timeframe}_{config} の分析を実行...")
        
        start_time = datetime.now()
        result = system._generate_single_analysis(
            symbol=symbol,
            timeframe=timeframe,
            config=config
        )
        end_time = datetime.now()
        
        print(f"✅ 分析完了: {result}")
        print(f"⏱️ 処理時間: {(end_time - start_time).total_seconds():.2f}秒")
        
        # 生成されたデータを検証
        if result:
            return verify_generated_data(symbol, timeframe, config)
        else:
            print("❌ 分析が失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_generated_data(symbol, timeframe, config):
    """生成されたデータのハードコード値検証"""
    file_path = Path(f"large_scale_analysis/compressed/{symbol}_{timeframe}_{config}.pkl.gz")
    
    if not file_path.exists():
        print(f"❌ ファイルが見つかりません: {file_path}")
        return False
    
    print(f"\n📊 生成データの検証: {file_path.name}")
    
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
            return False
        
        print(f"   レコード数: {len(df)}")
        
        # ハードコード値リスト
        hardcoded_values = [100.0, 105.0, 97.62, 97.619, 97.6190, 1000.0]
        
        # 価格カラムを検証
        price_columns = ['entry_price', 'take_profit_price', 'stop_loss_price', 
                       'exit_price', 'current_price']
        
        hardcoded_found = False
        suspicious_patterns = []
        
        for col in price_columns:
            if col in df.columns:
                values = df[col].values
                unique_values = pd.Series(values).unique()
                unique_count = len(unique_values)
                
                print(f"\n   {col}:")
                print(f"     ユニーク値数: {unique_count}/{len(values)}")
                print(f"     範囲: {values.min():.4f} - {values.max():.4f}")
                print(f"     平均: {values.mean():.4f}")
                
                # ハードコード値チェック
                for hv in hardcoded_values:
                    matching = sum(abs(val - hv) < 0.001 for val in values)
                    if matching > 0:
                        print(f"     ❌ ハードコード値 {hv}: {matching}件")
                        hardcoded_found = True
                
                # 疑わしいパターンチェック
                if unique_count == 1 and len(values) > 10:
                    suspicious_patterns.append(f"{col}が全て同じ値: {values[0]:.4f}")
                
                # 最初の5件表示
                print(f"     最初の5件: {[f'{v:.4f}' for v in values[:5]]}")
        
        # 結果サマリー
        print(f"\n📋 検証結果:")
        if hardcoded_found:
            print("   ❌ ハードコード値が検出されました！")
            return False
        elif suspicious_patterns:
            print("   ⚠️ 疑わしいパターン:")
            for pattern in suspicious_patterns:
                print(f"      - {pattern}")
            return False
        else:
            print("   ✅ ハードコード値なし - 実データ使用確認")
            return True
            
    except Exception as e:
        print(f"❌ 検証エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("🔍 複数銘柄での新規追加テスト")
    print("=" * 70)
    print("目的: BTC以外の銘柄でもハードコード値が発生しないことを確認")
    print("=" * 70)
    
    # テスト対象銘柄（様々なタイプ）
    test_symbols = [
        "ETH",    # メジャー銘柄
        "SOL",    # 人気アルトコイン
        "DOGE",   # ミームコイン
        "AVAX",   # DeFi関連
        "ARB",    # L2トークン
    ]
    
    # 結果集計
    results = []
    
    for symbol in test_symbols:
        success = test_symbol_addition(symbol, "1h", "Conservative_ML")
        results.append({
            'symbol': symbol,
            'success': success
        })
    
    # 最終レポート
    print("\n" + "=" * 70)
    print("📊 テスト結果サマリー")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    for result in results:
        status = "✅ 成功" if result['success'] else "❌ 失敗"
        print(f"{result['symbol']:10} {status}")
    
    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("\n🎉 全銘柄でハードコード値なし！フォールバック機構の完全除去を確認")
    else:
        print("\n⚠️ 一部の銘柄で問題が検出されました")
    
    # クリーンアップ（テストファイル削除）
    print("\n🧹 テストファイルのクリーンアップ...")
    cleanup_test_files(test_symbols)

def cleanup_test_files(symbols):
    """テストで生成されたファイルを削除"""
    compressed_dir = Path("large_scale_analysis/compressed")
    
    for symbol in symbols:
        pattern = f"{symbol}_*_Conservative_ML.pkl.gz"
        files = list(compressed_dir.glob(pattern))
        for file in files:
            try:
                file.unlink()
                print(f"   削除: {file.name}")
            except:
                pass

if __name__ == '__main__':
    main()