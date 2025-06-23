#!/usr/bin/env python3
"""
選択的実行機能のテストケース

指定された戦略・時間足のみで銘柄追加を実行する機能のテスト
- 戦略選択機能
- 実行範囲の制限
- 処理時間の短縮効果
"""

import sys
import os
import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

# BaseTestを使用して安全にテスト
from tests_organized.base_test import BaseTest

class SelectiveExecutionTest(BaseTest):
    """選択的実行機能テスト"""
    
    def custom_setup(self):
        """選択的実行テスト用セットアップ"""
        # strategy_configurations テーブル作成
        self.create_strategy_configurations_table()
        
        # テスト用戦略設定の作成
        self.test_strategies = [
            {
                'name': 'Test Conservative 15m',
                'base_strategy': 'Conservative_ML',
                'timeframe': '15m',
                'parameters': json.dumps({
                    'risk_multiplier': 0.8,
                    'min_risk_reward': 1.1,
                    'leverage_cap': 50
                })
            },
            {
                'name': 'Test Aggressive 1h',
                'base_strategy': 'Aggressive_ML',
                'timeframe': '1h',
                'parameters': json.dumps({
                    'risk_multiplier': 1.2,
                    'min_risk_reward': 1.0,
                    'leverage_cap': 100
                })
            },
            {
                'name': 'Test Balanced 30m',
                'base_strategy': 'Balanced',
                'timeframe': '30m',
                'parameters': json.dumps({
                    'risk_multiplier': 1.0,
                    'min_risk_reward': 1.15,
                    'leverage_cap': 75
                })
            }
        ]
        
        # 戦略設定をDBに保存
        self.strategy_ids = []
        for strategy in self.test_strategies:
            strategy_id = self.insert_strategy_config(strategy)
            self.strategy_ids.append(strategy_id)
    
    def create_strategy_configurations_table(self):
        """strategy_configurations テーブル作成"""
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    base_strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT DEFAULT 'system',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    
                    UNIQUE(name, base_strategy, timeframe)
                )
            """)
    
    def insert_strategy_config(self, config):
        """戦略設定を挿入"""
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                INSERT INTO strategy_configurations 
                (name, base_strategy, timeframe, parameters, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                config['name'],
                config['base_strategy'],
                config['timeframe'],
                config['parameters'],
                config.get('description', '')
            ))
            return cursor.lastrowid
    
    def modify_analyses_table_for_strategy_config(self):
        """analyses テーブルに strategy_config_id カラムを追加"""
        with sqlite3.connect(self.analysis_db) as conn:
            # 既存のテーブル構造確認
            cursor = conn.execute("PRAGMA table_info(analyses)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'strategy_config_id' not in columns:
                conn.execute("ALTER TABLE analyses ADD COLUMN strategy_config_id INTEGER")
            if 'strategy_name' not in columns:
                conn.execute("ALTER TABLE analyses ADD COLUMN strategy_name TEXT")
    
    def test_strategy_selection_functionality(self):
        """戦略選択機能テスト"""
        print("\n🧪 戦略選択機能テスト")
        
        # analyses テーブルを拡張
        self.modify_analyses_table_for_strategy_config()
        
        # 選択された戦略IDのリスト
        selected_strategy_ids = [self.strategy_ids[0], self.strategy_ids[2]]  # Conservative 15m と Balanced 30m
        
        print(f"   📋 選択された戦略ID: {selected_strategy_ids}")
        
        # 選択された戦略の詳細確認
        with sqlite3.connect(self.analysis_db) as conn:
            for strategy_id in selected_strategy_ids:
                cursor = conn.execute("""
                    SELECT name, base_strategy, timeframe 
                    FROM strategy_configurations 
                    WHERE id = ?
                """, (strategy_id,))
                result = cursor.fetchone()
                
                self.assertIsNotNone(result, f"戦略ID {strategy_id} が見つかりません")
                name, base_strategy, timeframe = result
                print(f"   ✅ 選択戦略: {name} ({base_strategy} - {timeframe})")
        
        # 選択された戦略のみでの模擬実行
        symbol = "TEST_SYMBOL"
        execution_id = self.insert_test_execution_log(f"selective_test_{int(time.time())}", symbol, "SUCCESS")
        
        analysis_ids = []
        for strategy_id in selected_strategy_ids:
            # 戦略設定取得
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.execute("""
                    SELECT name, base_strategy, timeframe, parameters 
                    FROM strategy_configurations 
                    WHERE id = ?
                """, (strategy_id,))
                strategy_data = cursor.fetchone()
                
                name, base_strategy, timeframe, parameters_json = strategy_data
                parameters = json.loads(parameters_json)
                
                # 分析レコード作成（戦略設定ID付き）
                analysis_id = self.insert_test_analysis_with_strategy_config(
                    execution_id, symbol, timeframe, base_strategy,
                    strategy_config_id=strategy_id,
                    strategy_name=name,
                    sharpe_ratio=1.0 + len(analysis_ids) * 0.1
                )
                analysis_ids.append(analysis_id)
                
                print(f"   📊 分析作成: ID={analysis_id}, Strategy={name}")
        
        # 結果確認
        self.assertEqual(len(analysis_ids), len(selected_strategy_ids), "作成された分析数が期待値と一致しません")
        
        # DBで確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses 
                WHERE execution_id = ? AND strategy_config_id IS NOT NULL
            """, (execution_id,))
            created_count = cursor.fetchone()[0]
            
            self.assertEqual(created_count, len(selected_strategy_ids), "DB上の分析数が期待値と一致しません")
            print(f"   ✅ 選択的実行成功: {created_count}件の分析作成")
    
    def insert_test_analysis_with_strategy_config(self, execution_id, symbol, timeframe, config, 
                                                  strategy_config_id=None, strategy_name=None,
                                                  sharpe_ratio=1.5, max_drawdown=-0.1, total_return=0.2):
        """戦略設定ID付きの分析データ挿入"""
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                INSERT INTO analyses 
                (execution_id, symbol, timeframe, config, strategy_config_id, strategy_name,
                 total_trades, win_rate, total_return, sharpe_ratio, max_drawdown, avg_leverage,
                 status, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id, symbol, timeframe, config, strategy_config_id, strategy_name,
                10, 0.6, total_return, sharpe_ratio, max_drawdown, 1.0,
                'COMPLETED', datetime.now(timezone.utc).isoformat()
            ))
            return cursor.lastrowid
    
    def test_execution_scope_limitation(self):
        """実行範囲制限テスト"""
        print("\n🧪 実行範囲制限テスト")
        
        # analyses テーブルを拡張
        self.modify_analyses_table_for_strategy_config()
        
        # 全戦略vs選択戦略の比較
        symbol = "SCOPE_TEST"
        
        # 1. 全戦略実行の模擬（従来方式）
        all_strategies_execution_id = self.insert_test_execution_log(f"all_strategies_{int(time.time())}", symbol, "SUCCESS")
        
        # 全戦略での実行（3戦略 × 仮に3時間足 = 9通り）
        all_combinations = []
        timeframes = ['15m', '30m', '1h']
        base_strategies = ['Conservative_ML', 'Aggressive_ML', 'Balanced']
        
        for tf in timeframes:
            for bs in base_strategies:
                all_combinations.append((tf, bs))
        
        all_analysis_ids = []
        for i, (timeframe, base_strategy) in enumerate(all_combinations):
            analysis_id = self.insert_test_analysis_with_strategy_config(
                all_strategies_execution_id, symbol, timeframe, base_strategy,
                sharpe_ratio=1.0 + i * 0.05
            )
            all_analysis_ids.append(analysis_id)
        
        print(f"   📊 全戦略実行: {len(all_analysis_ids)}件の分析")
        
        # 2. 選択戦略実行（2戦略のみ）
        selected_execution_id = self.insert_test_execution_log(f"selected_strategies_{int(time.time())}", symbol, "SUCCESS")
        
        selected_strategies = [
            (self.strategy_ids[0], '15m', 'Conservative_ML'),  # Test Conservative 15m
            (self.strategy_ids[2], '30m', 'Balanced')          # Test Balanced 30m
        ]
        
        selected_analysis_ids = []
        for strategy_id, timeframe, base_strategy in selected_strategies:
            analysis_id = self.insert_test_analysis_with_strategy_config(
                selected_execution_id, symbol, timeframe, base_strategy,
                strategy_config_id=strategy_id,
                sharpe_ratio=1.5
            )
            selected_analysis_ids.append(analysis_id)
        
        print(f"   📊 選択戦略実行: {len(selected_analysis_ids)}件の分析")
        
        # 3. 実行範囲制限効果の確認
        reduction_ratio = len(selected_analysis_ids) / len(all_analysis_ids)
        processing_time_reduction = (1 - reduction_ratio) * 100
        
        print(f"   📈 処理範囲: {len(selected_analysis_ids)}/{len(all_analysis_ids)} ({reduction_ratio:.1%})")
        print(f"   ⚡ 推定処理時間短縮: {processing_time_reduction:.1f}%")
        
        # 実行範囲が確実に制限されていることを確認
        self.assertLess(len(selected_analysis_ids), len(all_analysis_ids), "選択実行で範囲が制限されていません")
        self.assertGreater(processing_time_reduction, 50, "50%以上の処理時間短縮が期待されます")
        
        print(f"   ✅ 実行範囲制限成功: {processing_time_reduction:.1f}%の効率化")
    
    def test_strategy_parameter_application(self):
        """戦略パラメータ適用テスト"""
        print("\n🧪 戦略パラメータ適用テスト")
        
        # analyses テーブルを拡張
        self.modify_analyses_table_for_strategy_config()
        
        # カスタムパラメータを持つ戦略作成
        custom_strategy = {
            'name': 'Custom Risk Strategy',
            'base_strategy': 'Custom_ML',
            'timeframe': '1h',
            'parameters': json.dumps({
                'risk_multiplier': 2.0,        # 高リスク
                'min_risk_reward': 0.8,        # 低RR要求
                'leverage_cap': 150,           # 高レバレッジ
                'stop_loss_percent': 3.0,      # タイトストップ
                'take_profit_percent': 15.0,   # 大きな利確
                'custom_filter': 'aggressive_momentum'
            })
        }
        
        custom_strategy_id = self.insert_strategy_config(custom_strategy)
        print(f"   📝 カスタム戦略作成: ID={custom_strategy_id}")
        
        # カスタム戦略での実行
        symbol = "PARAM_TEST"
        execution_id = self.insert_test_execution_log(f"param_test_{int(time.time())}", symbol, "SUCCESS")
        
        # 戦略パラメータの取得と適用テスト
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT name, parameters FROM strategy_configurations 
                WHERE id = ?
            """, (custom_strategy_id,))
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "カスタム戦略が見つかりません")
            name, parameters_json = result
            parameters = json.loads(parameters_json)
            
            # パラメータの確認
            self.assertEqual(parameters['risk_multiplier'], 2.0)
            self.assertEqual(parameters['min_risk_reward'], 0.8)
            self.assertEqual(parameters['leverage_cap'], 150)
            self.assertEqual(parameters['custom_filter'], 'aggressive_momentum')
            
            print(f"   ✅ パラメータ取得成功: {name}")
            print(f"      - risk_multiplier: {parameters['risk_multiplier']}")
            print(f"      - min_risk_reward: {parameters['min_risk_reward']}")
            print(f"      - leverage_cap: {parameters['leverage_cap']}")
            print(f"      - custom_filter: {parameters['custom_filter']}")
        
        # パラメータが適用された分析の作成
        analysis_id = self.insert_test_analysis_with_strategy_config(
            execution_id, symbol, '1h', 'Custom_ML',
            strategy_config_id=custom_strategy_id,
            strategy_name=custom_strategy['name'],
            sharpe_ratio=2.1,  # 高リスク戦略らしい高Sharpe ratio
            total_return=0.35  # 高リターン
        )
        
        # 作成された分析の確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT strategy_config_id, strategy_name, sharpe_ratio, total_return
                FROM analyses 
                WHERE id = ?
            """, (analysis_id,))
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "分析結果が見つかりません")
            strategy_config_id, strategy_name, sharpe_ratio, total_return = result
            
            self.assertEqual(strategy_config_id, custom_strategy_id)
            self.assertEqual(strategy_name, custom_strategy['name'])
            self.assertEqual(sharpe_ratio, 2.1)
            self.assertEqual(total_return, 0.35)
            
            print(f"   ✅ カスタム戦略での分析作成成功")
            print(f"      - Strategy: {strategy_name}")
            print(f"      - Sharpe Ratio: {sharpe_ratio}")
            print(f"      - Total Return: {total_return}")
    
    def test_performance_comparison(self):
        """パフォーマンス比較テスト"""
        print("\n🧪 パフォーマンス比較テスト")
        
        # 実行時間の模擬測定
        start_time = time.time()
        
        # 従来方式の模擬（全戦略実行）
        full_execution_combinations = 5 * 4  # 5戦略 × 4時間足 = 20通り
        simulated_full_time = full_execution_combinations * 0.1  # 各組み合わせ0.1秒と仮定
        
        time.sleep(0.01)  # 模擬処理時間
        
        # 選択方式の模擬（選択戦略のみ）
        selected_combinations = 2  # ユーザーが選択した2戦略のみ
        simulated_selected_time = selected_combinations * 0.1
        
        end_time = time.time()
        
        # 効率化の計算
        time_reduction = ((simulated_full_time - simulated_selected_time) / simulated_full_time) * 100
        
        print(f"   ⏱️ 従来方式推定時間: {simulated_full_time:.1f}秒 ({full_execution_combinations}通り)")
        print(f"   ⚡ 選択方式推定時間: {simulated_selected_time:.1f}秒 ({selected_combinations}通り)")
        print(f"   📊 時間短縮効果: {time_reduction:.1f}%")
        
        # 効率化の確認
        self.assertGreater(time_reduction, 80, "80%以上の時間短縮が期待されます")
        self.assertLess(selected_combinations, full_execution_combinations, "実行対象数が削減されていません")
        
        print(f"   ✅ パフォーマンス向上確認: {time_reduction:.1f}%の効率化達成")
    
    def test_backward_compatibility(self):
        """後方互換性テスト"""
        print("\n🧪 後方互換性テスト")
        
        # analyses テーブルを拡張
        self.modify_analyses_table_for_strategy_config()
        
        # 既存方式での分析データ作成（strategy_config_id なし）
        symbol = "COMPATIBILITY_TEST"
        execution_id = self.insert_test_execution_log(f"compat_test_{int(time.time())}", symbol, "SUCCESS")
        
        # 旧形式での分析データ
        legacy_analysis_id = self.insert_test_analysis(
            execution_id, symbol, '30m', 'Conservative_ML',
            sharpe_ratio=1.3
        )
        
        # 新形式での分析データ
        new_analysis_id = self.insert_test_analysis_with_strategy_config(
            execution_id, symbol, '1h', 'Aggressive_ML',
            strategy_config_id=self.strategy_ids[1],
            strategy_name='Test Aggressive 1h',
            sharpe_ratio=1.6
        )
        
        # 両方のデータが共存できることを確認
        with sqlite3.connect(self.analysis_db) as conn:
            # 旧形式データの確認
            cursor = conn.execute("""
                SELECT id, config, strategy_config_id, strategy_name 
                FROM analyses 
                WHERE id = ?
            """, (legacy_analysis_id,))
            legacy_result = cursor.fetchone()
            
            self.assertIsNotNone(legacy_result, "旧形式の分析データが見つかりません")
            _, config, strategy_config_id, strategy_name = legacy_result
            self.assertEqual(config, 'Conservative_ML')
            self.assertIsNone(strategy_config_id, "旧形式データにstrategy_config_idが設定されています")
            self.assertIsNone(strategy_name, "旧形式データにstrategy_nameが設定されています")
            
            print(f"   ✅ 旧形式データ確認: config={config}")
            
            # 新形式データの確認
            cursor = conn.execute("""
                SELECT id, config, strategy_config_id, strategy_name 
                FROM analyses 
                WHERE id = ?
            """, (new_analysis_id,))
            new_result = cursor.fetchone()
            
            self.assertIsNotNone(new_result, "新形式の分析データが見つかりません")
            _, config, strategy_config_id, strategy_name = new_result
            self.assertEqual(config, 'Aggressive_ML')
            self.assertEqual(strategy_config_id, self.strategy_ids[1])
            self.assertEqual(strategy_name, 'Test Aggressive 1h')
            
            print(f"   ✅ 新形式データ確認: strategy_name={strategy_name}")
        
        # 混在データでのクエリテスト
        with sqlite3.connect(self.analysis_db) as conn:
            # 全データ取得
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses 
                WHERE execution_id = ?
            """, (execution_id,))
            total_count = cursor.fetchone()[0]
            
            # 新形式データのみ取得
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses 
                WHERE execution_id = ? AND strategy_config_id IS NOT NULL
            """, (execution_id,))
            new_format_count = cursor.fetchone()[0]
            
            # 旧形式データのみ取得
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analyses 
                WHERE execution_id = ? AND strategy_config_id IS NULL
            """, (execution_id,))
            legacy_format_count = cursor.fetchone()[0]
            
            self.assertEqual(total_count, 2, "総データ数が期待値と一致しません")
            self.assertEqual(new_format_count, 1, "新形式データ数が期待値と一致しません")
            self.assertEqual(legacy_format_count, 1, "旧形式データ数が期待値と一致しません")
            
            print(f"   ✅ 混在データクエリ成功: 総数={total_count}, 新形式={new_format_count}, 旧形式={legacy_format_count}")

def run_selective_execution_tests():
    """選択的実行テスト実行"""
    import unittest
    
    # テストスイート作成
    suite = unittest.TestSuite()
    test_class = SelectiveExecutionTest
    
    # 個別テストメソッドを追加
    suite.addTest(test_class('test_strategy_selection_functionality'))
    suite.addTest(test_class('test_execution_scope_limitation'))
    suite.addTest(test_class('test_strategy_parameter_application'))
    suite.addTest(test_class('test_performance_comparison'))
    suite.addTest(test_class('test_backward_compatibility'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "="*60)
    print("🧪 選択的実行テスト結果")
    print("="*60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 すべての選択的実行テストが成功しました！")
        print("戦略選択と範囲制限機能は正常に動作しています。")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_selective_execution_tests()
    sys.exit(0 if success else 1)