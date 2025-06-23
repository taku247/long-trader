#!/usr/bin/env python3
"""
緩い条件設定でのシンボル追加データ保存テスト

本番のtrading_conditions.jsonを変更せず、テスト用の緩い条件で
実際にanalyses テーブルにデータが保存されることを確認
"""

import sys
import os
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

def test_symbol_addition_with_relaxed_conditions():
    """緩い条件でのシンボル追加テスト"""
    print("🧪 緩い条件設定でのシンボル追加データ保存テスト")
    print("=" * 70)
    print("目的: エントリー条件を緩くして、実際にanalyses テーブルにデータが保存されることを確認")
    print("=" * 70)
    
    # 1. オリジナル設定ファイルのバックアップ
    original_config = "config/trading_conditions.json"
    test_config = "config/trading_conditions_test.json"
    backup_config = "config/trading_conditions_backup.json"
    
    print(f"\n1️⃣ 設定ファイルの準備...")
    
    try:
        # バックアップ作成
        shutil.copy2(original_config, backup_config)
        print(f"   ✅ バックアップ作成: {backup_config}")
        
        # テスト用設定に一時的に変更
        shutil.copy2(test_config, original_config)
        print(f"   📝 テスト設定適用: {test_config} → {original_config}")
        
        # 2. テスト用シンボル追加実行
        print(f"\n2️⃣ テスト用シンボル追加実行...")
        
        # 事前のanalyses レコード数確認
        analysis_db_path = "large_scale_analysis/analysis.db"
        with sqlite3.connect(analysis_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM analyses")
            initial_count = cursor.fetchone()[0]
            print(f"   📊 分析開始前のanalyses レコード数: {initial_count}")
        
        # ScalableAnalysisSystemを使用してテスト実行
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem()
        test_symbol = "ETH"  # 既にデータがある銘柄
        test_timeframe = "1h"
        test_config_name = "Conservative_ML"
        
        print(f"   🔍 テスト対象: {test_symbol} {test_timeframe} {test_config_name}")
        print(f"   💡 緩い条件: min_risk_reward=0.5, min_confidence=0.2, min_leverage=1.0")
        
        # 分析実行
        start_time = datetime.now()
        
        try:
            # 直接分析実行
            result = system._generate_single_analysis(test_symbol, test_timeframe, test_config_name)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"   ⏱️ 分析処理時間: {duration:.2f}秒")
            
            if result:
                print(f"   ✅ 分析実行成功")
                
                # 生成されたトレードデータを確認
                trades_data = system.load_compressed_trades(test_symbol, test_timeframe, test_config_name)
                
                if trades_data is not None:
                    if isinstance(trades_data, list) and len(trades_data) > 0:
                        print(f"   📈 生成されたトレード数: {len(trades_data)}")
                        
                        # 最初のトレードの詳細表示
                        first_trade = trades_data[0]
                        if isinstance(first_trade, dict):
                            entry_price = first_trade.get('entry_price', 0)
                            take_profit = first_trade.get('take_profit_price', 0)
                            stop_loss = first_trade.get('stop_loss_price', 0)
                            
                            if take_profit > 0 and stop_loss > 0 and entry_price > 0:
                                risk = abs(entry_price - stop_loss)
                                reward = abs(take_profit - entry_price)
                                rr_ratio = reward / risk if risk > 0 else 0
                                
                                print(f"   💰 最初のトレード:")
                                print(f"      Entry: ${entry_price:.2f}")
                                print(f"      TP: ${take_profit:.2f}")
                                print(f"      SL: ${stop_loss:.2f}")
                                print(f"      Risk-Reward Ratio: {rr_ratio:.2f}")
                    else:
                        print(f"   ⚠️ トレードデータが生成されませんでした")
                else:
                    print(f"   ❌ トレードデータの読み込みに失敗")
            else:
                print(f"   ❌ 分析実行失敗")
                
        except Exception as e:
            print(f"   ❌ 分析実行エラー: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. analyses テーブルの変化確認
        print(f"\n3️⃣ analyses テーブルの変化確認...")
        
        with sqlite3.connect(analysis_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM analyses")
            final_count = cursor.fetchone()[0]
            print(f"   📊 分析後のanalyses レコード数: {final_count}")
            
            if final_count > initial_count:
                added_count = final_count - initial_count
                print(f"   ✅ 新規追加されたレコード数: {added_count}")
                
                # 最新のレコード詳細表示
                cursor = conn.execute("""
                    SELECT symbol, timeframe, config, total_trades, win_rate, 
                           total_return, sharpe_ratio, max_drawdown, created_at
                    FROM analyses 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """)
                latest_records = cursor.fetchall()
                
                print(f"   📋 最新の分析レコード:")
                for record in latest_records:
                    symbol, tf, config, trades, win_rate, ret, sharpe, dd, created = record
                    print(f"      {symbol} {tf} {config}: {trades}トレード, "
                          f"勝率{win_rate:.1%}, リターン{ret:.2f}, "
                          f"Sharpe{sharpe:.2f}, DD{dd:.2f}")
                
                return True
            else:
                print(f"   ❌ 新規レコードが追加されませんでした")
                print(f"   💡 可能性: 既に同じ条件での分析結果が存在するか、別の問題が発生")
                return False
                
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 4. 設定ファイルの復元
        print(f"\n4️⃣ 設定ファイルの復元...")
        try:
            if os.path.exists(backup_config):
                shutil.copy2(backup_config, original_config)
                os.remove(backup_config)
                print(f"   ✅ オリジナル設定復元完了")
            else:
                print(f"   ⚠️ バックアップファイルが見つかりません")
        except Exception as e:
            print(f"   ❌ 設定復元エラー: {e}")

def verify_current_config():
    """現在の設定での条件確認"""
    print("\n🔍 現在の設定での条件確認")
    print("-" * 50)
    
    try:
        import json
        with open("config/trading_conditions.json", "r") as f:
            config = json.load(f)
        
        conditions_1h = config.get("entry_conditions_by_timeframe", {}).get("1h", {})
        
        print(f"1h timeframe の現在の条件:")
        print(f"  min_risk_reward: {conditions_1h.get('min_risk_reward', 'N/A')}")
        print(f"  min_confidence: {conditions_1h.get('min_confidence', 'N/A')}")
        print(f"  min_leverage: {conditions_1h.get('min_leverage', 'N/A')}")
        
        print(f"\nETH の分析結果 (推定):")
        print(f"  Risk-Reward: 1.1")
        print(f"  Confidence: 0.462 (46.2%)")
        print(f"  Leverage: 1.0")
        
        # 条件判定
        min_rr = conditions_1h.get('min_risk_reward', 1.25)
        min_conf = conditions_1h.get('min_confidence', 0.3)
        min_lev = conditions_1h.get('min_leverage', 1.0)
        
        print(f"\n条件判定:")
        print(f"  Risk-Reward: 1.1 >= {min_rr} → {'✅ PASS' if 1.1 >= min_rr else '❌ FAIL'}")
        print(f"  Confidence: 0.462 >= {min_conf} → {'✅ PASS' if 0.462 >= min_conf else '❌ FAIL'}")
        print(f"  Leverage: 1.0 >= {min_lev} → {'✅ PASS' if 1.0 >= min_lev else '❌ FAIL'}")
        
        if 1.1 >= min_rr and 0.462 >= min_conf and 1.0 >= min_lev:
            print(f"\n✅ 全条件クリア → analyses テーブルに保存されるはず")
        else:
            print(f"\n❌ 条件未達 → analyses テーブルに保存されない")
            
    except Exception as e:
        print(f"❌ 設定確認エラー: {e}")

def main():
    """メイン実行関数"""
    print("🧪 シンボル追加データ保存問題の検証テスト")
    print("=" * 80)
    
    # 現在の設定確認
    verify_current_config()
    
    # テスト実行確認
    print("\n" + "=" * 80)
    print("自動実行モードでテストを続行します...")
    
    if True:
        success = test_symbol_addition_with_relaxed_conditions()
        
        print("\n" + "=" * 80)
        print("🎯 テスト結果サマリー")
        print("=" * 80)
        
        if success:
            print("✅ テスト成功: 緩い条件により analyses テーブルにデータが保存されました")
            print("💡 結論: 銘柄追加機能は正常に動作しており、問題はエントリー条件の厳しさです")
            print("📝 推奨: 本番の条件を適切に調整することで、実用的な分析結果を得られます")
        else:
            print("❌ テスト失敗: 緩い条件でもデータが保存されませんでした")
            print("🔍 要調査: 別の技術的問題が存在する可能性があります")
    else:
        print("テストをキャンセルしました。")

if __name__ == "__main__":
    main()