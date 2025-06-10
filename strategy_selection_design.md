# 戦略選択・変更管理システム設計書

## 📋 概要

バックテスト結果に基づいて高パフォーマンス戦略を選択し、運用中の戦略変更を記録・分析するシステム。

## 🎯 システムの目的

1. **データドリブンな戦略選択**
   - バックテスト結果を一覧表示
   - パフォーマンス指標でソート・フィルタリング
   - 複数戦略の同時監視

2. **戦略変更の透明性確保**
   - すべての変更を詳細にログ記録
   - 変更理由と市場コンテキストの保存
   - 効果測定と改善サイクル

## 📊 戦略ランキングページ

### UI設計
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 戦略パフォーマンスランキング                                │
├─────────────────────────────────────────────────────────────┤
│ フィルター: [銘柄: HYPE▼] [時間足: 全て▼] [期間: 30日▼]      │
├───┬────────┬──────┬────────┬────────┬────────┬────────┬────┤
│ # │ 戦略名  │銘柄  │時間足  │Sharpe比│勝率    │最大DD  │選択│
├───┼────────┼──────┼────────┼────────┼────────┼────────┼────┤
│ 1 │Cons_ML │HYPE  │15m     │3.45    │68.2%   │-5.2%   │ ☑  │
│ 2 │Full_ML │SOL   │1h      │3.21    │65.5%   │-6.8%   │ ☐  │
│ 3 │Aggr_Tr │HYPE  │5m      │2.98    │71.3%   │-8.1%   │ ☑  │
└───┴────────┴──────┴────────┴────────┴────────┴────────┴────┘
                                    [詳細表示] [監視開始]
