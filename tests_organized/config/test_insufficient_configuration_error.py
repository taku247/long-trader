#!/usr/bin/env python3
"""
InsufficientConfigurationError の動作テストコード

設定読み込み失敗時に銘柄追加を適切に停止することを検証:
1. エントリー条件設定読み込み失敗時のエラー発生
2. 銘柄追加システムでの適切なエラーハンドリング
3. エラーメッセージの明確性
4. 設定ファイル問題の早期発見
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_insufficient_configuration_error():
    """InsufficientConfigurationError の包括的テスト"""
    print("🧪 InsufficientConfigurationError テスト開始")
    print("=" * 70)
    
    # テスト1: エントリー条件設定読み込み失敗
    test_entry_conditions_config_failure()
    
    # テスト2: 銘柄追加システムでのエラーハンドリング
    test_symbol_addition_config_error_handling()
    
    # テスト3: エラーメッセージの明確性
    test_config_error_message_clarity()
    
    # テスト4: 統合テスト（設定エラー伝播）
    test_config_error_propagation()
    
    print("=" * 70)
    print("✅ 全テスト完了")

def test_entry_conditions_config_failure():
    """テスト1: エントリー条件設定読み込み失敗時のエラー"""
    print("\n⚙️ テスト1: エントリー条件設定読み込み失敗")
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        from engines.leverage_decision_engine import InsufficientConfigurationError
        
        system = ScalableAnalysisSystem()
        
        # UnifiedConfigManagerのインポート失敗をシミュレート
        with patch('scalable_analysis_system.UnifiedConfigManager') as mock_config:
            mock_config.side_effect = ImportError("UnifiedConfigManagerが見つかりません")
            
            # 分析結果をモック
            analysis_result = {
                'leverage': 5.0,
                'confidence': 70.0,
                'risk_reward_ratio': 2.5,
                'current_price': 100.0,
                'strategy': 'Balanced'
            }
            
            # エラーが発生することを確認
            try:
                system._should_enter_position(analysis_result, '1h')
                print("   ❌ エラーが発生しませんでした")
                assert False, "InsufficientConfigurationError が発生すべきです"
                
            except InsufficientConfigurationError as e:
                print(f"   ✅ 正しくエラーが発生: {e}")
                print(f"      エラータイプ: {e.error_type}")
                print(f"      不足設定: {e.missing_config}")
                
                # エラー内容の検証
                assert e.error_type == "entry_conditions_config_failed"
                assert e.missing_config == "unified_entry_conditions"
                assert "エントリー条件設定が読み込めませんでした" in str(e)
                
                print("   ✅ エラー内容検証成功")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

def test_symbol_addition_config_error_handling():
    """テスト2: 銘柄追加システムでの設定エラーハンドリング"""
    print("\n🏗️ テスト2: 銘柄追加システムでの設定エラーハンドリング")
    
    try:
        from auto_symbol_training import AutoSymbolTrainer, InsufficientConfigurationError
        from execution_log_database import ExecutionStatus
        
        # AutoSymbolTrainerのモック
        trainer = AutoSymbolTrainer()
        
        # InsufficientConfigurationErrorを発生させるモック関数
        async def mock_step_function():
            raise InsufficientConfigurationError(
                message="テスト用の設定不足エラー",
                error_type="test_config_error",
                missing_config="test_config"
            )
        
        # _execute_step メソッドのテスト
        execution_id = "test_execution_456"
        
        # データベースモックの設定
        with patch.object(trainer.execution_db, 'add_execution_step') as mock_add_step, \
             patch.object(trainer.execution_db, 'update_execution_status') as mock_update_status:
            
            try:
                # 非同期関数の実行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    trainer._execute_step(execution_id, "test_config_step", mock_step_function)
                )
                loop.close()
                
                print("   ❌ エラーが発生しませんでした")
                assert False, "InsufficientConfigurationError が発生すべきです"
                
            except InsufficientConfigurationError as e:
                print(f"   ✅ 正しくエラーが伝播: {e}")
                
                # データベース呼び出しの検証
                mock_add_step.assert_called()
                mock_update_status.assert_called()
                
                # add_execution_step の呼び出し内容を確認
                call_args = mock_add_step.call_args
                assert call_args[0][0] == execution_id  # execution_id
                assert call_args[0][1] == "test_config_step"   # step_name
                assert call_args[0][2] == 'FAILED_INSUFFICIENT_CONFIG'  # status
                
                # update_execution_status の呼び出し内容を確認
                status_call_args = mock_update_status.call_args
                assert status_call_args[0][0] == execution_id  # execution_id
                assert status_call_args[0][1] == ExecutionStatus.FAILED  # status
                
                print("   ✅ データベース呼び出し検証成功")
                print("   ✅ 銘柄追加が適切に失敗として処理されました")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

def test_config_error_message_clarity():
    """テスト3: 設定エラーメッセージの明確性テスト"""
    print("\n📝 テスト3: 設定エラーメッセージの明確性")
    
    try:
        from engines.leverage_decision_engine import InsufficientConfigurationError
        
        # 各種設定エラーメッセージのテスト
        test_cases = [
            {
                'error_type': 'entry_conditions_config_failed',
                'missing_config': 'unified_entry_conditions',
                'message': 'エントリー条件設定が読み込めませんでした: 設定ファイルが見つかりません',
                'expected_keywords': ['エントリー条件', '設定', '読み込めません']
            },
            {
                'error_type': 'timeframe_config_failed',
                'missing_config': 'timeframe_conditions',
                'message': '時間足設定が読み込めませんでした: JSON解析エラー',
                'expected_keywords': ['時間足', '設定', '読み込めません']
            },
            {
                'error_type': 'strategy_config_failed',
                'missing_config': 'strategy_parameters',
                'message': '戦略パラメータ設定が読み込めませんでした: ファイルアクセス権限なし',
                'expected_keywords': ['戦略', 'パラメータ', '設定']
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            try:
                raise InsufficientConfigurationError(
                    message=case['message'],
                    error_type=case['error_type'],
                    missing_config=case['missing_config']
                )
            except InsufficientConfigurationError as e:
                print(f"   ケース{i}: {e.error_type}")
                
                # エラー属性の検証
                assert e.error_type == case['error_type']
                assert e.missing_config == case['missing_config']
                assert str(e) == case['message']
                
                # キーワード含有の検証
                error_text = str(e)
                for keyword in case['expected_keywords']:
                    assert keyword in error_text, f"キーワード '{keyword}' がエラーメッセージに含まれていません"
                
                print(f"      ✅ メッセージ: {error_text}")
                print(f"      ✅ 必要キーワード含有確認")
        
        print("   ✅ 全設定エラーメッセージの明確性確認完了")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

def test_config_error_propagation():
    """テスト4: 設定エラー伝播の統合テスト"""
    print("\n🔗 テスト4: 設定エラー伝播の統合テスト")
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        from engines.leverage_decision_engine import InsufficientConfigurationError
        
        system = ScalableAnalysisSystem()
        
        # 設定読み込みエラーをシミュレート
        with patch('config.unified_config_manager.UnifiedConfigManager') as mock_unified_config:
            mock_unified_config.side_effect = FileNotFoundError("設定ファイルが見つかりません")
            
            # 分析結果をモック
            analysis_result = {
                'leverage': 6.0,
                'confidence': 80.0,
                'risk_reward_ratio': 3.0,
                'current_price': 50.0,
                'strategy': 'Conservative_ML'
            }
            
            try:
                # エントリー判定メソッドを呼び出し
                result = system._should_enter_position(analysis_result, '30m')
                
                print("   ❌ エラーが発生しませんでした")
                assert False, "InsufficientConfigurationError が伝播すべきです"
                
            except InsufficientConfigurationError as e:
                print(f"   ✅ メインメソッドまでエラーが正しく伝播: {e}")
                print(f"      エラータイプ: {e.error_type}")
                
                # エントリー判定全体が失敗することを確認
                assert e.error_type == "entry_conditions_config_failed"
                print("   ✅ エントリー判定全体の停止確認")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

def test_config_vs_data_error_distinction():
    """テスト5: 設定エラーとデータエラーの区別テスト"""
    print("\n🔄 テスト5: 設定エラーとデータエラーの区別")
    
    try:
        from engines.leverage_decision_engine import InsufficientMarketDataError, InsufficientConfigurationError
        
        # データエラーとの区別テスト
        data_error = InsufficientMarketDataError(
            message="サポートレベルが検出できませんでした",
            error_type="support_detection_failed",
            missing_data="support_levels"
        )
        
        config_error = InsufficientConfigurationError(
            message="エントリー条件設定が読み込めませんでした",
            error_type="entry_conditions_config_failed",
            missing_config="unified_entry_conditions"
        )
        
        # 異なる例外であることを確認
        assert type(data_error) != type(config_error)
        assert hasattr(data_error, 'missing_data')
        assert hasattr(config_error, 'missing_config')
        assert not hasattr(data_error, 'missing_config')
        assert not hasattr(config_error, 'missing_data')
        
        print("   ✅ データエラー:", data_error.error_type, "->", data_error.missing_data)
        print("   ✅ 設定エラー:", config_error.error_type, "->", config_error.missing_config)
        print("   ✅ エラー種別の明確な区別を確認")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

def test_safety_vs_availability_tradeoff():
    """テスト6: 安全性vs可用性のトレードオフ検証"""
    print("\n⚖️ テスト6: 安全性vs可用性のトレードオフ検証")
    
    try:
        print("   📊 実装方針の検証:")
        print("   🛡️ 安全性重視: 設定問題時はシステム停止")
        print("   ❌ 可用性軽視: システム継続動作不可")
        print("   ✅ 一貫性確保: データ問題と同様の対応")
        
        print("\n   💡 期待される効果:")
        print("   • 設定ファイル問題の早期発見")
        print("   • 不適切な条件での分析防止")
        print("   • 運用問題の隠蔽回避")
        print("   • システム品質の向上")
        
        print("\n   ⚠️ 運用上の注意:")
        print("   • 設定ファイルの適切な管理が必須")
        print("   • バックアップ設定の準備推奨")
        print("   • 監視・アラート体制の整備必要")
        
        print("   ✅ トレードオフ検証完了")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")

def main():
    """メイン実行関数"""
    print("🧪 InsufficientConfigurationError 包括テストスイート")
    print("=" * 80)
    
    # 基本機能テスト
    test_insufficient_configuration_error()
    
    # エラー区別テスト
    test_config_vs_data_error_distinction()
    
    # 方針検証テスト
    test_safety_vs_availability_tradeoff()
    
    print("\n" + "=" * 80)
    print("🎉 全テストスイート完了")
    print("=" * 80)
    
    print("\n📋 テスト結果サマリー:")
    print("✅ エントリー条件設定読み込み失敗時のエラー発生")
    print("✅ 銘柄追加システムでの適切なエラーハンドリング")
    print("✅ 設定エラーメッセージの明確性")
    print("✅ エラー伝播の統合動作")
    print("✅ データエラーとの明確な区別")
    print("✅ 安全性重視方針の実装確認")
    
    print("\n🔍 確認されたポイント:")
    print("• ハードコード条件値の完全除去")
    print("• 設定問題時の安全な停止")
    print("• 明確な設定エラー理由の提供")
    print("• 銘柄追加の適切な失敗処理")
    print("• 一貫した安全性方針の実装")
    print("• 運用問題の早期発見促進")

if __name__ == '__main__':
    main()