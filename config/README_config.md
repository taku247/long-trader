# 時間足設定管理システム

## 🎯 概要

`TIMEFRAME_CONFIGS`をハードコードから外部設定ファイルに移行し、コードを変更せずに条件を調整できるシステムです。

## 📁 ファイル構成

```
config/
├── timeframe_conditions.json      # 時間足設定ファイル
├── timeframe_config_manager.py    # 設定管理クラス
└── README_config.md               # このファイル
```

## 🔧 設定ファイル (`timeframe_conditions.json`)

### 基本構造

```json
{
  "description": "時間足別の条件ベースシグナル生成設定",
  "timeframe_configs": {
    "1m": {
      "data_days": 14,
      "evaluation_interval_minutes": 5,
      "entry_conditions": {
        "min_leverage": 8.0,
        "min_confidence": 0.75,
        "min_risk_reward": 1.8
      }
    }
  }
}
```

### 設定項目の説明

#### **基本設定**
- `data_days`: データ取得期間（日数）
- `evaluation_interval_minutes`: 条件評価間隔（分）
- `min_train_samples`: 最小学習サンプル数
- `train_ratio` / `val_ratio` / `test_ratio`: データ分割比率

#### **エントリー条件**
- `min_leverage`: エントリー最小レバレッジ
- `min_confidence`: エントリー最小信頼度（0.0-1.0）
- `min_risk_reward`: エントリー最小リスクリワード比

#### **取引時間**
- `active_hours`: アクティブな時間帯（配列形式）
- `active_hours_range`: アクティブな時間帯（範囲形式）

## 💻 使用方法

### 1. 基本的な読み込み

```python
from config.timeframe_config_manager import TimeframeConfigManager

# 設定管理インスタンス作成
config_manager = TimeframeConfigManager()

# 5分足の設定を取得
config_5m = config_manager.get_timeframe_config('5m')
print(f"5分足の評価間隔: {config_5m['evaluation_interval_minutes']}分")
```

### 2. カスタム設定ファイルの使用

```python
# カスタム設定ファイルを指定
config_manager = TimeframeConfigManager('path/to/custom_config.json')
```

### 3. 設定の動的更新

```python
# 5分足設定を更新
config_manager.update_timeframe_config('5m', {
    'entry_conditions': {
        'min_leverage': 6.5,      # レバレッジ要件を緩和
        'min_confidence': 0.62    # 信頼度要件を微調整
    }
})

# 設定を保存
config_manager.save_config()
```

### 4. システムでの使用例

```python
# improved_scalable_analysis_system.py での使用
class ImprovedScalableAnalysisSystem:
    def __init__(self, config_file=None):
        self.config_manager = TimeframeConfigManager(config_file)
    
    def get_timeframe_config(self, timeframe: str):
        return self.config_manager.get_timeframe_config(timeframe)
```

## 🎛️ 設定例

### 短期高頻度トレード設定
```json
"1m": {
  "evaluation_interval_minutes": 5,
  "entry_conditions": {
    "min_leverage": 8.0,
    "min_confidence": 0.75,
    "min_risk_reward": 1.8
  }
}
```

### 中期安定トレード設定
```json
"15m": {
  "evaluation_interval_minutes": 60,
  "entry_conditions": {
    "min_leverage": 5.0,
    "min_confidence": 0.60,
    "min_risk_reward": 2.2
  }
}
```

### 長期安全トレード設定
```json
"1h": {
  "evaluation_interval_minutes": 240,
  "entry_conditions": {
    "min_leverage": 3.0,
    "min_confidence": 0.50,
    "min_risk_reward": 2.5
  }
}
```

## 🔒 検証機能

設定ファイルには自動検証機能が組み込まれています：

```json
"validation_rules": {
  "min_evaluation_interval": 1,
  "max_evaluation_interval": 1440,
  "min_confidence_range": [0.1, 1.0],
  "min_leverage_range": [1.0, 50.0],
  "min_risk_reward_range": [0.5, 10.0]
}
```

## 📤 設定のエクスポート・インポート

### エクスポート
```python
config_manager.export_current_config('backup_config.json')
```

### インポート
```python
config_manager.import_config('new_config.json')
```

## 🛡️ バックアップ

設定ファイルを変更する際、自動的にバックアップが作成されます：
- `timeframe_conditions.json.backup.20241215_143022`

## ⚡ コマンドライン操作

```bash
# 設定サマリー表示
python config/timeframe_config_manager.py

# 設定検証
python -c "from config.timeframe_config_manager import TimeframeConfigManager; TimeframeConfigManager().print_config_summary()"
```

## 🔧 トラブルシューティング

### よくある問題

1. **設定ファイルが見つからない**
   ```
   ⚠️ 設定ファイルが見つかりません: config/timeframe_conditions.json
   ```
   → 自動的にデフォルト設定ファイルが作成されます

2. **JSON形式エラー**
   ```
   ❌ 設定ファイルのJSON形式が不正
   ```
   → JSON構文をチェックしてください

3. **設定値が範囲外**
   ```
   ⚠️ 5m: min_confidence が範囲外: 1.5
   ```
   → `validation_rules`の範囲内に設定してください

## 🎯 メリット

1. **コードの変更不要**: 設定変更時にコード再デプロイが不要
2. **バージョン管理**: 設定ファイルもGitで管理可能
3. **検証機能**: 不正な設定値を自動検出
4. **バックアップ**: 設定変更時の自動バックアップ
5. **柔軟性**: 環境別設定ファイルの使い分け

## 🔄 マイグレーション

既存の`TIMEFRAME_CONFIGS`を設定ファイル化済み：
- ❌ 旧: ハードコード (`improved_scalable_analysis_system.py`内)
- ✅ 新: 外部設定ファイル (`config/timeframe_conditions.json`)

この変更により、システムの運用性と保守性が大幅に向上しました。