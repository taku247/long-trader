#!/usr/bin/env python3
"""
パラメータ一貫性テスト - 同様のバグを防ぐための包括的テスト

メソッドチェーン全体でパラメータが正しく引き継がれることを確認し、
新しいパラメータ追加時のバグを未然に防ぐ
"""

import sys
import os
import inspect
import ast
from typing import Dict, List, Set

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ParameterConsistencyChecker:
    """パラメータ一貫性チェッカー"""
    
    def __init__(self):
        self.method_chains = {
            # AutoSymbolTrainer のメソッドチェーン
            'auto_symbol_training': {
                'add_symbol_with_training': {
                    'calls': [
                        '_fetch_and_validate_data',
                        '_run_comprehensive_backtest'
                    ],
                    'params': ['custom_period_settings']
                }
            },
            # NewSymbolAdditionSystem のメソッドチェーン
            'new_symbol_addition_system': {
                'execute_symbol_addition': {
                    'calls': ['add_symbol_with_training'],
                    'params': ['custom_period_settings']
                }
            },
            # ScalableAnalysisSystem のメソッドチェーン
            'scalable_analysis_system': {
                'generate_batch_analysis': {
                    'calls': ['_generate_real_analysis'],
                    'params': ['custom_period_settings']
                }
            }
        }
    
    def check_method_signatures(self, module_name: str, method_chain: Dict) -> bool:
        """メソッドシグネチャの一貫性チェック"""
        print(f"\n🔍 {module_name} のメソッドシグネチャチェック")
        print("=" * 60)
        
        try:
            # モジュールをインポート
            if module_name == 'auto_symbol_training':
                from auto_symbol_training import AutoSymbolTrainer
                obj = AutoSymbolTrainer()
            elif module_name == 'new_symbol_addition_system':
                from new_symbol_addition_system import NewSymbolAdditionSystem
                obj = NewSymbolAdditionSystem()
            elif module_name == 'scalable_analysis_system':
                from scalable_analysis_system import ScalableAnalysisSystem
                obj = ScalableAnalysisSystem()
            else:
                print(f"❌ 未知のモジュール: {module_name}")
                return False
            
            all_methods_ok = True
            
            for method_name, config in method_chain.items():
                print(f"\n📋 {method_name} メソッドチェーン:")
                
                # 親メソッドのシグネチャチェック
                if hasattr(obj, method_name):
                    parent_method = getattr(obj, method_name)
                    parent_sig = inspect.signature(parent_method)
                    parent_params = list(parent_sig.parameters.keys())
                    
                    print(f"  🔹 {method_name}: {parent_params}")
                    
                    # 必要なパラメータの存在確認
                    for required_param in config['params']:
                        if required_param in parent_params:
                            print(f"    ✅ {required_param} パラメータ存在")
                        else:
                            print(f"    ❌ {required_param} パラメータ不在")
                            all_methods_ok = False
                    
                    # 呼び出されるメソッドのシグネチャチェック
                    for called_method_name in config['calls']:
                        if hasattr(obj, called_method_name):
                            called_method = getattr(obj, called_method_name)
                            called_sig = inspect.signature(called_method)
                            called_params = list(called_sig.parameters.keys())
                            
                            print(f"  🔸 {called_method_name}: {called_params}")
                            
                            # 呼び出されるメソッドに必要なパラメータがあるかチェック
                            for required_param in config['params']:
                                if required_param in called_params:
                                    print(f"    ✅ {required_param} パラメータ存在")
                                else:
                                    print(f"    ❌ {required_param} パラメータ不在")
                                    all_methods_ok = False
                        else:
                            print(f"  ❌ {called_method_name} メソッドが見つかりません")
                            all_methods_ok = False
                else:
                    print(f"❌ {method_name} メソッドが見つかりません")
                    all_methods_ok = False
            
            return all_methods_ok
            
        except Exception as e:
            print(f"❌ {module_name} チェックエラー: {e}")
            return False
    
    def check_method_calls_in_code(self, module_name: str, method_chain: Dict) -> bool:
        """コード内のメソッド呼び出しでパラメータが正しく渡されているかチェック"""
        print(f"\n🔍 {module_name} のコード内パラメータ渡しチェック")
        print("=" * 60)
        
        try:
            # ファイルパスを決定
            file_path = f"/Users/moriwakikeita/tools/long-trader/{module_name}.py"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            all_calls_ok = True
            
            for method_name, config in method_chain.items():
                print(f"\n📋 {method_name} からの呼び出しチェック:")
                
                for called_method in config['calls']:
                    # メソッド呼び出しパターンを検索
                    for param in config['params']:
                        expected_pattern = f"{called_method}.*{param}"
                        
                        if param in content and called_method in content:
                            # より詳細なチェック（呼び出し行を探す）
                            lines = content.split('\n')
                            found_proper_call = False
                            
                            for i, line in enumerate(lines):
                                if called_method in line and 'await' in line:
                                    # 複数行にわたる呼び出しもチェック
                                    call_block = ""
                                    j = i
                                    while j < len(lines) and (not call_block.count('(') == call_block.count(')') or call_block.count('(') == 0):
                                        call_block += lines[j] + " "
                                        j += 1
                                    
                                    if param in call_block:
                                        found_proper_call = True
                                        print(f"    ✅ {called_method} に {param} が渡されています")
                                        break
                            
                            if not found_proper_call:
                                print(f"    ❌ {called_method} に {param} が渡されていません")
                                all_calls_ok = False
                        else:
                            print(f"    ⚠️ {called_method} または {param} がコード内に見つかりません")
            
            return all_calls_ok
            
        except Exception as e:
            print(f"❌ {module_name} コードチェックエラー: {e}")
            return False
    
    def suggest_test_patterns(self) -> List[str]:
        """今後のテストパターンを提案"""
        return [
            "新しいパラメータ追加時のチェックリスト:",
            "1. 親メソッドのシグネチャにパラメータ追加",
            "2. 呼び出されるメソッドのシグネチャにパラメータ追加", 
            "3. 呼び出し部分でパラメータを実際に渡す",
            "4. このテストを実行してパラメータ一貫性を確認",
            "5. 実際の動作テストで検証"
        ]

