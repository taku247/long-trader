# Claude Code セッション記録

## 開発方針

### 実装完了時の記録要件
実装完了後、要件定義ディレクトリ `_docs/` に実装ログを残すこと。
- ファイル形式: `yyyy-mm-dd_機能名.md`
- 起動時にも読み込んで過去の実装内容を把握すること

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
- DBファイル分離問題: execution_logs.dbが2箇所に存在
- 手動リセット機能とフロントエンド同期問題: 完全解決済み (2025-06-19)

## 取引所設定
現在の設定: Gate.io (exchange_config.json)
- Hyperliquid ⇄ Gate.io のワンクリック切り替え可能