# 孤立データクリーンアップガイド

## 概要

`orphaned_data_cleanup.py` は、analysis.dbに蓄積される孤立した分析結果データを安全にクリーンアップするためのスクリプトです。

## 孤立データの種類

### 1. NULL execution_id
- execution_idがNULLの分析結果
- 古いバージョンで作成されたデータ

### 2. 空文字 execution_id
- execution_idが空文字("")の分析結果
- 設定ミスや初期化エラーによるもの

### 3. 無効 execution_id
- execution_logs.dbに存在しないexecution_idを持つ分析結果
- execution_logsが削除された後に残ったデータ

### 4. 古い孤立レコード
- 30日以上前に作成されたNULL execution_idのレコード
- 確実に不要と判断できる古いデータ

## 使用方法

### 基本的な使用方法

```bash
# 1. 分析のみ実行（安全確認）
python orphaned_data_cleanup.py --analysis-only

# 2. ドライラン実行（削除予定の確認）
python orphaned_data_cleanup.py --dry-run

# 3. 実際のクリーンアップ実行
python orphaned_data_cleanup.py
```

### オプション詳細

```bash
# 分析のみ（削除は行わない）
python orphaned_data_cleanup.py --analysis-only

# ドライラン（実際の削除は行わない）
python orphaned_data_cleanup.py --dry-run

# バックアップをスキップ（非推奨）
python orphaned_data_cleanup.py --skip-backup

# すべてのオプションを組み合わせ
python orphaned_data_cleanup.py --dry-run --analysis-only
```

## 実行手順（推奨）

### ステップ1: 現状分析
```bash
python orphaned_data_cleanup.py --analysis-only
```
**目的**: 削除対象データの確認とリスク評価

### ステップ2: ドライラン
```bash
python orphaned_data_cleanup.py --dry-run
```
**目的**: 削除処理の詳細確認（実際の削除は行わない）

### ステップ3: 実際の実行
```bash
python orphaned_data_cleanup.py
```
**目的**: 実際のクリーンアップ実行

## 安全機能

### 自動バックアップ
- 実行前に `backups/orphaned_cleanup_YYYYMMDD_HHMMSS/` にバックアップを作成
- `analysis_backup.db`: analysis.dbの完全バックアップ
- `backup_info.json`: バックアップ情報とメタデータ

### トランザクション処理
- すべての削除処理は単一のトランザクションで実行
- エラー発生時の自動ロールバック機能

### VACUUM処理
- 削除後のデータベース最適化でディスク容量を回復

## 出力例

### 分析結果の例
```
📊 孤立データ分析
----------------------------------------
📈 総分析結果: 150件
   - 有効データ: 120件
   - NULL execution_id: 20件
   - 空文字 execution_id: 5件
   - 無効 execution_id: 5件
   - 古い孤立データ(30日以上): 15件

💾 データベースサイズ: 2,450,000 bytes
💾 潜在的節約容量: 490,000 bytes (20%)
```

### クリーンアップ結果の例
```
🧹 クリーンアップ実行結果
----------------------------------------
✅ NULL execution_id レコード削除: 20件
✅ 空文字 execution_id レコード削除: 5件
✅ 無効 execution_id レコード削除: 5件
📊 総削除レコード数: 30件

実行後の状況:
  残存レコード数: 120件
  新データベースサイズ: 1,960,000 bytes
  削減サイズ: 490,000 bytes (20.0%)
```

## レポートファイル

実行後、以下のファイルが生成されます：

### cleanup_report.json
```json
{
  "timestamp": "2025-06-21T20:45:00",
  "analysis_before": {
    "total_analyses": 150,
    "null_execution_id": 20,
    "invalid_execution_id": 5
  },
  "cleanup_summary": {
    "total_deleted": 30,
    "deleted_null": 20,
    "deleted_invalid": 5
  },
  "backup_info": {
    "backup_dir": "backups/orphaned_cleanup_20250621_204500"
  }
}
```

## 定期実行の推奨

### 月次実行
```bash
# 毎月1日に分析実行
0 2 1 * * cd /path/to/long-trader && python orphaned_data_cleanup.py --analysis-only
```

### 必要に応じた実行
- 大量の銘柄追加後
- システムエラーによるデータ不整合発生時
- データベースサイズ最適化が必要な時

## 復旧手順

### バックアップからの復旧
```bash
# 1. 現在のDBを退避
mv web_dashboard/large_scale_analysis/analysis.db analysis.db.error

# 2. バックアップから復旧
cp backups/orphaned_cleanup_YYYYMMDD_HHMMSS/analysis_backup.db \
   web_dashboard/large_scale_analysis/analysis.db

# 3. 動作確認
python orphaned_data_cleanup.py --analysis-only
```

## 注意事項

### 実行前の確認事項
1. **重要プロセスの停止**: 分析実行中のプロセスがないことを確認
2. **ディスク容量**: バックアップ作成に十分な容量があることを確認
3. **権限確認**: データベースファイルへの読み書き権限を確認

### 実行タイミング
- **推奨**: システムアクティビティが低い時間帯（深夜など）
- **避ける**: 銘柄追加やバックテスト実行中

## トラブルシューティング

### よくあるエラー

#### 1. "database is locked" エラー
```bash
# 原因: 他のプロセスがDBを使用中
# 解決: 関連プロセスを停止してから再実行
```

#### 2. "permission denied" エラー
```bash
# 原因: ファイル権限の問題
# 解決: 適切な権限を設定
chmod 664 web_dashboard/large_scale_analysis/analysis.db
```

#### 3. "disk full" エラー
```bash
# 原因: ディスク容量不足
# 解決: 不要ファイルを削除してから再実行
df -h  # 容量確認
```

## 関連ファイル

- `orphaned_data_cleanup.py`: メインスクリプト
- `test_orphaned_cleanup.py`: テストスイート
- `db_integrity_utils.py`: 参照整合性チェック関数

## 更新履歴

- 2025-06-21: 初版作成
- テスト成功率: 100% (3/3テスト合格)