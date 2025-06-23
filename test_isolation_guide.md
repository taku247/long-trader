# テストコードDB隔離修正ガイド

## 🚨 検出された問題

### 1. 本番DB直接使用ファイル

以下のファイルが本番DBを直接使用しています:

- `test_delete_functionality.py:36` - Hardcoded production execution logs DB
- `test_symbol_addition_with_relaxed_conditions.py:47` - Hardcoded production analysis DB
- `test_strategy_api_isolated.py:148` - Hardcoded production analysis DB
- `test_post_migration_validation.py:33` - Hardcoded production execution logs DB
- `test_post_migration_validation.py:34` - Hardcoded production execution logs DB
- `test_post_migration_validation.py:76` - Hardcoded production execution logs DB
- `test_entry_conditions.py:68` - Hardcoded production execution logs DB
- `test_entry_conditions.py:87` - Hardcoded production analysis DB
- `tests/test_symbol_addition_pipeline.py:364` - Hardcoded production execution logs DB
- `tests/test_symbol_addition_pipeline.py:365` - Hardcoded production execution logs DB
- `tests_organized/test_runner.py:46` - Hardcoded production execution logs DB
- `tests_organized/base_test.py:68` - Hardcoded production execution logs DB
- `tests_organized/base_test.py:301` - Hardcoded production execution logs DB
- `tests_organized/base_test.py:302` - Hardcoded production analysis DB
- `tests_organized/test_runner.py:46` - Hardcoded production execution logs DB
- `tests_organized/symbol_addition/test_trx_force_addition.py:19` - Hardcoded production analysis DB
- `tests_organized/symbol_addition/test_symbol_addition_end_to_end.py:459` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification_safety.py:35` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification_safety.py:36` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification_safety.py:40` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification_safety.py:87` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification_safety.py:87` - Path to production execution logs DB
- `tests_organized/db/test_db_unification_safety.py:110` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification_safety.py:111` - Hardcoded production execution logs DB
- `tests_organized/db/test_execution_id_integration.py:36` - Hardcoded production execution logs DB
- `tests_organized/db/test_foreign_key_implementation.py:16` - Hardcoded production execution logs DB
- `tests_organized/db/test_foreign_key_implementation.py:16` - Path to production execution logs DB
- `tests_organized/db/test_db_unification.py:31` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification.py:32` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification.py:166` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification.py:180` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification.py:268` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification.py:307` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification.py:347` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_unification.py:384` - Hardcoded production execution logs DB
- `tests_organized/db/test_cascade_deletion.py:30` - Hardcoded production execution logs DB
- `tests_organized/db/test_foreign_key_constraints.py:31` - Hardcoded production execution logs DB
- `tests_organized/db/test_symbol_addition_db_sync.py:58` - Hardcoded production execution logs DB
- `tests_organized/db/test_orphaned_cleanup.py:30` - Hardcoded production execution logs DB
- `tests_organized/db/test_db_connectivity_check.py:45` - Hardcoded production execution logs DB
- `tests_organized/api/test_symbols_api.py:22` - Hardcoded production execution logs DB
- `tests_organized/api/test_symbols_api_unsafe_backup.py:15` - Hardcoded production execution logs DB
- `tests_organized/api/test_trade_endpoint_mock.py:15` - Hardcoded production analysis DB
- `tests_organized/api/test_sol_api_direct.py:22` - Hardcoded production execution logs DB
- `tests_organized/api/test_both_endpoints.py:17` - Hardcoded production analysis DB
- `tests_organized/api/test_both_endpoints.py:22` - Hardcoded production execution logs DB
- `tests_organized/api/test_both_endpoints.py:83` - Hardcoded production analysis DB
- `tests_organized/api/test_sol_api_direct_unsafe_backup.py:15` - Hardcoded production analysis DB
- `tests_organized/api/test_sol_api_direct_unsafe_backup.py:20` - Hardcoded production execution logs DB


## 🔧 修正方法

### BaseTestの使用 (推奨)

```python
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加  
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests_organized.base_test import BaseTest

class YourTest(BaseTest):
    def custom_setup(self):
        # テスト固有のセットアップ
        pass
    
    def test_something(self):
        # self.analysis_db - テスト用analysis DB
        # self.execution_logs_db - テスト用execution logs DB
        pass
```

### 環境変数による隔離

```python
import os
import tempfile

def setup_test_db():
    test_db_dir = tempfile.mkdtemp(prefix="test_")
    os.environ['TEST_ANALYSIS_DB'] = os.path.join(test_db_dir, "analysis.db")
    os.environ['TEST_EXECUTION_DB'] = os.path.join(test_db_dir, "execution_logs.db")
    return test_db_dir
```

### 修正パターン

❌ **修正前:**
```python
db_path = "large_scale_analysis/analysis.db"
```

✅ **修正後:**
```python
db_path = self.analysis_db  # BaseTest使用時
# または
db_path = os.environ.get('TEST_ANALYSIS_DB', 'large_scale_analysis/analysis.db')
```

## 🧪 テスト実行確認

修正後は以下で隔離を確認:

```bash
python test_strategy_api_isolated.py
```

## 📋 修正チェックリスト

- [ ] BaseTestを継承
- [ ] ハードコードされたDBパスを削除
- [ ] テスト用DBパスを使用
- [ ] 本番DBへの影響なしを確認
