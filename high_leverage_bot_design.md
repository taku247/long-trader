# ハイレバレッジロング判定Bot設計書

## 概要
アルトコイントレードにおいて、リアルタイムで最適なレバレッジ倍率を判定するbotの設計。既存のサポート・レジスタンス分析機能を統合し、リスクリワード比に基づいた自動判定を実現。

## システム構成

### 1. リスクリワード計算エンジン (`risk_reward_calculator.py`)

#### モジュール化設計
プラグイン形式で各サブ機能を差し替え可能な設計とし、異なるアルゴリズムやML手法を試せる構造にします。

#### サブ機能モジュール

##### 1-1. 下落リスク評価モジュール (pluggable)
```python
# インターフェース定義
class DownsideRiskEvaluator(ABC):
    @abstractmethod
    def evaluate(self, current_price, support_levels, market_data):
        """リスクスコア (0-100) を返す"""
        pass

# 実装例
class SimpleDistanceRiskEvaluator(DownsideRiskEvaluator):
    """シンプルな距離ベース評価"""
    
class MLSupportStrengthEvaluator(DownsideRiskEvaluator):
    """機械学習による支持線強度予測"""
    
class MultiLayerRiskEvaluator(DownsideRiskEvaluator):
    """多層支持線を考慮したリスク評価"""
```

##### 1-2. 上昇期待値計算モジュール (pluggable)
```python
# インターフェース定義
class UpsidePotentialCalculator(ABC):
    @abstractmethod
    def calculate(self, current_price, resistance_levels, market_data):
        """期待利益率と確率を返す"""
        pass

# 実装例
class LinearProjectionCalculator(UpsidePotentialCalculator):
    """線形予測ベース"""
    
class MLBreakoutPredictor(UpsidePotentialCalculator):
    """ML突破確率予測"""
    
class MomentumBasedCalculator(UpsidePotentialCalculator):
    """モメンタム指標ベース"""
```

#### 統合クラス
```python
class RiskRewardCalculator:
    def __init__(self, 
                 downside_evaluator: DownsideRiskEvaluator,
                 upside_calculator: UpsidePotentialCalculator):
        self.downside_evaluator = downside_evaluator
        self.upside_calculator = upside_calculator
    
    def get_risk_reward_ratio(self, symbol, timeframe):
        # プラグインモジュールを使用して計算
        pass
```

### 2. BTC相関分析モジュール (`btc_correlation_analyzer.py`)

#### モジュール化設計

##### 2-1. 相関係数計算モジュール (pluggable)
```python
# インターフェース定義
class CorrelationCalculator(ABC):
    @abstractmethod
    def calculate(self, token_prices, btc_prices, **kwargs):
        """相関係数と信頼度を返す"""
        pass

# 実装例
class SimpleCorrelationCalculator(CorrelationCalculator):
    """単純相関係数"""
    
class DynamicWindowCorrelation(CorrelationCalculator):
    """動的ウィンドウ相関"""
    
class MLCorrelationPredictor(CorrelationCalculator):
    """機械学習による相関予測"""
    
class RegimeSwitchingCorrelation(CorrelationCalculator):
    """市場レジーム別相関"""
```

##### 2-2. 暴落影響分析モジュール (pluggable)
```python
# インターフェース定義
class CrashImpactAnalyzer(ABC):
    @abstractmethod
    def analyze(self, symbol, btc_crash_magnitude, historical_data):
        """予想下落率と回復時間を返す"""
        pass

# 実装例
class HistoricalPatternAnalyzer(CrashImpactAnalyzer):
    """過去パターンマッチング"""
    
class MLCrashPredictor(CrashImpactAnalyzer):
    """機械学習による暴落予測"""
    
class ElasticityBasedAnalyzer(CrashImpactAnalyzer):
    """価格弾力性ベース分析"""
```

