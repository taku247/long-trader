#!/usr/bin/env python3
"""
TRX強制追加テスト
データベースの既存チェックをスキップして新規追加をテスト
"""

import sys
import os
from datetime import datetime
import sqlite3

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def clear_trx_from_db():
    """データベースからTRXエントリを削除"""
    print("🗑️ データベースからTRXエントリを削除...")
    try:
        db_path = "large_scale_analysis/analysis.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analyses WHERE symbol='TRX'")
            deleted = cursor.rowcount
            conn.commit()
            print(f"✅ {deleted}件のTRXエントリを削除")
    except Exception as e:
        print(f"❌ DB削除エラー: {e}")

def test_trx_direct():
    """TRXを直接分析（既存チェックなし）"""
    print("\n🔍 TRX直接分析テスト")
    print("=" * 70)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        import numpy as np
        from datetime import timedelta, timezone
        
        system = ScalableAnalysisSystem()
        
        # _generate_real_analysisを直接呼び出し
        print("📊 TRXの実データ分析を実行...")
        
        symbol = "TRX"
        timeframe = "1h"
        config = "Conservative_ML"
        
        start_time = datetime.now()
        
        # 直接実データ分析を実行（サンプル数を減らして高速化）
        trades_data = system._generate_real_analysis(symbol, timeframe, config, num_trades=10)
        
        end_time = datetime.now()
        
        print(f"\n✅ 分析完了")
        print(f"⏱️ 処理時間: {(end_time - start_time).total_seconds():.2f}秒")
        
        # 結果を検証
        if isinstance(trades_data, list):
            print(f"📊 生成トレード数: {len(trades_data)}")
            
            if trades_data:
                # 最初のトレードを詳細表示
                first_trade = trades_data[0]
                print("\n最初のトレード詳細:")
                for key, value in first_trade.items():
                    if 'price' in key:
                        print(f"  {key}: ${value:.6f}")
                    else:
                        print(f"  {key}: {value}")
                
                # ハードコード値チェック
                hardcoded_values = [100.0, 105.0, 97.62, 1000.0]
                hardcoded_found = False
                
                for trade in trades_data:
                    for key in ['entry_price', 'take_profit_price', 'stop_loss_price']:
                        if key in trade:
                            value = trade[key]
                            for hv in hardcoded_values:
                                if abs(value - hv) < 0.001:
                                    print(f"\n❌ ハードコード値検出: {key} = {value}")
                                    hardcoded_found = True
                
                if not hardcoded_found:
                    print("\n✅ ハードコード値なし！")
                    
                # 価格の妥当性チェック
                entry_prices = [t.get('entry_price', 0) for t in trades_data]
                if entry_prices:
                    avg_price = np.mean(entry_prices)
                    print(f"\n💰 TRX平均エントリー価格: ${avg_price:.6f}")
                    if 0.01 <= avg_price <= 1.0:
                        print("✅ TRXの妥当な価格範囲内")
                    else:
                        print("⚠️ TRXの通常価格範囲外")
                        
        else:
            print(f"❓ 予期しないデータ型: {type(trades_data)}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン実行関数"""
    print("🚀 TRX強制追加テスト")
    print("=" * 70)
    
    # 1. データベースクリア
    clear_trx_from_db()
    
    # 2. 直接分析テスト
    test_trx_direct()
    
    print("\n" + "=" * 70)
    print("✅ テスト完了")

if __name__ == '__main__':
    main()