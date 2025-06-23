# カスケード削除システムガイド

## 概要

`cascade_deletion_system.py` は、execution_logsを削除する際に関連するanalysesレコードと関連ファイルを自動的に削除するシステムです。

## 機能

### 自動削除対象
1. **execution_logs**: 指定されたexecution_id
2. **analyses**: 関連するすべての分析結果
3. **関連ファイル**: チャート、圧縮データファイル（オプション）

### 安全機能
1. **影響範囲分析**: 削除前の詳細な影響評価
2. **自動バックアップ**: 削除前の完全バックアップ
3. **ドライラン**: 実際の削除前の安全確認
4. **トランザクション処理**: エラー時の自動ロールバック

## 使用方法

### 基本的な使用手順

#### ステップ1: 影響範囲分析（必須）
```bash
# 削除対象の影響を確認
python cascade_deletion_system.py --analysis-only execution_id1 execution_id2
```

#### ステップ2: ドライラン（推奨）
```bash
# 削除処理の詳細確認（実際の削除は行わない）
python cascade_deletion_system.py --dry-run execution_id1 execution_id2
```

#### ステップ3: 実際の削除
```bash
# 実際のカスケード削除実行
python cascade_deletion_system.py execution_id1 execution_id2
```

### コマンドオプション

```bash
# 基本的な削除（バックアップ付き）
python cascade_deletion_system.py execution_id

# ドライラン（削除しない）
python cascade_deletion_system.py --dry-run execution_id

# 関連ファイルも削除
python cascade_deletion_system.py --delete-files execution_id

# バックアップをスキップ（非推奨）
python cascade_deletion_system.py --skip-backup execution_id

# 影響範囲分析のみ
python cascade_deletion_system.py --analysis-only execution_id

# 複数のexecution_idを指定
python cascade_deletion_system.py execution_id1 execution_id2 execution_id3
```

## 実行例

### 例1: 失敗した実行の削除
```bash
# ステップ1: 分析
python cascade_deletion_system.py --analysis-only symbol_addition_20250621_054000_6a714ea9

# 出力例:
# 📋 実行ログ: 1件が削除対象
#    - symbol_addition_20250621_054000_6a714ea9: TEST (FAILED)
# 📊 分析結果: 0件が削除対象

# ステップ2: ドライラン
python cascade_deletion_system.py --dry-run symbol_addition_20250621_054000_6a714ea9

# ステップ3: 実際の削除
python cascade_deletion_system.py symbol_addition_20250621_054000_6a714ea9
```

### 例2: 成功した実行の削除（関連データあり）
```bash
# ステップ1: 分析
python cascade_deletion_system.py --analysis-only symbol_addition_20250620_204235_ed4dbad1

# 出力例:
# 📋 実行ログ: 1件が削除対象
#    - symbol_addition_20250620_204235_ed4dbad1: STG (SUCCESS)
# 📊 分析結果: 30件が削除対象
#    銘柄別:
#      STG: 30件
# 💾 関連ファイル: 60件 (125.5MB)

# ステップ2: ドライラン（ファイル削除含む）
python cascade_deletion_system.py --dry-run --delete-files symbol_addition_20250620_204235_ed4dbad1

# ステップ3: 実際の削除（ファイル削除含む）
python cascade_deletion_system.py --delete-files symbol_addition_20250620_204235_ed4dbad1
```

## 詳細出力例

### 影響範囲分析の出力
```
📊 削除影響範囲分析
----------------------------------------
📋 実行ログ: 2件が削除対象
   - symbol_addition_20250620_204235_ed4dbad1: STG (SUCCESS)
   - symbol_addition_20250620_203000_ab123def: BTC (SUCCESS)

📊 分析結果: 60件が削除対象
   銘柄別:
     STG: 30件
     BTC: 30件
   戦略別:
     Conservative_ML: 24件
     Aggressive_ML: 24件
     Full_ML: 12件

💾 関連ファイル: 120件 (250.0MB)
```

