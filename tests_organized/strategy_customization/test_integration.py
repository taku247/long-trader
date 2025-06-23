#!/usr/bin/env python3
"""
戦略カスタマイズ機能の統合テスト

戦略カスタマイズ機能全体の統合テスト
- エンドツーエンドの戦略作成から実行まで
- アラート生成時の戦略トレーサビリティ
- 既存システムとの統合
"""

import sys
import os
import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

# BaseTestを使用して安全にテスト
from tests_organized.base_test import BaseTest

class StrategyCustomizationIntegrationTest(BaseTest):
    """戦略カスタマイズ統合テスト"""
    
    def custom_setup(self):
        """統合テスト用セットアップ"""
        # 必要なテーブル作成
        self.create_strategy_configurations_table()
        self.modify_analyses_table_for_integration()
        self.modify_alerts_table_for_integration()
        
        # テスト用戦略の作成
        self.create_test_strategies()
    
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
    
    def modify_analyses_table_for_integration(self):
        """analyses テーブルに戦略設定関連カラムを追加"""
        with sqlite3.connect(self.analysis_db) as conn:
            # 既存のテーブル構造確認
            cursor = conn.execute("PRAGMA table_info(analyses)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'strategy_config_id' not in columns:
                conn.execute("ALTER TABLE analyses ADD COLUMN strategy_config_id INTEGER")
            if 'strategy_name' not in columns:
                conn.execute("ALTER TABLE analyses ADD COLUMN strategy_name TEXT")
    
    def modify_alerts_table_for_integration(self):
        """alerts テーブルに戦略設定関連カラムを追加"""
        # alert_history.db は別ファイルなので、テスト用のアラートテーブルを作成
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE,
                    symbol TEXT,
                    alert_type TEXT,
                    priority TEXT,
                    timestamp DATETIME,
                    leverage REAL,
                    confidence REAL,
                    strategy TEXT,
                    timeframe TEXT,
                    entry_price REAL,
                    target_price REAL,
                    stop_loss REAL,
                    strategy_config_id INTEGER,
                    analysis_id INTEGER,
                    extra_data TEXT
                )
            """)
    
    def create_test_strategies(self):
        """テスト用戦略の作成"""
        self.test_strategies = [
            {
                'name': 'BTC Conservative Pro',
                'base_strategy': 'Conservative_ML',
                'timeframe': '1h',
                'parameters': json.dumps({
                    'risk_multiplier': 0.9,
                    'confidence_boost': 0.05,
                    'leverage_cap': 75,
                    'min_risk_reward': 1.3,
                    'stop_loss_percent': 4.5,
                    'take_profit_percent': 14.0,
                    'custom_sltp_calculator': 'ConservativeSLTPCalculator',
                    'additional_filters': {
                        'min_volume_usd': 5000000,
                        'btc_correlation_max': 0.6
                    }
                }),
                'description': 'Professional BTC conservative strategy with enhanced parameters'
            },
            {
                'name': 'ETH Momentum Hunter',
                'base_strategy': 'Aggressive_ML',
                'timeframe': '30m',
                'parameters': json.dumps({
                    'risk_multiplier': 1.4,
                    'confidence_boost': -0.1,
                    'leverage_cap': 120,
                    'min_risk_reward': 1.0,
                    'stop_loss_percent': 3.0,
                    'take_profit_percent': 18.0,
                    'custom_sltp_calculator': 'AggressiveSLTPCalculator',
                    'additional_filters': {
                        'min_volume_usd': 3000000,
                        'btc_correlation_max': 0.9
                    }
                }),
                'description': 'Aggressive ETH momentum trading strategy'
            },
            {
                'name': 'Scalping Master 15m',
                'base_strategy': 'Balanced',
                'timeframe': '15m',
                'parameters': json.dumps({
                    'risk_multiplier': 1.1,
                    'confidence_boost': 0.0,
                    'leverage_cap': 90,
                    'min_risk_reward': 1.1,
                    'stop_loss_percent': 2.5,
                    'take_profit_percent': 8.0,
                    'custom_sltp_calculator': 'DefaultSLTPCalculator'
                }),
                'description': 'Fast scalping strategy for 15m timeframe'
            }
        ]
        
        # 戦略をDBに保存
        self.strategy_ids = []
        for strategy in self.test_strategies:
            strategy_id = self.insert_strategy_config(strategy)
            self.strategy_ids.append(strategy_id)
    
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
    
    def test_end_to_end_strategy_workflow(self):
        """エンドツーエンドの戦略ワークフローテスト"""
        print("\n🧪 エンドツーエンド戦略ワークフローテスト")
        
        # フェーズ1: 戦略作成
        print("   📝 フェーズ1: 戦略作成")
        
        custom_strategy = {
            'name': 'E2E Test Strategy',
            'base_strategy': 'Custom_ML',
            'timeframe': '1h',
            'parameters': json.dumps({
                'risk_multiplier': 1.3,
                'leverage_cap': 85,
                'min_risk_reward': 1.2,
                'custom_sltp_calculator': 'CustomSLTPCalculator'
            }),
            'description': 'End-to-end test strategy'
        }
        
        strategy_id = self.insert_strategy_config(custom_strategy)
        self.assertIsNotNone(strategy_id, "戦略作成に失敗しました")
        print(f"      ✅ 戦略作成成功: ID={strategy_id}")
        
        # フェーズ2: 銘柄追加（選択的実行）
        print("   📊 フェーズ2: 銘柄追加（選択的実行）")
        
        symbol = "E2E_TEST"
        execution_id = self.insert_test_execution_log(f"e2e_test_{int(time.time())}", symbol, "SUCCESS")
        
        # 選択された戦略のみで分析実行
        analysis_id = self.insert_test_analysis_with_strategy_config(
            execution_id, symbol, '1h', 'Custom_ML',
            strategy_config_id=strategy_id,
            strategy_name=custom_strategy['name'],
            sharpe_ratio=1.8,
            total_return=0.32
        )
        
        self.assertIsNotNone(analysis_id, "分析結果の作成に失敗しました")
        print(f"      ✅ 分析実行成功: ID={analysis_id}")
        
        # フェーズ3: アラート生成
        print("   🚨 フェーズ3: アラート生成")
        
        alert_id = f"e2e_alert_{int(time.time())}"
        alert_data = {
            'alert_id': alert_id,
            'symbol': symbol,
            'alert_type': 'LONG_ENTRY',
            'priority': 'HIGH',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'leverage': 85,
            'confidence': 0.78,
            'strategy': 'Custom_ML',
            'timeframe': '1h',
            'entry_price': 3500.0,
            'target_price': 3920.0,
            'stop_loss': 3325.0,
            'strategy_config_id': strategy_id,
            'analysis_id': analysis_id,
            'extra_data': json.dumps({'source': 'e2e_test'})
        }
        
        with sqlite3.connect(self.analysis_db) as conn:
            conn.execute("""
                INSERT INTO test_alerts 
                (alert_id, symbol, alert_type, priority, timestamp, leverage, confidence,
                 strategy, timeframe, entry_price, target_price, stop_loss,
                 strategy_config_id, analysis_id, extra_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_data['alert_id'], alert_data['symbol'], alert_data['alert_type'],
                alert_data['priority'], alert_data['timestamp'], alert_data['leverage'],
                alert_data['confidence'], alert_data['strategy'], alert_data['timeframe'],
                alert_data['entry_price'], alert_data['target_price'], alert_data['stop_loss'],
                alert_data['strategy_config_id'], alert_data['analysis_id'], alert_data['extra_data']
            ))
        
        print(f"      ✅ アラート生成成功: ID={alert_id}")
        
        # フェーズ4: トレーサビリティ確認
        print("   🔍 フェーズ4: トレーサビリティ確認")
        
        # 戦略 → 分析 → アラートの完全な関連性を確認
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT 
                    sc.name as strategy_name,
                    sc.parameters,
                    a.symbol,
                    a.sharpe_ratio,
                    a.total_return,
                    ta.alert_id,
                    ta.leverage,
                    ta.confidence
                FROM strategy_configurations sc
                INNER JOIN analyses a ON sc.id = a.strategy_config_id
                INNER JOIN test_alerts ta ON a.id = ta.analysis_id
                WHERE sc.id = ?
            """, (strategy_id,))
            
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "戦略トレーサビリティの確認に失敗しました")
            
            strategy_name, parameters, analysis_symbol, sharpe_ratio, total_return, alert_id_result, alert_leverage, alert_confidence = result
            
            # 各段階でのデータ整合性を確認
            self.assertEqual(strategy_name, custom_strategy['name'])
            self.assertEqual(analysis_symbol, symbol)
            self.assertEqual(alert_id_result, alert_id)
            self.assertEqual(alert_leverage, 85)
            
            print(f"      ✅ 戦略トレーサビリティ確認成功")
            print(f"         戦略: {strategy_name}")
            print(f"         分析: {analysis_symbol}, Sharpe={sharpe_ratio}")
            print(f"         アラート: {alert_id_result}, Lev={alert_leverage}x")
        
        print("   🎉 エンドツーエンドワークフロー完了")
    
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
                15, 0.67, total_return, sharpe_ratio, max_drawdown, 1.0,
                'COMPLETED', datetime.now(timezone.utc).isoformat()
            ))
            return cursor.lastrowid
    
    def test_multi_strategy_comparison(self):
        """複数戦略比較テスト"""
        print("\n🧪 複数戦略比較テスト")
        
        # 同一銘柄・時間足で異なる戦略を実行
        symbol = "COMPARISON_TEST"
        timeframe = "1h"
        execution_id = self.insert_test_execution_log(f"comparison_test_{int(time.time())}", symbol, "SUCCESS")
        
        # 3つの異なる戦略で実行
        comparison_results = []
        
        for i, strategy_id in enumerate(self.strategy_ids):
            # 戦略設定取得
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.execute("""
                    SELECT name, base_strategy, parameters 
                    FROM strategy_configurations 
                    WHERE id = ?
                """, (strategy_id,))
                strategy_data = cursor.fetchone()
                
                name, base_strategy, parameters_json = strategy_data
                parameters = json.loads(parameters_json)
            
            # 各戦略で異なるパフォーマンスを模擬
            performance_variations = [
                {'sharpe_ratio': 1.2, 'total_return': 0.18, 'win_rate': 0.58},
                {'sharpe_ratio': 1.7, 'total_return': 0.28, 'win_rate': 0.72},
                {'sharpe_ratio': 1.4, 'total_return': 0.22, 'win_rate': 0.65}
            ]
            
            perf = performance_variations[i]
            
            analysis_id = self.insert_test_analysis_with_strategy_config(
                execution_id, symbol, timeframe, base_strategy,
                strategy_config_id=strategy_id,
                strategy_name=name,
                sharpe_ratio=perf['sharpe_ratio'],
                total_return=perf['total_return']
            )
            
            comparison_results.append({
                'strategy_id': strategy_id,
                'strategy_name': name,
                'analysis_id': analysis_id,
                'risk_multiplier': parameters['risk_multiplier'],
                'leverage_cap': parameters['leverage_cap'],
                'sharpe_ratio': perf['sharpe_ratio'],
                'total_return': perf['total_return']
            })
            
            print(f"   📊 戦略{i+1}: {name} - Sharpe={perf['sharpe_ratio']}, Return={perf['total_return']}")
        
        # 比較クエリのテスト
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT 
                    sc.name as strategy_name,
                    sc.parameters,
                    a.sharpe_ratio,
                    a.total_return
                FROM strategy_configurations sc
                INNER JOIN analyses a ON sc.id = a.strategy_config_id
                WHERE a.symbol = ? AND a.timeframe = ?
                ORDER BY a.sharpe_ratio DESC
            """, (symbol, timeframe))
            
            results = cursor.fetchall()
            
            self.assertEqual(len(results), 3, "比較対象の戦略数が期待値と一致しません")
            
            # Sharpe ratioでソートされていることを確認
            sharpe_ratios = [result[2] for result in results]
            self.assertEqual(sharpe_ratios, sorted(sharpe_ratios, reverse=True), "Sharpe ratioでソートされていません")
            
            print(f"   ✅ 戦略比較クエリ成功: {len(results)}戦略を比較")
            
            # 最高パフォーマンス戦略の特定
            best_strategy = results[0]
            print(f"   🏆 最高パフォーマンス: {best_strategy[0]} (Sharpe={best_strategy[2]})")
    
    def test_strategy_performance_tracking(self):
        """戦略パフォーマンス追跡テスト"""
        print("\n🧪 戦略パフォーマンス追跡テスト")
        
        # 特定戦略の複数回実行結果を追跡
        strategy_id = self.strategy_ids[0]  # BTC Conservative Pro
        
        # 複数の銘柄・時期での実行結果を模擬
        test_cases = [
            {'symbol': 'BTC', 'sharpe': 1.5, 'return': 0.22, 'date': '2025-06-20'},
            {'symbol': 'ETH', 'sharpe': 1.3, 'return': 0.18, 'date': '2025-06-21'},
            {'symbol': 'SOL', 'sharpe': 1.7, 'return': 0.26, 'date': '2025-06-22'},
            {'symbol': 'BTC', 'sharpe': 1.4, 'return': 0.20, 'date': '2025-06-23'}
        ]
        
        analysis_ids = []
        for case in test_cases:
            execution_id = self.insert_test_execution_log(
                f"tracking_test_{case['symbol']}_{case['date']}", 
                case['symbol'], 
                "SUCCESS"
            )
            
            analysis_id = self.insert_test_analysis_with_strategy_config(
                execution_id, case['symbol'], '1h', 'Conservative_ML',
                strategy_config_id=strategy_id,
                strategy_name='BTC Conservative Pro',
                sharpe_ratio=case['sharpe'],
                total_return=case['return']
            )
            analysis_ids.append(analysis_id)
        
        # パフォーマンス集計クエリ
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as execution_count,
                    AVG(sharpe_ratio) as avg_sharpe,
                    MAX(sharpe_ratio) as max_sharpe,
                    MIN(sharpe_ratio) as min_sharpe,
                    AVG(total_return) as avg_return,
                    MAX(total_return) as max_return
                FROM analyses 
                WHERE strategy_config_id = ?
            """, (strategy_id,))
            
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "パフォーマンス集計結果が取得できません")
            
            execution_count, avg_sharpe, max_sharpe, min_sharpe, avg_return, max_return = result
            
            self.assertEqual(execution_count, len(test_cases), "実行回数が期待値と一致しません")
            self.assertAlmostEqual(avg_sharpe, 1.475, places=2, msg="平均Sharpe ratioが期待値と一致しません")
            self.assertEqual(max_sharpe, 1.7, "最大Sharpe ratioが期待値と一致しません")
            
            print(f"   📈 戦略パフォーマンス集計:")
            print(f"      実行回数: {execution_count}")
            print(f"      平均Sharpe: {avg_sharpe:.3f}")
            print(f"      最大Sharpe: {max_sharpe}")
            print(f"      平均リターン: {avg_return:.3f}")
            print(f"      最大リターン: {max_return}")
        
        # 銘柄別パフォーマンス
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as count,
                    AVG(sharpe_ratio) as avg_sharpe
                FROM analyses 
                WHERE strategy_config_id = ?
                GROUP BY symbol
                ORDER BY avg_sharpe DESC
            """, (strategy_id,))
            
            symbol_results = cursor.fetchall()
            
            print(f"   📊 銘柄別パフォーマンス:")
            for symbol, count, avg_sharpe in symbol_results:
                print(f"      {symbol}: {count}回, 平均Sharpe={avg_sharpe:.3f}")
        
        print(f"   ✅ 戦略パフォーマンス追跡成功")
    
    def test_alert_strategy_traceability(self):
        """アラート戦略トレーサビリティテスト"""
        print("\n🧪 アラート戦略トレーサビリティテスト")
        
        # 複数の戦略から生成されたアラートの追跡
        symbol = "TRACE_TEST"
        execution_id = self.insert_test_execution_log(f"trace_test_{int(time.time())}", symbol, "SUCCESS")
        
        # 2つの異なる戦略で分析実行
        strategy_analyses = []
        
        for i, strategy_id in enumerate(self.strategy_ids[:2]):
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.execute("""
                    SELECT name, base_strategy, timeframe 
                    FROM strategy_configurations 
                    WHERE id = ?
                """, (strategy_id,))
                strategy_data = cursor.fetchone()
                name, base_strategy, timeframe = strategy_data
            
            analysis_id = self.insert_test_analysis_with_strategy_config(
                execution_id, symbol, timeframe, base_strategy,
                strategy_config_id=strategy_id,
                strategy_name=name,
                sharpe_ratio=1.5 + i * 0.2
            )
            
            strategy_analyses.append({
                'strategy_id': strategy_id,
                'strategy_name': name,
                'analysis_id': analysis_id,
                'timeframe': timeframe
            })
        
        # 各分析からアラート生成
        alert_ids = []
        for i, sa in enumerate(strategy_analyses):
            alert_id = f"trace_alert_{sa['strategy_id']}_{int(time.time())}"
            
            with sqlite3.connect(self.analysis_db) as conn:
                conn.execute("""
                    INSERT INTO test_alerts 
                    (alert_id, symbol, alert_type, timestamp, leverage, confidence,
                     strategy, timeframe, entry_price, target_price, stop_loss,
                     strategy_config_id, analysis_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert_id, symbol, 'LONG_ENTRY', datetime.now(timezone.utc).isoformat(),
                    75 + i * 10, 0.7 + i * 0.05, sa['strategy_name'], sa['timeframe'],
                    3500.0, 3850.0, 3350.0, sa['strategy_id'], sa['analysis_id']
                ))
            
            alert_ids.append(alert_id)
            print(f"   🚨 アラート生成: {alert_id} (戦略: {sa['strategy_name']})")
        
        # トレーサビリティクエリ
        with sqlite3.connect(self.analysis_db) as conn:
            cursor = conn.execute("""
                SELECT 
                    ta.alert_id,
                    sc.name as strategy_name,
                    sc.base_strategy,
                    sc.timeframe,
                    sc.parameters,
                    a.sharpe_ratio,
                    a.total_return,
                    ta.leverage,
                    ta.confidence
                FROM test_alerts ta
                INNER JOIN analyses a ON ta.analysis_id = a.id
                INNER JOIN strategy_configurations sc ON ta.strategy_config_id = sc.id
                WHERE ta.symbol = ?
                ORDER BY ta.timestamp
            """, (symbol,))
            
            traceability_results = cursor.fetchall()
            
            self.assertEqual(len(traceability_results), 2, "トレーサビリティ結果数が期待値と一致しません")
            
            print(f"   🔍 戦略トレーサビリティ結果:")
            for result in traceability_results:
                alert_id, strategy_name, base_strategy, timeframe, parameters, sharpe_ratio, total_return, leverage, confidence = result
                params = json.loads(parameters)
                risk_multiplier = params.get('risk_multiplier', 'N/A')
                
                print(f"      アラート: {alert_id}")
                print(f"        戦略: {strategy_name} ({base_strategy} - {timeframe})")
                print(f"        パラメータ: risk_multiplier={risk_multiplier}")
                print(f"        分析結果: Sharpe={sharpe_ratio}, Return={total_return}")
                print(f"        アラート: Lev={leverage}x, Conf={confidence}")
                print()
            
            # 戦略別アラート集計
            cursor = conn.execute("""
                SELECT 
                    sc.name,
                    COUNT(*) as alert_count,
                    AVG(ta.leverage) as avg_leverage,
                    AVG(ta.confidence) as avg_confidence
                FROM test_alerts ta
                INNER JOIN strategy_configurations sc ON ta.strategy_config_id = sc.id
                WHERE ta.symbol = ?
                GROUP BY sc.id, sc.name
            """, (symbol,))
            
            aggregation_results = cursor.fetchall()
            
            print(f"   📊 戦略別アラート集計:")
            for name, alert_count, avg_leverage, avg_confidence in aggregation_results:
                print(f"      {name}: {alert_count}件, 平均Lev={avg_leverage:.1f}x, 平均Conf={avg_confidence:.3f}")
        
        print(f"   ✅ アラート戦略トレーサビリティ成功")

def run_integration_tests():
    """統合テスト実行"""
    import unittest
    
    # テストスイート作成
    suite = unittest.TestSuite()
    test_class = StrategyCustomizationIntegrationTest
    
    # 個別テストメソッドを追加
    suite.addTest(test_class('test_end_to_end_strategy_workflow'))
    suite.addTest(test_class('test_multi_strategy_comparison'))
    suite.addTest(test_class('test_strategy_performance_tracking'))
    suite.addTest(test_class('test_alert_strategy_traceability'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "="*60)
    print("🧪 戦略カスタマイズ統合テスト結果")
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
        print("\n🎉 すべての統合テストが成功しました！")
        print("戦略カスタマイズ機能の統合は正常に動作しています。")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)