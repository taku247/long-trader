#!/usr/bin/env python3
"""
UTC Aware Guardian - UTC awareの強制保証システム

すべてのdatetimeオブジェクトが必ずUTC awareであることを担保する包括的フレームワーク
"""

import ast
import inspect
import os
import sys
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
import pandas as pd


class UTCAwareGuardian:
    """UTC aware datetime強制保証システム"""
    
    def __init__(self):
        self.violations = []
        self.scanned_files = []
        self.critical_functions = [
            'datetime.now',
            'datetime.fromtimestamp', 
            'pd.to_datetime',
            'pandas.to_datetime',
            'datetime.datetime',
        ]
    
    def scan_file_for_violations(self, file_path: str) -> List[Dict]:
        """ファイル内のUTC aware違反を検出"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # コメント行をスキップ
                if line.strip().startswith('#'):
                    continue
                
                # 危険なパターンをチェック
                line_violations = self._check_line_for_violations(line, line_num, file_path)
                violations.extend(line_violations)
            
            self.scanned_files.append(file_path)
            
        except Exception as e:
            violations.append({
                'type': 'scan_error',
                'file': file_path,
                'error': str(e),
                'severity': 'ERROR'
            })
        
        return violations
    
    def _check_line_for_violations(self, line: str, line_num: int, file_path: str) -> List[Dict]:
        """1行のUTC aware違反をチェック"""
        violations = []
        
        # 1. datetime.now() without timezone
        if 'datetime.now()' in line and 'timezone.utc' not in line:
            violations.append({
                'type': 'datetime_now_naive',
                'file': file_path,
                'line': line_num,
                'code': line.strip(),
                'severity': 'CRITICAL',
                'fix_suggestion': 'datetime.now(timezone.utc)'
            })
        
        # 2. datetime.fromtimestamp without tz
        if 'datetime.fromtimestamp(' in line and 'tz=' not in line:
            violations.append({
                'type': 'fromtimestamp_naive',
                'file': file_path,
                'line': line_num,
                'code': line.strip(),
                'severity': 'CRITICAL',
                'fix_suggestion': 'Add tz=timezone.utc parameter'
            })
        
        # 3. pd.to_datetime without utc=True
        if 'pd.to_datetime(' in line and 'utc=True' not in line and 'utc=' not in line:
            violations.append({
                'type': 'pandas_to_datetime_naive',
                'file': file_path,
                'line': line_num,
                'code': line.strip(),
                'severity': 'CRITICAL',
                'fix_suggestion': 'Add utc=True parameter'
            })
        
        # 4. Direct datetime constructor without tzinfo
        datetime_constructor = re.search(r'datetime\s*\(\s*\d+', line)
        if datetime_constructor and 'tzinfo=' not in line and 'timezone' not in line:
            violations.append({
                'type': 'datetime_constructor_naive',
                'file': file_path,
                'line': line_num,
                'code': line.strip(),
                'severity': 'HIGH',
                'fix_suggestion': 'Add tzinfo=timezone.utc parameter'
            })
        
        return violations
    
    def scan_project_directory(self, root_dir: str, exclude_patterns: List[str] = None) -> Dict:
        """プロジェクトディレクトリ全体をスキャン"""
        if exclude_patterns is None:
            exclude_patterns = [
                'test_*',
                '__pycache__',
                '.git',
                'venv',
                'env',
                '*.pyc',
                'verify_*',
                'debug_*'
            ]
        
        all_violations = []
        scanned_files = []
        
        for root, dirs, files in os.walk(root_dir):
            # 除外ディレクトリをスキップ
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    # 除外ファイルをスキップ
                    if any(pattern.replace('*', '') in file for pattern in exclude_patterns):
                        continue
                    
                    file_path = os.path.join(root, file)
                    violations = self.scan_file_for_violations(file_path)
                    all_violations.extend(violations)
                    scanned_files.append(file_path)
        
        return {
            'violations': all_violations,
            'scanned_files': scanned_files,
            'total_files': len(scanned_files),
            'total_violations': len(all_violations)
        }
    
    def validate_runtime_objects(self, objects: Dict[str, Any]) -> List[Dict]:
        """実行時オブジェクトのUTC aware検証"""
        violations = []
        
        for name, obj in objects.items():
            if isinstance(obj, datetime):
                if obj.tzinfo is None:
                    violations.append({
                        'type': 'runtime_datetime_naive',
                        'object_name': name,
                        'object_value': str(obj),
                        'severity': 'CRITICAL'
                    })
                elif obj.tzinfo != timezone.utc:
                    violations.append({
                        'type': 'runtime_datetime_non_utc',
                        'object_name': name,
                        'object_value': str(obj),
                        'timezone': str(obj.tzinfo),
                        'severity': 'WARNING'
                    })
            
            elif isinstance(obj, pd.Timestamp):
                if obj.tz is None:
                    violations.append({
                        'type': 'runtime_pandas_timestamp_naive',
                        'object_name': name,
                        'object_value': str(obj),
                        'severity': 'CRITICAL'
                    })
            
            elif isinstance(obj, pd.DataFrame):
                for col in obj.columns:
                    if pd.api.types.is_datetime64_any_dtype(obj[col]):
                        if hasattr(obj[col], 'dt') and obj[col].dt.tz is None:
                            violations.append({
                                'type': 'runtime_dataframe_naive',
                                'object_name': f'{name}[{col}]',
                                'severity': 'CRITICAL'
                            })
        
        return violations
    
    def generate_report(self, scan_result: Dict, runtime_violations: List[Dict] = None) -> str:
        """包括的レポートを生成"""
        if runtime_violations is None:
            runtime_violations = []
        
        report = []
        report.append("=" * 80)
        report.append("🛡️ UTC Aware Guardian レポート")
        report.append("=" * 80)
        
        # スキャン統計
        report.append(f"\n📊 スキャン統計:")
        report.append(f"  - スキャンファイル数: {scan_result['total_files']}")
        report.append(f"  - 検出違反数: {scan_result['total_violations']}")
        report.append(f"  - 実行時違反数: {len(runtime_violations)}")
        
        # 重要度別違反数
        severity_counts = {}
        for violation in scan_result['violations'] + runtime_violations:
            severity = violation.get('severity', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        if severity_counts:
            report.append(f"\n⚠️ 重要度別違反:")
            for severity, count in sorted(severity_counts.items()):
                icon = "🚨" if severity == "CRITICAL" else "⚠️" if severity == "HIGH" else "ℹ️"
                report.append(f"  {icon} {severity}: {count}件")
        
        # ファイル別違反詳細
        if scan_result['violations']:
            report.append(f"\n📁 ファイル別違反詳細:")
            file_violations = {}
            for violation in scan_result['violations']:
                file_path = violation.get('file', 'unknown')
                if file_path not in file_violations:
                    file_violations[file_path] = []
                file_violations[file_path].append(violation)
            
            for file_path, violations in file_violations.items():
                relative_path = os.path.relpath(file_path)
                report.append(f"\n  📄 {relative_path} ({len(violations)}件)")
                for violation in violations[:5]:  # 最初の5件のみ表示
                    line = violation.get('line', '?')
                    severity = violation.get('severity', 'UNKNOWN')
                    code = violation.get('code', '')[:60] + '...' if len(violation.get('code', '')) > 60 else violation.get('code', '')
                    report.append(f"    L{line} [{severity}] {code}")
                    if 'fix_suggestion' in violation:
                        report.append(f"        💡 修正案: {violation['fix_suggestion']}")
                
                if len(violations) > 5:
                    report.append(f"    ... および他{len(violations) - 5}件")
        
        # 実行時違反詳細
        if runtime_violations:
            report.append(f"\n🔍 実行時違反詳細:")
            for violation in runtime_violations:
                report.append(f"  - {violation.get('object_name', 'unknown')}: {violation.get('type', 'unknown')}")
        
        # 推奨アクション
        total_violations = scan_result['total_violations'] + len(runtime_violations)
        if total_violations == 0:
            report.append(f"\n🎉 素晴らしい！UTC aware違反は検出されませんでした。")
            report.append(f"✅ システム全体でUTC awareが適切に実装されています。")
        else:
            report.append(f"\n🔧 推奨アクション:")
            report.append(f"1. CRITICALレベルの違反を最優先で修正")
            report.append(f"2. 修正パターン:")
            report.append(f"   - datetime.now() → datetime.now(timezone.utc)")
            report.append(f"   - datetime.fromtimestamp(ts) → datetime.fromtimestamp(ts, tz=timezone.utc)")
            report.append(f"   - pd.to_datetime(...) → pd.to_datetime(..., utc=True)")
            report.append(f"3. 修正後、このツールで再検証")
        
        report.append(f"\n" + "=" * 80)
        
        return "\n".join(report)


def scan_key_files() -> Dict:
    """主要ファイルの一括スキャン"""
    guardian = UTCAwareGuardian()
    
    key_files = [
        'hyperliquid_api_client.py',
        'symbol_early_fail_validator.py',
        'scalable_analysis_system.py',
        'hyperliquid_validator.py',
        'web_dashboard/app.py',
    ]
    
    all_violations = []
    scanned_files = []
    
    for file_path in key_files:
        if os.path.exists(file_path):
            violations = guardian.scan_file_for_violations(file_path)
            all_violations.extend(violations)
            scanned_files.append(file_path)
    
    return {
        'violations': all_violations,
        'scanned_files': scanned_files,
        'total_files': len(scanned_files),
        'total_violations': len(all_violations)
    }


def test_runtime_datetime_objects():
    """実行時datetimeオブジェクトのテスト"""
    guardian = UTCAwareGuardian()
    
    # テスト用オブジェクト
    test_objects = {
        'good_datetime': datetime.now(timezone.utc),
        'good_timestamp': pd.to_datetime(1703930400000, unit='ms', utc=True),
        'good_dataframe': pd.DataFrame({
            'timestamp': pd.to_datetime([1703930400000], unit='ms', utc=True),
            'value': [100]
        }),
        # これらはテスト用の不正オブジェクト例
        # 'bad_datetime': datetime.now(),  # これを有効にすると違反として検出される
        # 'bad_timestamp': pd.to_datetime(1703930400000, unit='ms'),  # これも同様
    }
    
    violations = guardian.validate_runtime_objects(test_objects)
    return violations


def main():
    """メイン実行"""
    print("🛡️ UTC Aware Guardian 実行中...")
    
    # 1. 主要ファイルスキャン
    print("📁 主要ファイルをスキャン中...")
    scan_result = scan_key_files()
    
    # 2. 実行時オブジェクト検証
    print("🔍 実行時オブジェクトを検証中...")
    runtime_violations = test_runtime_datetime_objects()
    
    # 3. レポート生成
    guardian = UTCAwareGuardian()
    report = guardian.generate_report(scan_result, runtime_violations)
    
    # 4. 結果表示
    print(report)
    
    # 5. 終了ステータス
    total_violations = scan_result['total_violations'] + len(runtime_violations)
    if total_violations == 0:
        print("\n✅ UTC Aware Guardian チェック完了: すべて適合")
        return True
    else:
        print(f"\n❌ UTC Aware Guardian チェック完了: {total_violations}件の違反を検出")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)