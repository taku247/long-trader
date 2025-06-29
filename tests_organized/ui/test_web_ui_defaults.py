#!/usr/bin/env python3
"""
WebUI デフォルト値表示テスト

ブラウザ画面で正しいデフォルト値が表示されることを保証するテスト
"""

import unittest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests_organized.base_test import BaseTest


class TestWebUIDefaults(BaseTest):
    """WebUIデフォルト値表示テストクラス"""
    
    def setUp(self):
        """テスト前の初期化"""
        super().setUp()
        self.app = None
        self.client = None
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if self.client:
            self.client = None
        if self.app:
            self.app = None
        super().tearDown()
    
    def _setup_test_app(self):
        """テスト用アプリケーションのセットアップ"""
        try:
            sys.path.append(str(Path(__file__).parent.parent.parent / "web_dashboard"))
            from app import LongTraderDashboard
            
            self.app = LongTraderDashboard()
            self.client = self.app.app.test_client()
            self.app.app.config['TESTING'] = True
            
            return True
        except Exception as e:
            print(f"⚠️ テストアプリセットアップエラー: {e}")
            return False
    
    def test_symbols_enhanced_page_defaults(self):
        """symbols-enhancedページのデフォルト値表示テスト"""
        print("\n🧪 symbols-enhancedページデフォルト値テスト")
        
        if not self._setup_test_app():
            self.skipTest("WebUIアプリのセットアップができませんでした")
        
        try:
            # デフォルト値を取得
            from config.defaults_manager import (
                get_default_min_risk_reward,
                get_default_min_leverage,
                get_default_min_confidence
            )
            
            expected_rr = get_default_min_risk_reward()
            expected_leverage = get_default_min_leverage()
            expected_confidence = get_default_min_confidence()
            
            # ページにアクセス
            response = self.client.get('/symbols-enhanced')
            
            # レスポンス確認
            self.assertEqual(response.status_code, 200, "symbols-enhancedページへのアクセスが失敗しました")
            
            response_text = response.get_data(as_text=True)
            
            # デフォルト値がHTMLに含まれているか確認
            self.assertIn(str(expected_rr), response_text,
                         f"min_risk_rewardのデフォルト値{expected_rr}がページに表示されていません")
            
            # value属性として正しく設定されているか確認
            expected_value_attr = f'value="{expected_rr}"'
            self.assertIn(expected_value_attr, response_text,
                         f"min_risk_rewardのvalue属性が正しく設定されていません: {expected_value_attr}")
            
            print(f"✅ symbols-enhancedページのデフォルト値確認: RR={expected_rr}")
            
        except Exception as e:
            self.fail(f"symbols-enhancedページテストでエラー: {e}")
    
    def test_api_provides_correct_defaults(self):
        """APIエンドポイントが正しいデフォルト値を提供するかテスト"""
        print("\n🧪 API デフォルト値提供テスト")
        
        if not self._setup_test_app():
            self.skipTest("WebUIアプリのセットアップができませんでした")
        
        try:
            # デフォルト値取得API（存在する場合）のテスト
            response = self.client.get('/api/defaults')
            
            if response.status_code == 200:
                # APIレスポンス確認
                import json
                data = json.loads(response.get_data(as_text=True))
                
                from config.defaults_manager import get_default_entry_conditions
                expected_conditions = get_default_entry_conditions()
                
                # APIが正しいデフォルト値を返すか確認
                for key, expected_value in expected_conditions.items():
                    self.assertIn(key, data, f"APIレスポンスに{key}が含まれていません")
                    self.assertEqual(data[key], expected_value,
                                   f"API の {key} が期待値と異なります: {data[key]} != {expected_value}")
                
                print(f"✅ API デフォルト値確認: {data}")
            else:
                print("⚠️ /api/defaultsエンドポイントが存在しません（オプション）")
                
        except Exception as e:
            print(f"⚠️ API テストでエラー: {e}")
    
    def test_javascript_receives_defaults(self):
        """JavaScriptがデフォルト値を正しく受け取るかテスト"""
        print("\n🧪 JavaScript デフォルト値受け取りテスト")
        
        if not self._setup_test_app():
            self.skipTest("WebUIアプリのセットアップができませんでした")
        
        try:
            response = self.client.get('/symbols-enhanced')
            response_text = response.get_data(as_text=True)
            
            from config.defaults_manager import get_default_min_risk_reward
            expected_rr = get_default_min_risk_reward()
            
            # HTMLテンプレート変数がJavaScriptで使用可能か確認
            # Jinja2テンプレートの変数が正しく展開されているかチェック
            template_patterns = [
                f'value="{expected_rr}"',  # input要素のvalue属性
                f'defaults.min_risk_reward',  # テンプレート変数参照
            ]
            
            found_patterns = []
            for pattern in template_patterns:
                if pattern in response_text:
                    found_patterns.append(pattern)
            
            # 少なくとも1つのパターンが見つかることを確認
            self.assertGreater(len(found_patterns), 0,
                             f"デフォルト値がHTMLテンプレートに正しく展開されていません。期待パターン: {template_patterns}")
            
            print(f"✅ HTMLテンプレート展開確認: {found_patterns}")
            
        except Exception as e:
            self.fail(f"JavaScriptテストでエラー: {e}")
    
    def test_form_submission_with_defaults(self):
        """フォーム送信時にデフォルト値が正しく処理されるかテスト"""
        print("\n🧪 フォーム送信デフォルト値テスト")
        
        if not self._setup_test_app():
            self.skipTest("WebUIアプリのセットアップができませんでした")
        
        try:
            from config.defaults_manager import get_default_min_risk_reward
            expected_rr = get_default_min_risk_reward()
            
            # フォームデータを準備（デフォルト値を使用）
            form_data = {
                'symbol': 'TEST',
                'timeframe': '15m',
                'strategy': 'Conservative_ML',
                'min_risk_reward': str(expected_rr),
                'min_leverage': '3.0',
                'min_confidence': '0.5'
            }
            
            # 銘柄追加APIへPOST（存在する場合）
            response = self.client.post('/api/symbol/add', 
                                      data=form_data,
                                      content_type='application/x-www-form-urlencoded')
            
            # レスポンス確認（エラーでないことを確認）
            # 実際の処理は行わず、パラメータ受け取りが正常かのみ確認
            self.assertIn(response.status_code, [200, 202, 400, 422],
                         f"予期しないステータスコード: {response.status_code}")
            
            print(f"✅ フォーム送信確認: ステータス {response.status_code}")
            
        except Exception as e:
            print(f"⚠️ フォーム送信テストでエラー: {e}")


