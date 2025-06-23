#!/usr/bin/env python3
"""
テストコード全般のデータベース隔離修正ツール

本番DBを使用しているテストコードを特定・修正する
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple

class TestDatabaseIsolationFixer:
    """テストコードのDB隔離修正ツール"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.problems = []
        self.fixed_files = []
    
    def scan_test_files(self) -> List[Tuple[str, str, int]]:
        """テストファイルをスキャンして問題を特定"""
        print("🔍 Scanning test files for database isolation issues...")
        
        # テストファイルのパターン
        test_patterns = [
            "test_*.py",
            "*/test_*.py", 
            "tests_organized/**/*.py"
        ]
        
        problem_patterns = [
            (r'"large_scale_analysis/analysis\.db"', "Hardcoded production analysis DB"),
            (r"'large_scale_analysis/analysis\.db'", "Hardcoded production analysis DB"),
            (r'"execution_logs\.db"', "Hardcoded production execution logs DB"),
            (r"'execution_logs\.db'", "Hardcoded production execution logs DB"),
            (r'Path\("large_scale_analysis/analysis\.db"\)', "Path to production analysis DB"),
            (r'Path\("execution_logs\.db"\)', "Path to production execution logs DB"),
        ]
        
        problems = []
        
        # プロジェクト内の全テストファイルを検索
        for pattern in test_patterns:
            for test_file in self.project_root.glob(pattern):
                if test_file.is_file() and test_file.suffix == '.py':
                    try:
                        content = test_file.read_text(encoding='utf-8')
                        
                        for line_num, line in enumerate(content.splitlines(), 1):
                            for pattern_regex, description in problem_patterns:
                                if re.search(pattern_regex, line):
                                    problems.append((str(test_file), description, line_num))
                                    print(f"   ❌ {test_file.relative_to(self.project_root)}:{line_num} - {description}")
                    
                    except Exception as e:
                        print(f"   ⚠️ Error reading {test_file}: {e}")
        
        self.problems = problems
        return problems
    
    def check_base_test_usage(self) -> List[str]:
        """BaseTestを使用していないテストクラスを特定"""
        print("\n🔍 Checking BaseTest usage...")
        
        non_base_test_files = []
        
        for test_file in self.project_root.glob("tests_organized/**/*.py"):
            if test_file.is_file() and test_file.name.startswith('test_'):
                try:
                    content = test_file.read_text(encoding='utf-8')
                    
                    # テストクラスがあるかチェック
                    if 'class Test' in content or 'class ' in content and 'Test' in content:
                        # BaseTestをimportしているかチェック
                        if 'from tests_organized.base_test import BaseTest' not in content and \
                           'from .base_test import BaseTest' not in content and \
                           'from base_test import BaseTest' not in content:
                            non_base_test_files.append(str(test_file))
                            print(f"   ⚠️ {test_file.relative_to(self.project_root)} - BaseTest未使用")
                
                except Exception as e:
                    print(f"   ⚠️ Error reading {test_file}: {e}")
        
        return non_base_test_files
    
    def create_isolation_guide(self):
        """隔離修正ガイドを作成"""
        guide_content = """# テストコードDB隔離修正ガイド

## 🚨 検出された問題

### 1. 本番DB直接使用ファイル
"""
        
        if self.problems:
            guide_content += "\n以下のファイルが本番DBを直接使用しています:\n\n"
            for file_path, description, line_num in self.problems:
                rel_path = Path(file_path).relative_to(self.project_root)
                guide_content += f"- `{rel_path}:{line_num}` - {description}\n"
        
        guide_content += """

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
"""
        
        guide_path = self.project_root / "test_isolation_guide.md"
        guide_path.write_text(guide_content, encoding='utf-8')
        print(f"\n📋 隔離修正ガイドを作成: {guide_path}")
    
    def create_migration_template(self):
        """BaseTest移行テンプレートを作成"""
        template_content = '''#!/usr/bin/env python3
"""
テンプレート: BaseTestを使用したテストクラス

元のテストファイルをこの形式に変換してください
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests_organized.base_test import BaseTest

class YourTestName(BaseTest):
    """適切な説明を記述"""
    
    def custom_setup(self):
        """テスト固有のセットアップ"""
        # 例: テスト用データの作成
        # self.test_symbol = "TEST_SYMBOL"
        pass
    
    def test_your_functionality(self):
        """テストケースの説明"""
        
        # ✅ 正しい方法: テスト用DBを使用
        # self.analysis_db - テスト用analysis.db
        # self.execution_logs_db - テスト用execution_logs.db
        
        # 例:
        # with sqlite3.connect(self.analysis_db) as conn:
        #     # テスト処理
        #     pass
        
        # アサーション
        self.assertTrue(True, "テストの説明")

def run_test():
    """テスト実行関数"""
    import unittest
    
    suite = unittest.TestSuite()
    suite.addTest(YourTestName('test_your_functionality'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    import sys
    success = run_test()
    sys.exit(0 if success else 1)
'''
        
        template_path = self.project_root / "test_basetest_template.py"
        template_path.write_text(template_content, encoding='utf-8')
        print(f"📝 BaseTest移行テンプレートを作成: {template_path}")
    
    def generate_summary_report(self):
        """サマリーレポート生成"""
        print("\n" + "="*60)
        print("🎯 テストコードDB隔離問題サマリー")
        print("="*60)
        
        print(f"📊 検出された問題: {len(self.problems)}件")
        
        if self.problems:
            print("\n⚠️ 修正が必要なファイル:")
            unique_files = set(prob[0] for prob in self.problems)
            for file_path in sorted(unique_files):
                rel_path = Path(file_path).relative_to(self.project_root)
                print(f"  - {rel_path}")
        
        non_base_test_files = self.check_base_test_usage()
        if non_base_test_files:
            print(f"\n🔧 BaseTest未使用ファイル: {len(non_base_test_files)}件")
        
        print(f"\n📋 作成されたファイル:")
        print(f"  - test_isolation_guide.md (修正ガイド)")
        print(f"  - test_basetest_template.py (移行テンプレート)")
        
        if self.problems or non_base_test_files:
            print("\n❌ テストコードの隔離に問題があります")
            print("   上記のガイドを参照して修正してください")
        else:
            print("\n✅ すべてのテストコードが適切に隔離されています")

def main():
    """メイン実行関数"""
    project_root = "/Users/moriwakikeita/tools/long-trader"
    
    print("🔒 テストコードDB隔離問題スキャナー")
    print("="*60)
    
    fixer = TestDatabaseIsolationFixer(project_root)
    
    # 問題スキャン
    fixer.scan_test_files()
    
    # ガイド・テンプレート作成
    fixer.create_isolation_guide()
    fixer.create_migration_template()
    
    # サマリーレポート
    fixer.generate_summary_report()

if __name__ == "__main__":
    main()