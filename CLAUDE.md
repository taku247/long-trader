# Claude Code セッション記録

## 🌐 MCPサーバー統合環境 (2025-06-26)
**✅ Claude Code MCP Server導入済み**: ブラウザでの直接動作確認が可能

### 🖥️ ブラウザアクセス可能なURL
- **Webダッシュボード**: `http://localhost:5001`
- **リアルタイム分析進捗**: `http://localhost:5001/analysis-progress`
- **銘柄管理画面**: `http://localhost:5001/symbols-enhanced`
- **API直接アクセス**: `http://localhost:5001/api/analysis/recent`

### 📊 MCP統合機能
- **ファイルベースリアルタイム進捗追跡**: ProcessPoolExecutor環境での進捗共有完全対応
- **プロセス間進捗データ同期**: `/tmp/progress_*.json`による永続化
- **メモリ+ファイル統合API**: 最新データ自動優先表示
- **Claude Codeからの直接操作**: 銘柄追加・進捗確認・動作テストが可能

### 🎯 動作確認手順
1. Claude Codeから銘柄追加実行: `curl -X POST http://localhost:5001/api/symbol/add -d '{"symbol":"SOL"}'`
2. 進捗をリアルタイム確認: `http://localhost:5001/analysis-progress`
3. 分析結果の詳細表示: 各フェーズ（data_validation → backtest → support_resistance → ml_prediction → leverage_decision）

**💡 Note**: MCP環境により、ローカルサーバーへの直接アクセス・API呼び出し・ファイル操作が可能なため、完全な動作検証が実現

## 開発方針

### 🚨 is_realtime/is_backtest フラグ管理の必須確認 (2025-06-25)
**⚠️ 重大**: リアルタイム処理とバックテスト処理が混在する問題の防止

#### 🔄 フラグ使用時の必須チェック項目
1. **価格取得時の確認**:
   - `current_price = data['close'].iloc[-1]` → ❌ 常に最新価格
   - `current_price = data.loc[target_idx, 'open']` → ✅ 各時点価格
   
2. **時刻コンテキストの確認**:
   - `datetime.now()` → ❌ バックテストでも現在時刻
   - `target_timestamp` → ✅ バックテスト時の対象時刻

3. **メソッド呼び出し時のフラグ渡し**:
   ```python
   # ❌ フラグ未指定（デフォルトでis_realtime=True）
   result = analyze_market_context(data)
   
   # ✅ 明示的なフラグ指定
   result = analyze_market_context(data, is_realtime=False)
   ```

#### 🎯 特に注意すべきファイル
- `engines/high_leverage_bot_orchestrator.py`: `_analyze_market_context`呼び出し
- `engines/leverage_decision_engine.py`: リスクリワード比計算
- `scalable_analysis_system.py`: バックテスト分析実行
- `auto_symbol_training.py`: 自動学習でのバックテスト

#### ⚠️ 作業中の一時的なフラグ変更について
**絶対に忘れてはいけない復元作業**:
1. **デバッグ目的**でis_realtime=Trueに一時変更した場合
2. **テスト目的**でフラグを強制的に固定した場合  
3. **検証目的**で条件分岐を無効化した場合

**復元忘れチェック項目**:
- [ ] コミット前に全ファイルでフラグ設定を確認
- [ ] テスト実行時に意図しない動作がないか確認
- [ ] 本番デプロイ前にリアルタイム/バックテスト動作の確認

#### 🛡️ 防止策
```bash
# フラグ関連の変更をコミット前にチェック
git diff | grep -E "(is_realtime|is_backtest)" 

# 一時的な変更がないかファイル全体をチェック  
grep -r "is_realtime.*True.*#.*TODO\|#.*TEMP\|#.*DEBUG" .
```

### データベース設計の必須確認 (2025-06-23)
**⚠️ 重要**: データベース関連の実装・変更時は以下を必ず実行すること

#### 📊 ER図確認・更新手順
1. **実装前の確認**: データベース関連の実装・調整前に必ずER図を確認
   - ファイル: `database_er_diagram.md`
   - 現在のテーブル構造とリレーションシップを把握
   - 変更予定箇所が他のテーブルに与える影響を事前確認

2. **テーブル変更時の更新**: CREATE TABLE、ALTER TABLE等でスキーマ変更した場合は必ずER図を更新
   - 新しい列の追加・削除
   - 外部キー関係の変更
   - インデックスの追加・削除
   - 新テーブルの追加

3. **ER図更新内容**:
   - Mermaid図式の更新
   - テーブル詳細説明の更新
   - リレーションシップの追加・修正
   - 追加インデックス情報の記載

