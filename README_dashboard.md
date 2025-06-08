# High Leverage Bot Dashboard

バックテスト結果とトレード詳細分析を統合したモダンなダッシュボードシステム

## 🚀 機能概要

### 1. バックテスト結果ダッシュボード
- **メトリクス表示**: 6つの主要指標をカード形式で表示
- **フィルタリング**: 銘柄、時間足、設定、Sharpe比、勝率で絞り込み
- **パフォーマンス分析**: リスク・リターンの散布図
- **ヒートマップ**: 銘柄×時間足の最高パフォーマンス
- **モジュール分析**: レバレッジ計算手法別の性能比較

### 2. 詳細トレード分析
- **エントリー判定理由**: 各トレードでの具体的な判定根拠
- **チャート可視化**: 支持線・抵抗線とエントリーポイントの表示
- **レバレッジ決定ロジック**: レバレッジ倍率の決定理由
- **インタラクティブチャート**: Plotlyによる高機能チャート

## 📦 セットアップ

### 必要ライブラリのインストール
```bash
pip install -r requirements.txt
```

### サンプルデータの生成
```bash
# バックテスト結果データ生成
python create_sample_data.py

# 詳細トレード分析データ生成
python trade_visualization.py
```

## 🎯 起動方法

### 完全版ダッシュボード（推奨）
```bash
python run_with_analysis.py
```

### 基本ダッシュボードのみ
```bash
python dashboard.py
```

## 📊 ダッシュボードの使い方

### 1. 基本操作
1. ブラウザで `http://127.0.0.1:8050` を開く
2. フィルターで戦略を絞り込み
3. メトリクスとチャートで性能を比較

### 2. 詳細トレード分析
1. **Trade Analysis**セクションに移動
2. ドロップダウンから分析したい戦略を選択
3. **View Chart**ボタンで詳細チャートを新しいタブで表示

### 3. 分析チャートの見方

#### メインチャート（上段）
- **白線**: 価格チャート
- **緑の破線**: 支持線（強度数値付き）
- **赤の破線**: 抵抗線（強度数値付き）
- **🔺緑**: 勝ちトレードのエントリーポイント
- **🔻赤**: 負けトレードのエントリーポイント
- **マーカーサイズ**: レバレッジ倍率に比例

#### レバレッジチャート（中段）
- **使用レバレッジの推移**
- **色**: PnLに応じた色分け（緑=利益、赤=損失）

#### 累積損益チャート（下段）
- **累積収益率の推移**
- **青色エリア**: 利益ゾーン

## 📁 ファイル構成

```
long-trader/
├── dashboard.py                 # メインダッシュボード
├── trade_visualization.py      # トレード分析システム
├── create_sample_data.py       # サンプルデータ生成
├── run_with_analysis.py        # 完全版起動スクリプト
├── requirements.txt            # 依存ライブラリ
├── results/                    # バックテスト結果
│   ├── backtest_results_summary.csv
│   └── trades/                 # 詳細トレードログ
└── trade_analysis/             # トレード分析結果
    ├── analysis_index.json     # 分析インデックス
    ├── charts/                 # HTMLチャート
    └── data/                   # 分析データ
```

## 🔍 トレード判定ロジックの詳細

### エントリー判定要素
1. **支持線分析**
   - 最寄り支持線までの距離
   - 支持線の強度（タッチ回数、反発履歴）
   - 支持線突破確率

2. **抵抗線分析**
   - 最寄り抵抗線までの距離
   - 突破期待値
   - リスクリワード比

3. **レバレッジ決定**
   - 基本レバレッジ（設定による）
   - リスク調整係数
   - 支持線の強度による調整

### 設定別ロジック
- **Conservative_ML**: 支持線強度重視（低レバレッジ）
- **Aggressive_Traditional**: リスクリワード比重視（高レバレッジ）
- **Full_ML**: 機械学習予測値重視（バランス）

## 🎨 カスタマイズ

### 新しい分析の追加
```python
from trade_visualization import TradeVisualizationSystem

visualizer = TradeVisualizationSystem()
metadata = visualizer.save_complete_analysis('SYMBOL', 'TIMEFRAME', 'CONFIG')
```

### ダッシュボードのカスタマイズ
- `dashboard.py`の`setup_layout()`でUI変更
- `create_metric_cards()`で新しいメトリクス追加
- CSSスタイルは`index_string`で変更

## 🐛 トラブルシューティング

### よくある問題

#### ダッシュボードが起動しない
```bash
# 依存ライブラリの再インストール
pip install --upgrade -r requirements.txt
```

#### データが表示されない
```bash
# サンプルデータの再生成
python create_sample_data.py
python trade_visualization.py
```

#### チャートが開かない
- ブラウザのポップアップブロッカーを無効化
- HTMLファイルの存在確認: `trade_analysis/charts/`

### デバッグモード
```python
# dashboard.py の最後の行を変更
dashboard.run(debug=True)
```

## 📈 実際のデータでの使用

### 1. 実データの準備
- `results/backtest_results_summary.csv`を実際の結果で置き換え
- 必須カラム: symbol, timeframe, module_config, sharpe_ratio, total_return, win_rate, etc.

### 2. 実トレード分析の生成
```python
# 実際のバックテスト結果からトレード分析を生成
visualizer = TradeVisualizationSystem()
metadata = visualizer.save_complete_analysis(
    symbol="ACTUAL_SYMBOL",
    timeframe="1h", 
    config_name="YOUR_CONFIG"
)
```

## 🔮 今後の拡張可能性

- **リアルタイム監視**: ライブデータでの動的更新
- **アラート機能**: 特定条件での通知
- **バックテスト自動実行**: 新データでの自動再計算
- **レポート出力**: PDF/Excel形式での結果出力
- **API連携**: 取引所APIとの直接連携

## 📞 サポート

問題や改善提案がある場合は、イシューとして報告してください。