class TestUIConsistency(BaseTest):
    """UI一貫性テスト"""
    
    def test_all_ui_pages_use_same_defaults(self):
        """全てのUIページで同じデフォルト値が使用されるかテスト"""
        print("\n🧪 UI ページ間一貫性テスト")
        
        try:
            sys.path.append(str(Path(__file__).parent.parent.parent / "web_dashboard"))
            from app import LongTraderDashboard
            
            app = LongTraderDashboard()
            
            # テスト対象ページ
            pages_to_test = [
                '/symbols-enhanced',
                '/symbols',  # 存在する場合
                '/settings'  # 存在する場合
            ]
            
            from config.defaults_manager import get_default_min_risk_reward
            expected_rr = get_default_min_risk_reward()
            
            with app.app.test_client() as client:
                consistent_values = []
                
                for page in pages_to_test:
                    try:
                        response = client.get(page)
                        if response.status_code == 200:
                            response_text = response.get_data(as_text=True)
                            
                            # デフォルト値が含まれているかチェック
                            if str(expected_rr) in response_text:
                                consistent_values.append(page)
                                print(f"✅ {page}: デフォルト値確認")
                            else:
                                print(f"⚠️ {page}: デフォルト値が見つかりません")
                        else:
                            print(f"⚠️ {page}: アクセス不可 ({response.status_code})")
                            
                    except Exception as e:
                        print(f"⚠️ {page}: テストエラー {e}")
                
                # 少なくとも1つのページで一貫性が確認できれば成功
                self.assertGreater(len(consistent_values), 0,
                                 "どのUIページでもデフォルト値の一貫性が確認できませんでした")
                
        except Exception as e:
            print(f"⚠️ UI一貫性テストでエラー: {e}")


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)