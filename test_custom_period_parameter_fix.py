#!/usr/bin/env python3
"""
カスタム期間パラメータ修正のテスト
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_method_signatures():
    """メソッドシグネチャのテスト"""
    print("🔍 メソッドシグネチャテスト")
    print("=" * 50)
    
    try:
        from auto_symbol_training import AutoSymbolTrainer
        import inspect
        
        trainer = AutoSymbolTrainer()
        
        # 各メソッドのシグネチャ確認
        methods_to_check = [
            'add_symbol_with_training',
            '_fetch_and_validate_data',
            '_run_comprehensive_backtest'
        ]
        
        success_count = 0
        for method_name in methods_to_check:
            if hasattr(trainer, method_name):
                method = getattr(trainer, method_name)
                signature = inspect.signature(method)
                params = list(signature.parameters.keys())
                
                print(f"✅ {method_name}:")
                print(f"   パラメータ: {params}")
                
                # custom_period_settingsパラメータの存在確認
                if 'custom_period_settings' in params:
                    print(f"   ✓ custom_period_settings パラメータ存在")
                    success_count += 1
                else:
                    print(f"   ❌ custom_period_settings パラメータ不在")
            else:
                print(f"❌ {method_name} メソッドが見つかりません")
        
        print(f"\n📊 結果: {success_count}/{len(methods_to_check)} メソッドが正しく修正されています")
        return success_count == len(methods_to_check)
        
    except Exception as e:
        print(f"❌ シグネチャテストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_flow():
    """パラメータフロー確認"""
    print(f"\n🔍 パラメータフロー確認")
    print("=" * 50)
    
    try:
        # auto_symbol_training.pyの内容を確認
        file_path = "/Users/moriwakikeita/tools/long-trader/auto_symbol_training.py"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 重要な修正箇所の確認
        check_points = [
            "_fetch_and_validate_data, symbol, custom_period_settings",
            "_run_comprehensive_backtest, symbol, selected_strategies, selected_timeframes, strategy_configs, skip_pretask_creation, custom_period_settings",
            "async def _fetch_and_validate_data(self, symbol: str, custom_period_settings: dict = None)",
            "async def _run_comprehensive_backtest(self, symbol: str, selected_strategies: list = None, selected_timeframes: list = None, strategy_configs: list = None, skip_pretask_creation: bool = False, custom_period_settings: dict = None)"
        ]
        
        missing_fixes = []
        for point in check_points:
            if point not in content:
                missing_fixes.append(point)
        
        if missing_fixes:
            print(f"❌ 以下の修正が見つかりません:")
            for fix in missing_fixes:
                print(f"   - {fix}")
            return False
        else:
            print("✅ 全ての重要な修正が確認されました:")
            for point in check_points:
                print(f"   ✓ {point[:50]}...")
            return True
            
    except Exception as e:
        print(f"❌ パラメータフロー確認エラー: {e}")
        return False

def test_simple_instantiation():
    """シンプルなインスタンス化テスト"""
    print(f"\n🔍 基本動作テスト")
    print("=" * 50)
    
    try:
        from auto_symbol_training import AutoSymbolTrainer
        
        # インスタンス化
        trainer = AutoSymbolTrainer()
        print("✅ AutoSymbolTrainer インスタンス化成功")
        
        # パラメータ付きメソッド呼び出し準備テスト
        test_period_settings = {
            'mode': 'custom',
            'start_date': '2025-06-01T17:42:00',
            'end_date': '2025-06-25T17:42:00'
        }
        
        print(f"✅ テスト用期間設定準備: {test_period_settings}")
        
        # メソッドシグネチャでエラーが出ないかチェック（実際には実行しない）
        import inspect
        sig = inspect.signature(trainer.add_symbol_with_training)
        try:
            # 引数バインディングテスト
            bound_args = sig.bind('TEST', custom_period_settings=test_period_settings)
            bound_args.apply_defaults()
            print("✅ パラメータバインディング成功")
            return True
        except Exception as e:
            print(f"❌ パラメータバインディングエラー: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 基本動作テストエラー: {e}")
        return False

if __name__ == "__main__":
    print("🚀 カスタム期間パラメータ修正テスト開始")
    print("=" * 70)
    
    success1 = test_method_signatures()
    success2 = test_parameter_flow()
    success3 = test_simple_instantiation()
    
    print(f"\n🎯 修正テスト結果")
    print("=" * 50)
    print(f"📝 メソッドシグネチャ: {'✅ 正常' if success1 else '❌ 問題'}")
    print(f"🔄 パラメータフロー: {'✅ 正常' if success2 else '❌ 問題'}")
    print(f"⚡ 基本動作: {'✅ 正常' if success3 else '❌ 問題'}")
    
    overall_success = success1 and success2 and success3
    
    if overall_success:
        print(f"\n🎉 カスタム期間パラメータの修正が完了しました！")
        print("🔄 再度XRPで期間指定テストを実行してください")
    else:
        print(f"\n⚠️ 修正に問題があります - 追加対応が必要")
    
    sys.exit(0 if overall_success else 1)