#### 統合クラス
```python
class BTCCorrelationAnalyzer:
    def __init__(self,
                 correlation_calculator: CorrelationCalculator,
                 crash_analyzer: CrashImpactAnalyzer):
        self.correlation_calculator = correlation_calculator
        self.crash_analyzer = crash_analyzer
```

### 3. レバレッジ推奨システム (`leverage_recommendation_system.py`)

#### モジュール化設計

##### 3-1. リスク評価モジュール (pluggable)
```python
# インターフェース定義
class RiskAssessor(ABC):
    @abstractmethod
    def assess(self, market_data, support_levels, btc_correlation):
        """総合リスクスコア (0-100) を返す"""
        pass

# 実装例
class ConservativeRiskAssessor(RiskAssessor):
    """保守的リスク評価"""
    
class MLRiskPredictor(RiskAssessor):
    """機械学習リスク予測"""
    
class VaRBasedAssessor(RiskAssessor):
    """Value at Risk ベース"""
```

##### 3-2. リワード評価モジュール (pluggable)
```python
# インターフェース定義
class RewardEvaluator(ABC):
    @abstractmethod
    def evaluate(self, market_data, resistance_levels):
        """期待リワードと確率を返す"""
        pass

# 実装例
class SimpleTargetEvaluator(RewardEvaluator):
    """単純ターゲット評価"""
    
class MLProfitPredictor(RewardEvaluator):
    """機械学習利益予測"""
    
class MultiObjectiveEvaluator(RewardEvaluator):
    """多目的最適化評価"""
```

##### 3-3. レバレッジ計算モジュール (pluggable)
```python
# インターフェース定義
class LeverageCalculator(ABC):
    @abstractmethod
    def calculate(self, risk_score, reward_expectation, market_conditions):
        """推奨レバレッジを返す"""
        pass

# 実装例
class KellyLeverageCalculator(LeverageCalculator):
    """Kelly基準ベース"""
    
class FixedFractionalCalculator(LeverageCalculator):
    """固定比率法"""
    
class MLOptimalLeverage(LeverageCalculator):
    """機械学習最適化"""
    
class RiskParityCalculator(LeverageCalculator):
    """リスクパリティ法"""
```

#### 統合クラス
```python
class LeverageRecommendationSystem:
    def __init__(self,
                 risk_assessor: RiskAssessor,
                 reward_evaluator: RewardEvaluator,
                 leverage_calculator: LeverageCalculator):
        self.risk_assessor = risk_assessor
        self.reward_evaluator = reward_evaluator
        self.leverage_calculator = leverage_calculator
```

### 4. 統合メインシステム (`high_leverage_bot.py`)

#### 実行フロー
1. **データ収集**
   - OHLCV + 指標データ取得
   - BTC価格データ取得
   - サポレジレベル更新

2. **分析実行**
   - リスクリワード計算
   - BTC相関分析
   - ML予測実行

3. **判定・推奨**
   - 最適レバレッジ計算
   - リスク警告表示
   - エントリー/エグジット推奨

4. **モニタリング**
   - ポジション追跡
   - 動的ストップロス調整
   - 利確レベル管理

## モジュール構成まとめ

### 3つのコア機能と7つのサブ機能

1. **リスクリワード計算エンジン**
   - 下落リスク評価モジュール
   - 上昇期待値計算モジュール

2. **BTC相関分析モジュール**
   - 相関係数計算モジュール
   - 暴落影響分析モジュール

3. **レバレッジ推奨システム**
   - リスク評価モジュール
   - リワード評価モジュール
   - レバレッジ計算モジュール

### プラグイン設定ファイル例
```yaml
# config/module_config.yaml
risk_reward_engine:
  downside_evaluator: "MLSupportStrengthEvaluator"
  upside_calculator: "MLBreakoutPredictor"

btc_correlation:
  correlation_calculator: "DynamicWindowCorrelation"
  crash_analyzer: "MLCrashPredictor"

leverage_system:
  risk_assessor: "MLRiskPredictor"
  reward_evaluator: "MLProfitPredictor"
  leverage_calculator: "KellyLeverageCalculator"
```