### 削除実行の出力
```
🗑️ カスケード削除実行 
----------------------------------------
✅ 分析結果削除: 60件
✅ ファイル削除: 120件 (250.0MB)
✅ 実行ログ削除: 2件
🔧 データベース最適化中...
✅ データベース最適化完了

📋 カスケード削除レポート
==================================================
実行結果:
  削除済み execution_logs: 2件
  削除済み analyses: 60件
  削除済みファイル: 120件 (250.0MB)

バックアップ:
  場所: backups/cascade_deletion_20250621_210000
```

## 安全機能

### 自動バックアップ
削除前に以下がバックアップされます：
- `execution_logs_backup.db`: execution_logs.dbの完全コピー
- `analysis_backup.db`: analysis.dbの完全コピー
- `backup_info.json`: バックアップ情報とメタデータ

バックアップ場所: `backups/cascade_deletion_YYYYMMDD_HHMMSS/`

### トランザクション制御
1. 分析結果削除
2. 関連ファイル削除
3. 実行ログ削除
4. データベース最適化

各ステップでエラーが発生した場合、自動的にロールバックされます。

## 使用場面

### 推奨される使用場面
1. **失敗した実行の削除**: エラーで中断された実行の完全削除
2. **テストデータの削除**: 開発・テスト用データの一括削除
3. **古いデータの削除**: 不要になった過去の実行データの削除
4. **容量最適化**: ディスク容量確保のための選択的削除

### 注意が必要な場面
1. **成功した実行の削除**: 有用な分析結果も削除されるため要注意
2. **RUNNING状態の削除**: 実行中プロセスへの影響を考慮
3. **本番データの削除**: バックアップ必須、十分な検証が必要

## 復旧手順

### バックアップからの復旧
```bash
# 1. 現在のDBを退避
mv execution_logs.db execution_logs.db.error
mv web_dashboard/large_scale_analysis/analysis.db analysis.db.error

# 2. バックアップから復旧
cp backups/cascade_deletion_YYYYMMDD_HHMMSS/execution_logs_backup.db execution_logs.db
cp backups/cascade_deletion_YYYYMMDD_HHMMSS/analysis_backup.db web_dashboard/large_scale_analysis/analysis.db

# 3. 動作確認
python cascade_deletion_system.py --analysis-only target_execution_id
```

## トラブルシューティング

### よくあるエラー

#### 1. "execution_id not found" 
```
⚠️ 警告: 存在しないexecution_id: {'invalid_id'}
```
**原因**: 指定されたexecution_idが存在しない  
**解決**: execution_idを正しく確認してから再実行

#### 2. "database is locked"
**原因**: 他のプロセスがDBを使用中  
**解決**: 関連プロセスを停止してから再実行

#### 3. "permission denied" (ファイル削除時)
**原因**: ファイル権限の問題  
**解決**: 適切な権限を設定

### 安全確認事項

#### 削除前の確認
1. **実行状態の確認**: RUNNING状態のexecution_idでないこと
2. **重要データの確認**: 重要な分析結果が含まれていないこと
3. **バックアップ容量**: 十分なディスク容量があること

#### 削除後の確認
1. **関連プロセスの動作**: 他のシステムへの影響がないこと
2. **参照整合性**: データベース間の整合性が保たれていること

## パフォーマンス

### 削除性能
- **小規模削除** (1-10件): 数秒
- **中規模削除** (10-100件): 10-30秒  
- **大規模削除** (100件以上): 1-5分

### 最適化機能
- 削除後の自動VACUUM実行
- インデックス再構築
- ディスク容量の即座回復

## 関連ファイル

- `cascade_deletion_system.py`: メインシステム
- `test_cascade_deletion.py`: テストスイート
- `db_integrity_utils.py`: 参照整合性チェック関数

## 更新履歴

- 2025-06-21: 初版作成
- テスト成功率: 100% (4/4テスト合格)
- 影響範囲分析、ドライラン、実削除、バックアップ機能すべて正常動作確認済み