```

### 表示項目
- **基本情報**: 戦略名、銘柄、時間足
- **パフォーマンス指標**: Sharpe比、勝率、最大ドローダウン
- **追加指標**: 月間リターン、取引回数、平均保有時間
- **リスク指標**: VaR、最大連続損失

### フィルタリング機能
- 銘柄別
- 時間足別
- 期間別（7日、30日、90日、全期間）
- パフォーマンス閾値
- リスクレベル

## 📝 戦略変更ログシステム

### ログデータ構造
```python
{
    'log_id': 'uuid-timestamp',
    'timestamp': '2024-01-10 15:30:45',
    'change_type': 'STRATEGY_SWITCH',  # SWITCH/ADD/REMOVE/PAUSE/RESUME
    'trigger': 'PERFORMANCE_DEGRADATION',
    'details': {
        'from_strategy': {
            'id': 'HYPE_15m_Conservative_ML',
            'performance_metrics': {
                'sharpe_7d': 0.85,
                'return_7d': -12.5,
                'consecutive_losses': 8,
                'drawdown_current': -15.2
            }
        },
        'to_strategy': {
            'id': 'HYPE_30m_Full_ML',
            'performance_metrics': {
                'sharpe_7d': 3.21,
                'return_7d': 18.3,
                'rank': 2
            }
        },
        'reasoning': [
            '7日間パフォーマンスが-10%を下回った',
            '8連続損失を記録',
            'Sharpe比が1.0を下回った',
            '次点の戦略は安定したパフォーマンスを維持'
        ],
        'market_context': {
            'btc_price': 45230.50,
            'btc_trend': 'BEARISH',
            'market_volatility': 'HIGH',
            'volume_profile': 'ABOVE_AVERAGE',
            'major_events': ['FOMC発表前']
        }
    },
    'automated': True,
    'approved_by': 'SYSTEM',
    'execution_status': 'SUCCESS',
    'post_change_monitoring': {
        '1h': {'return': 2.3, 'status': 'positive'},
        '24h': {'return': 5.8, 'status': 'positive'},
        '7d': None  # 未到達
    }
}
```

### 変更トリガー定義
```python
CHANGE_TRIGGERS = {
    # パフォーマンスベース
    'PERFORMANCE_DEGRADATION': {
        'description': '戦略パフォーマンス低下',
        'conditions': {
            'return_7d': '<= -10%',
            'sharpe_ratio': '< 1.0',
            'consecutive_losses': '>= 8'
        }
    },
    'DRAWDOWN_EXCEEDED': {
        'description': '最大ドローダウン超過',
        'conditions': {
            'current_drawdown': '> max_allowed_drawdown'
        }
    },
    
    # 市場環境ベース
    'MARKET_REGIME_CHANGE': {
        'description': '市場レジーム変化検知',
        'conditions': {
            'volatility_change': '> 200%',
            'correlation_breakdown': True
        }
    },
    
    # 定期メンテナンス
    'SCHEDULED_ROTATION': {
        'description': '定期ローテーション',
        'conditions': {
            'days_active': '>= 30',
            'performance_rank_drop': '> 5'
        }
    },
    
    # 手動介入
    'MANUAL_OVERRIDE': {
        'description': 'ユーザー手動変更',
        'requires_reason': True
    }
}
```

## 📊 変更履歴ダッシュボード

### 履歴表示ページ
```
┌────────────────────────────────────────────────────────┐
│ 📋 戦略変更履歴                                         │
├────────────────────────────────────────────────────────┤
│ 期間: [過去7日 ▼]  フィルター: [全変更 ▼]              │
├──────────────┬─────────────┬───────────────┬──────────┤
│ 日時         │ 変更内容     │ トリガー       │ 結果    │
├──────────────┼─────────────┼───────────────┼──────────┤
│ 01-10 15:30  │ HYPE戦略切替 │ 性能低下      │ ✅改善   │
│ 01-09 08:15  │ SOL戦略追加  │ 新規上位戦略  │ ✅有効   │
│ 01-08 22:00  │ WIF戦略一時停止│ 市場異常    │ ⚠️損失回避│
└──────────────┴─────────────┴───────────────┴──────────┘
```

### 詳細ビュー機能
- 変更前後のパフォーマンス比較チャート
- 市場環境の可視化
- 判断理由の詳細表示
- 効果測定結果

## 📈 分析レポート機能

### 月次分析レポート
```python
{
    'report_period': '2024-01',
    'summary': {
        'total_changes': 23,
        'success_rate': 78.3,  # %
        'avg_improvement': 15.2  # %
    },
    'change_breakdown': {
        'by_trigger': {
            'performance': {'count': 12, 'success_rate': 65},
            'market': {'count': 7, 'success_rate': 85},
            'scheduled': {'count': 4, 'success_rate': 100}
        },
        'by_timeframe': {
            '1m': {'count': 5, 'avg_improvement': 8.2},
            '5m': {'count': 8, 'avg_improvement': 12.5},
            '15m': {'count': 6, 'avg_improvement': 18.3},
            '1h': {'count': 4, 'avg_improvement': 22.1}
        }
    },
    'best_decisions': [
        {
            'date': '2024-01-08',
            'change': 'WIF戦略一時停止',
            'avoided_loss': 25.3,
            'reason': '市場異常を正確に検知'
        }
    ],
    'worst_decisions': [
        {
            'date': '2024-01-15',
            'change': 'PEPE戦略切替',
            'additional_loss': -5.2,
            'reason': '一時的な下落を過剰反応'
        }
    ],
    'recommendations': [
        '市場異常検知による変更は高い成功率',
        '短期的なパフォーマンス低下での変更は要検討',
        '15m以上の時間足での変更が効果的'
    ]
}
```

## 🔄 実装フロー

### Phase 1: 戦略ランキングページ
1. バックテスト結果の集計API
2. ランキング表示UI
3. フィルタリング機能
4. 戦略選択・監視開始機能

### Phase 2: 変更ログシステム
1. ログデータベース設計
2. 変更トリガー実装
3. 自動変更ロジック
4. ログ記録API

### Phase 3: 分析ダッシュボード
1. 変更履歴表示
2. 詳細ビュー
3. 分析レポート生成
4. 改善提案機能

## 🎯 期待される効果

1. **運用の透明性向上**
   - すべての判断が記録・追跡可能
   - 成功/失敗パターンの蓄積

2. **継続的改善**
   - データに基づく戦略選択
   - 変更ロジックの最適化

3. **リスク管理強化**
   - 異常な変更パターンの検知
   - 人的エラーの防止