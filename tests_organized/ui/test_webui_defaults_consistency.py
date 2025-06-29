#!/usr/bin/env python3
"""
WebUIデフォルト値の一貫性テスト

ブラウザから銘柄追加する際のデフォルト値が
中央管理システムと一致していることを確認
"""

import unittest
import re
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests_organized.base_test import BaseTest
from config.defaults_manager import get_default_min_risk_reward, get_default_min_leverage, get_default_min_confidence


class TestWebUIDefaultsConsistency(BaseTest):
    """WebUIデフォルト値一貫性テストクラス"""
    
    def test_symbols_enhanced_html_defaults(self):
        """symbols_enhanced.htmlのデフォルト値が中央システムと一致することを確認"""
        print("\n🧪 WebUIテンプレートデフォルト値チェック")
        
        # 中央システムから期待値を取得
        expected_min_risk_reward = get_default_min_risk_reward()
        expected_min_leverage = get_default_min_leverage()
        expected_min_confidence = get_default_min_confidence()
        
        print(f"期待値: min_risk_reward={expected_min_risk_reward}, min_leverage={expected_min_leverage}, min_confidence={expected_min_confidence}")
        
        # HTMLテンプレートを読み込み
        template_path = Path(__file__).parent.parent.parent / "web_dashboard" / "templates" / "symbols_enhanced.html"
        self.assertTrue(template_path.exists(), f"テンプレートファイルが見つかりません: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # JavaScript resetFilterParams関数内のデフォルト値をチェック
        violations = []
        
        # min_risk_reward値の検索
        risk_reward_pattern = r"getElementById\('minRiskReward'\)\.value\s*=\s*'([^']+)'"
        risk_reward_matches = re.findall(risk_reward_pattern, html_content)
        for match in risk_reward_matches:
            actual_value = float(match)
            if actual_value != expected_min_risk_reward:
                violations.append(f"minRiskReward JavaScript値: {actual_value} != 期待値: {expected_min_risk_reward}")
        
        # min_leverage値の検索
        leverage_pattern = r"getElementById\('minLeverage'\)\.value\s*=\s*'([^']+)'"
        leverage_matches = re.findall(leverage_pattern, html_content)
        for match in leverage_matches:
            actual_value = float(match)
            if actual_value != expected_min_leverage:
                violations.append(f"minLeverage JavaScript値: {actual_value} != 期待値: {expected_min_leverage}")
        
        # min_confidence値の検索
        confidence_pattern = r"getElementById\('minConfidence'\)\.value\s*=\s*'([^']+)'"
        confidence_matches = re.findall(confidence_pattern, html_content)
        for match in confidence_matches:
            actual_value = float(match)
            if actual_value != expected_min_confidence:
                violations.append(f"minConfidence JavaScript値: {actual_value} != 期待値: {expected_min_confidence}")
        
        # HTMLフォームのvalue属性もチェック
        # min_leverage input値
        leverage_input_pattern = r'<input[^>]*id="minLeverage"[^>]*value="([^"]+)"'
        leverage_input_matches = re.findall(leverage_input_pattern, html_content)
        for match in leverage_input_matches:
            actual_value = float(match)
            if actual_value != expected_min_leverage:
                violations.append(f"minLeverage input値: {actual_value} != 期待値: {expected_min_leverage}")
        
        # min_confidence input値
        confidence_input_pattern = r'<input[^>]*id="minConfidence"[^>]*value="([^"]+)"'
        confidence_input_matches = re.findall(confidence_input_pattern, html_content)
        for match in confidence_input_matches:
            actual_value = float(match)
            if actual_value != expected_min_confidence:
                violations.append(f"minConfidence input値: {actual_value} != 期待値: {expected_min_confidence}")
        
        # 違反がある場合はテスト失敗
        if violations:
            violation_msg = "\n".join([f"- {v}" for v in violations])
            self.fail(f"WebUIデフォルト値の不整合が見つかりました:\n{violation_msg}")
        
        print("✅ WebUIテンプレートのデフォルト値は中央システムと一致しています")
    
    def test_template_risk_reward_uses_dynamic_defaults(self):
        """min_risk_rewardのHTMLテンプレート値が動的に中央デフォルトを参照することを確認"""
        print("\n🧪 動的デフォルト値参照チェック")
        
        template_path = Path(__file__).parent.parent.parent / "web_dashboard" / "templates" / "symbols_enhanced.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # min_risk_reward inputが動的にdefaults値を使用しているかチェック
        dynamic_pattern = r'value="\{\{\s*defaults\.min_risk_reward\s+if\s+defaults\s+else\s+[^}]+\s*\}\}"'
        
        if not re.search(dynamic_pattern, html_content):
            self.fail("min_risk_reward inputフィールドが動的なdefaults値を使用していません")
        
        print("✅ min_risk_rewardは動的にdefaults値を参照しています")


if __name__ == '__main__':
    unittest.main()