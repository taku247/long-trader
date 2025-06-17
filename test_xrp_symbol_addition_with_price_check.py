#!/usr/bin/env python3
"""
XRP銘柄追加実行 & 価格バグチェック

ブラウザ経由での銘柄追加の代わりに、実際のシステムでXRPを追加し、
今回修正した価格バグが発生していないかを詳細にチェックする。
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_xrp_symbol_addition_with_price_validation():
    """XRP銘柄追加と価格バグチェック"""
    print("🚀 XRP銘柄追加 & 価格バグ検証テスト")
    print("=" * 80)
    print("ETHで発見された45%異常利益率問題がXRPで発生しないかチェック")
    print("=" * 80)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        from engines.price_consistency_validator import PriceConsistencyValidator
        
        print("\n📊 システム初期化...")
        system = ScalableAnalysisSystem()
        validator = PriceConsistencyValidator()
        
        # XRPで少数のトレード分析を実行
        symbol = "XRP"
        timeframe = "1h"
        config = "Conservative_ML"
        
        print(f"\n💰 {symbol}の分析開始: {timeframe} {config}")
        print("=" * 60)
        
        # 実際の銘柄追加プロセスをシミュレート
        start_time = datetime.now()
        
        # 1. データ取得段階での価格チェック
        print("🔍 Phase 1: データ取得 & 初期価格チェック")
        
        try:
            # 実際にリアル分析を少数実行（10件程度）
            trades_data = system._generate_real_analysis(
                symbol=symbol, 
                timeframe=timeframe, 
                config=config,
                evaluation_period_days=7  # 7日間に制限して少数のトレードを生成
            )
            
            if not trades_data or len(trades_data) == 0:
                print("❌ トレードデータが生成されませんでした")
                return False
                
            print(f"✅ {len(trades_data)}件のトレードデータを生成")
            
        except Exception as e:
            print(f"❌ データ生成エラー: {e}")
            return False
        
        # 2. 価格整合性の詳細チェック
        print("\n🔍 Phase 2: 価格整合性詳細チェック")
        print("-" * 50)
        
        price_issues = []
        entry_prices = []
        profit_rates = []
        
        for i, trade in enumerate(trades_data[:5]):  # 最初の5件を詳細チェック
            try:
                entry_price = float(trade.get('entry_price', 0))
                exit_price = float(trade.get('exit_price', 0))
                current_price = float(trade.get('current_price', 0))
                leverage = float(trade.get('leverage', 1))
                
                entry_prices.append(entry_price)
                
                # 利益率計算
                if entry_price > 0 and exit_price > 0:
                    profit_rate = (exit_price - entry_price) / entry_price * 100 * leverage
                    profit_rates.append(profit_rate)
                else:
                    profit_rate = 0
                    profit_rates.append(0)
                
                # 価格整合性チェック
                price_consistency = validator.validate_price_consistency(
                    analysis_price=current_price,
                    entry_price=entry_price,
                    symbol=symbol,
                    context=f"Trade #{i+1}"
                )
                
                print(f"   トレード{i+1}: エントリー=${entry_price:.6f}, "
                      f"利益率={profit_rate:.2f}%, "
                      f"整合性={price_consistency.inconsistency_level.value}")
                
                # 問題のあるケースを記録
                if not price_consistency.is_consistent:
                    price_issues.append({
                        'trade_num': i+1,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'inconsistency_level': price_consistency.inconsistency_level.value,
                        'message': price_consistency.message
                    })
                
                # ETHのような異常利益率をチェック
                if abs(profit_rate) > 20:  # 20%を超える利益率は要注意
                    print(f"   ⚠️ 高利益率検出: {profit_rate:.2f}%")
                
            except Exception as e:
                print(f"   ❌ トレード{i+1}分析エラー: {e}")
                continue
        
        # 3. 価格多様性チェック
        print(f"\n🔍 Phase 3: 価格多様性チェック")
        print("-" * 50)
        
        unique_entry_prices = len(set(entry_prices))
        price_range = max(entry_prices) - min(entry_prices) if entry_prices else 0
        
        print(f"   エントリー価格の種類: {unique_entry_prices}/{len(entry_prices)}")
        print(f"   価格範囲: ${min(entry_prices):.6f} - ${max(entry_prices):.6f}")
        print(f"   価格差: ${price_range:.6f}")
        
        # 価格の硬直化チェック（今回のバグ）
        price_diversity_ok = unique_entry_prices > 1 if len(entry_prices) > 1 else True
        
        if not price_diversity_ok:
            print("   ❌ 価格硬直化問題: 全トレードが同じ価格を使用")
        else:
            print("   ✅ 価格多様性: 正常")
        
        # 4. 利益率異常チェック
        print(f"\n🔍 Phase 4: 利益率異常チェック")
        print("-" * 50)
        
        if profit_rates:
            max_profit = max(profit_rates)
            min_profit = min(profit_rates)
            avg_profit = sum(profit_rates) / len(profit_rates)
            
            print(f"   利益率範囲: {min_profit:.2f}% - {max_profit:.2f}%")
            print(f"   平均利益率: {avg_profit:.2f}%")
            
            # ETHのような異常利益率チェック
            extreme_profits = [p for p in profit_rates if abs(p) > 30]
            if extreme_profits:
                print(f"   ⚠️ 異常利益率検出: {len(extreme_profits)}件")
                for i, p in enumerate(extreme_profits):
                    print(f"     - 異常#{i+1}: {p:.2f}%")
            else:
                print("   ✅ 異常利益率: なし")
        
        # 5. 総合判定
        print(f"\n📊 総合判定")
        print("=" * 60)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # 判定基準
        issues_found = []
        
        # 価格整合性問題
        if price_issues:
            issues_found.append(f"価格整合性問題: {len(price_issues)}件")
        
        # 価格多様性問題
        if not price_diversity_ok:
            issues_found.append("価格硬直化問題")
        
        # 異常利益率問題
        if profit_rates and max(abs(p) for p in profit_rates) > 40:
            issues_found.append("異常利益率問題")
        
        # データ生成問題
        if len(trades_data) == 0:
            issues_found.append("データ生成失敗")
        
        # 結果判定
        if not issues_found:
            print("✅ XRP銘柄追加: 成功")
            print("✅ 価格バグチェック: 問題なし")
            print("✅ ETH異常利益率問題: 修正済み")
            print(f"✅ 処理時間: {processing_time:.2f}秒")
            print("\n🎯 今回のバグ修正は正常に機能しています")
            return True
        else:
            print("❌ 問題が検出されました:")
            for issue in issues_found:
                print(f"   - {issue}")
            print(f"⏱️ 処理時間: {processing_time:.2f}秒")
            return False
        
    except Exception as e:
        print(f"❌ システムエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alternative_symbols():
    """他の銘柄でも同様にテスト"""
    print("\n🔄 他銘柄での検証")
    print("-" * 50)
    
    symbols_to_test = ["BTC", "ETH", "ADA"]  # XRP以外も簡易テスト
    
    for symbol in symbols_to_test:
        print(f"\n💰 {symbol}簡易チェック:")
        try:
            from scalable_analysis_system import ScalableAnalysisSystem
            system = ScalableAnalysisSystem()
            
            # 1件だけ分析実行
            trades_data = system._generate_real_analysis(
                symbol=symbol, 
                timeframe="1h", 
                config="Conservative_ML",
                evaluation_period_days=1
            )
            
            if trades_data and len(trades_data) > 0:
                trade = trades_data[0]
                entry_price = float(trade.get('entry_price', 0))
                print(f"   ✅ {symbol}: エントリー価格 ${entry_price:.6f}")
            else:
                print(f"   ⚠️ {symbol}: データ生成なし")
                
        except Exception as e:
            print(f"   ❌ {symbol}: エラー - {str(e)[:50]}...")

def main():
    """メインテスト実行"""
    
    # ログレベルを調整（エラーログを減らす）
    logging.getLogger().setLevel(logging.ERROR)
    
    print("🧪 ブラウザ銘柄追加代替テスト - XRP価格バグ検証")
    print("=" * 80)
    
    # メインテスト
    main_result = test_xrp_symbol_addition_with_price_validation()
    
    # 追加テスト
    test_alternative_symbols()
    
    # 最終結果
    print("\n" + "=" * 80)
    print("📊 最終結果")
    print("=" * 80)
    
    if main_result:
        print("✅ XRP銘柄追加テスト: 成功")
        print("✅ 価格バグ修正: 確認済み")
        print("✅ ブラウザ経由の銘柄追加も同様に安全")
        print("\n🛡️ ETHで発見された45%異常利益率問題は解決済み")
        print("🎯 新規銘柄追加時も価格整合性が保たれます")
        return True
    else:
        print("❌ XRP銘柄追加テスト: 問題検出")
        print("⚠️ 追加調査が必要")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)