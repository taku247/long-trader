#!/usr/bin/env python3
"""
新シンボル追加 - ワンコマンドツール
新しい暗号通貨シンボルを既存のシステムに追加し、全戦略をテストする最も簡単な方法

使用法:
    python add_new_symbol.py BTC
    python add_new_symbol.py BTC ETH ADA
"""

import sys
import os
from pathlib import Path

def main():
    """メイン実行関数"""
    
    # 引数チェック
    if len(sys.argv) < 2:
        print("使用法: python add_new_symbol.py <SYMBOL1> [SYMBOL2] [SYMBOL3] ...")
        print("例:")
        print("  python add_new_symbol.py BTC")
        print("  python add_new_symbol.py BTC ETH ADA SOL")
        print("  python add_new_symbol.py DOGE SHIB PEPE")
        return
    
    # シンボル取得
    symbols = [arg.upper() for arg in sys.argv[1:]]
    
    print("=" * 60)
    print("🚀 新シンボル追加 & 戦略テストシステム")
    print("=" * 60)
    print(f"追加するシンボル: {', '.join(symbols)}")
    
    try:
        # 新シンボルテスターをインポート
        from new_symbol_strategy_tester import NewSymbolStrategyTester
        
        # テスター初期化
        tester = NewSymbolStrategyTester()
        
        print(f"\n利用可能な戦略:")
        for strategy in tester.existing_strategies['configs']:
            print(f"  - {strategy}")
        
        print(f"タイムフレーム: {', '.join(tester.existing_strategies['timeframes'])}")
        
        # 各シンボルでテスト実行
        all_results = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n{'='*40}")
            print(f"📊 {symbol} テスト実行中 ({i}/{len(symbols)})")
            print(f"{'='*40}")
            
            # 戦略テスト実行
            results_df = tester.test_all_strategies_on_symbol(symbol, use_scalable_system=False)
            
            # 結果保存
            tester.update_main_results_csv(results_df)
            
            # サマリーレポート生成
            tester.generate_summary_report(symbol, results_df)
            
            # 推奨戦略取得
            recommendations = tester.get_recommended_strategies(symbol, results_df, top_n=3)
            
            print(f"\n🏆 {symbol} 推奨戦略 TOP 3:")
            for rec in recommendations:
                print(f"  {rec['rank']}. {rec['timeframe']} - {rec['strategy']}")
                print(f"     Sharpe: {rec['sharpe_ratio']:.2f} | 収益: {rec['total_return']:.1f}% | 勝率: {rec['win_rate']:.1%}")
                print(f"     理由: {rec['recommendation_reason']}")
            
            all_results.append({
                'symbol': symbol,
                'results': results_df,
                'recommendations': recommendations
            })
        
        # 全体サマリー
        print(f"\n{'='*60}")
        print(f"📈 全体サマリー")
        print(f"{'='*60}")
        
        print(f"✅ 処理完了シンボル数: {len(symbols)}")
        print(f"✅ 総テスト設定数: {sum(len(r['results']) for r in all_results)}")
        
        # 各シンボルの最高パフォーマンス戦略
        print(f"\n🥇 各シンボル最高パフォーマンス:")
        for result in all_results:
            symbol = result['symbol']
            best_rec = result['recommendations'][0]  # TOP 1
            print(f"  {symbol}: {best_rec['timeframe']} {best_rec['strategy']} (Sharpe: {best_rec['sharpe_ratio']:.2f})")
        
        # ファイル出力確認
        print(f"\n📁 生成されたファイル:")
        results_dir = Path("results")
        if results_dir.exists():
            print(f"  📊 メイン結果: results/backtest_results_summary.csv")
            print(f"  📈 トレード詳細: results/trades/")
            
            trades_count = len(list((results_dir / "trades").glob("*.csv")))
            print(f"  💼 総トレードファイル数: {trades_count}")
        
        # レポートファイル
        for symbol in symbols:
            report_file = results_dir / f"{symbol}_strategy_test_report.txt"
            if report_file.exists():
                print(f"  📋 {symbol}レポート: {report_file}")
        
        # 次のステップ
        print(f"\n🎯 次のステップ:")
        print(f"  1. 詳細結果確認: python dashboard.py")
        print(f"  2. 戦略再現: python strategy_reproducer.py")
        print(f"  3. 実市場分析: python real_market_integration.py")
        
        # 推奨事項
        print(f"\n💡 推奨事項:")
        print(f"  - ダッシュボードで詳細パフォーマンスを確認")
        print(f"  - 高Sharpe比戦略の設定をexport")
        print(f"  - 実データでのバックテスト実行を検討")
        
    except ImportError as e:
        print(f"❌ 必要なモジュールが見つかりません: {e}")
        print("new_symbol_strategy_tester.py が同じディレクトリにあることを確認してください")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        print("詳細なエラー情報:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()