# 🏗️ アラート履歴分析システム アーキテクチャ図

## 📊 システム全体構成図

```mermaid
graph TB
    subgraph "リアルタイム監視システム"
        A[Real-time Monitor] --> B[Alert Manager]
        B --> C[Discord通知]
        B --> D[ログファイル]
    end
    
    subgraph "新規実装: アラート履歴システム"
        B --> E[Alert DB Writer]
        E --> F[(SQLite DB)]
        
        G[Price Tracker] --> H[Price API]
        G --> F
        
        I[Performance Calculator] --> F
    end
    
    subgraph "Webダッシュボード"
        J[Flask Server] --> K[/api/alerts/history]
        J --> L[/api/charts/data]
        J --> M[/api/performance/stats]
        
        K --> F
        L --> F
        M --> F
        
        N[Analysis Page] --> O[Plotly.js Charts]
        N --> P[Statistics Panel]
        N --> Q[Filter Controls]
    end
    
    subgraph "ユーザーインターフェース"
        R[Web Browser] --> N
        O --> S[価格チャート]
        O --> T[アラートマーカー]
        O --> U[成功/失敗表示]
    end
```

## 🔄 データフロー図

```mermaid
sequenceDiagram
    participant M as Monitor
    participant AM as Alert Manager
    participant DB as SQLite DB
    participant PT as Price Tracker
    participant API as Price API
    participant WD as Web Dashboard
    participant UI as Browser
    
    Note over M,AM: アラート検知フロー
    M->>AM: Trading Opportunity検知
    AM->>DB: アラート情報保存
    AM-->>Discord: 通知送信
    
    Note over PT,API: 価格追跡フロー
    loop 定期実行（1時間ごと）
        PT->>DB: アクティブアラート取得
        PT->>API: 現在価格取得
        PT->>DB: 価格変動記録
        PT->>DB: パフォーマンス計算・更新
    end
    
    Note over WD,UI: 表示フロー
    UI->>WD: /analysis ページアクセス
    WD->>DB: アラート履歴取得
    WD->>DB: 価格データ取得
    WD->>UI: チャートデータ返却
    UI->>UI: Plotly.jsでチャート描画
```

## 🗄️ データベース構造図

```mermaid
erDiagram
    ALERTS {
        int id PK
        string alert_id UK
        string symbol
        string alert_type
        string priority
        datetime timestamp
        float leverage
        float confidence
        string strategy
        string timeframe
        float entry_price
        float target_price
        float stop_loss
        text metadata
    }
    
    PRICE_TRACKING {
        int id PK
        string alert_id FK
        string symbol
        datetime timestamp
        float price
        int time_elapsed_hours
        float percentage_change
    }
    
    PERFORMANCE_SUMMARY {
        int id PK
        string alert_id FK
        string symbol
        boolean is_success
        float max_gain
        float max_loss
        float final_return_24h
        float final_return_72h
        text evaluation_note
    }
    
    ALERTS ||--o{ PRICE_TRACKING : "has many"
    ALERTS ||--o| PERFORMANCE_SUMMARY : "has one"
```

## 🎯 コンポーネント詳細図

