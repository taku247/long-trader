# EarlyFail データベース接続性チェック実装

## 実装日時
2025年6月22日

## 概要
EarlyFailシステムにデータベース接続性チェック機能を追加。
銘柄追加時に重いマルチプロセス処理を実行する前に、必須データベースの接続可能性を軽量チェックすることで、システムの安定性向上を図る。

## 背景・課題
- 過去にマルチプロセス環境でのDB参照エラーが発生（"no such table: execution_logs" など）
- 重い分析処理を開始した後でDBエラーが発生すると、リソースの無駄と時間の浪費が生じる
- 早期段階でのシステムヘルスチェックが不足していた

## 実装内容

### 1. FailReasonに新項目追加
```python
class FailReason(Enum):
    # 既存項目...
    DATABASE_CONNECTION_FAILED = "database_connection_failed"
```

### 2. 新検証メソッド `_check_database_connectivity()` を実装
**位置**: 検証順序3番目（軽量検証として早期実行）

**チェック内容**:
- execution_logs.db の存在・接続・テーブル確認
- large_scale_analysis/analysis.db の存在・接続・テーブル確認
- 各DBに対する簡単なクエリテスト（COUNT文）

**パス検索ロジック**:
```python
db_candidates = {
    'execution_logs': [
        'execution_logs.db',
        '../execution_logs.db', 
        Path(parent_dir) / 'execution_logs.db'
    ],
    'analysis': [
        'large_scale_analysis/analysis.db',
        '../large_scale_analysis/analysis.db',
        Path(parent_dir) / 'large_scale_analysis' / 'analysis.db'
    ]
}
```

### 3. 設定ファイル対応
```json
{
    "enable_database_connectivity_check": true
}
```

### 4. 検証順序の更新
1. シンボル存在チェック
2. 取引所サポートチェック
3. **データベース接続性チェック** ← 新規追加
4. API接続タイムアウト
5. 取引所アクティブ状態
6. システムリソース
7. データ品質
8. 履歴データ可用性
9. カスタム検証ルール

### 5. 成功ログの更新
- 検証項目数: 8項目 → 9項目
- ログメッセージに「DB接続」を追加
- システム通知の更新

## エラーハンドリング

### ファイル不存在エラー
```python
return EarlyFailResult(
    symbol=symbol,
    passed=False,
    fail_reason=FailReason.DATABASE_CONNECTION_FAILED,
    error_message=f"必須データベース '{db_name}.db' が見つかりません",
    suggestion="システム管理者にお問い合わせください"
)
```

### SQLiteエラー
```python
return EarlyFailResult(
    symbol=symbol,
    passed=False,
    fail_reason=FailReason.DATABASE_CONNECTION_FAILED,
    error_message=f"データベース '{db_name}' の接続/クエリに失敗: {str(db_error)}",
    suggestion="データベースファイルの整合性を確認してください"
)
```

## 成功時の返却データ
```python
{
    "database_status": {
        "execution_logs": {
            "status": "connected",
            "records": 25,
            "path": "/path/to/execution_logs.db"
        },
        "analysis": {
            "status": "connected", 
            "records": 180,
            "path": "/path/to/large_scale_analysis/analysis.db"
        }
    },
    "check_type": "connectivity_and_table_access"
}
```

## 効果
1. **早期エラー検出**: 重い処理実行前にDBエラーを発見
2. **システム安定性向上**: マルチプロセス実行前の環境確認
3. **デバッグ効率化**: DB接続問題の迅速な特定
4. **リソース保護**: 無駄な重い処理の回避

## 互換性
- 既存の設定ファイルとの後方互換性を維持
- `enable_database_connectivity_check: false` で無効化可能
- 軽量チェック（通常1秒未満）のため性能への影響は軽微

## テスト方針
1. 正常ケース: 全DBが正常に接続可能
2. ファイル不存在: いずれかのDBファイルが存在しない
3. テーブル不存在: DBファイルは存在するがテーブルが不正
4. 接続エラー: ファイルが破損している場合
5. 設定無効化: チェックをスキップできること

## 実装ファイル
- `symbol_early_fail_validator.py` - メイン実装
- `early_fail_config.json` - 設定ファイル（自動生成）