# New Symbol Strategy Testing Guide

このガイドでは、新しい暗号通貨シンボルに対して既存の全戦略をテストする方法を説明します。

## 🚀 クイックスタート

### 最も簡単な方法
```bash
# 単一シンボルのテスト
python add_new_symbol.py BTC

# 複数シンボルのテスト
python add_new_symbol.py BTC ETH ADA SOL
```

これだけで、指定したシンボルに対して全ての戦略（5種類）× 全てのタイムフレーム（4種類）= 20パターンのテストが自動実行されます。

## 📊 利用可能な戦略

システムでは以下の5つの戦略が利用可能です：

1. **Conservative_ML** - 保守的ML戦略
   - リスク重視のML分析
   - 期待Sharpe比: 1.2
   - 最大レバレッジ: 3.0x

2. **Aggressive_Traditional** - アグレッシブ従来型
   - 高レバレッジ伝統的テクニカル分析
   - 期待Sharpe比: 1.8
   - 最大レバレッジ: 8.0x

3. **Full_ML** - フルML戦略
   - 全コンポーネントML化
   - 期待Sharpe比: 2.1
   - 最大レバレッジ: 6.0x

4. **Hybrid_Strategy** - ハイブリッド戦略
   - MLと従来手法の組み合わせ
   - 期待Sharpe比: 1.5
   - 最大レバレッジ: 5.0x

5. **Risk_Optimized** - リスク最適化
   - リスク重視の保守的アプローチ
   - 期待Sharpe比: 1.0
   - 最大レバレッジ: 2.5x

## ⏰ 対応タイムフレーム

- **15m** - 15分足（短期スキャルピング）
- **1h** - 1時間足（標準デイトレード）
- **4h** - 4時間足（スイングトレード）
- **1d** - 日足（ポジショントレード）

## 🛠 詳細な使用方法

### 1. 基本的なシンボル追加とテスト

```python
# Pythonスクリプトとして使用
from new_symbol_strategy_tester import NewSymbolStrategyTester

# テスター初期化
tester = NewSymbolStrategyTester()

# 新しいシンボルで全戦略をテスト
results_df = tester.test_all_strategies_on_symbol('BTC')

# 結果をメインCSVに追加
tester.update_main_results_csv(results_df)

# サマリーレポート生成
tester.generate_summary_report('BTC', results_df)

# 推奨戦略取得
recommendations = tester.get_recommended_strategies('BTC', results_df)
```

### 2. バッチ設定生成

```python
from batch_strategy_generator import BatchStrategyGenerator

# 設定生成器初期化
generator = BatchStrategyGenerator()

# 単一シンボルの設定生成
btc_configs = generator.generate_configs_for_symbol('BTC')

# 複数シンボルの設定生成
multi_configs = generator.generate_configs_for_multiple_symbols(['BTC', 'ETH', 'ADA'])

# JSON設定ファイル保存
generator.save_configs_to_json(multi_configs, 'my_test_configs.json')
```

### 3. スケーラブルシステムとの統合

```python
from scalable_analysis_system import ScalableAnalysisSystem

# 大規模分析システム使用
system = ScalableAnalysisSystem()

# バッチ設定準備
batch_configs = [
    {'symbol': 'BTC', 'timeframe': '1h', 'config': 'Full_ML'},
    {'symbol': 'BTC', 'timeframe': '4h', 'config': 'Conservative_ML'},
    # ... 他の設定
]

# 並列バッチ分析実行
processed = system.generate_batch_analysis(batch_configs, max_workers=4)

# 結果クエリ
results = system.query_analyses(
    filters={'symbol': ['BTC'], 'min_sharpe': 1.5},
    order_by='sharpe_ratio',
    limit=10
)
```

## 📁 生成されるファイル

### 1. メイン結果ファイル
- `results/backtest_results_summary.csv` - 全戦略の結果サマリー

