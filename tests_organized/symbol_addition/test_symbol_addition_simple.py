#!/usr/bin/env python3
"""
銘柄追加の簡易動作確認テスト
- 短期間データでのテスト
- 条件を満たしやすい設定
"""

import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_symbol_addition():
    """銘柄追加テスト（簡易版）"""
    print("🚀 銘柄追加動作確認テスト")
    print("=" * 60)
    
    from scalable_analysis_system import ScalableAnalysisSystem
    system = ScalableAnalysisSystem()
    
    # テストケース：より条件を満たしやすい設定
    test_cases = [
        # Aggressive_MLは条件が緩い
        ("ETH", "15m", "Aggressive_ML"),
        ("SOL", "30m", "Aggressive_ML"),
    ]
    
    successful_additions = 0
    
    for symbol, timeframe, config in test_cases:
        print(f"\n📊 テスト: {symbol} {timeframe} {config}")
        print("-" * 50)
        
        try:
            start_time = datetime.now()
            
            # 直接分析を実行（短期間データで）
            result = system._generate_single_analysis(symbol, timeframe, config)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result:
                print(f"✅ 銘柄追加成功")
                print(f"⏱️ 処理時間: {duration:.2f}秒")
                
                # 生成されたデータを確認
                import pandas as pd
                trades_df = system.load_compressed_trades(symbol, timeframe, config)
                
                if trades_df is not None:
                    # リストの場合はDataFrameに変換
                    if isinstance(trades_df, list):
                        if len(trades_df) > 0:
                            trades_df = pd.DataFrame(trades_df)
                            print(f"📈 生成されたトレード数: {len(trades_df)}")
                            
                            # 価格の多様性確認
                            if 'entry_price' in trades_df.columns:
                                unique_prices = trades_df['entry_price'].nunique()
                                print(f"💰 ユニークな価格数: {unique_prices}")
                                
                                # 最初の3件表示
                                print(f"\n📊 最初の3件のトレード:")
                                for i, row in trades_df.head(3).iterrows():
                                    print(f"   {i+1}. Entry: ${row.get('entry_price', 0):.2f}, "
                                          f"TP: ${row.get('take_profit_price', 0):.2f}, "
                                          f"SL: ${row.get('stop_loss_price', 0):.2f}")
                        else:
                            print("⚠️ トレードデータなし（条件未達）")
                    else:
                        print(f"📈 データ形式: {type(trades_df)}")
                
                successful_additions += 1
            else:
                print(f"❌ 銘柄追加失敗")
                print(f"⏱️ 処理時間: {duration:.2f}秒")
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
    
    # サマリー
    print(f"\n{'='*60}")
    print(f"📊 テスト結果サマリー:")
    print(f"   成功: {successful_additions}/{len(test_cases)}")
    
    # ハードコード値検知テストも実行
    print(f"\n{'='*60}")
    print("🔍 ハードコード値検知テスト:")
    
    try:
        import subprocess
        result = subprocess.run(
            ["python", "tests/test_hardcoded_value_detection.py"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # 最後の数行だけ表示
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines[-10:]:
            if "✅" in line or "❌" in line or "失敗" in line or "エラー" in line:
                print(f"   {line}")
                
    except Exception as e:
        print(f"   ⚠️ ハードコード値検知テスト実行エラー: {e}")
    
    print(f"\n✅ 動作確認完了")

if __name__ == "__main__":
    test_symbol_addition()