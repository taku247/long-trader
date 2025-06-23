# データ範囲ミスマッチエラーの詳細分析

## 実装日時
2025年6月23日

## 概要
銘柄分析時に「該当ローソク足が見つかりません」エラーが発生する構造的問題の詳細分析と対応方針。

## 問題の発生状況

### エラー例（ETH分析時）
```
⚠️ 分析エラー (評価1): 実際の市場価格取得に失敗: ETH - 該当ローソク足が見つかりません: 
ETH 3m trade_time=2025-03-24 22:11:27.719775+00:00, candle_start=2025-03-24 22:09:00+00:00. 
利用可能な最初の10件: [Timestamp('2025-03-24 22:21:00+0000', tz='UTC'), ...]
```

### 問題の詳細
- **要求時刻**: 2025-03-24 22:11:27（仮想的に生成された取引時刻）
- **実データ**: 2025-03-24 22:21:00から開始（12分のギャップ）
- **結果**: 該当するローソク足が存在せずエラー

## 根本原因の分析

### 1. 時間優先設計の構造的欠陥

#### 現在の問題ある処理フロー
```python
# scalable_analysis_system.py
def _generate_real_analysis():
    # Step1: 90日前から仮想的な時刻を生成
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=90)  # 固定90日
    
    # Step2: 時間軸を機械的に進める
    current_time = start_time
    while current_time <= end_time:
        trade_time = current_time  # 仮想trade_time
        
        # Step3: この時刻でデータを探す（存在しない可能性）
        price = _get_real_market_price(trade_time)  # ← ここでエラー
        
        current_time += evaluation_interval
```

#### 正しいあるべき処理フロー
```python
# データ中心設計
def analyze_with_actual_data():
    # Step1: 実際のデータ範囲を確認
    market_data = fetch_available_data()
    
    # Step2: データの時間軸に基づいて分析
    for timestamp in market_data.index:
        analyze_at_timestamp(timestamp)  # 必ず存在するデータ
```

### 2. 誤った前提条件

#### 前提1: 全銘柄で90日分のデータ存在
- **現実**: 新規上場銘柄は30-60日のみ
- **ZORA**: 2025-06-20に同様の問題が発生済み
- **ETH**: データは存在するが完全性にギャップ

#### 前提2: 取引所APIが完全なデータを提供
- **Hyperliquid**: 30%の失敗を「正常」として設計
- **Gate.io**: レート制限によりデータ欠損が発生
- **共通**: データ保証がないにも関わらず固定期間を前提

#### 前提3: 固定間隔での評価が有効
```python
# 時間足ごとの固定間隔（データ密度無視）
default_intervals = {
    '1m': timedelta(minutes=5),
    '3m': timedelta(minutes=15),
    '30m': timedelta(hours=2),
    '1h': timedelta(hours=4)
}
```

### 3. 過去の対応履歴

#### 2025-06-20: Early Fail実装
- **問題認識**: ZORAで90日要求に対し30日データのみ
- **対応**: 事前チェック機能追加（対症療法）
- **根本解決なし**: 時間優先設計は変更せず

#### 2025-06-21: エラーハンドリング強化
- **方針**: エラー隠蔽から明示化へ
- **効果**: データ不足時にシステム停止
- **限界**: 根本的な設計は未変更

## 影響範囲

### 1. 新規上場銘柄
- データ < 90日で必ず失敗
- Early Failで事前排除されるケースが多い

### 2. 既存銘柄
- データ欠損期間でエラー発生
- 取引所メンテナンス期間
- API制限によるデータ未取得期間

### 3. パフォーマンス
- エラー処理のオーバーヘッド
- 再試行による処理遅延
- リソースの無駄な消費

## 対応方針

### A. 根本的解決（データ中心設計への移行）

#### A1. 全面的な設計変更
```python
class DataDrivenAnalysisEngine:
    async def analyze_symbol_data_driven(self, symbol, timeframe, config):
        # 1. 実データの取得と範囲確認
        market_data = await self._fetch_and_validate_market_data()
        
        # 2. データから分析ポイントを生成
        analysis_points = self._generate_analysis_points_from_data()
        
        # 3. 存在するデータのみで分析
        for timestamp, candle_data in analysis_points:
            analyze_at_timestamp(timestamp, candle_data)
```

**メリット**:
- 構造的問題の根本解決
- すべての銘柄で安定動作
- リソース効率の大幅改善

**デメリット**:
- 大規模なリファクタリング必要
- テスト工数が膨大
- 移行期間中の互換性維持

#### A2. ハイブリッド設計
```python
def adaptive_analysis_period(symbol):
    # データ可用性に応じて期間を動的調整
    data_range = get_actual_data_range(symbol)
    
    if data_range.days >= 90:
        return 90  # 通常モード
    elif data_range.days >= 30:
        return data_range.days - 5  # 短期モード
    else:
        raise EarlyFailError("データ不足")
```

### B. 中間的解決

#### B1. 事前データ範囲バリデーション
```python
def validate_and_adjust_timeline(symbol, requested_period):
    available_range = check_data_availability(symbol)
    
    if requested_period > available_range:
        adjusted_period = available_range - safety_margin
        return adjusted_period
    
    return requested_period
```

#### B2. 動的trade_time生成
```python
def generate_smart_trade_times(symbol, timeframe, evaluation_days):
    market_data = get_market_data_light(symbol, timeframe)
    available_timestamps = market_data.index
    
    optimal_interval = calculate_optimal_interval(available_timestamps)
    return generate_timeline_from_data(available_timestamps, optimal_interval)
```

### C. 部分的解決（短期対応）

#### C1. 柔軟なローソク足マッチング
```python
def flexible_market_price_lookup(trade_time, market_data, tolerance_minutes=30):
    # 完全一致を優先
    exact_match = find_exact_candle(trade_time, market_data)
    if exact_match:
        return exact_match
    
    # 許容範囲内で最近接を検索
    nearest_match = find_nearest_candle(trade_time, market_data, tolerance_minutes)
    if nearest_match:
        return nearest_match
    
    return None  # スキップ
```

## 実装優先順位

### フェーズ1: 緊急対応（1-2日）
- C1（柔軟マッチング）実装
- 現在のETH分析を完了させる

### フェーズ2: 中期対応（1週間）
- B1（事前バリデーション）実装
- Early Failシステムとの統合

### フェーズ3: 根本対応（2-3週間）
- A2（ハイブリッド設計）実装
- 段階的な移行とテスト

## 技術的詳細

### 影響を受けるファイル
1. `scalable_analysis_system.py`
   - `_generate_real_analysis()`: 時間生成ロジック
   - `_get_real_market_price()`: 価格取得処理

2. `high_leverage_bot_orchestrator.py`
   - `_fetch_market_data()`: 固定90日取得

3. `hyperliquid_api_client.py`
   - データ取得の実装（変更不要）

### 設定ファイルの見直し
- `timeframe_configs/*.json`: 期間設定の柔軟化
- `early_fail_config.json`: 検証ルールの更新

## まとめ

このデータ範囲ミスマッチエラーは、システムが「理論上の時間軸」で分析を行い、「実際のデータ制約」を後から考慮する時間優先設計に起因する構造的問題である。

根本的解決にはデータ中心設計への移行が必要だが、段階的なアプローチにより、現在の問題を解決しつつ長期的な改善を図ることが可能。

## 関連ドキュメント
- `_docs/2025-06-20_early-fail-validation-system.md`
- `_docs/2025-06-21_strategy-implementation-and-error-handling.md`