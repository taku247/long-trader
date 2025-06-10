# 学習・バックテスト実行ログシステム設計書

## 📋 概要

銘柄追加時および定期実行時の学習・バックテストの実行履歴を詳細に記録し、追跡可能にするシステム。

## 🎯 ログ記録の目的

1. **実行履歴の完全な追跡**
   - いつ、どの銘柄で、どの処理が実行されたか
   - 成功/失敗の記録
   - 実行時間とリソース使用量

2. **問題の早期発見**
   - エラーパターンの把握
   - パフォーマンス劣化の検知
   - データ品質の監視

3. **コンプライアンス**
   - 監査証跡の保持
   - 再現可能性の確保

## 📊 ログデータ構造

### 実行ログのスキーマ
```python
{
    'execution_id': 'exec_20240110_153045_uuid',
    'execution_type': 'SYMBOL_ADDITION',  # SYMBOL_ADDITION/SCHEDULED/MANUAL/EMERGENCY
    'timestamp_start': '2024-01-10 15:30:45',
    'timestamp_end': '2024-01-10 15:45:23',
    'duration_seconds': 878,
    'status': 'SUCCESS',  # SUCCESS/PARTIAL_SUCCESS/FAILED
    
    'target': {
        'symbols': ['HYPE'],
        'timeframes': ['1m', '3m', '5m', '15m', '30m', '1h'],
        'strategies': ['Conservative_ML', 'Aggressive_Traditional', 'Full_ML']
    },
    
    'operations': {
        'data_fetch': {
            'status': 'SUCCESS',
            'duration': 45,
            'records_fetched': 129600,
            'date_range': {
                'start': '2023-10-12',
                'end': '2024-01-10'
            }
        },
        'backtest': {
            'status': 'SUCCESS',
            'duration': 623,
            'total_combinations': 18,  # 3 strategies × 6 timeframes
            'results_summary': {
                'best_performance': {
                    'strategy': 'Conservative_ML',
                    'timeframe': '15m',
                    'sharpe_ratio': 3.45,
                    'total_return': 156.8
                },
                'failed_tests': 0,
                'low_performance_count': 2  # Sharpe < 1.0
            }
        },
        'ml_training': {
            'status': 'SUCCESS',
            'duration': 210,
            'models_trained': {
                'support_resistance_ml': {
                    'accuracy': 0.73,
                    'f1_score': 0.71,
                    'training_samples': 8500
                },
                'btc_correlation': {
                    'r_squared': 0.82,
                    'training_samples': 10000
                }
            }
        }
    },
    
    'resources': {
        'cpu_usage_avg': 78.5,
        'memory_peak_mb': 2048,
        'disk_io_mb': 512
    },
    
    'errors': [],  # エラーがあった場合の詳細
    
    'metadata': {
        'triggered_by': 'USER:admin',  # or 'SYSTEM:scheduler'
        'server_id': 'prod-01',
        'version': '1.2.0'
    }
}
```

### 定期実行ログの追加情報
```python
{
    'schedule_info': {
        'schedule_type': 'HOURLY_BACKTEST',  # HOURLY_BACKTEST/WEEKLY_TRAINING/MONTHLY_OPTIMIZATION
        'cron_expression': '0 * * * *',
        'next_execution': '2024-01-10 16:00:00',
        'consecutive_failures': 0
    },
    
    'comparison_with_previous': {
        'performance_change': {
            'HYPE_15m_Conservative_ML': {
                'sharpe_before': 3.21,
                'sharpe_after': 3.45,
                'change_percent': 7.48
            }
        },
        'new_top_strategies': ['HYPE_5m_Full_ML'],
        'degraded_strategies': ['HYPE_1h_Aggressive_Traditional']
    }
}
```

## 📝 ログ管理システム

### ログ記録クラス
```python
class TrainingBacktestLogger:
    def __init__(self):
        self.db_path = "execution_logs.db"
        self.current_execution = None
    
    def start_execution(self, execution_type: str, targets: dict):
        """実行開始時のログ"""
        self.current_execution = {
            'execution_id': self._generate_id(),
            'execution_type': execution_type,
            'timestamp_start': datetime.now(),
            'target': targets,
            'operations': {}
        }
        
    def log_operation(self, operation_name: str, status: str, details: dict):
        """各操作のログ"""
        self.current_execution['operations'][operation_name] = {
            'status': status,
            'timestamp': datetime.now(),
            **details
        }
    
    def complete_execution(self, status: str):
        """実行完了時のログ保存"""
        self.current_execution['status'] = status
        self.current_execution['timestamp_end'] = datetime.now()
        self._save_to_database()
        self._send_notification_if_needed()
```

