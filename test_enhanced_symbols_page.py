#!/usr/bin/env python3
"""
拡張戦略分析銘柄管理ページの期間指定機能テスト
"""

import sys
import os
import tempfile

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_page_ui_elements():
    """ページのUI要素存在確認"""
    print("🔍 拡張銘柄管理ページUI要素テスト")
    print("=" * 50)
    
    try:
        # HTMLファイルを読み込んで期間指定要素の存在確認
        html_path = "/Users/moriwakikeita/tools/long-trader/web_dashboard/templates/symbols_enhanced.html"
        
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 期間指定UI要素の存在確認
        ui_elements = [
            'id="periodMode"',
            'id="startDate"', 
            'id="endDate"',
            'id="startDateField"',
            'id="endDateField"',
            'id="periodInfo"',
            'id="periodInfoText"',
            'function togglePeriodOptions',
            '支持線検出用に200本前から取得',
            'カスタム期間指定'
        ]
        
        missing_elements = []
        for element in ui_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ 以下のUI要素が見つかりません:")
            for element in missing_elements:
                print(f"   - {element}")
            return False
        else:
            print("✅ 全てのUI要素が存在します:")
            for element in ui_elements:
                print(f"   ✓ {element}")
            return True
            
    except Exception as e:
        print(f"❌ UIテストエラー: {e}")
        return False

def test_javascript_functions():
    """JavaScript関数の存在確認"""
    print(f"\n🔍 JavaScript関数テスト")
    print("=" * 50)
    
    try:
        html_path = "/Users/moriwakikeita/tools/long-trader/web_dashboard/templates/symbols_enhanced.html"
        
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # JavaScript関数の存在確認
        js_functions = [
            'function togglePeriodOptions()',
            'function updateExecutionEstimate()',
            'payload.period_mode = periodMode',
            'payload.start_date = startDate',
            'payload.end_date = endDate',
            'カスタム期間(+200本前データ)',
            '自動期間設定'
        ]
        
        missing_functions = []
        for func in js_functions:
            if func not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ 以下のJavaScript要素が見つかりません:")
            for func in missing_functions:
                print(f"   - {func}")
            return False
        else:
            print("✅ 全てのJavaScript要素が存在します:")
            for func in js_functions:
                print(f"   ✓ {func}")
            return True
            
    except Exception as e:
        print(f"❌ JavaScriptテストエラー: {e}")
        return False

def test_route_accessibility():
    """ルートアクセシビリティテスト"""
    print(f"\n🔍 ルートアクセシビリティテスト")
    print("=" * 50)
    
    try:
        # app.pyでルート定義を確認
        app_path = "/Users/moriwakikeita/tools/long-trader/web_dashboard/app.py"
        
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 拡張銘柄管理ページのルート確認
        route_elements = [
            "@self.app.route('/symbols-enhanced')",
            "def symbols_enhanced_page():",
            "render_template('symbols_enhanced.html')"
        ]
        
        missing_routes = []
        for element in route_elements:
            if element not in content:
                missing_routes.append(element)
        
        if missing_routes:
            print(f"❌ 以下のルート要素が見つかりません:")
            for element in missing_routes:
                print(f"   - {element}")
            return False
        else:
            print("✅ 拡張銘柄管理ページのルートが正しく定義されています:")
            print("   ✓ URL: /symbols-enhanced")
            print("   ✓ Template: symbols_enhanced.html")
            return True
            
    except Exception as e:
        print(f"❌ ルートテストエラー: {e}")
        return False

def test_backend_integration():
    """バックエンド統合確認"""
    print(f"\n🔍 バックエンド統合テスト")
    print("=" * 50)
    
    try:
        # 既存のカスタム期間機能テストを実行
        from test_custom_period_feature import test_api_parameter_flow
        
        print("📡 APIパラメータフロー確認:")
        api_success = test_api_parameter_flow()
        
        if api_success:
            print("✅ バックエンド統合OK - 期間設定が正しく処理されます")
            return True
        else:
            print("❌ バックエンド統合に問題があります")
            return False
            
    except Exception as e:
        print(f"❌ バックエンド統合テストエラー: {e}")
        return False

if __name__ == "__main__":
    print("🚀 拡張戦略分析銘柄管理ページテスト開始")
    print("=" * 70)
    
    success1 = test_page_ui_elements()
    success2 = test_javascript_functions()
    success3 = test_route_accessibility()
    success4 = test_backend_integration()
    
    print(f"\n🎯 拡張銘柄管理ページテスト結果")
    print("=" * 60)
    print(f"🎨 UI要素: {'✅ 完備' if success1 else '❌ 不備'}")
    print(f"⚡ JavaScript: {'✅ 完備' if success2 else '❌ 不備'}")  
    print(f"🛣️ ルート: {'✅ 正常' if success3 else '❌ 問題'}")
    print(f"🔗 バックエンド統合: {'✅ 正常' if success4 else '❌ 問題'}")
    
    overall_success = success1 and success2 and success3 and success4
    
    if overall_success:
        print(f"\n🎉 拡張戦略分析銘柄管理ページに期間指定機能が正常に実装されました！")
        print("📍 アクセス方法:")
        print("   1. cd web_dashboard && python app.py")
        print("   2. http://localhost:5001/symbols-enhanced")
        print("   3. 「分析期間設定」でカスタム期間指定を選択")
        print("   4. 開始・終了日時を指定して銘柄追加実行")
    else:
        print(f"\n⚠️ 一部問題があります - 修正が必要")
    
    sys.exit(0 if overall_success else 1)