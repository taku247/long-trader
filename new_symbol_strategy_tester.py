"""
⚠️ **DEPRECATED - LEGACY FILE WARNING** ⚠️

新シンボル戦略テストシステム
任意の新しい暗号通貨シンボルに対して、既存の全戦略を自動的にテストするシステム

🚨 **重要な警告**: 
このファイルはレガシーファイルです。現在のメインシステムでは使用されていません。
バックテスト結果はランダム生成データに基づいており、実際の市場データとは無関係です。

✅ **現在の推奨方法**: 
銘柄追加は web_dashboard/app.py のWebインターフェースから実行してください。
実際の市場データに基づく分析が行われます。

⚠️ **このファイルの使用は推奨されません** - 誤解を招くランダムデータが生成されます
"""
import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
import logging
from datetime import datetime
from scalable_analysis_system import ScalableAnalysisSystem

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewSymbolStrategyTester:
    def __init__(self, results_dir="results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.trades_dir = self.results_dir / "trades"
        self.trades_dir.mkdir(exist_ok=True)
        
        # 既存の戦略情報を分析
        self.existing_strategies = self._analyze_existing_strategies()
        self.scalable_system = ScalableAnalysisSystem()
        
    def _analyze_existing_strategies(self):
        """既存の戦略情報を分析"""
        strategies = {
            'timeframes': ['15m', '1h'],
            'configs': [
                'Conservative_ML',
                'Aggressive_Traditional', 
                'Full_ML',
                'Hybrid_Strategy',
                'Risk_Optimized'
            ],
            'config_details': {
                'Conservative_ML': {
                    'description': 'Conservative machine learning approach with risk-first analysis',
                    'expected_sharpe': 1.2,
                    'expected_win_rate': 0.65,
                    'max_leverage': 3.0,
                    'risk_tolerance': 0.02
                },
                'Aggressive_Traditional': {
                    'description': 'Aggressive traditional technical analysis with high leverage',
                    'expected_sharpe': 1.8,
                    'expected_win_rate': 0.55,
                    'max_leverage': 8.0,
                    'risk_tolerance': 0.05
                },
                'Full_ML': {
                    'description': 'Full machine learning pipeline for all components',
                    'expected_sharpe': 2.1,
                    'expected_win_rate': 0.62,
                    'max_leverage': 6.0,
                    'risk_tolerance': 0.035
                },
                'Hybrid_Strategy': {
                    'description': 'Hybrid approach combining ML and traditional methods',
                    'expected_sharpe': 1.5,
                    'expected_win_rate': 0.58,
                    'max_leverage': 5.0,
                    'risk_tolerance': 0.03
                },
                'Risk_Optimized': {
                    'description': 'Risk-first optimization with conservative parameters',
                    'expected_sharpe': 1.0,
                    'expected_win_rate': 0.68,
                    'max_leverage': 2.5,
                    'risk_tolerance': 0.015
                }
            }
        }
        return strategies
    
    def generate_new_symbol_configs(self, symbol):
        """新しいシンボルに対する全戦略設定を生成"""
        configs = []
        
        for timeframe in self.existing_strategies['timeframes']:
            for strategy_config in self.existing_strategies['configs']:
                config = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'config': strategy_config
                }
                configs.append(config)
        
        logger.info(f"生成された設定数: {len(configs)} (シンボル: {symbol})")
        return configs
    
    def test_all_strategies_on_symbol(self, symbol, use_scalable_system=False):
        """指定されたシンボルで全戦略をテスト"""
        logger.info(f"=== {symbol} での全戦略テスト開始 ===")
        
        # 設定生成
        configs = self.generate_new_symbol_configs(symbol)
        
        if use_scalable_system:
            # スケーラブルシステムを使用（高速並列処理）
            return self._test_with_scalable_system(configs)
        else:
            # 独自実装（詳細制御可能）
            return self._test_with_custom_system(symbol, configs)
    
    def _test_with_scalable_system(self, configs):
        """スケーラブルシステムを使用してテスト"""
        logger.info("スケーラブルシステムを使用してバッチ分析実行")
        
        processed = self.scalable_system.generate_batch_analysis(configs, max_workers=4)
        
        # 結果をスケーラブルシステムから取得
        results = []
        for config in configs:
            analysis = self.scalable_system.get_analysis_details(
                config['symbol'], 
                config['timeframe'], 
                config['config']
            )
            if analysis:
                results.append({
                    'symbol': config['symbol'],
                    'timeframe': config['timeframe'],
                    'strategy': config['config'],
                    'total_return': analysis['info']['total_return'],
                    'sharpe_ratio': analysis['info']['sharpe_ratio'],
                    'win_rate': analysis['info']['win_rate'],
                    'max_drawdown': analysis['info']['max_drawdown'],
                    'total_trades': analysis['info']['total_trades'],
                    'avg_leverage': analysis['info']['avg_leverage']
                })
        
        return pd.DataFrame(results)
    
    def _test_with_custom_system(self, symbol, configs):
        """カスタムシステムでテスト（より詳細な制御）"""
        logger.info("カスタムシステムでテスト実行")
        
        results = []
        
        for config in configs:
            logger.info(f"テスト中: {config['symbol']} {config['timeframe']} {config['config']}")
            
            # バックテストシミュレーション
            backtest_result = self._simulate_backtest(
                symbol, 
                config['timeframe'], 
                config['config']
            )
            
            # CSVファイル生成
            self._generate_trades_csv(backtest_result, config)
            
            # 結果記録
            results.append({
                'symbol': symbol,
                'timeframe': config['timeframe'],
                'strategy': config['config'],
                'total_return': backtest_result['total_return'],
                'sharpe_ratio': backtest_result['sharpe_ratio'],
                'win_rate': backtest_result['win_rate'],
                'max_drawdown': backtest_result['max_drawdown'],
                'total_trades': backtest_result['total_trades'],
                'avg_leverage': backtest_result['avg_leverage'],
                'profit_factor': backtest_result['profit_factor']
            })
        
        return pd.DataFrame(results)
    
    def _simulate_backtest(self, symbol, timeframe, strategy_config):
        """バックテストシミュレーション - ⚠️ DEPRECATED: ランダムデータ生成のため無効化"""
        # TODO: ランダムバックテスト生成は品質問題のためコメントアウト (2024-06-18)
        # 実際の市場データを使用したバックテスト実装が必要
        
        # 警告メッセージを表示
        print("⚠️ 警告: このメソッドはランダムデータを生成するため無効化されています")
        print("✅ 推奨: web_dashboard/app.py のWebインターフェースを使用してください")
        
        # 無効化されたランダム生成コード
        # np.random.seed(hash(f"{symbol}_{timeframe}_{strategy_config}") % 2**32)
        # 
        # # 戦略固有のパフォーマンス特性
        # strategy_details = self.existing_strategies['config_details'][strategy_config]
        # 
        # # シンボル固有の調整（市場特性シミュレーション）
        # symbol_multiplier = self._get_symbol_performance_multiplier(symbol)
        # timeframe_multiplier = self._get_timeframe_performance_multiplier(timeframe)
        # 
        # # ベースパフォーマンス計算
        # base_sharpe = strategy_details['expected_sharpe'] * symbol_multiplier * timeframe_multiplier
        # base_win_rate = strategy_details['expected_win_rate']
        # 
        # # ランダム変動
        # noise = np.random.normal(1.0, 0.2)
        # final_sharpe = max(0.1, base_sharpe * noise)
        # final_win_rate = max(0.3, min(0.8, base_win_rate + np.random.normal(0, 0.05)))
        
        # # トレード数（ランダム生成 - 無効化済み）
        # num_trades = int(np.random.normal(120, 30))
        # num_trades = max(50, num_trades)
        # 
        # # トレードデータ生成（ランダム生成 - 無効化済み）
        # trades = self._generate_trade_data(
        #     num_trades, 
        #     final_win_rate, 
        #     strategy_details['max_leverage'],
        #     final_sharpe
        # )
        
        # 安全なデフォルト値を返す（実行エラー回避）
        import pandas as pd
        trades = pd.DataFrame({
            'cumulative_return': [0.0],
            'leverage': [1.0],
            'pnl_pct': [0.0]
        })
        
        # メトリクス計算（無効化済み - 安全な値を返す）
        total_return = 0.0  # 無効化済み
        max_drawdown = 0.0  # 無効化済み
        avg_leverage = 1.0  # 無効化済み
        
        # Profit Factor計算（無効化済み - 安全な値を返す）
        # winning_trades = trades[trades['pnl_pct'] > 0]['pnl_pct'].sum()
        # losing_trades = abs(trades[trades['pnl_pct'] < 0]['pnl_pct'].sum())
        # profit_factor = winning_trades / losing_trades if losing_trades > 0 else 2.0
        profit_factor = 0.0  # 無効化済み
        
        # 無効化済み - 安全なデフォルト値を返す
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': strategy_config,
            'total_return': 0.0,     # 無効化済み
            'sharpe_ratio': 0.0,     # 無効化済み  
            'win_rate': 0.0,         # 無効化済み
            'max_drawdown': 0.0,     # 無効化済み
            'total_trades': 0,       # 無効化済み
            'avg_leverage': 0.0,     # 無効化済み
            'profit_factor': 0.0,    # 無効化済み
            'trades_data': pd.DataFrame(),  # 空DataFrame
            'status': 'disabled_random_generation'
        }
    
    def _get_symbol_performance_multiplier(self, symbol):
        """シンボル固有のパフォーマンス乗数"""
        # 一般的な暗号通貨の特性をシミュレート
        symbol_characteristics = {
            'BTC': 1.1,    # 安定した大型銘柄
            'ETH': 1.05,   # 大型アルトコイン
            'SOL': 1.2,    # 高ボラティリティ
            'ADA': 0.9,    # 安定志向
            'DOT': 0.95,   # 中程度のボラティリティ
            'AVAX': 1.1,   # 高成長
            'MATIC': 1.0,  # 標準
            'ARB': 1.15,   # 新興L2
            'OP': 1.1,     # L2トークン
            'HYPE': 1.3,   # 高ボラティリティミームコイン
            'PEPE': 0.8,   # ミームコイン
            'WIF': 0.85,   # ミームコイン
            'BONK': 0.75   # 高リスクミームコイン
        }
        
        return symbol_characteristics.get(symbol, 1.0)  # デフォルト値
    
    def _get_timeframe_performance_multiplier(self, timeframe):
        """タイムフレーム固有のパフォーマンス乗数"""
        timeframe_multipliers = {
            '15m': 0.8,  # 短期間、ノイズが多い
            '1h': 1.0,   # 標準
            '30m': 0.9,  # 30分足
            '5m': 0.7,   # 5分足、ノイズが非常に多い
            '3m': 0.65,  # 3分足
            '1m': 0.6    # 1分足、最も短期
        }
        return timeframe_multipliers.get(timeframe, 1.0)
    
    def _generate_trade_data(self, num_trades, win_rate, max_leverage, sharpe_ratio):
        """トレードデータを生成 - ⚠️ DEPRECATED: ランダムデータ生成のため無効化"""
        # TODO: ランダムトレード生成は品質問題のためコメントアウト (2024-06-18)
        # 実際の市場データを使用したトレード生成実装が必要
        
        print("⚠️ 警告: ランダムトレードデータ生成は無効化されています")
        
        # 無効化されたランダム生成コード
        # trades = []
        # cumulative_return = 0
        # 
        # # 日付生成
        # start_date = pd.Timestamp('2024-01-01')
        # end_date = pd.Timestamp('2024-06-30')
        # dates = pd.date_range(start_date, end_date, periods=num_trades)
        # 
        # for i, date in enumerate(dates):
        #     # 勝敗判定（ランダム）
        #     is_win = np.random.random() < win_rate
        #     
        #     if is_win:
        #         # 勝ちトレード: Sharpe比に基づく利益（ランダム）
        #         pnl_pct = np.random.exponential(0.02 + sharpe_ratio * 0.01)
        #     else:
        #         # 負けトレード（ランダム）
        #         pnl_pct = -np.random.exponential(0.015)
        #     
        #     # レバレッジ（ランダム）
        #     leverage = np.random.uniform(1.5, max_leverage)
        #     leveraged_pnl = pnl_pct * leverage
        #     cumulative_return += leveraged_pnl
        #     
        #     # エントリー価格（仮想 - ランダム）
        #     entry_price = np.random.uniform(20, 100)
        #     exit_price = entry_price * (1 + pnl_pct)
            
        #     trade = {
        #         'timestamp': date,
        #         'entry_price': entry_price,
        #         'exit_price': exit_price,
        #         'leverage': leverage,
        #         'pnl_pct': leveraged_pnl,
        #         'raw_pnl_pct': pnl_pct,
        #         'cumulative_return': cumulative_return,
        #         'position_size': np.random.uniform(100, 1000),  # ランダムポジションサイズ
        #         'duration_hours': np.random.exponential(2),     # ランダム持続時間
        #         'is_win': is_win
        #     }
        #     
        #     trades.append(trade)
        # 
        # return pd.DataFrame(trades)
        
        # 安全なデフォルトDataFrameを返す（実行エラー回避）
        return pd.DataFrame({
            'timestamp': [pd.Timestamp('2024-01-01')],
            'entry_price': [0.0],
            'exit_price': [0.0],
            'leverage': [1.0],
            'pnl_pct': [0.0],
            'raw_pnl_pct': [0.0],
            'cumulative_return': [0.0],
            'position_size': [0.0],
            'duration_hours': [0.0],
            'is_win': [False]
        })
    
    def _calculate_max_drawdown(self, cumulative_returns):
        """最大ドローダウンを計算"""
        if len(cumulative_returns) == 0:
            return 0
        
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / (peak + 1e-8)  # ゼロ除算回避
        return np.min(drawdown)
    
    def _generate_trades_csv(self, backtest_result, config):
        """トレードCSVファイルを生成"""
        trades_df = backtest_result['trades_data']
        
        filename = f"{config['symbol']}_{config['timeframe']}_{config['config']}_trades.csv"
        file_path = self.trades_dir / filename
        
        trades_df.to_csv(file_path, index=False)
        logger.info(f"CSVファイル生成: {filename}")
    
    def update_main_results_csv(self, new_results_df):
        """メイン結果CSVを更新"""
        main_csv_path = self.results_dir / "backtest_results_summary.csv"
        
        # 既存データ読み込み
        if main_csv_path.exists():
            existing_df = pd.read_csv(main_csv_path)
            
            # 重複除去のため、新しいシンボルのデータを削除してから追加
            symbol = new_results_df['symbol'].iloc[0]
            existing_df = existing_df[existing_df['symbol'] != symbol]
            
            # データ統合
            updated_df = pd.concat([existing_df, new_results_df], ignore_index=True)
        else:
            updated_df = new_results_df.copy()
        
        # 保存
        updated_df.to_csv(main_csv_path, index=False)
        logger.info(f"メイン結果CSVを更新: {len(updated_df)}行")
    
    def generate_summary_report(self, symbol, results_df):
        """サマリーレポートを生成"""
        report = f"""
=== {symbol} 戦略テスト結果サマリー ===

総戦略数: {len(results_df)}
テスト期間: 2024年1月〜6月（シミュレーション）

【パフォーマンス統計】
平均Sharpe比: {results_df['sharpe_ratio'].mean():.2f}
最高Sharpe比: {results_df['sharpe_ratio'].max():.2f} ({results_df.loc[results_df['sharpe_ratio'].idxmax(), 'strategy']})
平均勝率: {results_df['win_rate'].mean():.1%}
平均収益: {results_df['total_return'].mean():.1f}%

【タイムフレーム別ベストパフォーマー】
"""
        
        for timeframe in self.existing_strategies['timeframes']:
            tf_data = results_df[results_df['timeframe'] == timeframe]
            if not tf_data.empty:
                best = tf_data.loc[tf_data['sharpe_ratio'].idxmax()]
                report += f"{timeframe}: {best['strategy']} (Sharpe: {best['sharpe_ratio']:.2f}, 収益: {best['total_return']:.1f}%)\n"
        
        report += f"""
【戦略別平均パフォーマンス】
"""
        
        for strategy in self.existing_strategies['configs']:
            strategy_data = results_df[results_df['strategy'] == strategy]
            if not strategy_data.empty:
                avg_sharpe = strategy_data['sharpe_ratio'].mean()
                avg_return = strategy_data['total_return'].mean()
                report += f"{strategy}: Sharpe {avg_sharpe:.2f}, 収益 {avg_return:.1f}%\n"
        
        # レポートファイル保存
        report_path = self.results_dir / f"{symbol}_strategy_test_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        logger.info(f"レポート保存: {report_path}")
        
        return report
    
    def get_recommended_strategies(self, symbol, results_df, top_n=3):
        """推奨戦略を取得"""
        # Sharpe比でソート
        sorted_results = results_df.sort_values('sharpe_ratio', ascending=False)
        
        recommendations = []
        for i, (_, row) in enumerate(sorted_results.head(top_n).iterrows()):
            rec = {
                'rank': i + 1,
                'symbol': symbol,
                'timeframe': row['timeframe'],
                'strategy': row['strategy'],
                'sharpe_ratio': row['sharpe_ratio'],
                'total_return': row['total_return'],
                'win_rate': row['win_rate'],
                'max_drawdown': row['max_drawdown'],
                'avg_leverage': row['avg_leverage'],
                'recommendation_reason': self._get_recommendation_reason(row)
            }
            recommendations.append(rec)
        
        return recommendations
    
    def _get_recommendation_reason(self, row):
        """推奨理由を生成"""
        reasons = []
        
        if row['sharpe_ratio'] > 2.0:
            reasons.append("優秀なリスク調整後リターン")
        if row['win_rate'] > 0.65:
            reasons.append("高い勝率")
        if row['max_drawdown'] > -0.1:
            reasons.append("低いドローダウン")
        if row['total_return'] > 0.5:
            reasons.append("高い総収益")
        
        return ", ".join(reasons) if reasons else "バランスの取れたパフォーマンス"