### 実行タイプの定義
```python
EXECUTION_TYPES = {
    'SYMBOL_ADDITION': {
        'description': '新規銘柄追加時の初期処理',
        'required_operations': ['data_fetch', 'backtest', 'ml_training'],
        'timeout_minutes': 30
    },
    'SCHEDULED_BACKTEST': {
        'description': '定期バックテスト実行',
        'required_operations': ['data_fetch', 'backtest'],
        'timeout_minutes': 15
    },
    'SCHEDULED_TRAINING': {
        'description': '定期ML学習',
        'required_operations': ['data_fetch', 'ml_training'],
        'timeout_minutes': 60
    },
    'EMERGENCY_RETRAIN': {
        'description': '緊急再学習',
        'required_operations': ['ml_training'],
        'timeout_minutes': 20
    }
}
```

## 📊 ログビューアー

### ダッシュボード表示
```
┌────────────────────────────────────────────────────────────┐
│ 📋 学習・バックテスト実行履歴                                │
├────────────────────────────────────────────────────────────┤
│ フィルター: [全タイプ ▼] [過去7日 ▼] [全ステータス ▼]       │
├──────────────┬──────────┬────────┬────────┬───────┬───────┤
│ 実行日時      │ タイプ    │ 対象    │ 時間   │ 状態   │ 詳細  │
├──────────────┼──────────┼────────┼────────┼───────┼───────┤
│ 01-10 15:30  │ 銘柄追加  │ HYPE   │ 14:38  │ ✅成功 │ [見る]│
│ 01-10 12:00  │ 定期BT   │ 全銘柄  │ 08:15  │ ✅成功 │ [見る]│
│ 01-10 09:15  │ 緊急学習  │ SOL    │ 05:22  │ ⚠️部分 │ [見る]│
└──────────────┴──────────┴────────┴────────┴───────┴───────┘
```

### 詳細ビュー機能
- 各操作の実行時間と結果
- エラーの詳細とスタックトレース
- パフォーマンス指標の変化
- リソース使用状況グラフ

## 🔔 通知・アラート

### 通知条件
```python
NOTIFICATION_RULES = {
    'execution_failed': {
        'condition': 'status == FAILED',
        'priority': 'HIGH',
        'channels': ['discord', 'email']
    },
    'performance_degradation': {
        'condition': 'avg_sharpe_change < -20%',
        'priority': 'MEDIUM',
        'channels': ['discord']
    },
    'long_execution': {
        'condition': 'duration > timeout * 1.5',
        'priority': 'LOW',
        'channels': ['log']
    }
}
```

## 📈 分析機能

### 実行統計レポート
```python
def generate_execution_report(period='monthly'):
    return {
        'summary': {
            'total_executions': 245,
            'success_rate': 94.3,
            'avg_duration': '12:34',
            'total_compute_hours': 51.2
        },
        'by_type': {
            'SYMBOL_ADDITION': {
                'count': 15,
                'avg_duration': '18:45',
                'success_rate': 100
            },
            'SCHEDULED_BACKTEST': {
                'count': 180,
                'avg_duration': '08:15',
                'success_rate': 95.6
            }
        },
        'performance_improvements': {
            'avg_sharpe_increase': 12.3,
            'models_improved': 85,
            'models_degraded': 15
        },
        'resource_usage': {
            'peak_hours': ['02:00-04:00', '14:00-16:00'],
            'total_cost_estimate': '$125.40'
        }
    }
```

## 🔧 実装の統合

### 銘柄追加フロー
```python
async def add_symbol_with_logging(symbol: str):
    logger = TrainingBacktestLogger()
    
    try:
        # 実行開始ログ
        logger.start_execution('SYMBOL_ADDITION', {
            'symbols': [symbol],
            'timeframes': ALL_TIMEFRAMES,
            'strategies': ALL_STRATEGIES
        })
        
        # データ取得
        logger.log_operation('data_fetch', 'STARTED', {})
        data = await fetch_historical_data(symbol)
        logger.log_operation('data_fetch', 'SUCCESS', {
            'records_fetched': len(data)
        })
        
        # バックテスト実行
        logger.log_operation('backtest', 'STARTED', {})
        results = await run_all_backtests(symbol, data)
        logger.log_operation('backtest', 'SUCCESS', {
            'results_summary': summarize_results(results)
        })
        
        # ML学習
        logger.log_operation('ml_training', 'STARTED', {})
        models = await train_ml_models(symbol, data)
        logger.log_operation('ml_training', 'SUCCESS', {
            'models_trained': models.get_metrics()
        })
        
        # 完了
        logger.complete_execution('SUCCESS')
        
    except Exception as e:
        logger.log_operation('error', 'FAILED', {
            'error_message': str(e),
            'traceback': traceback.format_exc()
        })
        logger.complete_execution('FAILED')
        raise
```

## 🎯 期待される効果

1. **完全な実行履歴**
   - すべての処理が追跡可能
   - 問題発生時の原因特定が容易

2. **パフォーマンス最適化**
   - ボトルネックの特定
   - リソース使用の最適化

3. **品質保証**
   - 学習・バックテストの品質監視
   - 継続的な改善