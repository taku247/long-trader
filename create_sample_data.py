"""
ダッシュボード確認用のサンプルデータ生成スクリプト
"""
import pandas as pd
import numpy as np
import os

def create_sample_backtest_data():
    """サンプルのバックテスト結果データを生成"""
    
    # 設定
    symbols = ['HYPE', 'SOL', 'PEPE', 'WIF', 'BONK']
    timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
    module_configs = [
        'Conservative_ML',
        'Aggressive_Traditional', 
        'Full_ML',
        'Hybrid_Strategy',
        'Risk_Optimized'
    ]
    
    # モジュールの詳細設定
    module_details = {
        'Conservative_ML': {
            'downside_evaluator': 'MultiLayerRiskEvaluator',
            'upside_calculator': 'MLBreakoutPredictor',
            'correlation_calculator': 'DynamicWindowCorrelation',
            'crash_analyzer': 'HistoricalPatternAnalyzer',
            'risk_assessor': 'ConservativeRiskAssessor',
            'reward_evaluator': 'MLProfitPredictor',
            'leverage_calculator': 'FixedFractionalCalculator'
        },
        'Aggressive_Traditional': {
            'downside_evaluator': 'SimpleDistanceRiskEvaluator',
            'upside_calculator': 'LinearProjectionCalculator',
            'correlation_calculator': 'SimpleCorrelationCalculator',
            'crash_analyzer': 'ElasticityBasedAnalyzer',
            'risk_assessor': 'MLRiskPredictor',
            'reward_evaluator': 'SimpleTargetEvaluator',
            'leverage_calculator': 'KellyLeverageCalculator'
        },
        'Full_ML': {
            'downside_evaluator': 'MLSupportStrengthEvaluator',
            'upside_calculator': 'MLBreakoutPredictor',
            'correlation_calculator': 'MLCorrelationPredictor',
            'crash_analyzer': 'MLCrashPredictor',
            'risk_assessor': 'MLRiskPredictor',
            'reward_evaluator': 'MLProfitPredictor',
            'leverage_calculator': 'MLOptimalLeverage'
        },
        'Hybrid_Strategy': {
            'downside_evaluator': 'MultiLayerRiskEvaluator',
            'upside_calculator': 'MLBreakoutPredictor',
            'correlation_calculator': 'MLCorrelationPredictor',
            'crash_analyzer': 'MLCrashPredictor',
            'risk_assessor': 'VaRBasedAssessor',
            'reward_evaluator': 'MultiObjectiveEvaluator',
            'leverage_calculator': 'RiskParityCalculator'
        },
        'Risk_Optimized': {
            'downside_evaluator': 'VaRBasedAssessor',
            'upside_calculator': 'LinearProjectionCalculator',
            'correlation_calculator': 'RegimeSwitchingCorrelation',
            'crash_analyzer': 'HistoricalPatternAnalyzer',
            'risk_assessor': 'ConservativeRiskAssessor',
            'reward_evaluator': 'SimpleTargetEvaluator',
            'leverage_calculator': 'FixedFractionalCalculator'
        }
    }
    
    # データ生成
    results = []
    np.random.seed(42)  # 再現性のため
    
    for symbol in symbols:
        for timeframe in timeframes:
            for config in module_configs:
                
                # 銘柄とタイムフレームによる基本性能の調整
                symbol_multiplier = {
                    'HYPE': 1.2, 'SOL': 1.1, 'PEPE': 0.8, 'WIF': 0.9, 'BONK': 0.7
                }[symbol]
                
                timeframe_multiplier = {
                    '1m': 0.5, '3m': 0.6, '5m': 0.65, '15m': 0.7, '30m': 0.85, '1h': 1.0
                }[timeframe]
                
                # 設定による性能調整
                config_multiplier = {
                    'Conservative_ML': 0.9,
                    'Aggressive_Traditional': 1.3,
                    'Full_ML': 1.1,
                    'Hybrid_Strategy': 1.0,
                    'Risk_Optimized': 0.8
                }[config]
                
                base_performance = symbol_multiplier * timeframe_multiplier * config_multiplier
                
                # ランダムなバリエーション
                noise = np.random.normal(1.0, 0.3)
                final_multiplier = base_performance * noise
                
                # メトリクス計算
                base_sharpe = np.random.normal(1.5, 0.8) * final_multiplier
                sharpe_ratio = max(0.1, min(4.0, base_sharpe))  # 0.1-4.0の範囲
                
                total_return = sharpe_ratio * np.random.normal(0.3, 0.15) * final_multiplier
                max_drawdown = np.random.normal(-0.15, 0.1) / final_multiplier  # 良い戦略ほど小さいDD
                max_drawdown = max(-0.5, min(-0.01, max_drawdown))
                
                win_rate = 0.4 + (sharpe_ratio - 0.5) * 0.1 + np.random.normal(0, 0.05)
                win_rate = max(0.2, min(0.8, win_rate))
                
                avg_leverage = 2.0 + sharpe_ratio * 0.5 + np.random.normal(0, 0.3)
                avg_leverage = max(1.0, min(10.0, avg_leverage))
                
                total_trades = int(np.random.normal(150, 50))
                total_trades = max(50, total_trades)
                
                profit_factor = 1.0 + sharpe_ratio * 0.3 + np.random.normal(0, 0.2)
                profit_factor = max(0.5, profit_factor)
                
                # 結果に追加
                result = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'module_config': config,
                    'total_return': total_return,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'win_rate': win_rate,
                    'avg_leverage': avg_leverage,
                    'total_trades': total_trades,
                    'profit_factor': profit_factor,
                    **module_details[config]
                }
                
                results.append(result)
    
    return pd.DataFrame(results)