def main():
    """使用例とデモ - ⚠️ DEPRECATED WARNING"""
    print("=" * 80)
    print("⚠️ **DEPRECATED - LEGACY FILE WARNING** ⚠️")
    print("=" * 80)
    print("このファイルはレガシーファイルです。ランダムデータ生成により")
    print("実際の市場データとは無関係な結果が表示されます。")
    print()
    print("✅ **推奨**: web_dashboard/app.py のWebインターフェースを使用")
    print("   → http://localhost:5001")
    print("=" * 80)
    print()
    
    # 実行を確認
    response = input("それでも続行しますか？ (y/N): ").strip().lower()
    if response != 'y':
        print("実行を中止しました。")
        return
    
    print("=" * 60)
    print("新シンボル戦略テストシステム（レガシー版）")
    print("=" * 60)
    
    # システム初期化
    tester = NewSymbolStrategyTester()
    
    print("\n利用可能な戦略:")
    for i, strategy in enumerate(tester.existing_strategies['configs'], 1):
        details = tester.existing_strategies['config_details'][strategy]
        print(f"{i}. {strategy}")
        print(f"   - {details['description']}")
        print(f"   - 期待Sharpe比: {details['expected_sharpe']}")
        print(f"   - 最大レバレッジ: {details['max_leverage']}x")
    
    print(f"\n利用可能なタイムフレーム: {', '.join(tester.existing_strategies['timeframes'])}")
    
    # 新しいシンボルでテスト
    test_symbol = input("\nテストしたいシンボルを入力 (例: BTC, ETH, ADA): ").upper()
    
    if not test_symbol:
        test_symbol = "BTC"  # デフォルト
    
    print(f"\n{test_symbol} での全戦略テストを開始...")
    
    # テスト実行
    results_df = tester.test_all_strategies_on_symbol(test_symbol, use_scalable_system=False)
    
    # メイン結果CSV更新
    tester.update_main_results_csv(results_df)
    
    # サマリーレポート生成
    tester.generate_summary_report(test_symbol, results_df)
    
    # 推奨戦略表示
    recommendations = tester.get_recommended_strategies(test_symbol, results_df)
    
    print(f"\n【{test_symbol} 推奨戦略 TOP 3】")
    for rec in recommendations:
        print(f"{rec['rank']}. {rec['timeframe']} - {rec['strategy']}")
        print(f"   Sharpe: {rec['sharpe_ratio']:.2f} | 収益: {rec['total_return']:.1f}% | 勝率: {rec['win_rate']:.1%}")
        print(f"   理由: {rec['recommendation_reason']}")
    
    print(f"\n✅ 全ての結果は results/ ディレクトリに保存されました")
    print(f"📊 ダッシュボードで詳細確認: python dashboard.py")

if __name__ == "__main__":
    main()