### モジュール切り替えによる実験例
```python
# 保守的設定
conservative_config = {
    "downside_evaluator": "MultiLayerRiskEvaluator",
    "leverage_calculator": "FixedFractionalCalculator"
}

# アグレッシブ設定
aggressive_config = {
    "downside_evaluator": "SimpleDistanceRiskEvaluator",
    "leverage_calculator": "MLOptimalLeverage"
}

# A/Bテスト用
test_configs = [
    {"name": "ML-based", "modules": ml_config},
    {"name": "Traditional", "modules": traditional_config}
]
```

## 既存システムとの統合

### 活用する既存機能
- `support_resistance_ml.py`: ブレイクアウト確率予測
- `support_resistance_visualizer.py`: サポレジレベル強度計算
- `ohlcv_by_claude.py`: データ取得・指標計算

### データフロー
```
[市場データ] → [サポレジ検出] → [ML予測] → [リスク計算] → [レバレッジ判定]
     ↓              ↓              ↓           ↓            ↓
[BTC価格] → [相関分析] → [市場環境] → [調整係数] → [最終推奨]
```

## 実装優先順位

### Phase 1: 基本機能
1. リスクリワード計算エンジン
2. 簡易レバレッジ判定ロジック
3. 既存システムとの統合テスト

### Phase 2: 高度化
1. BTC相関分析
2. 動的ストップロス
3. 複数時間軸分析

### Phase 3: 最適化
1. ML予測精度向上
2. バックテスト機能
3. リアルタイム監視ダッシュボード

## 設定可能パラメータ

### リスク管理
- `max_leverage`: 最大レバレッジ倍率 (デフォルト: 10x)
- `stop_loss_pct`: 損切り許容率 (デフォルト: -5%)
- `min_risk_reward`: 最小リスクリワード比 (デフォルト: 2.0)

### 市場環境
- `btc_correlation_threshold`: BTC相関警告しきい値 (デフォルト: 0.7)
- `volatility_adjustment`: ボラティリティ調整係数 (デフォルト: 0.8)
- `market_fear_multiplier`: 市場恐怖時の調整 (デフォルト: 0.5)

### ML予測
- `breakout_confidence_min`: ブレイクアウト予測最小信頼度 (デフォルト: 0.6)
- `support_strength_min`: 支持線強度最小値 (デフォルト: 50)

## 出力形式

### 推奨レバレッジ
```json
{
  "symbol": "HYPE",
  "current_price": 24.567,
  "recommended_leverage": 3.2,
  "confidence": 0.78,
  "risk_reward_ratio": 2.8,
  "nearest_support": {
    "price": 22.1,
    "distance_pct": -10.0,
    "strength": 85,
    "breakout_probability": 0.15
  },
  "nearest_resistance": {
    "price": 28.5,
    "distance_pct": 16.0,
    "breakout_probability": 0.65
  },
  "btc_correlation_risk": "medium",
  "warnings": ["high_volatility", "btc_correlation_high"]
}
```

## 大規模検証フレームワーク

### 複数銘柄・時間足・モジュール組み合わせ検証システム

#### 検証フレームワーク設計 (`backtest_framework.py`)
```python
class BacktestFramework:
    def __init__(self, data_manager, module_factory):
        self.data_manager = data_manager
        self.module_factory = module_factory
        self.results_db = ResultsDatabase()
    
    def run_grid_search(self, config):
        """
        グリッドサーチによる全組み合わせ検証
        """
        symbols = config['symbols']  # ['HYPE', 'SOL', 'PEPE', ...]
        timeframes = config['timeframes']  # ['15m', '1h', '4h', '1d']
        module_combinations = config['module_combinations']
        
        for symbol in symbols:
            for timeframe in timeframes:
                for modules in module_combinations:
                    result = self.run_single_backtest(
                        symbol, timeframe, modules
                    )
                    self.results_db.store(result)
    
    def run_parallel_backtests(self, test_configs):
        """
        並列実行による高速検証
        """
        with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
            futures = []
            for config in test_configs:
                future = executor.submit(self.run_single_backtest, **config)
                futures.append(future)
            
            results = [future.result() for future in futures]
        return results
```

