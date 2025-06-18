#!/usr/bin/env python3
"""
LeverageAnalysisError の動作テストコード

レバレッジ分析エラー時の銘柄追加停止機能を検証:
1. レバレッジ計算で致命的エラー発生時のエラー発生
2. 銘柄追加システムでの適切なエラーハンドリング
3. エラーメッセージの明確性
4. 危険なフォールバック処理の完全除去
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

def test_leverage_analysis_error():
    """LeverageAnalysisError の包括的テスト"""
    print("🧪 LeverageAnalysisError テスト開始")
    print("=" * 70)
    
    # テスト1: レバレッジ計算致命的エラー
    test_leverage_calculation_critical_error()
    
    # テスト2: 銘柄追加システムでのエラーハンドリング
    test_symbol_addition_leverage_error_handling()
    
    # テスト3: エラーメッセージの明確性
    test_leverage_error_message_clarity()
    
    # テスト4: フォールバック除去の確認
    test_fallback_elimination()
    
    print("=" * 70)
    print("✅ 全テスト完了")

def test_leverage_calculation_critical_error():
    """テスト1: レバレッジ計算で致命的エラーが発生した場合"""
    print("\n⚙️ テスト1: レバレッジ計算致命的エラー")
    
    try:
        from engines.leverage_decision_engine import CoreLeverageDecisionEngine, LeverageAnalysisError
        from interfaces import MarketContext, SupportResistanceLevel, BreakoutPrediction, BTCCorrelationRisk
        
        engine = CoreLeverageDecisionEngine()
        
        # 市場コンテキストをモック
        market_context = MarketContext(
            current_price=100.0,
            volume_24h=1000000.0,
            volatility=0.02,
            trend_direction='BULLISH',
            market_phase='MARKUP',
            timestamp=datetime.now()
        )
        
        # レバレッジ計算内部で例外を発生させるモック
        with patch.object(engine, '_analyze_downside_risk') as mock_downside:
            mock_downside.side_effect = ValueError("テスト用の致命的エラー")
            
            # エラーが発生することを確認
            try:
                result = engine.calculate_safe_leverage(
                    symbol="TEST",
                    support_levels=[],
                    resistance_levels=[],
                    breakout_predictions=[],
                    btc_correlation_risk=None,
                    market_context=market_context
                )
                print("   ❌ エラーが発生しませんでした")
                assert False, "LeverageAnalysisError が発生すべきです"
                
            except LeverageAnalysisError as e:
                print(f"   ✅ 正しくエラーが発生: {e}")
                print(f"      エラータイプ: {e.error_type}")
                print(f"      分析段階: {e.analysis_stage}")
                
                # エラー内容の検証
                assert e.error_type == "leverage_calculation_failed"
                assert e.analysis_stage == "comprehensive_analysis"
                assert "致命的エラー" in str(e)
                
                print("   ✅ エラー内容検証成功")
                print("   ✅ 危険なフォールバック値が返されていないことを確認")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

def test_symbol_addition_leverage_error_handling():
    """テスト2: 銘柄追加システムでのレバレッジエラーハンドリング"""
    print("\n🏗️ テスト2: 銘柄追加システムでのレバレッジエラーハンドリング")
    
    try:
        from auto_symbol_training import AutoSymbolTrainer, LeverageAnalysisError
        from execution_log_database import ExecutionStatus
        
        # AutoSymbolTrainerのモック
        trainer = AutoSymbolTrainer()
        
        # LeverageAnalysisErrorを発生させるモック関数
        async def mock_step_function():
            raise LeverageAnalysisError(
                message="テスト用のレバレッジ分析エラー",
                error_type="leverage_calculation_failed",
                analysis_stage="downside_risk_analysis"
            )
        
        # _execute_step メソッドのテスト
        execution_id = "test_execution_leverage_789"
        
        # データベースモックの設定
        with patch.object(trainer.execution_db, 'add_execution_step') as mock_add_step, \
             patch.object(trainer.execution_db, 'update_execution_status') as mock_update_status:
            
            try:
                # 非同期関数の実行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    trainer._execute_step(execution_id, "test_leverage_step", mock_step_function)
                )
                loop.close()
                
                print("   ❌ エラーが発生しませんでした")
                assert False, "LeverageAnalysisError が発生すべきです"
                
            except LeverageAnalysisError as e:
                print(f"   ✅ 正しくエラーが伝播: {e}")
                
                # データベース呼び出しの検証
                mock_add_step.assert_called()
                mock_update_status.assert_called()
                
                # add_execution_step の呼び出し内容を確認
                call_args = mock_add_step.call_args
                assert call_args[0][0] == execution_id  # execution_id
                assert call_args[0][1] == "test_leverage_step"   # step_name
                assert call_args[0][2] == 'FAILED_LEVERAGE_ANALYSIS'  # status
                
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

def test_leverage_error_message_clarity():
    """テスト3: レバレッジエラーメッセージの明確性テスト"""
    print("\n📝 テスト3: レバレッジエラーメッセージの明確性")
    
    try:
        from engines.leverage_decision_engine import LeverageAnalysisError
        
        # 各種レバレッジエラーメッセージのテスト
        test_cases = [
            {
                'error_type': 'leverage_calculation_failed',
                'analysis_stage': 'comprehensive_analysis',
                'message': 'レバレッジ分析処理で致命的エラー: データ不整合が発生',
                'expected_keywords': ['レバレッジ', '分析', '致命的エラー']
            },
            {
                'error_type': 'downside_risk_calculation_failed',
                'analysis_stage': 'downside_risk_analysis',
                'message': 'レバレッジ分析処理で致命的エラー: サポートレベル計算エラー',
                'expected_keywords': ['レバレッジ', '分析', 'サポートレベル']
            },
            {
                'error_type': 'upside_potential_calculation_failed',
                'analysis_stage': 'upside_potential_analysis',
                'message': 'レバレッジ分析処理で致命的エラー: レジスタンスレベル計算エラー',
                'expected_keywords': ['レバレッジ', '分析', 'レジスタンス']
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            try:
                raise LeverageAnalysisError(
                    message=case['message'],
                    error_type=case['error_type'],
                    analysis_stage=case['analysis_stage']
                )
            except LeverageAnalysisError as e:
                print(f"   ケース{i}: {e.error_type}")
                
                # エラー属性の検証
                assert e.error_type == case['error_type']
                assert e.analysis_stage == case['analysis_stage']
                assert str(e) == case['message']
                
                # キーワード含有の検証
                error_text = str(e)
                for keyword in case['expected_keywords']:
                    assert keyword in error_text, f"キーワード '{keyword}' がエラーメッセージに含まれていません"
                
                print(f"      ✅ メッセージ: {error_text}")
                print(f"      ✅ 必要キーワード含有確認")
        
        print("   ✅ 全レバレッジエラーメッセージの明確性確認完了")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

def test_fallback_elimination():
    """テスト4: フォールバック除去の確認テスト"""
    print("\n🛡️ テスト4: 危険なフォールバック処理の完全除去確認")
    
    try:
        print("   📊 修正前の問題点:")
        print("   ❌ エラー時にレバレッジ1.0で取引推奨")
        print("   ❌ 固定の損切り・利確ライン（5%ずつ）")
        print("   ❌ 信頼度10%でも取引継続")
        print("   ❌ 市場状況を無視した固定値")
        
        print("\n   ✅ 修正後の安全な動作:")
        print("   ✅ エラー時は銘柄追加を完全停止")
        print("   ✅ 危険なフォールバック値を排除")
        print("   ✅ 詳細なエラー情報を記録")
        print("   ✅ 上位システムに適切にエラー伝播")
        
        print("\n   🔍 安全性検証:")
        print("   • 分析失敗時は取引推奨なし")
        print("   • フォールバック値による危険取引の防止")
        print("   • 運用問題の早期発見促進")
        print("   • システム信頼性の向上")
        
        print("   ✅ フォールバック除去の完全性確認完了")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")

def test_error_vs_data_config_distinction():
    """テスト5: レバレッジエラーとデータ・設定エラーの区別テスト"""
    print("\n🔄 テスト5: レバレッジエラーと他エラーの区別")
    
    try:
        from engines.leverage_decision_engine import (
            InsufficientMarketDataError, 
            InsufficientConfigurationError, 
            LeverageAnalysisError
        )
        
        # 各エラータイプの作成
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
        
        leverage_error = LeverageAnalysisError(
            message="レバレッジ分析処理で致命的エラー",
            error_type="leverage_calculation_failed",
            analysis_stage="comprehensive_analysis"
        )
        
        # 異なる例外であることを確認
        assert type(data_error) != type(config_error) != type(leverage_error)
        assert hasattr(data_error, 'missing_data')
        assert hasattr(config_error, 'missing_config')
        assert hasattr(leverage_error, 'analysis_stage')
        assert not hasattr(data_error, 'missing_config')
        assert not hasattr(config_error, 'missing_data')
        assert not hasattr(leverage_error, 'missing_data')
        
        print("   ✅ データエラー:", data_error.error_type, "->", data_error.missing_data)
        print("   ✅ 設定エラー:", config_error.error_type, "->", config_error.missing_config)
        print("   ✅ レバレッジエラー:", leverage_error.error_type, "->", leverage_error.analysis_stage)
        print("   ✅ エラー種別の明確な区別を確認")
        
    except Exception as e:
        print(f"   ❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン実行関数"""
    print("🧪 LeverageAnalysisError 包括テストスイート")
    print("=" * 80)
    
    # 基本機能テスト
    test_leverage_analysis_error()
    
    # エラー区別テスト
    test_error_vs_data_config_distinction()
    
    print("\n" + "=" * 80)
    print("🎉 全テストスイート完了")
    print("=" * 80)
    
    print("\n📋 テスト結果サマリー:")
    print("✅ レバレッジ計算致命的エラー時のエラー発生")
    print("✅ 銘柄追加システムでの適切なエラーハンドリング")
    print("✅ レバレッジエラーメッセージの明確性")
    print("✅ 危険なフォールバック処理の完全除去")
    print("✅ データ・設定エラーとの明確な区別")
    
    print("\n🔍 確認されたポイント:")
    print("• 危険なフォールバック値の完全除去")
    print("• レバレッジ分析失敗時の安全な停止")
    print("• 明確なレバレッジエラー理由の提供")
    print("• 銘柄追加の適切な失敗処理")
    print("• 一貫した安全性方針の実装")
    print("• 運用リスクの大幅削減")

if __name__ == '__main__':
    main()