```
┌─────────────────────────────────────────────────────────────┐
│                    アラート履歴分析システム                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │   Monitor   │────▶│Alert Manager│────▶│  DB Writer  │  │
│  └─────────────┘     └─────────────┘     └──────┬──────┘  │
│                                                  │         │
│                                                  ▼         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │Price Tracker│────▶│  Price API  │     │  SQLite DB  │  │
│  └──────┬──────┘     └─────────────┘     └──────▲──────┘  │
│         │                                        │         │
│         └────────────────────────────────────────┘         │
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │Web Dashboard│────▶│ Flask APIs  │────▶│Analysis Page│  │
│  └─────────────┘     └─────────────┘     └─────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📱 画面構成図

```
┌───────────────────────────────────────────────────────┐
│  📊 アラート履歴分析ダッシュボード                        │
├───────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐ │
│ │トークン選択▼│ │ 期間選択 ▼   │ │ 戦略フィルタ ▼ │ │
│ └─────────────┘ └──────────────┘ └─────────────────┘ │
├───────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              📈 価格チャート                      │ │
│  │  $30┤                    🎯                     │ │
│  │     │                   ╱ ╲                     │ │
│  │  $25┤        🎯────────╱   ╲                   │ │
│  │     │       ╱                ╲                  │ │
│  │  $20┤──────╱          🎯      ╲                │ │
│  │     └─────────────────────────────────────────│ │
│  │      6/1    6/5    6/9    6/13    6/17        │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌──────────────────┐  ┌────────────────────────┐   │
│  │ 📊 統計サマリー   │  │ 📋 アラート詳細        │   │
│  ├──────────────────┤  ├────────────────────────┤   │
│  │ 成功率: 73%      │  │ 選択アラート情報表示    │   │
│  │ 平均リターン: 12% │  │ - 時刻、価格          │   │
│  │ 最高成果: 24.9%  │  │ - その後の価格推移     │   │
│  └──────────────────┘  └────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

## 🔧 モジュール関係図

```mermaid
graph LR
    subgraph "既存システム"
        A[high_leverage_bot.py]
        B[real_time_system/monitor.py]
        C[real_time_system/alert_manager.py]
    end
    
    subgraph "新規モジュール"
        D[alert_db_writer.py]
        E[price_tracker.py]
        F[performance_calculator.py]
        G[alert_history_api.py]
        H[analysis_page.html]
        I[chart_controller.js]
    end
    
    subgraph "データストア"
        J[(alerts.db)]
        K[config.json]
    end
    
    B --> C
    C --> D
    D --> J
    E --> J
    F --> J
    G --> J
    H --> I
    I --> G
    E --> K
```

## 🚀 処理シーケンス図

```
1. アラート検知・保存
   Monitor → Alert Manager → DB Writer → SQLite
   
2. 価格追跡（1時間ごと）
   Scheduler → Price Tracker → API → SQLite
   
3. パフォーマンス計算
   Price Tracker → Performance Calculator → SQLite
   
4. Web表示
   Browser → Flask → SQLite → JSON → Plotly.js
```

## 📊 状態遷移図

```mermaid
stateDiagram-v2
    [*] --> アラート検知
    アラート検知 --> DB保存
    DB保存 --> 価格追跡開始
    
    価格追跡開始 --> 1時間後チェック
    1時間後チェック --> 3時間後チェック
    3時間後チェック --> 1日後チェック
    1日後チェック --> 3日後チェック
    3日後チェック --> 追跡完了
    
    1時間後チェック --> パフォーマンス評価
    3時間後チェック --> パフォーマンス評価
    1日後チェック --> パフォーマンス評価
    3日後チェック --> パフォーマンス評価
    
    パフォーマンス評価 --> 成功判定
    パフォーマンス評価 --> 失敗判定
    
    成功判定 --> 統計更新
    失敗判定 --> 統計更新
    
    追跡完了 --> [*]
```

## 🎨 UI/UXフロー図

```
┌─────────┐     ┌────────────┐     ┌───────────┐
│Dashboard│────▶│Analysis Tab│────▶│Token Select│
└─────────┘     └────────────┘     └─────┬─────┘
                                          │
                                          ▼
┌─────────┐     ┌────────────┐     ┌───────────┐
│ Export  │◀────│Chart Display│◀────│Date Range │
└─────────┘     └──────┬─────┘     └───────────┘
                       │
                       ▼
                ┌────────────┐
                │Alert Detail│
                │  Popup     │
                └────────────┘
```

## 🔐 セキュリティ考慮事項

```
1. SQLインジェクション対策
   - パラメータバインディング使用
   - 入力値バリデーション

2. API レート制限
   - Price API呼び出し制限
   - キャッシュ活用

3. データアクセス制御
   - 読み取り専用ビュー
   - 機密情報マスキング
```