#### モジュール組み合わせ設定例
```yaml
# config/grid_search_config.yaml
symbols:
  - HYPE
  - SOL
  - PEPE
  - WIF
  - BONK

timeframes:
  - 15m
  - 1h
  - 4h
  - 1d

module_combinations:
  - name: "Conservative_ML"
    modules:
      downside_evaluator: "MultiLayerRiskEvaluator"
      upside_calculator: "MLBreakoutPredictor"
      correlation_calculator: "DynamicWindowCorrelation"
      crash_analyzer: "HistoricalPatternAnalyzer"
      risk_assessor: "ConservativeRiskAssessor"
      reward_evaluator: "MLProfitPredictor"
      leverage_calculator: "FixedFractionalCalculator"
  
  - name: "Aggressive_Traditional"
    modules:
      downside_evaluator: "SimpleDistanceRiskEvaluator"
      upside_calculator: "LinearProjectionCalculator"
      correlation_calculator: "SimpleCorrelationCalculator"
      crash_analyzer: "ElasticityBasedAnalyzer"
      risk_assessor: "MLRiskPredictor"
      reward_evaluator: "SimpleTargetEvaluator"
      leverage_calculator: "KellyLeverageCalculator"
  
  - name: "Full_ML"
    modules:
      downside_evaluator: "MLSupportStrengthEvaluator"
      upside_calculator: "MLBreakoutPredictor"
      correlation_calculator: "MLCorrelationPredictor"
      crash_analyzer: "MLCrashPredictor"
      risk_assessor: "MLRiskPredictor"
      reward_evaluator: "MLProfitPredictor"
      leverage_calculator: "MLOptimalLeverage"
```

#### 検証結果分析システム
```python
class ResultsAnalyzer:
    def analyze_results(self, results_db):
        """
        検証結果の統計分析
        """
        # 最高性能の組み合わせ
        best_combinations = self.find_best_performers(
            metric='sharpe_ratio',
            min_trades=100
        )
        
        # 銘柄別最適設定
        symbol_optimal_configs = self.find_optimal_by_symbol()
        
        # 時間足別最適設定
        timeframe_optimal_configs = self.find_optimal_by_timeframe()
        
        # モジュール貢献度分析
        module_importance = self.analyze_module_contribution()
        
        return {
            'best_overall': best_combinations,
            'by_symbol': symbol_optimal_configs,
            'by_timeframe': timeframe_optimal_configs,
            'module_analysis': module_importance
        }
```

### 実装可能性評価

#### 技術的実現性: ✅ 高い
1. **データ管理**: 既存のOHLCV取得機能を拡張
2. **並列処理**: Python標準ライブラリで実装可能
3. **結果保存**: SQLiteやParquetで効率的に管理
4. **可視化**: 既存の可視化機能を活用

#### 必要リソース
- **計算時間**: 
  - 1組み合わせ: 約30秒（6ヶ月データ）
  - 5銘柄×4時間足×10組み合わせ = 200テスト
  - 並列8コア: 約25分で完了
  
- **ストレージ**:
  - 結果データ: 約1GB/1000テスト
  - 中間データ: 約5GB（キャッシュ可能）

#### 段階的実装計画
1. **Phase 1**: 単一銘柄・時間足での組み合わせ検証
2. **Phase 2**: 複数銘柄対応・並列処理
3. **Phase 3**: リアルタイム更新・継続的最適化

### 検証結果の保存と可視化

