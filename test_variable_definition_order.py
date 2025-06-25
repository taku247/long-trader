#!/usr/bin/env python3
"""
変数定義順序バグ防止テスト - ohlcv_data未定義エラーのような問題を防ぐテスト

変数の定義前参照や、メソッド間でのデータフロー問題を検出して
同様のバグが発生しないようにする包括的テストシステム
"""

import ast
import sys
import os
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class VariableDefinitionOrderChecker:
    """変数定義順序チェッカー"""
    
    def __init__(self):
        self.critical_files = [
            "scalable_analysis_system.py",
            "auto_symbol_training.py", 
            "engines/high_leverage_bot_orchestrator.py",
            "new_symbol_addition_system.py"
        ]
        self.critical_variables = [
            "ohlcv_data",
            "custom_period_settings",
            "market_data",
            "data",
            "result",
            "bot"
        ]
    
    def check_variable_definition_order(self, file_path: str) -> Dict[str, List[str]]:
        """ファイル内の変数定義順序をチェック"""
        print(f"\n🔍 変数定義順序チェック: {file_path}")
        print("=" * 60)
        
        issues = {
            "undefined_references": [],
            "potential_issues": [],
            "conditional_definitions": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # ASTパースによる詳細分析
            tree = ast.parse(content)
            
            # 各関数・メソッドを個別に分析
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_issues = self._analyze_method_variables(node, content)
                    for issue_type, issue_list in method_issues.items():
                        issues[issue_type].extend(issue_list)
            
            # 正規表現による追加チェック
            regex_issues = self._regex_based_checks(content, file_path)
            for issue_type, issue_list in regex_issues.items():
                issues[issue_type].extend(issue_list)
            
            # 結果表示
            self._display_check_results(file_path, issues)
            
            return issues
            
        except Exception as e:
            print(f"❌ {file_path} 分析エラー: {e}")
            return issues
    
    def _analyze_method_variables(self, method_node: ast.AST, content: str) -> Dict[str, List[str]]:
        """メソッド内の変数定義・使用順序を分析"""
        issues = {
            "undefined_references": [],
            "potential_issues": [],
            "conditional_definitions": []
        }
        
        method_name = method_node.name
        defined_vars = set()
        used_vars = set()
        
        # メソッド内の全ノードを走査
        for node in ast.walk(method_node):
            if isinstance(node, ast.Assign):
                # 変数定義
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_vars.add(target.id)
            
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                # 変数使用
                var_name = node.id
                if var_name in self.critical_variables:
                    if var_name not in defined_vars:
                        issues["undefined_references"].append(
                            f"{method_name}: '{var_name}' が定義前に使用されている可能性"
                        )
                    used_vars.add(var_name)
        
        return issues
    
    def _regex_based_checks(self, content: str, file_path: str) -> Dict[str, List[str]]:
        """正規表現による追加チェック"""
        issues = {
            "undefined_references": [],
            "potential_issues": [],
            "conditional_definitions": []
        }
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 重要変数の使用をチェック
            for var in self.critical_variables:
                if re.search(rf'\b{var}\b', line) and '=' not in line:
                    # 変数が使用されているが代入でない
                    if self._is_potential_undefined_usage(lines, i-1, var):
                        issues["potential_issues"].append(
                            f"行{i}: '{var}' の使用時に定義済み確認が必要 - {line.strip()}"
                        )
            
            # 条件分岐内での変数定義をチェック
            if re.search(r'^\s*(if|elif|else|try|except|for|while)', line):
                next_lines = lines[i:i+10] if i < len(lines)-10 else lines[i:]
                for j, next_line in enumerate(next_lines):
                    for var in self.critical_variables:
                        if f"{var} =" in next_line:
                            issues["conditional_definitions"].append(
                                f"行{i+j+1}: '{var}' が条件分岐内で定義 - {next_line.strip()}"
                            )
        
        return issues
    
    def _is_potential_undefined_usage(self, lines: List[str], current_line: int, var: str) -> bool:
        """変数が定義前に使用されている可能性をチェック"""
        # 現在行より前の行で変数が定義されているかチェック
        for i in range(current_line):
            if f"{var} =" in lines[i] or f"{var}:" in lines[i]:
                return False
        
        # 関数パラメータとして定義されているかチェック
        for i in range(max(0, current_line-20), current_line):
            if re.search(rf'def.*{var}', lines[i]) or re.search(rf'async def.*{var}', lines[i]):
                return False
        
        return True
    
    def _display_check_results(self, file_path: str, issues: Dict[str, List[str]]):
        """チェック結果を表示"""
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        
        if total_issues == 0:
            print("✅ 変数定義順序: 問題なし")
            return
        
        print(f"⚠️ 変数定義順序の問題: {total_issues}件発見")
        
        if issues["undefined_references"]:
            print("\n🔴 未定義参照エラー:")
            for issue in issues["undefined_references"]:
                print(f"  - {issue}")
        
        if issues["potential_issues"]:
            print("\n🟡 潜在的問題:")
            for issue in issues["potential_issues"]:
                print(f"  - {issue}")
        
        if issues["conditional_definitions"]:
            print("\n🟠 条件分岐内定義:")
            for issue in issues["conditional_definitions"]:
                print(f"  - {issue}")

def test_data_flow_consistency():
    """データフロー一貫性テスト"""
    print(f"\n🔍 データフロー一貫性テスト")
    print("=" * 60)
    
    data_flow_patterns = [
        {
            "description": "OHLCVデータ取得 → 使用",
            "get_pattern": r"ohlcv_data\s*=.*(?:get_ohlcv_data|_fetch_market_data)",
            "use_pattern": r"ohlcv_data\.(?:index|empty|iloc)",
            "files": ["scalable_analysis_system.py", "auto_symbol_training.py"]
        },
        {
            "description": "カスタム期間設定 → 使用",
            "get_pattern": r"custom_period_settings\s*=",
            "use_pattern": r"custom_period_settings\.get\(",
            "files": ["auto_symbol_training.py", "engines/high_leverage_bot_orchestrator.py"]
        },
        {
            "description": "ボットインスタンス → データ取得",
            "get_pattern": r"bot\s*=.*HighLeverageBotOrchestrator",
            "use_pattern": r"bot\._fetch_market_data",
            "files": ["scalable_analysis_system.py"]
        }
    ]
    
    all_flows_ok = True
    
    for pattern in data_flow_patterns:
        print(f"\n📋 {pattern['description']}")
        
        for file_path in pattern['files']:
            full_path = f"/Users/moriwakikeita/tools/long-trader/{file_path}"
            if os.path.exists(full_path):
                flow_ok = _check_data_flow_pattern(full_path, pattern)
                if not flow_ok:
                    all_flows_ok = False
                    print(f"  ❌ {file_path}: データフロー問題")
                else:
                    print(f"  ✅ {file_path}: データフロー正常")
            else:
                print(f"  ⚠️ {file_path}: ファイルが見つかりません")
    
    return all_flows_ok

def _check_data_flow_pattern(file_path: str, pattern: Dict) -> bool:
    """特定のデータフローパターンをチェック"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        get_matches = re.findall(pattern['get_pattern'], content)
        use_matches = re.findall(pattern['use_pattern'], content)
        
        # データ取得パターンがあるのに使用パターンがない場合は問題
        if get_matches and not use_matches:
            return False
        
        # 使用パターンがあるのにデータ取得パターンがない場合も問題
        if use_matches and not get_matches:
            return False
        
        return True
        
    except Exception as e:
        print(f"    ❌ エラー: {e}")
        return False

def test_critical_variable_initialization():
    """重要変数の初期化テスト"""
    print(f"\n🔍 重要変数初期化テスト")
    print("=" * 60)
    
    initialization_rules = [
        {
            "variable": "ohlcv_data",
            "required_init": ["pd.DataFrame()", "get_ohlcv_data", "_fetch_market_data"],
            "files": ["scalable_analysis_system.py", "auto_symbol_training.py"]
        },
        {
            "variable": "custom_period_settings", 
            "required_init": ["dict", "get(", "json.loads"],
            "files": ["auto_symbol_training.py", "scalable_analysis_system.py"]
        },
        {
            "variable": "bot",
            "required_init": ["HighLeverageBotOrchestrator()", "=.*bot"],
            "files": ["scalable_analysis_system.py"]
        }
    ]
    
    all_init_ok = True
    
    for rule in initialization_rules:
        print(f"\n📋 {rule['variable']} 初期化チェック")
        
        for file_path in rule['files']:
            full_path = f"/Users/moriwakikeita/tools/long-trader/{file_path}"
            if os.path.exists(full_path):
                init_ok = _check_variable_initialization(full_path, rule)
                if not init_ok:
                    all_init_ok = False
                    print(f"  ❌ {file_path}: {rule['variable']} 初期化問題")
                else:
                    print(f"  ✅ {file_path}: {rule['variable']} 初期化正常")
    
    return all_init_ok

def _check_variable_initialization(file_path: str, rule: Dict) -> bool:
    """変数初期化パターンをチェック"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        var_name = rule['variable']
        
        # 変数が使用されているかチェック
        if var_name not in content:
            return True  # 使用されていなければOK
        
        # 初期化パターンのいずれかが存在するかチェック
        for init_pattern in rule['required_init']:
            if re.search(rf"{var_name}.*{init_pattern}", content):
                return True
        
        # 関数パラメータとして渡されているかチェック
        if re.search(rf'def.*{var_name}', content):
            return True
        
        return False
        
    except Exception as e:
        return False

def create_variable_safety_checklist():
    """変数安全性チェックリスト作成"""
    checklist = """
🛡️ 変数定義順序バグ防止チェックリスト

## 🔧 実装時のチェック項目

### 1. **変数定義前の使用防止**
   □ 変数を使用する前に必ず定義されているか確認
   □ 条件分岐内での定義は、分岐外でも定義されているか確認
   □ ループ内で定義される変数は、ループ外で初期化されているか確認

### 2. **重要変数の安全な初期化**
   □ ohlcv_data: データ取得前にNone初期化
   □ custom_period_settings: メソッド開始時にデフォルト値設定
   □ bot: インスタンス作成前にNone初期化
   □ result: 分析結果格納前に空辞書で初期化

### 3. **データフローの一貫性**
   □ データ取得 → 検証 → 使用 の順序を守る
   □ パラメータ受け渡しで型・形式が一致しているか確認
   □ 非同期処理での変数スコープを適切に管理

### 4. **エラーハンドリング**
   □ 変数が未定義の場合の適切なエラーメッセージ
   □ データ取得失敗時のフォールバック処理
   □ 例外発生時の変数状態の適切なクリーンアップ

### 5. **コードレビューポイント**
   □ メソッド内で使用される変数の定義場所を確認
   □ 条件分岐で定義される変数の代替パスを確認
   □ 複数ファイル間での変数受け渡しパターンを確認

## 🧪 テスト推奨事項

### 1. **単体テストでの確認**
   □ 各メソッドで使用される変数の初期化テスト
   □ 異常ケースでの変数状態テスト
   □ パラメータ未指定時の動作テスト

### 2. **統合テストでの確認**
   □ データフロー全体での変数一貫性テスト
   □ 複数ファイル間での変数受け渡しテスト
   □ 実際のシナリオでの変数定義順序テスト

### 3. **定期実行推奨テスト**
   □ test_variable_definition_order.py を実行
   □ test_parameter_consistency_v2.py を実行
   □ 実際のシンボル分析での動作確認

## 🚨 警告パターン

### 1. **危険な実装パターン**
   ❌ if条件内でのみ変数定義
   ❌ try-except内でのみ変数定義
   ❌ ループ内での初回のみ変数定義
   ❌ 非同期処理での変数スコープ漏れ

### 2. **推奨実装パターン**
   ✅ メソッド開始時の変数初期化
   ✅ 明示的なNone/デフォルト値設定
   ✅ 段階的な変数設定（取得→検証→使用）
   ✅ 適切なエラーハンドリング付き変数操作

## 📋 修正テンプレート

```python
def example_method(self, symbol: str, custom_period_settings: dict = None):
    # 1. 変数初期化（必須）
    ohlcv_data = None
    result = {}
    bot = None
    
    try:
        # 2. 段階的なデータ取得
        bot = self._create_bot_instance()
        ohlcv_data = self._fetch_data(symbol, custom_period_settings)
        
        # 3. データ検証
        if ohlcv_data is None or ohlcv_data.empty:
            raise ValueError("Data not available")
        
        # 4. 処理実行
        result = self._process_data(ohlcv_data)
        
        return result
        
    except Exception as e:
        # 5. 適切なエラーハンドリング
        logger.error(f"Method failed: {e}")
        return {"error": str(e)}
```
"""
    return checklist

def test_all_variable_definition_safety():
    """全変数定義安全性テスト"""
    print("🛡️ 変数定義順序バグ防止テスト v3")
    print("=" * 70)
    print("ohlcv_data未定義エラーのような問題を防ぐ包括的テスト")
    print()
    
    checker = VariableDefinitionOrderChecker()
    
    # 1. 各ファイルの変数定義順序チェック
    all_files_ok = True
    for file_path in checker.critical_files:
        full_path = f"/Users/moriwakikeita/tools/long-trader/{file_path}"
        if os.path.exists(full_path):
            issues = checker.check_variable_definition_order(full_path)
            total_issues = sum(len(issue_list) for issue_list in issues.values())
            if total_issues > 0:
                all_files_ok = False
        else:
            print(f"⚠️ ファイルが見つかりません: {file_path}")
            all_files_ok = False
    
    # 2. データフロー一貫性テスト
    data_flow_ok = test_data_flow_consistency()
    
    # 3. 重要変数初期化テスト
    init_ok = test_critical_variable_initialization()
    
    # 4. 結果サマリー
    print(f"\n🎯 変数定義安全性テスト結果")
    print("=" * 70)
    print(f"📄 ファイル変数定義順序: {'✅ 正常' if all_files_ok else '❌ 問題'}")
    print(f"🔄 データフロー一貫性: {'✅ 正常' if data_flow_ok else '❌ 問題'}")
    print(f"🔧 重要変数初期化: {'✅ 正常' if init_ok else '❌ 問題'}")
    
    overall_success = all_files_ok and data_flow_ok and init_ok
    
    print(f"\n{'='*70}")
    print(f"🏆 最終判定: {'✅ 変数安全性OK' if overall_success else '⚠️ 要修正'}")
    print(f"{'='*70}")
    
    if overall_success:
        print("🎉 変数定義順序バグが発生するリスクは低いです！")
        print("🔒 ohlcv_data未定義エラーのような問題は予防されています")
    else:
        print("🔧 変数定義に関する問題があります")
        print("⚠️ 修正してから本番環境で使用してください")
    
    # チェックリスト表示
    print(create_variable_safety_checklist())
    
    return overall_success

if __name__ == "__main__":
    success = test_all_variable_definition_safety()
    sys.exit(0 if success else 1)