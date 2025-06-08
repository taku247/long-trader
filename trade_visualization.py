"""
バックテスト詳細可視化システム
各トレードのエントリー判定理由とチャートを生成・保存
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import os
import json
from datetime import datetime, timedelta
import numpy as np

class TradeVisualizationSystem:
    def __init__(self, output_dir="trade_analysis"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/charts", exist_ok=True)
        os.makedirs(f"{output_dir}/data", exist_ok=True)
    
    def create_detailed_trade_log(self, symbol, timeframe, config_name, 
                                num_trades=50, support_levels=None, resistance_levels=None):
        """
        詳細なトレードログを生成（エントリー判定理由付き）
        """
        np.random.seed(42)
        
        # 仮想的な価格データ生成
        dates = pd.date_range('2024-01-01', periods=200, freq='H')
        prices = self.generate_price_data(len(dates))
        
        # 支持線・抵抗線データ（サンプル）
        if support_levels is None:
            support_levels = [
                {'price': 22.5, 'strength': 85, 'touch_count': 4},
                {'price': 20.0, 'strength': 95, 'touch_count': 6},
                {'price': 18.5, 'strength': 70, 'touch_count': 3}
            ]
        
        if resistance_levels is None:
            resistance_levels = [
                {'price': 28.0, 'strength': 90, 'touch_count': 5},
                {'price': 30.5, 'strength': 75, 'touch_count': 3},
                {'price': 32.0, 'strength': 60, 'touch_count': 2}
            ]
        
        trades = []
        
        for i in range(num_trades):
            # ランダムなエントリータイミング
            entry_idx = np.random.randint(20, len(dates) - 20)
            entry_date = dates[entry_idx]
            entry_price = prices[entry_idx]
            
            # 最寄りの支持線・抵抗線を特定
            nearest_support = min(support_levels, 
                                key=lambda x: abs(x['price'] - entry_price) if x['price'] < entry_price else float('inf'))
            nearest_resistance = min(resistance_levels, 
                                   key=lambda x: abs(x['price'] - entry_price) if x['price'] > entry_price else float('inf'))
            
            # エントリー判定ロジック
            support_distance = (entry_price - nearest_support['price']) / entry_price
            resistance_distance = (nearest_resistance['price'] - entry_price) / entry_price
            
            # リスクリワード比計算
            risk_reward_ratio = resistance_distance / support_distance if support_distance > 0 else 1.0
            
            # レバレッジ決定
            if config_name == "Conservative_ML":
                base_leverage = 2.0 + min(nearest_support['strength'] / 50, 2.0)
            elif config_name == "Aggressive_Traditional":
                base_leverage = 4.0 + risk_reward_ratio
            elif config_name == "Full_ML":
                base_leverage = 3.0 + (nearest_support['strength'] + nearest_resistance['strength']) / 100
            else:
                base_leverage = 3.0
            
            # リスク調整
            if support_distance < 0.05:  # 支持線に近い
                leverage_multiplier = 1.5
            elif support_distance > 0.15:  # 支持線から遠い
                leverage_multiplier = 0.7
            else:
                leverage_multiplier = 1.0
                
            final_leverage = np.clip(base_leverage * leverage_multiplier, 1.0, 10.0)
            
            # 出口価格決定
            exit_idx = entry_idx + np.random.randint(1, 15)  # 1-15時間後
            if exit_idx >= len(prices):
                exit_idx = len(prices) - 1
            
            exit_price = prices[exit_idx]
            exit_date = dates[exit_idx]
            
            # PnL計算
            price_change = (exit_price - entry_price) / entry_price
            leveraged_pnl = price_change * final_leverage
            
            # 判定理由の詳細
            entry_reason = {
                'support_analysis': {
                    'nearest_price': nearest_support['price'],
                    'distance_pct': support_distance * 100,
                    'strength': nearest_support['strength'],
                    'touch_count': nearest_support['touch_count']
                },
                'resistance_analysis': {
                    'nearest_price': nearest_resistance['price'],
                    'distance_pct': resistance_distance * 100,
                    'strength': nearest_resistance['strength'],
                    'touch_count': nearest_resistance['touch_count']
                },
                'risk_reward_ratio': risk_reward_ratio,
                'leverage_reasoning': {
                    'base_leverage': base_leverage,
                    'risk_multiplier': leverage_multiplier,
                    'final_leverage': final_leverage,
                    'logic': f"Config: {config_name}, Support strength: {nearest_support['strength']}, Distance factor: {leverage_multiplier:.2f}"
                },
                'market_conditions': {
                    'trend': 'bullish' if prices[entry_idx] > prices[entry_idx-5] else 'bearish',
                    'volatility': np.std(prices[max(0, entry_idx-10):entry_idx]) if entry_idx >= 10 else 0
                }
            }
            
            trade = {
                'trade_id': f"{symbol}_{timeframe}_{config_name}_{i+1:03d}",
                'symbol': symbol,
                'timeframe': timeframe,
                'config': config_name,
                'entry_date': entry_date,
                'exit_date': exit_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'leverage': final_leverage,
                'pnl_pct': leveraged_pnl,
                'duration_hours': (exit_date - entry_date).total_seconds() / 3600,
                'is_win': leveraged_pnl > 0,
                'entry_reasoning': json.dumps(entry_reason, default=str),
                'stop_loss': nearest_support['price'],
                'take_profit': nearest_resistance['price']
            }
            
            trades.append(trade)
        
        return pd.DataFrame(trades), prices, dates, support_levels, resistance_levels
    
    def generate_price_data(self, length, start_price=25.0):
        """仮想的な価格データを生成"""
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, length)  # 小さなトレンド + ボラティリティ
        prices = [start_price]
        
        for i in range(1, length):
            # サポート・レジスタンスでの反発を模擬
            current_price = prices[-1]
            
            # 支持線付近での反発
            if current_price < 21:
                returns[i] += 0.01  # 上昇バイアス
            elif current_price > 29:
                returns[i] -= 0.01  # 下降バイアス
                
            next_price = current_price * (1 + returns[i])
            prices.append(max(15.0, min(35.0, next_price)))  # 価格範囲制限
        
        return prices
    
    def create_trade_analysis_chart(self, trades_df, prices, dates, 
                                  support_levels, resistance_levels, 
                                  symbol, timeframe, config_name):
        """
        詳細なトレード分析チャートを生成
        """
        # サブプロット作成
        fig = make_subplots(
            rows=3, cols=1,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(
                f'{symbol} ({timeframe}) - {config_name} Strategy Analysis',
                'Leverage Used',
                'Cumulative PnL'
            ),
            vertical_spacing=0.08
        )
        
        # 1. 価格チャート + エントリーポイント
        fig.add_trace(
            go.Scatter(
                x=dates, y=prices,
                mode='lines',
                name='Price',
                line=dict(color='white', width=1),
                hovertemplate='Price: $%{y:.2f}<br>Date: %{x}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 支持線・抵抗線
        for level in support_levels:
            fig.add_hline(
                y=level['price'],
                line=dict(color='green', width=2, dash='dash'),
                annotation_text=f"Support: ${level['price']:.1f} (S:{level['strength']})",
                annotation_position="bottom right",
                row=1, col=1
            )
        
        for level in resistance_levels:
            fig.add_hline(
                y=level['price'],
                line=dict(color='red', width=2, dash='dash'),
                annotation_text=f"Resistance: ${level['price']:.1f} (S:{level['strength']})",
                annotation_position="top right",
                row=1, col=1
            )
        
        # エントリーポイント
        winning_trades = trades_df[trades_df['is_win'] == True]
        losing_trades = trades_df[trades_df['is_win'] == False]
        
        if not winning_trades.empty:
            fig.add_trace(
                go.Scatter(
                    x=winning_trades['entry_date'],
                    y=winning_trades['entry_price'],
                    mode='markers',
                    name='Winning Entries',
                    marker=dict(
                        symbol='triangle-up',
                        size=winning_trades['leverage'] * 3,
                        color='lime',
                        line=dict(color='darkgreen', width=1)
                    ),
                    hovertemplate='Entry: $%{y:.2f}<br>Leverage: %{customdata:.1f}x<br>Date: %{x}<extra></extra>',
                    customdata=winning_trades['leverage']
                ),
                row=1, col=1
            )
        
        if not losing_trades.empty:
            fig.add_trace(
                go.Scatter(
                    x=losing_trades['entry_date'],
                    y=losing_trades['entry_price'],
                    mode='markers',
                    name='Losing Entries',
                    marker=dict(
                        symbol='triangle-down',
                        size=losing_trades['leverage'] * 3,
                        color='red',
                        line=dict(color='darkred', width=1)
                    ),
                    hovertemplate='Entry: $%{y:.2f}<br>Leverage: %{customdata:.1f}x<br>Date: %{x}<extra></extra>',
                    customdata=losing_trades['leverage']
                ),
                row=1, col=1
            )
        
        # 2. レバレッジ使用量
        fig.add_trace(
            go.Scatter(
                x=trades_df['entry_date'],
                y=trades_df['leverage'],
                mode='markers+lines',
                name='Leverage Used',
                marker=dict(
                    color=trades_df['pnl_pct'],
                    colorscale='RdYlGn',
                    size=8,
                    colorbar=dict(title="PnL %", y=0.35, len=0.3)
                ),
                line=dict(color='orange', width=1),
                hovertemplate='Leverage: %{y:.1f}x<br>PnL: %{customdata:.1%}<br>Date: %{x}<extra></extra>',
                customdata=trades_df['pnl_pct']
            ),
            row=2, col=1
        )
        
        # 3. 累積損益
        cumulative_pnl = trades_df['pnl_pct'].cumsum()
        fig.add_trace(
            go.Scatter(
                x=trades_df['entry_date'],
                y=cumulative_pnl,
                mode='lines',
                name='Cumulative PnL',
                line=dict(color='cyan', width=2),
                fill='tonexty',
                fillcolor='rgba(0, 255, 255, 0.1)',
                hovertemplate='Cumulative PnL: %{y:.1%}<br>Date: %{x}<extra></extra>'
            ),
            row=3, col=1
        )
        
        # レイアウト設定
        fig.update_layout(
            title=dict(
                text=f"Trade Analysis: {symbol} ({timeframe}) - {config_name}",
                x=0.5,
                font=dict(size=20, color='white')
            ),
            template='plotly_dark',
            height=800,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # 軸設定
        fig.update_xaxes(title_text="Date", row=3, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Leverage", row=2, col=1)
        fig.update_yaxes(title_text="Cumulative PnL (%)", row=3, col=1, tickformat='.1%')
        
        return fig
    
    def create_entry_reasoning_summary(self, trades_df):
        """エントリー判定理由のサマリーを作成"""
        reasoning_data = []
        
        for _, trade in trades_df.iterrows():
            reasoning = json.loads(trade['entry_reasoning'])
            
            reasoning_data.append({
                'trade_id': trade['trade_id'],
                'entry_price': trade['entry_price'],
                'leverage': trade['leverage'],
                'pnl_pct': trade['pnl_pct'],
                'support_distance': reasoning['support_analysis']['distance_pct'],
                'support_strength': reasoning['support_analysis']['strength'],
                'resistance_distance': reasoning['resistance_analysis']['distance_pct'],
                'resistance_strength': reasoning['resistance_analysis']['strength'],
                'risk_reward_ratio': reasoning['risk_reward_ratio'],
                'leverage_logic': reasoning['leverage_reasoning']['logic']
            })
        
        return pd.DataFrame(reasoning_data)
    
    def save_complete_analysis(self, symbol, timeframe, config_name):
        """完全な分析結果を生成・保存"""
        print(f"分析生成中: {symbol} {timeframe} {config_name}")
        
        # データ生成
        trades_df, prices, dates, support_levels, resistance_levels = self.create_detailed_trade_log(
            symbol, timeframe, config_name
        )
        
        # チャート作成
        fig = self.create_trade_analysis_chart(
            trades_df, prices, dates, support_levels, resistance_levels,
            symbol, timeframe, config_name
        )
        
        # 判定理由サマリー
        reasoning_df = self.create_entry_reasoning_summary(trades_df)
        
        # ファイル名
        base_filename = f"{symbol}_{timeframe}_{config_name}"
        
        # HTMLチャート保存
        chart_path = f"{self.output_dir}/charts/{base_filename}_analysis.html"
        fig.write_html(chart_path)
        
        # データ保存
        trades_path = f"{self.output_dir}/data/{base_filename}_trades.csv"
        reasoning_path = f"{self.output_dir}/data/{base_filename}_reasoning.csv"
        
        trades_df.to_csv(trades_path, index=False)
        reasoning_df.to_csv(reasoning_path, index=False)
        
        # メタデータ
        metadata = {
            'symbol': symbol,
            'timeframe': timeframe,
            'config': config_name,
            'generated_at': datetime.now().isoformat(),
            'total_trades': len(trades_df),
            'win_rate': (trades_df['is_win'].sum() / len(trades_df)) * 100,
            'total_return': trades_df['pnl_pct'].sum() * 100,
            'avg_leverage': trades_df['leverage'].mean(),
            'chart_path': chart_path,
            'data_paths': {
                'trades': trades_path,
                'reasoning': reasoning_path
            }
        }
        
        metadata_path = f"{self.output_dir}/data/{base_filename}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✓ 分析完了: {chart_path}")
        return metadata

def generate_sample_analyses():
    """サンプル分析を生成"""
    visualizer = TradeVisualizationSystem()
    
    # サンプル設定
    configs = [
        ('HYPE', '1h', 'Conservative_ML'),
        ('SOL', '4h', 'Aggressive_Traditional'),
        ('PEPE', '15m', 'Full_ML')
    ]
    
    analyses = []
    for symbol, timeframe, config in configs:
        metadata = visualizer.save_complete_analysis(symbol, timeframe, config)
        analyses.append(metadata)
    
    # インデックスファイル作成
    index_path = f"{visualizer.output_dir}/analysis_index.json"
    with open(index_path, 'w') as f:
        json.dump(analyses, f, indent=2)
    
    print(f"\n✓ 全分析完了: {len(analyses)}件")
    print(f"インデックス: {index_path}")
    return analyses

if __name__ == "__main__":
    analyses = generate_sample_analyses()
    
    print("\n生成された分析:")
    for analysis in analyses:
        print(f"- {analysis['symbol']} ({analysis['timeframe']}) {analysis['config']}")
        print(f"  勝率: {analysis['win_rate']:.1f}%, 収益: {analysis['total_return']:.1f}%")
        print(f"  チャート: {analysis['chart_path']}")