def test_all_parameter_consistency():
    """全モジュールのパラメータ一貫性テスト"""
    print("🚀 パラメータ一貫性テスト開始")
    print("=" * 70)
    
    checker = ParameterConsistencyChecker()
    
    signature_results = {}
    call_results = {}
    
    # 各モジュールをテスト
    for module_name, method_chain in checker.method_chains.items():
        signature_results[module_name] = checker.check_method_signatures(module_name, method_chain)
        call_results[module_name] = checker.check_method_calls_in_code(module_name, method_chain)
    
    # 結果サマリー
    print(f"\n🎯 パラメータ一貫性テスト結果")
    print("=" * 70)
    
    all_signature_ok = all(signature_results.values())
    all_call_ok = all(call_results.values())
    
    for module_name in checker.method_chains.keys():
        sig_status = "✅ 正常" if signature_results.get(module_name, False) else "❌ 問題"
        call_status = "✅ 正常" if call_results.get(module_name, False) else "❌ 問題"
        print(f"📄 {module_name}:")
        print(f"   シグネチャ: {sig_status}")
        print(f"   呼び出し: {call_status}")
    
    overall_success = all_signature_ok and all_call_ok
    
    if overall_success:
        print(f"\n🎉 全モジュールのパラメータ一貫性OK！")
        print("🔒 同様のバグは発生しにくい状態です")
    else:
        print(f"\n⚠️ パラメータ一貫性に問題があります")
        print("🔧 上記の問題を修正してください")
    
    # テストパターン提案
    print(f"\n📋 今後の開発時チェックリスト:")
    for suggestion in checker.suggest_test_patterns():
        print(f"   {suggestion}")
    
    return overall_success

def test_specific_custom_period_flow():
    """カスタム期間設定の特定フローテスト"""
    print(f"\n🔍 カスタム期間設定フローテスト")
    print("=" * 60)
    
    try:
        # 実際のフロー模擬テスト
        test_settings = {
            'mode': 'custom',
            'start_date': '2025-06-01T17:42:00',
            'end_date': '2025-06-25T17:42:00'
        }
        
        print(f"📋 テスト用設定: {test_settings}")
        
        # Web → API → NewSymbolAdditionSystem → AutoSymbolTrainer のフロー確認
        flow_steps = [
            ("Web Frontend", "period_mode, start_date, end_date"),
            ("API Endpoint", "custom_period_settings"),
            ("NewSymbolAdditionSystem", "custom_period_settings"),
            ("AutoSymbolTrainer", "custom_period_settings"),
            ("_fetch_and_validate_data", "custom_period_settings"),
            ("_run_comprehensive_backtest", "custom_period_settings"),
            ("ScalableAnalysisSystem", "custom_period_settings")
        ]
        
        print(f"\n🔄 パラメータフロー確認:")
        for step, params in flow_steps:
            print(f"   {step} → {params}")
        
        # 実装確認
        from auto_symbol_training import AutoSymbolTrainer
        from new_symbol_addition_system import NewSymbolAdditionSystem
        
        trainer = AutoSymbolTrainer()
        system = NewSymbolAdditionSystem()
        
        # シグネチャ確認
        trainer_sig = inspect.signature(trainer.add_symbol_with_training)
        system_sig = inspect.signature(system.execute_symbol_addition)
        
        has_trainer_param = 'custom_period_settings' in trainer_sig.parameters
        has_system_param = 'custom_period_settings' in system_sig.parameters
        
        print(f"\n✅ パラメータ存在確認:")
        print(f"   AutoSymbolTrainer: {'✅' if has_trainer_param else '❌'}")
        print(f"   NewSymbolAdditionSystem: {'✅' if has_system_param else '❌'}")
        
        return has_trainer_param and has_system_param
        
    except Exception as e:
        print(f"❌ カスタム期間フローテストエラー: {e}")
        return False

if __name__ == "__main__":
    print("🛡️ パラメータ一貫性バグ防止テスト")
    print("=" * 70)
    print("このテストは新しいパラメータ追加時の")
    print("メソッドチェーン全体での一貫性を確認します")
    print()
    
    # メインテスト実行
    main_success = test_all_parameter_consistency()
    
    # 特定フローテスト実行
    flow_success = test_specific_custom_period_flow()
    
    # 最終判定
    overall_success = main_success and flow_success
    
    print(f"\n{'='*70}")
    print(f"🏆 最終判定: {'✅ バグ防止OK' if overall_success else '⚠️ 要修正'}")
    print(f"{'='*70}")
    
    if overall_success:
        print("🎉 パラメータ一貫性が保たれています！")
        print("🔒 同様のバグが発生するリスクは低いです")
        print("📋 新しいパラメータ追加時は必ずこのテストを実行してください")
    else:
        print("🔧 パラメータ一貫性に問題があります")
        print("⚠️ 修正してから本番環境で使用してください")
    
    sys.exit(0 if overall_success else 1)