# Real-Time Trading Monitor - Phase 1

自動監視システムによるリアルタイム取引機会検出システムです。

## 概要

このシステムは、設定された間隔で複数の暗号通貨銘柄を監視し、高レバレッジ取引機会を自動検出してアラートを送信します。

## 機能

- **自動監視**: 設定可能な間隔（1分～1440分）での並列監視
- **インテリジェントアラート**: レバレッジ≥10x、信頼度≥70%の機会を検出
- **Discord通知**: Webhook経由でのリアルタイム通知
- **リスク警告**: 危険な市場状況の検出と警告
- **設定管理**: 動的設定変更とホットリロード
- **レート制限**: APIレート制限に対応した安全な監視
- **エラーハンドリング**: 堅牢なエラー処理と自動復旧

## ディレクトリ構造

```
real_time_system/
├── monitor.py              # メイン監視システム
├── alert_manager.py        # アラート管理システム
├── config/
│   ├── monitoring_config.json  # システム設定
│   └── watchlist.json          # 監視銘柄設定
├── utils/
│   └── scheduler_utils.py      # スケジューラーユーティリティ
└── logs/
    └── monitoring.log          # 監視ログ
```

## 設定ファイル

### monitoring_config.json
システム全体の設定を管理します：

- **monitoring**: 監視間隔、並列度、APIレート制限
- **notifications**: Discord、コンソール、ファイル通知設定
- **alerts**: アラート閾値、クールダウン、レート制限
- **system**: ヘルスチェック、設定リロード間隔

### watchlist.json
監視対象銘柄とその個別設定：

- **default_settings**: デフォルト設定
- **symbols**: 銘柄別の詳細設定（レバレッジ閾値、戦略、優先度等）

## 使用方法

### 基本実行
```bash
# デフォルト設定で開始
python real_time_system/monitor.py

# 特定の間隔で実行
python real_time_system/monitor.py --interval 5

# 特定の銘柄のみ監視
python real_time_system/monitor.py --symbols HYPE,SOL,WIF

# 設定ファイルを指定
python real_time_system/monitor.py --config /path/to/config.json
```

### システムテスト
```bash
# 全コンポーネントのテスト
python real_time_system/monitor.py --test

# システム状態確認
python real_time_system/monitor.py --status
```

## Discord通知設定

1. Discord サーバーでWebhookを作成
2. `monitoring_config.json`の`discord.webhook_url`にWebhook URLを設定
3. 必要に応じて`mention_role`でロールIDを設定

### Webhook URL形式
```
https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

## アラートの種類

### 1. 取引機会アラート
- レバレッジ≥10x、信頼度≥70%の機会を検出
- エントリー価格、ターゲット、ストップロス情報を含む
- 優先度は設定された閾値に基づいて自動決定

### 2. リスク警告アラート
- 危険な市場状況を検出
- 高ボラティリティ、急激な価格変動等

### 3. システムステータス
- 開始・停止・エラー情報
- 定期的なヘルスチェック結果

## ログとモニタリング

- **コンソール出力**: リアルタイムでの状況確認
- **ファイルログ**: `logs/monitoring.log`に詳細ログを保存
- **アラート履歴**: 過去1000件のアラートを保持
- **統計情報**: 時間別、タイプ別、銘柄別の統計

## APIレート制限対応

- 設定可能な遅延時間（デフォルト1秒）
- 自動リトライ機能（最大3回）
- 並列実行制限（デフォルト5ワーカー）

## エラーハンドリング

- 自動復旧機能
- エラー回数による自動無効化
- グレースフルシャットダウン
- 設定リロード機能

## 監視対象銘柄

デフォルトで以下の銘柄を監視：

- **HYPE**: 高優先度、複数時間軸（15m, 1h, 4h）
- **SOL**: 高優先度、保守的設定（1h, 4h）
- **WIF**: 中優先度、攻撃的設定（15m, 1h）
- **BONK**: 低優先度、保守的設定（1h）
- **PEPE**: デフォルト無効（高リスク）

## カスタマイズ

### 新しい銘柄の追加
`watchlist.json`に新しいエントリーを追加：

```json
"SYMBOL": {
    "enabled": true,
    "timeframes": ["15m", "1h"],
    "strategies": ["Conservative_ML", "Full_ML"],
    "min_leverage": 10.0,
    "min_confidence": 70.0,
    "position_size_limit": 1000.0,
    "priority": "medium"
}
```

### アラート閾値の調整
`monitoring_config.json`の`alerts`セクションで調整：

```json
"alerts": {
    "leverage_threshold": 15.0,
    "confidence_threshold": 80.0,
    "cooldown_minutes": 30
}
```

## トラブルシューティング

### よくある問題

1. **Discord通知が送信されない**
   - Webhook URLが正しいか確認
   - `--test`でテスト実行

2. **高いCPU使用率**
   - 監視間隔を長くする
   - 並列ワーカー数を減らす

3. **APIエラー**
   - レート制限設定を調整
   - リトライ設定を確認

### ログの確認
```bash
tail -f real_time_system/logs/monitoring.log
```

## 今後の拡張予定

- **Phase 2**: Web UI ダッシュボード
- **Phase 3**: 自動取引実行機能
- **Phase 4**: ML モデルの動的更新

## 必要な依存関係

- Python 3.8+
- requests
- 既存のhigh_leverage_bot_orchestratorシステム

このシステムは堅牢で拡張可能な設計となっており、将来的な機能追加に対応できます。