### 2. 詳細トレードファイル
- `results/trades/{SYMBOL}_{TIMEFRAME}_{STRATEGY}_trades.csv`
- 例: `results/trades/BTC_1h_Full_ML_trades.csv`

### 3. レポートファイル
- `{SYMBOL}_strategy_test_report.txt`
- 例: `BTC_strategy_test_report.txt`

### 4. 設定ファイル（オプション）
- `new_symbols_configs.json` - バッチ設定
- `strategy_{SYMBOL}_{TIMEFRAME}_{STRATEGY}.json` - 個別戦略設定

## 📈 結果の分析

### ダッシュボードでの確認
```bash
python dashboard.py
```
ブラウザで http://127.0.0.1:8050 にアクセス

### 戦略再現システム
```bash
python strategy_reproducer.py
```
高パフォーマンス戦略の詳細設定をエクスポート

### 実市場統合分析
```bash
python real_market_integration.py
```
実際の市場データとの統合分析

## 🎯 推奨ワークフロー

### 新しいシンボルを追加する場合：

1. **クイックテスト**
   ```bash
   python add_new_symbol.py YOUR_SYMBOL
   ```

2. **結果確認**
   ```bash
   python dashboard.py
   ```

3. **詳細分析**
   - ダッシュボードで各戦略のパフォーマンスを確認
   - 高Sharpe比戦略の詳細をチェック
   - タイムフレーム別の最適戦略を特定

4. **戦略選択と実装**
   ```bash
   python strategy_reproducer.py
   ```
   - 最良の戦略設定をエクスポート
   - 実装用スクリプト生成

### 複数シンボルの一括テスト：

```bash
# メジャー暗号通貨
python add_new_symbol.py BTC ETH BNB XRP ADA DOGE

# DeFiトークン
python add_new_symbol.py UNI AAVE COMP SUSHI CRV

# Layer 2トークン
python add_new_symbol.py MATIC ARB OP IMX LRC
```

## 🔧 カスタマイズ

### 新しい戦略の追加

`new_symbol_strategy_tester.py` の `existing_strategies` に新しい戦略を追加：

```python
self.existing_strategies = {
    'configs': [
        'Conservative_ML',
        'Aggressive_Traditional', 
        'Full_ML',
        'Hybrid_Strategy',
        'Risk_Optimized',
        'Your_New_Strategy'  # 新しい戦略を追加
    ],
    'config_details': {
        'Your_New_Strategy': {
            'description': 'Your strategy description',
            'expected_sharpe': 1.5,
            'expected_win_rate': 0.60,
            'max_leverage': 4.0,
            'risk_tolerance': 0.025
        }
    }
}
```

### パフォーマンス調整

シンボル固有の特性を調整：

```python
def _get_symbol_performance_multiplier(self, symbol):
    symbol_characteristics = {
        'BTC': 1.1,    # 安定
        'ETH': 1.05,   # 大型アルト
        'YOUR_TOKEN': 1.2,  # カスタム設定
    }
    return symbol_characteristics.get(symbol, 1.0)
```

## 📚 関連ファイル

- `new_symbol_strategy_tester.py` - メインのテストシステム
- `batch_strategy_generator.py` - バッチ設定生成
- `add_new_symbol.py` - ワンコマンドツール
- `scalable_analysis_system.py` - 大規模分析システム
- `strategy_reproducer.py` - 戦略再現ツール
- `dashboard.py` - 結果可視化ダッシュボード

## ⚠️ 注意事項

1. **データの性質**: 現在のシステムはシミュレーションベース
2. **実市場データ**: 実際の取引前には実市場データでの検証が必要
3. **リスク管理**: 高レバレッジ戦略は慎重に評価
4. **パフォーマンス**: 大量のシンボルテスト時はシステムリソースに注意

## 🚀 次のステップ

1. **実市場データ統合**: OHLCVデータの実装
2. **ライブトレーディング**: 実際の取引システムとの連携
3. **高度な分析**: より詳細なリスク評価とポートフォリオ最適化
4. **監視システム**: リアルタイムパフォーマンス監視