#### CSV/Parquet形式での結果保存
```python
class ResultsExporter:
    def export_to_csv(self, results_db, output_dir="results"):
        """
        検証結果をCSV形式で保存
        """
        # メイン結果ファイル
        main_results = []
        for result in results_db.get_all_results():
            main_results.append({
                'symbol': result.symbol,
                'timeframe': result.timeframe,
                'module_config': result.module_config_name,
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'avg_leverage': result.avg_leverage,
                'total_trades': result.total_trades,
                'profit_factor': result.profit_factor,
                # モジュール詳細
                'downside_evaluator': result.modules['downside_evaluator'],
                'upside_calculator': result.modules['upside_calculator'],
                'correlation_calculator': result.modules['correlation_calculator'],
                'crash_analyzer': result.modules['crash_analyzer'],
                'risk_assessor': result.modules['risk_assessor'],
                'reward_evaluator': result.modules['reward_evaluator'],
                'leverage_calculator': result.modules['leverage_calculator']
            })
        
        # CSVに保存
        pd.DataFrame(main_results).to_csv(
            f"{output_dir}/backtest_results_summary.csv", 
            index=False
        )
        
        # 詳細トレードログ（各組み合わせごと）
        for result in results_db.get_all_results():
            trades_df = pd.DataFrame(result.trades)
            filename = f"{result.symbol}_{result.timeframe}_{result.module_config_name}_trades.csv"
            trades_df.to_csv(f"{output_dir}/trades/{filename}", index=False)
```

