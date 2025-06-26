#!/usr/bin/env python3
"""
他銘柄テスト - BTC、ETHでの検証
"""

import asyncio
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_symbol_training import AutoSymbolTrainer


async def test_symbol(symbol: str, period_days: int = 30):
    """指定銘柄でのテスト実行"""
    
    print(f"🧪 {symbol}銘柄テスト開始 ({period_days}日間データ)")
    print("=" * 80)
    
    # AutoSymbolTrainerの初期化
    trainer = AutoSymbolTrainer()
    
    try:
        # 実行IDを生成
        execution_id = datetime.now().strftime(f'%Y%m%d_%H%M%S_{symbol.lower()}_test')
        
        print(f"📊 テスト銘柄: {symbol}")
        print(f"📅 実行ID: {execution_id}")
        print(f"📅 データ期間: {period_days}日間")
        print(f"🎯 選択戦略: Balanced_Conservative のみ")
        print(f"⏰ 選択時間足: 1h のみ")
        print("=" * 80)
        
        # テスト実行
        result_id = await trainer.add_symbol_with_training(
            symbol=symbol,
            execution_id=execution_id,
            selected_strategies=["Balanced_Conservative"],
            selected_timeframes=["1h"],
            custom_period_settings={
                "mode": "custom",
                "period_days": period_days
            }
        )
        
        print(f"\n✅ {symbol}銘柄テスト完了!")
        print(f"📊 実行ID: {result_id}")
        
        # 分析結果の確認
        from scalable_analysis_system import ScalableAnalysisSystem
        analysis_system = ScalableAnalysisSystem("large_scale_analysis")
        
        # 結果を取得
        results = analysis_system.query_analyses(
            filters={
                'symbol': symbol,
                'execution_id': result_id
            }
        )
        
        if results and len(results) > 0:
            print(f"\n📊 {symbol} 分析結果:")
            for result in results:
                print(f"   - 時間足: {result.get('timeframe')}")
                print(f"   - 戦略: {result.get('config')}")
                print(f"   - 総取引数: {result.get('total_trades', 0)}")
                print(f"   - シャープレシオ: {result.get('sharpe_ratio', 0):.2f}")
                print(f"   - 最大ドローダウン: {result.get('max_drawdown', 0):.2f}%")
                print(f"   - 総利益: {result.get('total_profit', 0):.2f}%")
                
                # 取引数が0以上の場合は成功と見なす
                if result.get('total_trades', 0) > 0:
                    print(f"   🎉 {symbol}: 取引シグナル検出成功!")
                    return True
                print()
        else:
            print(f"⚠️ {symbol}: 取引シグナルが検出されませんでした")
        
        return False
        
    except Exception as e:
        print(f"\n❌ {symbol}テストでエラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_symbols():
    """複数銘柄でのテスト実行"""
    
    print("🚀 複数銘柄テスト開始")
    print("=" * 80)
    
    # テスト対象銘柄
    test_symbols = ["BTC", "ETH"]
    results = {}
    
    for symbol in test_symbols:
        print(f"\n📈 {symbol}銘柄テスト開始...")
        success = await test_symbol(symbol, period_days=30)
        results[symbol] = success
        print(f"🎯 {symbol}テスト結果: {'✅ 成功' if success else '❌ シグナルなし'}")
        print("-" * 80)
    
    # 総合結果
    print("\n📊 総合テスト結果:")
    successful_symbols = [symbol for symbol, success in results.items() if success]
    
    for symbol, success in results.items():
        status = "✅ 取引シグナル検出" if success else "❌ シグナルなし"
        print(f"   {symbol}: {status}")
    
    print(f"\n🎯 成功率: {len(successful_symbols)}/{len(test_symbols)} ({len(successful_symbols)/len(test_symbols)*100:.1f}%)")
    
    if successful_symbols:
        print(f"✅ 取引シグナル検出成功銘柄: {', '.join(successful_symbols)}")
        print("🎉 システムは正常に動作しています!")
    else:
        print("⚠️ 全銘柄で取引シグナルが検出されませんでした")
        print("💡 より長期間のデータや異なる戦略パラメータを試すことを推奨します")
    
    print("\n🎉 複数銘柄テスト終了")


if __name__ == "__main__":
    asyncio.run(test_multiple_symbols())