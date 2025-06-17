#!/usr/bin/env python3
"""
支持線・抵抗線検出失敗時の修正効果確認テスト

修正前後の動作比較:
- 修正前: 支持線・抵抗線なし → 銘柄追加失敗（例外発生）
- 修正後: 支持線・抵抗線なし → 警告出力して継続（正常完了）
"""

import sys
import os
import asyncio
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer


async def test_support_resistance_handling():
    """支持線・抵抗線処理の修正効果テスト"""
    
    print("🧪 支持線・抵抗線検出失敗時の処理テスト")
    print("="*60)
    
    trainer = AutoSymbolTrainer()
    
    # テスト用設定
    test_configs = [
        {'symbol': 'TEST', 'timeframe': '1h', 'strategy': 'Conservative_ML'}
    ]
    
    print("\n📋 テストシナリオ:")
    print("- 支持線・抵抗線が0個検出される状況をシミュレート")
    print("- generate_batch_analysis が 0 を返す（処理済み件数0）")
    print("- 修正後は例外ではなく警告で処理継続される想定")
    
    # generate_batch_analysisが0を返すようにモック
    with patch.object(trainer.analysis_system, 'generate_batch_analysis', return_value=0) as mock_analysis:
        with patch('builtins.print') as mock_print:
            
            try:
                print("\n🔄 バックテスト実行中...")
                await trainer._run_comprehensive_backtest("TEST", test_configs)
                
                print("✅ SUCCESS: 例外が発生せず処理が継続されました")
                
                # 出力されたメッセージを確認
                print("\n📄 出力されたメッセージ:")
                printed_messages = [str(call[0][0]) for call in mock_print.call_args_list]
                
                warning_found = False
                for msg in printed_messages:
                    if '⚠️' in msg and 'TEST' in msg:
                        print(f"   ✅ 警告メッセージ: {msg}")
                        warning_found = True
                    elif msg.strip():  # 空でないメッセージ
                        print(f"   📝 その他: {msg}")
                
                if warning_found:
                    print("✅ 適切な警告メッセージが出力されています")
                else:
                    print("⚠️ 警告メッセージが見つかりませんでした")
                
                # モックが呼ばれたことを確認
                assert mock_analysis.called, "generate_batch_analysis が呼ばれていません"
                print("✅ generate_batch_analysis が正しく呼ばれました")
                
                return True
                
            except Exception as e:
                print(f"❌ FAIL: 例外が発生しました - {e}")
                print(f"   エラータイプ: {type(e).__name__}")
                print(f"   エラー詳細: {str(e)}")
                return False


async def test_normal_case():
    """正常ケース（支持線・抵抗線が見つかる場合）のテスト"""
    
    print("\n" + "="*60)
    print("🧪 正常ケース: 支持線・抵抗線検出成功")
    print("="*60)
    
    trainer = AutoSymbolTrainer()
    test_configs = [
        {'symbol': 'TEST', 'timeframe': '1h', 'strategy': 'Conservative_ML'}
    ]
    
    # generate_batch_analysisが成功を返すようにモック
    with patch.object(trainer.analysis_system, 'generate_batch_analysis', return_value=1) as mock_analysis:
        with patch('builtins.print') as mock_print:
            
            try:
                print("🔄 正常ケースのバックテスト実行中...")
                await trainer._run_comprehensive_backtest("TEST", test_configs)
                
                print("✅ SUCCESS: 正常ケースも問題なく動作しています")
                
                # 警告メッセージが出ないことを確認
                printed_messages = [str(call[0][0]) for call in mock_print.call_args_list]
                warning_count = sum(1 for msg in printed_messages if '⚠️' in msg)
                
                if warning_count == 0:
                    print("✅ 正常ケースでは警告メッセージが出力されていません（正常）")
                else:
                    print(f"⚠️ 正常ケースで警告メッセージが{warning_count}件出力されました")
                
                return True
                
            except Exception as e:
                print(f"❌ FAIL: 正常ケースで例外が発生しました - {e}")
                return False


async def main():
    """メインテスト実行"""
    
    print("🚀 支持線・抵抗線処理修正効果の確認テスト")
    print("="*80)
    
    # テスト1: 支持線・抵抗線未検出時の処理
    result1 = await test_support_resistance_handling()
    
    # テスト2: 正常ケース
    result2 = await test_normal_case()
    
    # 結果サマリー
    print("\n" + "="*80)
    print("📊 テスト結果サマリー")
    print("="*80)
    
    if result1:
        print("✅ 支持線・抵抗線未検出時: 処理継続 - PASS")
    else:
        print("❌ 支持線・抵抗線未検出時: 処理継続 - FAIL")
    
    if result2:
        print("✅ 正常ケース: 問題なし - PASS")
    else:
        print("❌ 正常ケース: 問題あり - FAIL")
    
    overall_success = result1 and result2
    
    if overall_success:
        print("\n🎉 全テストが成功しました！")
        print("✅ 修正により、支持線・抵抗線が見つからない場合でも")
        print("   銘柄追加プロセスが正常に継続されます。")
        print("✅ ARB、OP、AAVEなどの問題も解決されるはずです。")
    else:
        print("\n⚠️ 一部テストが失敗しました。追加の修正が必要です。")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print(f"\nテスト終了 (exit code: {exit_code})")
    sys.exit(exit_code)