#### モダンダッシュボードUI設計
```python
# dashboard.py - モダンなUIのスタンドアロンダッシュボード
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import os

class ModernBacktestDashboard:
    def __init__(self, results_dir="results"):
        self.results_dir = results_dir
        # ダークテーマでBootstrapを使用
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
        self.df = pd.read_csv(f"{results_dir}/backtest_results_summary.csv")
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
                    body { background-color: #0f1419; color: #ffffff; font-family: 'Inter', sans-serif; }
                    .main-container { padding: 2rem; background: linear-gradient(135deg, #1a1a2e, #16213e); min-height: 100vh; }
                    .card-custom { 
                        background: rgba(255, 255, 255, 0.05); 
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 12px;
                        backdrop-filter: blur(10px);
                        margin-bottom: 1.5rem;
                        padding: 1.5rem;
                    }
                    .metric-card {
                        background: linear-gradient(45deg, #667eea, #764ba2);
                        border-radius: 16px;
                        padding: 1.5rem;
                        margin: 0.5rem;
                        text-align: center;
                        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    }
                    .metric-value { font-size: 2.5rem; font-weight: bold; color: #ffffff; }
                    .metric-label { font-size: 0.9rem; color: rgba(255, 255, 255, 0.8); text-transform: uppercase; }
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
                            html.H1("🚀 High Leverage Bot", 
                                   style={'color': '#00d4aa', 'font-weight': 'bold', 'margin': 0}),
                            html.P("Advanced Backtest Results Dashboard", 
                                   style={'color': 'rgba(255,255,255,0.7)', 'margin': 0})
                        ], style={'text-align': 'center', 'padding': '2rem 0'})
                    ])
                ]),
                
                # フィルターセクション
                html.Div([
                    html.H3("🔍 Filters", className="section-title"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Symbol", style={'color': '#00d4aa', 'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id='symbol-filter',
                                options=[{'label': 'All Symbols', 'value': 'all'}] + 
                                        [{'label': s, 'value': s} for s in self.df['symbol'].unique()],
                                value='all',
                                style={'backgroundColor': '#2d3748', 'color': '#000000'},
                                className='mb-3'
                            )
                        ], md=3),
                        
                        dbc.Col([
                            html.Label("Timeframe", style={'color': '#00d4aa', 'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id='timeframe-filter',
                                options=[{'label': 'All Timeframes', 'value': 'all'}] + 
                                        [{'label': t, 'value': t} for t in self.df['timeframe'].unique()],
                                value='all',
                                style={'backgroundColor': '#2d3748', 'color': '#000000'},
                                className='mb-3'
                            )
                        ], md=3),
                        
                        dbc.Col([
                            html.Label("Min Sharpe Ratio", style={'color': '#00d4aa', 'font-weight': 'bold'}),
                            dcc.Slider(
                                id='sharpe-filter',
                                min=0, max=3, step=0.1, value=0,
                                marks={i: {'label': str(i), 'style': {'color': '#ffffff'}} for i in range(4)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], md=4),
                        
                        dbc.Col([
                            html.Label("Module Config", style={'color': '#00d4aa', 'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id='config-filter',
                                options=[{'label': 'All Configs', 'value': 'all'}] + 
                                        [{'label': c, 'value': c} for c in self.df['module_config'].unique()],
                                value='all',
                                style={'backgroundColor': '#2d3748', 'color': '#000000'},
                                className='mb-3'
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
                                     style={'height': '400px'})
                        ], className="card-custom")
                    ], md=8),
                    
                    dbc.Col([
                        html.Div([
                            html.H3("🎯 Top Performers", className="section-title"),
                            html.Div(id='top-performers')
                        ], className="card-custom")
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
            return html.Div("No data available", style={'text-align': 'center'})
        
        metrics = [
            {
                'title': 'Total Strategies',
                'value': len(filtered_df),
                'icon': '📈',
                'color': 'linear-gradient(45deg, #667eea, #764ba2)'
            },
            {
                'title': 'Avg Sharpe',
                'value': f"{filtered_df['sharpe_ratio'].mean():.2f}",
                'icon': '⭐',
                'color': 'linear-gradient(45deg, #f093fb, #f5576c)'
            },
            {
                'title': 'Best Sharpe',
                'value': f"{filtered_df['sharpe_ratio'].max():.2f}",
                'icon': '🚀',
                'color': 'linear-gradient(45deg, #4facfe, #00f2fe)'
            },
            {
                'title': 'Avg Win Rate',
                'value': f"{filtered_df['win_rate'].mean():.1%}",
                'icon': '🎯',
                'color': 'linear-gradient(45deg, #43e97b, #38f9d7)'
            },
            {
                'title': 'Max Drawdown',
                'value': f"{filtered_df['max_drawdown'].mean():.1%}",
                'icon': '📉',
                'color': 'linear-gradient(45deg, #fa709a, #fee140)'
            }
        ]
        
        cards = []
        for metric in metrics:
            card = html.Div([
                html.Div([
                    html.Div(metric['icon'], style={'font-size': '2rem', 'margin-bottom': '0.5rem'}),
                    html.Div(metric['value'], className='metric-value'),
                    html.Div(metric['title'], className='metric-label')
                ], style={
                    'background': metric['color'],
                    'border-radius': '16px',
                    'padding': '1.5rem',
                    'text-align': 'center',
                    'box-shadow': '0 8px 32px rgba(0, 0, 0, 0.3)',
                    'height': '140px',
                    'display': 'flex',
                    'flex-direction': 'column',
                    'justify-content': 'center'
                })
            ])
            cards.append(dbc.Col(card, md=2, className='mb-3'))
        
        return dbc.Row(cards)
```
    
    def setup_callbacks(self):
        @self.app.callback(
            [Output('metrics-summary', 'children'),
             Output('scatter-matrix', 'figure'),
             Output('results-table', 'data'),
             Output('module-analysis', 'figure'),
             Output('performance-heatmap', 'figure')],
            [Input('symbol-filter', 'value'),
             Input('timeframe-filter', 'value'),
             Input('sharpe-filter', 'value')]
        )
        def update_dashboard(symbol, timeframe, min_sharpe):
            # データフィルタリング
            filtered_df = self.df.copy()
            if symbol != 'all':
                filtered_df = filtered_df[filtered_df['symbol'] == symbol]
            if timeframe != 'all':
                filtered_df = filtered_df[filtered_df['timeframe'] == timeframe]
            filtered_df = filtered_df[filtered_df['sharpe_ratio'] >= min_sharpe]
            
            # メトリクスサマリー
            metrics = html.Div([
                html.Div([
                    html.H3(f"検証数: {len(filtered_df)}"),
                    html.H3(f"平均Sharpe: {filtered_df['sharpe_ratio'].mean():.2f}"),
                    html.H3(f"最高Sharpe: {filtered_df['sharpe_ratio'].max():.2f}"),
                    html.H3(f"平均勝率: {filtered_df['win_rate'].mean():.1%}")
                ], style={'display': 'flex', 'justifyContent': 'space-around'})
            ])
            
            # 散布図マトリックス
            scatter_fig = px.scatter_matrix(
                filtered_df,
                dimensions=['sharpe_ratio', 'total_return', 'max_drawdown', 'win_rate'],
                color='module_config',
                title="パフォーマンス指標の相関"
            )
            
            # テーブルデータ
            table_data = filtered_df.to_dict('records')
            
            # モジュール分析
            module_cols = ['downside_evaluator', 'upside_calculator', 'leverage_calculator']
            module_fig = make_subplots(rows=1, cols=3, subplot_titles=module_cols)
            
            for i, col in enumerate(module_cols):
                module_stats = filtered_df.groupby(col)['sharpe_ratio'].agg(['mean', 'std', 'count'])
                module_fig.add_trace(
                    go.Bar(x=module_stats.index, y=module_stats['mean'], 
                           error_y=dict(type='data', array=module_stats['std']),
                           name=col),
                    row=1, col=i+1
                )
            
            # パフォーマンスヒートマップ
            pivot_table = filtered_df.pivot_table(
                values='sharpe_ratio',
                index='symbol',
                columns='timeframe',
                aggfunc='max'
            )
            heatmap_fig = px.imshow(
                pivot_table,
                labels=dict(x="時間足", y="銘柄", color="Sharpe Ratio"),
                title="銘柄×時間足 最高パフォーマンス"
            )
            
            return metrics, scatter_fig, table_data, module_fig, heatmap_fig
    
    def run(self, host='127.0.0.1', port=8050, debug=False):
        """ダッシュボードを起動"""
        print(f"ダッシュボードを起動中... http://{host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)

# スタンドアロン実行スクリプト
if __name__ == "__main__":
    dashboard = BacktestDashboard(results_dir="results")
    dashboard.run(debug=True)
```

### 検証レポート出力例
```
=== Grid Search Results Summary ===
Total Combinations Tested: 200
Best Overall Configuration:
  - Symbol: HYPE
  - Timeframe: 1h
  - Modules: Conservative_ML
  - Sharpe Ratio: 2.34
  - Win Rate: 68%
  - Avg Leverage: 3.2x

Symbol-Specific Optimal Configs:
  HYPE: Full_ML (1h)
  SOL: Conservative_ML (4h)
  PEPE: Aggressive_Traditional (15m)
  
Module Performance Analysis:
  Most Impactful: MLBreakoutPredictor (+15% Sharpe)
  Least Impactful: SimpleCorrelationCalculator (+2% Sharpe)
```

### スタンドアロン実行方法
```bash
# 1. バックテスト実行（AI不要）
python run_backtest.py --config config/grid_search_config.yaml

# 2. 結果をCSVエクスポート（AI不要）
python export_results.py --output-dir results

# 3. ダッシュボード起動（AI不要）
python dashboard.py

# ブラウザでhttp://localhost:8050を開く
```

## テスト・検証戦略

### バックテスト
- 過去6ヶ月のデータで推奨レバレッジの妥当性検証
- 異なる市場環境（上昇/下降/横ばい）での性能評価
- BTC暴落時の保護効果測定

### リアルタイムテスト
- ペーパートレードでの実証
- 推奨vs実際結果の追跡
- 継続的なモデル改善

## 注意事項・リスク

### 技術的制約
- ML予測の不確実性
- データ遅延による判定ズレ
- 極端な市場状況での予測精度低下

### 金融リスク
- レバレッジ取引固有のリスク
- 流動性リスク
- システム障害時のエクスポージャー

### 免責事項
本システムは情報提供・教育目的のみで、投資助言ではありません。
実際の取引は自己責任で行ってください。