def create_sample_trades_data(results_df):
    """各戦略のサンプルトレードデータを生成"""
    
    trades_dir = "results/trades"
    os.makedirs(trades_dir, exist_ok=True)
    
    np.random.seed(42)
    
    for _, row in results_df.iterrows():
        trades = []
        num_trades = int(row['total_trades'])
        
        # 日付生成
        start_date = pd.Timestamp('2024-01-01')
        end_date = pd.Timestamp('2024-06-30')
        dates = pd.date_range(start_date, end_date, periods=num_trades)
        
        cumulative_return = 0
        
        for i, date in enumerate(dates):
            # トレード結果の生成
            win_prob = row['win_rate']
            is_win = np.random.random() < win_prob
            
            if is_win:
                pnl_pct = np.random.exponential(0.03)  # 勝ちトレードの利益
            else:
                pnl_pct = -np.random.exponential(0.015)  # 負けトレードの損失
            
            cumulative_return += pnl_pct
            
            leverage = np.random.normal(row['avg_leverage'], 1.0)
            leverage = max(1.0, min(10.0, leverage))
            
            trade = {
                'timestamp': date,
                'entry_price': np.random.uniform(20, 50),
                'exit_price': 0,  # 計算で設定
                'leverage': leverage,
                'pnl_pct': pnl_pct,
                'cumulative_return': cumulative_return,
                'position_size': np.random.uniform(100, 1000),
                'duration_hours': np.random.exponential(2),
                'is_win': is_win
            }
            
            trade['exit_price'] = trade['entry_price'] * (1 + pnl_pct)
            trades.append(trade)
        
        # ファイル保存
        trades_df = pd.DataFrame(trades)
        filename = f"{row['symbol']}_{row['timeframe']}_{row['module_config']}_trades.csv"
        trades_df.to_csv(f"{trades_dir}/{filename}", index=False)

def main():
    """メイン実行"""
    print("サンプルデータを生成中...")
    
    # resultsディレクトリ作成
    os.makedirs("results", exist_ok=True)
    
    # バックテスト結果データ生成
    results_df = create_sample_backtest_data()
    
    # メインCSVファイル保存
    results_df.to_csv("results/backtest_results_summary.csv", index=False)
    print(f"✓ メイン結果データを保存: {len(results_df)}行")
    
    # トレード詳細データ生成
    print("トレード詳細データを生成中...")
    create_sample_trades_data(results_df)
    print(f"✓ トレード詳細データを保存")
    
    # 統計表示
    print(f"\n【生成データ統計】")
    print(f"総戦略数: {len(results_df)}")
    print(f"銘柄数: {len(results_df['symbol'].unique())}")
    print(f"時間足数: {len(results_df['timeframe'].unique())}")
    print(f"設定数: {len(results_df['module_config'].unique())}")
    print(f"平均Sharpe比: {results_df['sharpe_ratio'].mean():.2f}")
    print(f"最高Sharpe比: {results_df['sharpe_ratio'].max():.2f}")
    print(f"平均勝率: {results_df['win_rate'].mean():.1%}")
    
    print(f"\nダッシュボード起動コマンド:")
    print(f"python dashboard.py")

if __name__ == "__main__":
    main()