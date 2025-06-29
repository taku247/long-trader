#!/usr/bin/env python3
"""
ハードコード値検出スクリプト

設定ファイル内のハードコードされたパラメータを検出し、
"use_default"マーカーによる一元管理への移行を支援する。
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import re


class HardcodedValueDetector:
    """ハードコード値検出クラス"""
    
    def __init__(self, project_root: str = None):
        """初期化"""
        self.project_root = Path(project_root or Path(__file__).parent)
        
        # 検出対象パラメータ（defaults.jsonで管理すべきもの）
        self.target_parameters = {
            'min_risk_reward': 'entry_conditions',
            'min_leverage': 'entry_conditions', 
            'min_confidence': 'entry_conditions',
            'max_leverage': 'leverage_limits',
            'min_support_strength': 'technical_analysis',
            'min_resistance_strength': 'technical_analysis',
            'btc_correlation_threshold': 'market_analysis',
            'stop_loss_percent': 'risk_management',
            'take_profit_percent': 'risk_management',
            'leverage_cap': 'leverage_limits',
            'risk_multiplier': 'strategy_config',
            'confidence_boost': 'strategy_config'
        }
        
        # 除外ファイル（バックアップなど）
        self.exclude_patterns = [
            'backup*',
            '*backup*',
            '*.backup.*',
            'test_*',
            '*_test*'
        ]
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """ファイルを除外すべきかチェック"""
        file_name = file_path.name
        
        for pattern in self.exclude_patterns:
            if file_path.match(pattern):
                return True
        
        return False
    
    def detect_hardcoded_values(self) -> Dict[str, List[Dict]]:
        """ハードコード値を検出"""
        issues = {}
        
        # JSONファイルを検索
        config_dir = self.project_root / "config"
        json_files = list(config_dir.glob("*.json"))
        
        for json_file in json_files:
            if self.should_exclude_file(json_file):
                print(f"⏭️ スキップ: {json_file.name}")
                continue
            
            file_issues = self._analyze_json_file(json_file)
            if file_issues:
                issues[str(json_file.relative_to(self.project_root))] = file_issues
        
        return issues
    
    def _analyze_json_file(self, file_path: Path) -> List[Dict]:
        """個別JSONファイルの分析"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._analyze_dict_recursive(data, [], issues, file_path.name)
            
        except Exception as e:
            print(f"⚠️ {file_path.name} 読み込みエラー: {e}")
        
        return issues
    
    def _analyze_dict_recursive(self, data, path: List[str], issues: List[Dict], filename: str):
        """再帰的に辞書を分析"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = path + [key]
                
                # 対象パラメータかチェック
                if key in self.target_parameters:
                    if isinstance(value, (int, float)) and value != "use_default":
                        issues.append({
                            'parameter': key,
                            'path': '.'.join(current_path),
                            'value': value,
                            'category': self.target_parameters[key],
                            'recommendation': 'Replace with "use_default"',
                            'file': filename
                        })
                
                # 再帰的に探索
                self._analyze_dict_recursive(value, current_path, issues, filename)
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = path + [f"[{i}]"]
                self._analyze_dict_recursive(item, current_path, issues, filename)
    
    def detect_python_hardcoded_values(self) -> Dict[str, List[Dict]]:
        """Pythonファイル内のハードコード値を検出"""
        issues = {}
        
        # Pythonファイルを検索
        python_files = list(self.project_root.rglob("*.py"))
        
        for py_file in python_files:
            if self.should_exclude_file(py_file) or 'test' in str(py_file):
                continue
            
            file_issues = self._analyze_python_file(py_file)
            if file_issues:
                issues[str(py_file.relative_to(self.project_root))] = file_issues
        
        return issues
    
    def _analyze_python_file(self, file_path: Path) -> List[Dict]:
        """個別Pythonファイルの分析"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # 対象パラメータの検索
                for param in self.target_parameters:
                    # 辞書形式でのハードコード値検出
                    pattern = f"['\"{param}['\"]\\s*:\\s*([0-9]+\\.?[0-9]*)"
                    matches = re.findall(pattern, line)
                    
                    for match in matches:
                        # get_default_* 関数呼び出しでない場合のみ問題とする
                        if 'get_default_' not in line:
                            issues.append({
                                'parameter': param,
                                'line': line_num,
                                'value': match,
                                'code': line.strip(),
                                'category': self.target_parameters[param],
                                'recommendation': f'Use get_default_{param}() function',
                                'file': file_path.name
                            })
        
        except Exception as e:
            print(f"⚠️ {file_path.name} 読み込みエラー: {e}")
        
        return issues
    
    def generate_report(self) -> str:
        """検出レポート生成"""
        json_issues = self.detect_hardcoded_values()
        python_issues = self.detect_python_hardcoded_values()
        
        report = []
        report.append("🔍 ハードコード値検出レポート")
        report.append("=" * 50)
        
        # JSONファイルの問題
        if json_issues:
            report.append("\n📄 JSONファイルの問題:")
            for file, issues in json_issues.items():
                report.append(f"\n  📁 {file}:")
                for issue in issues:
                    report.append(f"    ❌ {issue['path']}: {issue['value']} ({issue['recommendation']})")
        else:
            report.append("\n✅ JSONファイル: 問題なし")
        
        # Pythonファイルの問題
        if python_issues:
            report.append("\n🐍 Pythonファイルの問題:")
            for file, issues in python_issues.items():
                report.append(f"\n  📁 {file}:")
                for issue in issues:
                    report.append(f"    ❌ Line {issue['line']}: {issue['parameter']}={issue['value']}")
                    report.append(f"        Code: {issue['code']}")
                    report.append(f"        Fix: {issue['recommendation']}")
        else:
            report.append("\n✅ Pythonファイル: 問題なし")
        
        # サマリー
        total_json_issues = sum(len(issues) for issues in json_issues.values())
        total_python_issues = sum(len(issues) for issues in python_issues.values())
        total_issues = total_json_issues + total_python_issues
        
        report.append(f"\n📊 検出サマリー:")
        report.append(f"  JSONファイル問題: {total_json_issues}")
        report.append(f"  Pythonファイル問題: {total_python_issues}")
        report.append(f"  総問題数: {total_issues}")
        
        if total_issues == 0:
            report.append("\n🎉 ハードコード値は検出されませんでした！")
        else:
            report.append(f"\n⚠️ {total_issues}個の問題が検出されました。修正を推奨します。")
        
        return '\n'.join(report)
    
    def suggest_defaults_json_structure(self) -> str:
        """defaults.jsonの推奨構造を提案"""
        suggestions = {
            'entry_conditions': ['min_risk_reward', 'min_leverage', 'min_confidence'],
            'leverage_limits': ['max_leverage', 'leverage_cap'],
            'technical_analysis': ['min_support_strength', 'min_resistance_strength'],
            'market_analysis': ['btc_correlation_threshold'],
            'risk_management': ['stop_loss_percent', 'take_profit_percent'],
            'strategy_config': ['risk_multiplier', 'confidence_boost']
        }
        
        suggested_structure = {
            "description": "システム全体のデフォルト値定義（拡張版）",
            "version": "2.0.0",
            "last_updated": "2025-06-28"
        }
        
        for category, params in suggestions.items():
            suggested_structure[category] = {param: f"<{param}_default_value>" for param in params}
        
        return json.dumps(suggested_structure, indent=2, ensure_ascii=False)


def main():
    """メイン実行"""
    detector = HardcodedValueDetector()
    
    print("🔍 ハードコード値検出を開始...")
    
    report = detector.generate_report()
    print(report)
    
    # レポートをファイルに保存
    report_file = "hardcoded_values_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 詳細レポートを保存: {report_file}")
    
    # defaults.json構造提案
    suggestions_file = "suggested_defaults_structure.json"
    suggestions = detector.suggest_defaults_json_structure()
    with open(suggestions_file, 'w', encoding='utf-8') as f:
        f.write(suggestions)
    
    print(f"💡 推奨defaults.json構造を保存: {suggestions_file}")


if __name__ == "__main__":
    main()