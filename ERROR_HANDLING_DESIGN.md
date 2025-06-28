# エラーハンドリング設計ドキュメント

## 概要
Long Traderシステムにおけるエラーハンドリングの設計方針と実装ガイドライン

## 設計原則

### 1. Fail-Fast原則
- エラーが発生したら即座に例外を発生させる
- エラーを無視して処理を継続しない
- 1つでもエラーがあれば全体を停止

### 2. 詳細なエラー情報の保持
- エラータイプを明確に分類
- 詳細なエラーメッセージを切り詰めない
- スタックトレースを含める

### 3. 段階的エラー処理
- 各処理段階で適切なエラータイプを使用
- エラー情報が上位層で失われないように設計

## カスタムエラータイプ

### 1. InsufficientMarketDataError
**場所**: `engines/leverage_decision_engine.py`

**用途**: 市場データ不足による分析失敗

**属性**:
- `error_type`: エラーの種類（例: "support_detection_failed"）
- `missing_data`: 不足しているデータ（例: "support_levels"）

**発生例**:
```python
if not support_levels:
    raise InsufficientMarketDataError(
        message="サポートレベルが検出できませんでした",
        error_type="support_detection_failed",
        missing_data="support_levels"
    )
```

### 2. InsufficientConfigurationError
**場所**: `engines/leverage_decision_engine.py`

**用途**: 設定不足による分析失敗

**属性**:
- `error_type`: エラーの種類（例: "config_manager_init_failed"）
- `missing_config`: 不足している設定（例: "LeverageConfigManager"）

**発生例**:
```python
if config_manager is None:
    raise InsufficientConfigurationError(
        message="レバレッジエンジン設定管理システムの初期化に失敗",
        error_type="config_manager_init_failed",
        missing_config="LeverageConfigManager"
    )
```

### 3. LeverageAnalysisError
**場所**: `engines/leverage_decision_engine.py`

**用途**: レバレッジ分析処理の失敗

**属性**:
- `error_type`: エラーの種類（例: "leverage_calculation_failed"）
- `analysis_stage`: 分析段階（例: "comprehensive_analysis"）

**発生例**:
```python
raise LeverageAnalysisError(
    message="レバレッジ分析処理で致命的エラー",
    error_type="leverage_calculation_failed",
    analysis_stage="comprehensive_analysis"
)
```

### 4. ValidationError
**場所**: `interfaces/data_types.py`

**用途**: データ検証エラー

**発生例**:
```python
if level.strength < 0.0 or level.strength > 1.0:
    raise ValidationError(f"強度は0.0-1.0の範囲である必要があります: {level.strength}")
```

### 5. CriticalAnalysisError
**場所**: `engines/stop_loss_take_profit_calculators.py`

**用途**: 重要な分析データが不足している場合

**発生例**:
```python
if not support_levels and not resistance_levels:
    raise CriticalAnalysisError("損切り・利確計算に必要なサポレジデータがありません")
```

### 6. SymbolError系
**場所**: `hyperliquid_validator.py`

**用途**: 銘柄関連のエラー

**種類**:
- `SymbolError`: 基底クラス
- `InvalidSymbolError`: 存在しない銘柄

## エラーハンドリングのベストプラクティス

### 1. エラーメッセージの記録
```python
try:
    # 処理
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    
    # 詳細なエラーログ（切り詰めなし）
    self.logger.error(f"❌ {process_name}: エラー発生 ({error_type})")
    self.logger.error(f"   エラー詳細: {error_msg}")
    
    # DBには拡張形式で保存
    db_error_msg = f"[{error_type}] {error_msg}"[:1000]
```

### 2. エラーの再スロー
```python
try:
    # ML予測処理
except Exception as e:
    if "特定のパターン" in str(e):
        # 特定のエラーは詳細情報を追加して再スロー
        raise Exception(f"ML予測システムでエラー: {str(e)}")
    else:
        # その他は致命的エラーとして処理
        raise Exception(f"予期しないエラー: {str(e)}")
```

### 3. 段階別エラー追跡
```python
prediction_errors = []

for level in levels:
    try:
        # 各レベルの処理
    except Exception as e:
        error_info = {
            'level_price': level.price,
            'error_type': type(e).__name__,
            'error_message': str(e)
        }
        prediction_errors.append(error_info)

# エラーがあれば例外発生
if prediction_errors:
    detailed_errors = [f"{err['level_price']}: {err['error_type']}" for err in prediction_errors]
    raise Exception(f"処理エラー: {', '.join(detailed_errors)}")
```

## データベースでのエラー記録

### analysesテーブル
- `error_message`: TEXT型（最大1000文字）
- 形式: `[エラータイプ] 詳細メッセージ`

### execution_logsテーブル
- `current_operation`: TEXT型（最大250文字）
- 形式: `[エラータイプ] 詳細メッセージ`

## トラブルシューティング

### エラー発生時の調査手順

1. **エラータイプの確認**
   ```sql
   SELECT error_message FROM analyses 
   WHERE error_message IS NOT NULL 
   ORDER BY task_created_at DESC LIMIT 10;
   ```

2. **エラータイプ別の集計**
   ```sql
   SELECT 
     SUBSTR(error_message, 2, INSTR(error_message, ']') - 2) as error_type,
     COUNT(*) as count
   FROM analyses 
   WHERE error_message IS NOT NULL 
   GROUP BY error_type;
   ```

3. **詳細ログの確認**
   - ログファイルで`❌`マークを検索
   - エラータイプと詳細メッセージを確認

## 今後の改善提案

1. **構造化エラーログ**
   - JSON形式でエラー情報を保存
   - エラー分析の自動化

2. **エラー監視ダッシュボード**
   - リアルタイムエラー表示
   - エラータイプ別の統計

3. **自動リトライシステム**
   - 一時的なエラーの自動再試行
   - エラータイプに応じたリトライ戦略

## 更新履歴
- 2025-06-28: 初版作成
- エラーハンドリングの全面改善実施
- Fail-Fast原則の採用