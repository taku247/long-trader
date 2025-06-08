"""
モダンなハイレバレッジBot バックテスト結果ダッシュボード
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, dash_table, callback_context
import dash_bootstrap_components as dbc
import os
import numpy as np
import json
import webbrowser
from pathlib import Path

class ModernBacktestDashboard:
    def __init__(self, results_dir="results"):
        self.results_dir = results_dir
        # ダークテーマでBootstrapを使用
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
        
        # データ読み込み
        try:
            self.df = pd.read_csv(f"{results_dir}/backtest_results_summary.csv")
            print(f"データ読み込み完了: {len(self.df)}行")
        except FileNotFoundError:
            print(f"エラー: {results_dir}/backtest_results_summary.csv が見つかりません")
            print("先に create_sample_data.py を実行してください")
            exit(1)
        
        # トレード分析データ読み込み
        self.load_trade_analyses()
            
        self.setup_layout()
        self.setup_callbacks()
        
        # カスタムCSS
        self.app.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>High Leverage Bot Dashboard</title>
                {%favicon%}
                {%css%}
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                    
                    body { 
                        background-color: #0f1419; 
                        color: #ffffff; 
                        font-family: 'Inter', sans-serif; 
                        margin: 0;
                        padding: 0;
                    }
                    .main-container { 
                        padding: 2rem; 
                        background: linear-gradient(135deg, #1a1a2e, #16213e); 
                        min-height: 100vh; 
                    }
                    .card-custom { 
                        background: rgba(255, 255, 255, 0.05); 
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 12px;
                        backdrop-filter: blur(10px);
                        margin-bottom: 1.5rem;
                        padding: 1.5rem;
                        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                    }
                    .filter-section { 
                        background: rgba(255, 255, 255, 0.03);
                        border-radius: 12px;
                        padding: 1.5rem;
                        margin-bottom: 2rem;
                        border: 1px solid rgba(255, 255, 255, 0.05);
                    }
                    .section-title { 
                        color: #00d4aa; 
                        font-size: 1.5rem; 
                        font-weight: 600; 
                        margin-bottom: 1rem;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }
                    .header-title {
                        background: linear-gradient(45deg, #00d4aa, #4facfe);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                        font-size: 3rem;
                        font-weight: 700;
                        margin: 0;
                    }
                    .top-performer-item {
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 8px;
                        padding: 1rem;
                        margin-bottom: 0.5rem;
                        border-left: 4px solid #00d4aa;
                    }
                    
                    /* Dropdown styling */
                    .Select-control {
                        background-color: #2d3748 !important;
                        border-color: rgba(255, 255, 255, 0.1) !important;
                    }
                    
                    /* Table styling */
                    .dash-table-container {
                        background: rgba(255, 255, 255, 0.02);
                        border-radius: 8px;
                    }
                </style>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''
    
    def setup_layout(self):
        self.app.layout = html.Div([
            dbc.Container([
                # ヘッダー
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H1("🚀 High Leverage Bot", className="header-title"),
                            html.P("Advanced Backtest Results Dashboard", 
                                   style={'color': 'rgba(255,255,255,0.7)', 'margin': 0, 'font-size': '1.2rem'})
                        ], style={'text-align': 'center', 'padding': '2rem 0'})
                    ])
                ]),
                
                # フィルターセクション
                html.Div([
                    html.H3("🔍 Filters", className="section-title"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Symbol", style={'color': '#00d4aa', 'font-weight': 'bold', 'margin-bottom': '0.5rem'}),
                            dcc.Dropdown(
                                id='symbol-filter',
                                options=[{'label': 'All Symbols', 'value': 'all'}] + 
                                        [{'label': s, 'value': s} for s in sorted(self.df['symbol'].unique())],
                                value='all',
                                style={'backgroundColor': '#2d3748', 'color': '#000000'},
                                className='mb-3'
                            )
                        ], md=2),
                        
                        dbc.Col([
                            html.Label("Timeframe", style={'color': '#00d4aa', 'font-weight': 'bold', 'margin-bottom': '0.5rem'}),
                            dcc.Dropdown(
                                id='timeframe-filter',
                                options=[{'label': 'All Timeframes', 'value': 'all'}] + 
                                        [{'label': t, 'value': t} for t in sorted(self.df['timeframe'].unique())],
                                value='all',
                                style={'backgroundColor': '#2d3748', 'color': '#000000'},
                                className='mb-3'
                            )
                        ], md=2),
                        
                        dbc.Col([
                            html.Label("Module Config", style={'color': '#00d4aa', 'font-weight': 'bold', 'margin-bottom': '0.5rem'}),
                            dcc.Dropdown(
                                id='config-filter',
                                options=[{'label': 'All Configs', 'value': 'all'}] + 
                                        [{'label': c, 'value': c} for c in sorted(self.df['module_config'].unique())],
                                value='all',
                                style={'backgroundColor': '#2d3748', 'color': '#000000'},
                                className='mb-3'
                            )
                        ], md=3),
                        
                        dbc.Col([
                            html.Label("Min Sharpe Ratio", style={'color': '#00d4aa', 'font-weight': 'bold', 'margin-bottom': '0.5rem'}),
                            dcc.Slider(
                                id='sharpe-filter',
                                min=0, max=3, step=0.1, value=0,
                                marks={i: {'label': str(i), 'style': {'color': '#ffffff', 'font-size': '0.8rem'}} for i in range(4)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], md=3),
                        
                        dbc.Col([
                            html.Label("Win Rate Range", style={'color': '#00d4aa', 'font-weight': 'bold', 'margin-bottom': '0.5rem'}),
                            dcc.RangeSlider(
                                id='winrate-filter',
                                min=0, max=1, step=0.05, value=[0, 1],
                                marks={i/10: {'label': f'{i*10}%', 'style': {'color': '#ffffff', 'font-size': '0.8rem'}} for i in range(0, 11, 2)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], md=2)
                    ])
                ], className="filter-section"),
                
                # メトリクスカード
                html.Div(id='metrics-cards', className='mb-4'),
                
                # メインチャートエリア
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H3("📊 Performance Overview", className="section-title"),
                            dcc.Graph(id='performance-overview', 
                                     config={'displayModeBar': False},
                                     style={'height': '450px'})
                        ], className="card-custom")
                    ], md=8),
                    
                    dbc.Col([
                        html.Div([
                            html.H3("🎯 Top Performers", className="section-title"),
                            html.Div(id='top-performers')
                        ], className="card-custom", style={'height': '500px', 'overflow-y': 'auto'})
                    ], md=4)
                ]),
                
                # 詳細分析エリア
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H3("🔥 Strategy Heatmap", className="section-title"),
                            dcc.Graph(id='strategy-heatmap', 
                                     config={'displayModeBar': False},
                                     style={'height': '400px'})
                        ], className="card-custom")
                    ], md=6),
                    
                    dbc.Col([
                        html.Div([
                            html.H3("⚙️ Module Analysis", className="section-title"),
                            dcc.Graph(id='module-performance', 
                                     config={'displayModeBar': False},
                                     style={'height': '400px'})
                        ], className="card-custom")
                    ], md=6)
                ]),
                
                # トレード詳細分析セクション
                html.Div([
                    html.H3("🔍 Trade Analysis", className="section-title"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Strategy to Analyze", style={'color': '#00d4aa', 'font-weight': 'bold', 'margin-bottom': '0.5rem'}),
                            dcc.Dropdown(
                                id='analysis-selector',
                                options=self.get_trade_analysis_options(),
                                placeholder="Select a strategy to view detailed analysis",
                                style={'backgroundColor': '#2d3748', 'color': '#000000'},
                                className='mb-3'
                            )
                        ], md=6),
                        dbc.Col([
                            html.Div([
                                dbc.Button(
                                    "📊 View Chart", 
                                    id="view-chart-btn", 
                                    color="info", 
                                    className="me-2",
                                    disabled=True
                                ),
                                dbc.Button(
                                    "📄 Download Data", 
                                    id="download-data-btn", 
                                    color="success",
                                    disabled=True
                                ),
                            ], style={'margin-top': '1.8rem'})
                        ], md=6)
                    ]),
                    html.Div(id='analysis-info', className='mt-3')
                ], className="card-custom"),

                # データテーブル
                html.Div([
                    html.H3("📋 Detailed Results", className="section-title"),
                    html.Div(id='results-table-container')
                ], className="card-custom")
                
            ], fluid=True, className="main-container")
        ])
    
    def create_metric_cards(self, filtered_df):
        """メトリクスカードを生成"""
        if len(filtered_df) == 0:
            return html.Div("No data available", style={'text-align': 'center', 'color': 'rgba(255,255,255,0.7)'})
        
        metrics = [
            {
                'title': 'Total Strategies',
                'value': f"{len(filtered_df)}",
                'icon': '📈',
                'color': 'linear-gradient(45deg, #667eea, #764ba2)',
                'subtitle': 'Tested'
            },
            {
                'title': 'Avg Sharpe',
                'value': f"{filtered_df['sharpe_ratio'].mean():.2f}",
                'icon': '⭐',
                'color': 'linear-gradient(45deg, #f093fb, #f5576c)',
                'subtitle': 'Performance'
            },
            {
                'title': 'Best Sharpe',
                'value': f"{filtered_df['sharpe_ratio'].max():.2f}",
                'icon': '🚀',
                'color': 'linear-gradient(45deg, #4facfe, #00f2fe)',
                'subtitle': 'Peak'
            },
            {
                'title': 'Avg Win Rate',
                'value': f"{filtered_df['win_rate'].mean():.0%}",
                'icon': '🎯',
                'color': 'linear-gradient(45deg, #43e97b, #38f9d7)',
                'subtitle': 'Success'
            },
            {
                'title': 'Avg Return',
                'value': f"{filtered_df['total_return'].mean():.1%}",
                'icon': '💰',
                'color': 'linear-gradient(45deg, #fa709a, #fee140)',
                'subtitle': 'Profit'
            },
            {
                'title': 'Avg Leverage',
                'value': f"{filtered_df['avg_leverage'].mean():.1f}x",
                'icon': '⚡',
                'color': 'linear-gradient(45deg, #a8edea, #fed6e3)',
                'subtitle': 'Multiplier'
            }
        ]
        
        cards = []
        for metric in metrics:
            card = html.Div([
                html.Div([
                    html.Div(metric['icon'], style={'font-size': '2.5rem', 'margin-bottom': '0.5rem'}),
                    html.Div(metric['value'], style={'font-size': '2.2rem', 'font-weight': 'bold', 'color': '#ffffff'}),
                    html.Div(metric['title'], style={'font-size': '0.9rem', 'color': 'rgba(255, 255, 255, 0.8)', 'text-transform': 'uppercase', 'font-weight': '500'}),
                    html.Div(metric['subtitle'], style={'font-size': '0.7rem', 'color': 'rgba(255, 255, 255, 0.6)', 'margin-top': '0.2rem'})
                ], style={
                    'background': metric['color'],
                    'border-radius': '16px',
                    'padding': '1.5rem',
                    'text-align': 'center',
                    'box-shadow': '0 8px 32px rgba(0, 0, 0, 0.3)',
                    'height': '160px',
                    'display': 'flex',
                    'flex-direction': 'column',
                    'justify-content': 'center',
                    'transition': 'transform 0.2s ease',
                })
            ])
            cards.append(dbc.Col(card, md=2, className='mb-3'))
        
        return dbc.Row(cards)
    
    def load_trade_analyses(self):
        """トレード分析データを読み込み"""
        self.trade_analyses = []
        analysis_dir = "trade_analysis"
        
        if os.path.exists(f"{analysis_dir}/analysis_index.json"):
            try:
                with open(f"{analysis_dir}/analysis_index.json", 'r') as f:
                    self.trade_analyses = json.load(f)
                print(f"トレード分析データ読み込み完了: {len(self.trade_analyses)}件")
            except Exception as e:
                print(f"トレード分析データ読み込みエラー: {e}")
                self.trade_analyses = []
        else:
            print("トレード分析データが見つかりません")
            self.trade_analyses = []
    
    def get_trade_analysis_options(self):
        """トレード分析の選択肢を生成"""
        if not self.trade_analyses:
            return []
        
        options = []
        for analysis in self.trade_analyses:
            label = f"{analysis['symbol']} ({analysis['timeframe']}) - {analysis['config']}"
            value = f"{analysis['symbol']}_{analysis['timeframe']}_{analysis['config']}"
            options.append({'label': label, 'value': value})
        
        return options
    
    def setup_callbacks(self):
        @self.app.callback(
            [Output('metrics-cards', 'children'),
             Output('performance-overview', 'figure'),
             Output('top-performers', 'children'),
             Output('strategy-heatmap', 'figure'),
             Output('module-performance', 'figure'),
             Output('results-table-container', 'children')],
            [Input('symbol-filter', 'value'),
             Input('timeframe-filter', 'value'),
             Input('config-filter', 'value'),
             Input('sharpe-filter', 'value'),
             Input('winrate-filter', 'value')]
        )
        def update_dashboard(symbol, timeframe, config, min_sharpe, winrate_range):
            # データフィルタリング
            filtered_df = self.df.copy()
            
            if symbol != 'all':
                filtered_df = filtered_df[filtered_df['symbol'] == symbol]
            if timeframe != 'all':
                filtered_df = filtered_df[filtered_df['timeframe'] == timeframe]
            if config != 'all':
                filtered_df = filtered_df[filtered_df['module_config'] == config]
                
            filtered_df = filtered_df[filtered_df['sharpe_ratio'] >= min_sharpe]
            filtered_df = filtered_df[
                (filtered_df['win_rate'] >= winrate_range[0]) & 
                (filtered_df['win_rate'] <= winrate_range[1])
            ]
            
            # メトリクスカード
            metrics_cards = self.create_metric_cards(filtered_df)
            
            # パフォーマンス概要チャート
            if len(filtered_df) > 0:
                performance_fig = px.scatter(
                    filtered_df,
                    x='sharpe_ratio',
                    y='total_return',
                    color='module_config',
                    size='win_rate',
                    hover_data=['symbol', 'timeframe', 'avg_leverage'],
                    title="Risk-Return Profile",
                    template='plotly_dark'
                )
                performance_fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
            else:
                performance_fig = go.Figure()
                performance_fig.update_layout(
                    title="No data to display",
                    template='plotly_dark',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
            
            # トップパフォーマー
            if len(filtered_df) > 0:
                top_10 = filtered_df.nlargest(10, 'sharpe_ratio')
                top_performers_children = []
                
                for i, (_, row) in enumerate(top_10.iterrows()):
                    item = html.Div([
                        html.Div([
                            html.Span(f"#{i+1}", style={'color': '#00d4aa', 'font-weight': 'bold', 'margin-right': '0.5rem'}),
                            html.Span(f"{row['symbol']} ({row['timeframe']})", style={'font-weight': 'bold'}),
                        ], style={'margin-bottom': '0.3rem'}),
                        html.Div([
                            html.Span(f"Sharpe: {row['sharpe_ratio']:.2f}", style={'margin-right': '1rem', 'color': '#4facfe'}),
                            html.Span(f"Win: {row['win_rate']:.0%}", style={'color': '#43e97b'})
                        ], style={'font-size': '0.9rem', 'color': 'rgba(255,255,255,0.8)'}),
                        html.Div(row['module_config'], style={'font-size': '0.8rem', 'color': 'rgba(255,255,255,0.6)', 'margin-top': '0.2rem'})
                    ], className='top-performer-item')
                    top_performers_children.append(item)
            else:
                top_performers_children = [html.Div("No data available", style={'text-align': 'center', 'color': 'rgba(255,255,255,0.7)'})]
            
            # ストラテジーヒートマップ
            if len(filtered_df) > 0:
                pivot_table = filtered_df.pivot_table(
                    values='sharpe_ratio',
                    index='symbol',
                    columns='timeframe',
                    aggfunc='max'
                )
                heatmap_fig = px.imshow(
                    pivot_table,
                    labels=dict(x="Timeframe", y="Symbol", color="Max Sharpe"),
                    title="Best Performance by Symbol × Timeframe",
                    template='plotly_dark',
                    color_continuous_scale='Viridis'
                )
                heatmap_fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
            else:
                heatmap_fig = go.Figure()
                heatmap_fig.update_layout(
                    title="No data to display",
                    template='plotly_dark',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
            
            # モジュール分析
            if len(filtered_df) > 0:
                module_stats = filtered_df.groupby('leverage_calculator')['sharpe_ratio'].agg(['mean', 'std', 'count']).reset_index()
                module_fig = px.bar(
                    module_stats,
                    x='leverage_calculator',
                    y='mean',
                    error_y='std',
                    title="Performance by Leverage Calculator",
                    template='plotly_dark'
                )
                module_fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    xaxis_tickangle=-45
                )
            else:
                module_fig = go.Figure()
                module_fig.update_layout(
                    title="No data to display",
                    template='plotly_dark',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
            
            # 結果テーブル
            if len(filtered_df) > 0:
                display_cols = ['symbol', 'timeframe', 'module_config', 'sharpe_ratio', 'total_return', 'win_rate', 'avg_leverage', 'max_drawdown']
                table_data = filtered_df[display_cols].round(3)
                
                results_table = dash_table.DataTable(
                    data=table_data.to_dict('records'),
                    columns=[
                        {"name": col.replace('_', ' ').title(), "id": col, 
                         "type": "numeric" if col in ['sharpe_ratio', 'total_return', 'win_rate', 'avg_leverage', 'max_drawdown'] else "text",
                         "format": {"specifier": ".2%"} if col in ['total_return', 'win_rate', 'max_drawdown'] else {"specifier": ".2f"} if col in ['sharpe_ratio', 'avg_leverage'] else None}
                        for col in display_cols
                    ],
                    sort_action="native",
                    filter_action="native",
                    page_size=15,
                    style_cell={
                        'textAlign': 'center',
                        'backgroundColor': 'rgba(255, 255, 255, 0.05)',
                        'color': 'white',
                        'border': '1px solid rgba(255, 255, 255, 0.1)'
                    },
                    style_header={
                        'backgroundColor': 'rgba(0, 212, 170, 0.2)',
                        'fontWeight': 'bold',
                        'color': '#00d4aa'
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{sharpe_ratio} > 2', 'column_id': 'sharpe_ratio'},
                            'backgroundColor': 'rgba(67, 233, 123, 0.3)',
                            'color': 'white',
                        },
                        {
                            'if': {'filter_query': '{sharpe_ratio} < 1', 'column_id': 'sharpe_ratio'},
                            'backgroundColor': 'rgba(245, 87, 108, 0.3)',
                            'color': 'white',
                        }
                    ]
                )
            else:
                results_table = html.Div("No data available", style={'text-align': 'center', 'color': 'rgba(255,255,255,0.7)'})
            
            return (metrics_cards, performance_fig, top_performers_children, 
                   heatmap_fig, module_fig, results_table)
        
        @self.app.callback(
            [Output('view-chart-btn', 'disabled'),
             Output('download-data-btn', 'disabled'),
             Output('analysis-info', 'children')],
            [Input('analysis-selector', 'value')]
        )
        def update_analysis_controls(selected_analysis):
            if not selected_analysis:
                return True, True, ""
            
            # 選択された分析の詳細情報を取得
            analysis_data = None
            for analysis in self.trade_analyses:
                analysis_key = f"{analysis['symbol']}_{analysis['timeframe']}_{analysis['config']}"
                if analysis_key == selected_analysis:
                    analysis_data = analysis
                    break
            
            if not analysis_data:
                return True, True, html.Div("Analysis data not found", style={'color': 'red'})
            
            # 情報表示
            info_content = dbc.Card([
                dbc.CardBody([
                    html.H5(f"{analysis_data['symbol']} ({analysis_data['timeframe']}) - {analysis_data['config']}", 
                           className="card-title", style={'color': '#00d4aa'}),
                    dbc.Row([
                        dbc.Col([
                            html.P([
                                html.Strong("Total Trades: "), f"{analysis_data['total_trades']}"
                            ], className="mb-1"),
                            html.P([
                                html.Strong("Win Rate: "), f"{analysis_data['win_rate']:.1f}%"
                            ], className="mb-1"),
                        ], md=6),
                        dbc.Col([
                            html.P([
                                html.Strong("Total Return: "), f"{analysis_data['total_return']:.1f}%"
                            ], className="mb-1"),
                            html.P([
                                html.Strong("Avg Leverage: "), f"{analysis_data['avg_leverage']:.1f}x"
                            ], className="mb-1"),
                        ], md=6)
                    ]),
                    html.P([
                        html.Strong("Generated: "), 
                        analysis_data['generated_at'][:19].replace('T', ' ')
                    ], className="mb-0", style={'font-size': '0.9rem', 'color': 'rgba(255,255,255,0.7)'})
                ])
            ], style={'background': 'rgba(255, 255, 255, 0.05)', 'border': '1px solid rgba(255, 255, 255, 0.1)'})
            
            return False, False, info_content
        
        # Store for selected analysis
        self.app.layout.children.append(dcc.Store(id='selected-analysis-store'))
        
        @self.app.callback(
            Output('selected-analysis-store', 'data'),
            [Input('analysis-selector', 'value')]
        )
        def store_selected_analysis(value):
            return value
        
        @self.app.callback(
            Output('view-chart-btn', 'children'),
            [Input('view-chart-btn', 'n_clicks'),
             Input('selected-analysis-store', 'data')],
            prevent_initial_call=True
        )
        def handle_view_chart(n_clicks, selected_analysis):
            if n_clicks and selected_analysis:
                # Find the chart path
                chart_path = None
                for analysis in self.trade_analyses:
                    analysis_key = f"{analysis['symbol']}_{analysis['timeframe']}_{analysis['config']}"
                    if analysis_key == selected_analysis:
                        chart_path = analysis['chart_path']
                        break
                
                if chart_path and os.path.exists(chart_path):
                    # Convert to absolute path and open in browser
                    abs_path = os.path.abspath(chart_path)
                    webbrowser.open(f"file://{abs_path}")
                    return "📊 Chart Opened!"
                else:
                    return "❌ Chart not found"
            
            return "📊 View Chart"
    
    def run(self, host='127.0.0.1', port=8050, debug=False):
        """ダッシュボードを起動"""
        print(f"🚀 ダッシュボードを起動中...")
        print(f"📊 URL: http://{host}:{port}")
        print(f"💡 ブラウザで上記URLを開いてください")
        self.app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    dashboard = ModernBacktestDashboard(results_dir="results")
    dashboard.run(debug=True)