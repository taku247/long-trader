"""
バックテスト結果とトレード分析を含む完全なダッシュボードを起動
"""
import os
import sys
from trade_visualization import generate_sample_analyses
from dashboard import ModernBacktestDashboard

def main():
    print("=" * 60)
    print("🚀 High Leverage Bot - Complete Analysis Dashboard")
    print("=" * 60)
    
    # Step 1: サンプルデータの確認
    if not os.path.exists("results/backtest_results_summary.csv"):
        print("⚠️  バックテスト結果データが見つかりません")
        print("📝 create_sample_data.py を実行してください")
        print("実行コマンド: python create_sample_data.py")
        return
    
    print("✅ バックテスト結果データを確認")
    
    # Step 2: トレード分析データの生成
    print("\n📊 詳細トレード分析を生成中...")
    try:
        analyses = generate_sample_analyses()
        print(f"✅ トレード分析完了: {len(analyses)}件の分析を生成")
        
        # 生成された分析の詳細表示
        print("\n📋 生成された分析:")
        for analysis in analyses:
            print(f"  • {analysis['symbol']} ({analysis['timeframe']}) - {analysis['config']}")
            print(f"    勝率: {analysis['win_rate']:.1f}% | 収益: {analysis['total_return']:.1f}% | トレード数: {analysis['total_trades']}")
            print(f"    チャート: {analysis['chart_path']}")
        
    except Exception as e:
        print(f"❌ トレード分析生成エラー: {e}")
        return
    
    # Step 3: ダッシュボード起動
    print(f"\n🚀 ダッシュボードを起動しています...")
    print(f"📊 機能一覧:")
    print(f"  ✓ バックテスト結果の比較・フィルタリング")
    print(f"  ✓ パフォーマンス指標の可視化")
    print(f"  ✓ 詳細トレード分析チャート")
    print(f"  ✓ エントリー判定理由の確認")
    print(f"  ✓ レバレッジ使用状況の分析")
    print(f"\n💡 使い方:")
    print(f"  1. フィルターで戦略を絞り込み")
    print(f"  2. 'Trade Analysis'セクションで詳細分析を選択")
    print(f"  3. 'View Chart'ボタンで詳細チャートを表示")
    
    try:
        dashboard = ModernBacktestDashboard(results_dir="results")
        print(f"\n📈 ダッシュボードURL: http://127.0.0.1:8050")
        print(f"🛑 終了するには Ctrl+C を押してください")
        dashboard.run(debug=False)
        
    except KeyboardInterrupt:
        print(f"\n\n👋 ダッシュボードを終了しました")
    except Exception as e:
        print(f"❌ ダッシュボード起動エラー: {e}")

if __name__ == "__main__":
    main()