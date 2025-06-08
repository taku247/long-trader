"""
圧縮データへのアクセス方法デモ
"""
from scalable_analysis_system import ScalableAnalysisSystem
import pandas as pd

def demo_data_access():
    """圧縮データアクセスのデモ"""
    system = ScalableAnalysisSystem()
    
    print("=" * 60)
    print("圧縮データアクセス機能のデモ")
    print("=" * 60)
    
    # 1. 単一データの読み込み
    print("\n1. 単一分析データの読み込み:")
    # 実際のデータがある場合の例（存在しない場合はNoneが返る）
    trades_df = system.load_compressed_trades('TOKEN001', '1h', 'Config_01')
    if trades_df is not None:
        print(f"  - トレード数: {len(trades_df)}")
        print(f"  - カラム: {trades_df.columns.tolist()}")
        print(f"  - 累積収益: {trades_df['cumulative_return'].iloc[-1]:.2%}")
    else:
        print("  - データが見つかりません（まずscalable_analysis_system.pyを実行してください）")
    
    # 2. 複数データの一括読み込み
    print("\n2. 条件に基づく複数データの読み込み:")
    # Sharpe比が1.0以上の分析のトレードデータを全て読み込み
    all_trades = system.load_multiple_trades(criteria={'min_sharpe': 1.0})
    print(f"  - 読み込まれた分析数: {len(all_trades)}")
    for key, trades in list(all_trades.items())[:3]:  # 最初の3件を表示
        print(f"  - {key}: {len(trades)}トレード")
    
    # 3. CSVエクスポート
    print("\n3. 圧縮データのCSVエクスポート:")
    # 最初のデータをCSVに出力
    if all_trades:
        first_key = list(all_trades.keys())[0]
        symbol, timeframe, config = first_key.split('_', 2)
        success = system.export_to_csv(symbol, timeframe, config, 
                                     f"sample_export_{symbol}_{timeframe}.csv")
        if success:
            print(f"  - エクスポート成功: sample_export_{symbol}_{timeframe}.csv")
    
    # 4. 詳細情報の取得
    print("\n4. 分析の詳細情報取得:")
    # 上位パフォーマンスの詳細を取得
    top_analyses = system.query_analyses(order_by='sharpe_ratio', limit=5)
    if not top_analyses.empty:
        top_analysis = top_analyses.iloc[0]
        details = system.get_analysis_details(
            top_analysis['symbol'],
            top_analysis['timeframe'],
            top_analysis['config']
        )
        
        if details:
            print(f"  - Symbol: {details['info']['symbol']}")
            print(f"  - Sharpe: {details['info']['sharpe_ratio']:.2f}")
            print(f"  - Total Return: {details['info']['total_return']:.1%}")
            print(f"  - Trades DataFrame shape: {details['trades'].shape if details['trades'] is not None else 'N/A'}")
    
    # 5. メモリ効率的な処理
    print("\n5. メモリ効率的な大量データ処理:")
    print("  圧縮により90%のストレージ削減")
    print("  必要な時だけ解凍してメモリに読み込み")
    print("  処理後は自動的にメモリから解放")
    
    # 6. 使用例のコード
    print("\n6. 実際の使用例コード:")
    print("""
    # 特定の分析のトレードデータを読み込み
    trades_df = system.load_compressed_trades('BTC', '1h', 'Conservative_ML')
    
    # 高性能分析のデータを一括読み込み
    high_perf_trades = system.load_multiple_trades({'min_sharpe': 2.0})
    
    # データをCSVに出力
    system.export_to_csv('BTC', '1h', 'Conservative_ML', 'output.csv')
    
    # 詳細情報の取得
    details = system.get_analysis_details('BTC', '1h', 'Conservative_ML')
    """)

if __name__ == "__main__":
    demo_data_access()