#### 🧪 データベーステスト必須実行
- DB関連変更後は必ず関連テストを実行
- `python run_unified_tests.py --categories db`

### テスト駆動開発の必須化 (2025-06-23)
**⚠️ 重要**: 新機能実装・既存機能変更時は以下の手順を必ず実行すること

#### 🔄 実装時のテスト実行手順
1. **関連テスト実行**: 実装対象機能の関連テストを先に実行
   ```bash
   # 例: API機能変更時
   python run_unified_tests.py --categories api
   
   # 例: DB関連変更時  
   python run_unified_tests.py --categories db
   
   # 例: 個別機能テスト
   python tests_organized/api/test_symbols_api.py
   ```

2. **実装調整**: テスト結果を見ながら実装を調整・改善

3. **段階的テスト**: 実装進行中も定期的に関連テストを実行

4. **全テスト実行**: 実装完了後は必ず全テストを実行
   ```bash
   # 全テスト実行（本番DB保護確認付き）
   python run_unified_tests.py
   
   # 高速モード（時間短縮時）
   python run_unified_tests.py --quick
   ```

5. **テスト失敗対応**: 
   - 失敗したテストがある場合は必ず修正
   - 成功率100%になるまで実装を調整
   - 新機能の場合は対応するテストも追加

#### 🧪 テストファイル構成
- **tests_organized/**: カテゴリ別整理済み（137個のテスト）
- **base_test.py**: 統一テスト基底クラス（本番DB保護）
- **run_unified_tests.py**: 統一テストランナー

### テストコード品質管理 (重要)
**⚠️ テストコード調整時は必ず以下を実行すること:**
```bash
./scripts/test-isolation-check.sh
```
- **目的**: 本番DB使用テストの検出・防止
- **チェック内容**: BaseTest使用確認、テストデータ汚染チェック、隔離テスト実行
- **修正ガイド**: 問題検出時は `test_isolation_guide.md` を参照
- **テンプレート**: `test_basetest_template.py` を使用してBaseTest移行

### 実装完了時の記録要件
実装完了後、要件定義ディレクトリ `_docs/` に実装ログを残すこと。
- ファイル形式: `yyyy-mm-dd_機能名.md`
- 起動時にも読み込んで過去の実装内容を把握すること
- **テスト結果も含めて記録**すること

### 実装ログ読み込みシステム
**ファイル**: `implementation_log_reader.py`
- 起動時に `_docs/` ディレクトリの実装ログを自動読み込み
- 過去の実装履歴をサマリー表示
- キーワード検索・期間絞り込み機能
- 使用方法: `from implementation_log_reader import load_implementation_context`

### Early Fail検証システム実装 (2025-06-20)
- ZORAのような新規上場銘柄で90日分のOHLCVデータ不足により、重いマルチプロセス処理が実行される問題を解決
- Webエンドポイント段階での軽量検証システムを実装
- カスタマイズ可能な設定ファイル (`early_fail_config.json`) でルール管理
- テストスイート完成 (100%成功率)

## プロジェクト概要
ハイレバレッジ取引判定Bot - アルトコイン取引での最適なレバレッジ倍率自動判定システム

## 主要コンポーネント
- **high_leverage_bot.py**: メイン実行スクリプト
- **web_dashboard/app.py**: Webダッシュボード
- **symbol_early_fail_validator.py**: Early Fail検証システム
- **scalable_analysis_system.py**: 大規模バックテスト分析
- **auto_symbol_training.py**: 自動学習システム

## 既知の問題
- DBファイル分離問題: execution_logs.dbが2箇所に存在 → **解決済み (2025-06-23)**
- 手動リセット機能とフロントエンド同期問題: 完全解決済み (2025-06-19)
- データ範囲ミスマッチエラー: 時間優先設計の構造的欠陥 → **ドキュメント化済み (2025-06-23)**

## 取引所設定
現在の設定: Gate.io (exchange_config.json)
- Hyperliquid ⇄ Gate.io のワンクリック切り替え可能

## テスト環境 (2025-06-23)
### 統一テスト基盤
- **137個**のテストファイルをカテゴリ別に整理
- **本番DB保護**: 全テストが`tempfile`使用で安全実行
- **統一基底クラス**: `BaseTest`, `DatabaseTest`, `APITest`
- **統一ランナー**: `run_unified_tests.py` で本番DB保護確認付き実行

### テスト実行コマンド
```bash
# 全テスト実行（推奨）
python run_unified_tests.py

# カテゴリ別実行
python run_unified_tests.py --categories api db symbol_addition

# 高速モード
python run_unified_tests.py --quick

# 個別テスト
python tests_organized/api/test_symbols_api.py
```