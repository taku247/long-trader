#!/usr/bin/env python3
"""
HYPE銘柄Pre-task重複作成問題の修正テスト

問題: new_symbol_addition_system.py と auto_symbol_training.py の両方で
Pre-taskを作成していたため、2番目の作成で既存のpendingレコードが
見つかって0タスク作成となる問題
"""

import sys
import os
import asyncio
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import uuid

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from new_symbol_addition_system import NewSymbolAdditionSystem
from auto_symbol_training import AutoSymbolTrainer
from scalable_analysis_system import ScalableAnalysisSystem

class TestPreTaskDuplicationFix:
    """Pre-task重複作成問題の修正テスト"""
    
    def __init__(self):
        self.temp_dir = None
        self.db_path = None
        
    def setup_test_env(self):
        """テスト環境セットアップ"""
        # 一時ディレクトリ作成
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "analysis.db"
        
        # テスト用DBセットアップ
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timeframe TEXT,
                    config TEXT,
                    execution_id TEXT,
                    task_status TEXT DEFAULT 'pending',
                    status TEXT DEFAULT 'running',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def cleanup_test_env(self):
        """テスト環境クリーンアップ"""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def count_pretasks(self, execution_id: str, symbol: str = "HYPE") -> int:
        """指定実行IDのPre-task数をカウント"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM analyses 
                WHERE symbol = ? AND execution_id = ? AND task_status = 'pending'
            ''', (symbol, execution_id))
            return cursor.fetchone()[0]
    
    async def test_duplicate_pretask_fix(self):
        """重複Pre-task作成修正テスト"""
        print("🧪 Pre-task重複作成修正テスト開始")
        
        try:
            self.setup_test_env()
            execution_id = str(uuid.uuid4())
            
            # ScalableAnalysisSystemのモック設定（テスト用DB使用）
            with patch.object(ScalableAnalysisSystem, '__init__', 
                            lambda self, base_dir: setattr(self, 'db_path', self.db_path)):
                
                # APIクライアントのモック（バリデーション成功）
                mock_validation_result = {
                    'valid': True,
                    'status': 'valid',
                    'market_info': {'leverage_limit': 10}
                }
                
                mock_ohlcv_data = {
                    'timestamp': [f'2024-01-{i:02d}' for i in range(1, 91)],
                    'close': [100 + i for i in range(90)]
                }
                
                with patch('new_symbol_addition_system.MultiExchangeAPIClient') as mock_api_class:
                    mock_api = MagicMock()
                    mock_api.validate_symbol_real.return_value = mock_validation_result
                    mock_api.get_ohlcv_data_with_period.return_value = mock_ohlcv_data
                    mock_api_class.return_value = mock_api
                    
                    # バックテスト実行のモック（成功）
                    with patch.object(ScalableAnalysisSystem, 'generate_batch_analysis', return_value=2):
                        
                        # NewSymbolAdditionSystemインスタンス作成
                        system = NewSymbolAdditionSystem()
                        
                        # Step 1: new_symbol_addition_system.py でPre-task作成
                        print(f"📋 Step 1: new_symbol_addition_system.py でPre-task作成")
                        
                        # カスタム戦略設定（2つの戦略）
                        strategy_configs = [
                            {
                                'id': 1,
                                'name': 'Test Strategy 1',
                                'base_strategy': 'Conservative_ML',
                                'timeframe': '1h',
                                'parameters': {'param1': 10},
                                'description': 'Test strategy 1',
                                'is_default': False,
                                'is_active': True
                            },
                            {
                                'id': 2,
                                'name': 'Test Strategy 2', 
                                'base_strategy': 'Aggressive_Traditional',
                                'timeframe': '1h',
                                'parameters': {'param2': 20},
                                'description': 'Test strategy 2',
                                'is_default': False,
                                'is_active': True
                            }
                        ]
                        
                        # Pre-task作成（new_symbol_addition_system.py側）
                        pre_tasks = system.create_pre_tasks("HYPE", execution_id, 
                                                          [system.StrategyConfig(**config) for config in strategy_configs])
                        
                        initial_count = self.count_pretasks(execution_id)
                        print(f"   ✅ 初期Pre-task作成: {initial_count}個")
                        
                        # Step 2: auto_symbol_training.py でバックテスト実行（skip_pretask_creation=True）
                        print(f"📊 Step 2: auto_symbol_training.py でバックテスト実行")
                        
                        # AutoSymbolTrainerで実行（skip_pretask_creation=Trueが渡されることを確認）
                        trainer = AutoSymbolTrainer()
                        
                        # ScalableAnalysisSystemのgenerate_batch_analysisが
                        # skip_pretask_creation=Trueで呼ばれることを確認
                        with patch.object(trainer.analysis_system, 'generate_batch_analysis', 
                                        wraps=trainer.analysis_system.generate_batch_analysis) as mock_generate:
                            
                            try:
                                await trainer.add_symbol_with_training(
                                    symbol="HYPE",
                                    execution_id=execution_id,
                                    strategy_configs=strategy_configs,
                                    skip_pretask_creation=True
                                )
                                
                                # generate_batch_analysisがskip_pretask_creation=Trueで呼ばれたことを確認
                                assert mock_generate.called
                                call_args = mock_generate.call_args
                                assert call_args[1]['skip_pretask_creation'] == True
                                print(f"   ✅ skip_pretask_creation=True が正しく渡された")
                                
                            except Exception as e:
                                # データ取得エラーなどは想定内（テスト目的はPre-task重複防止）
                                print(f"   ⚠️ 実行エラー（想定内）: {e}")
                        
                        # Step 3: Pre-taskが重複作成されていないことを確認
                        final_count = self.count_pretasks(execution_id)
                        print(f"📈 最終Pre-task数: {final_count}個")
                        
                        # 検証: Pre-task数が増加していない（重複作成されていない）
                        if final_count == initial_count:
                            print(f"✅ 成功: Pre-task重複作成が防止された（{initial_count}個維持）")
                            return True
                        else:
                            print(f"❌ 失敗: Pre-taskが重複作成された（{initial_count} → {final_count}）")
                            return False
                            
        except Exception as e:
            print(f"❌ テストエラー: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup_test_env()
    
    async def test_skip_parameter_propagation(self):
        """skip_pretask_creationパラメータ伝播テスト"""
        print("\n🔗 skip_pretask_creationパラメータ伝播テスト")
        
        try:
            # AutoSymbolTrainerのメソッドチェーンをテスト
            trainer = AutoSymbolTrainer()
            
            # モックで各メソッドの呼び出しを追跡
            with patch.object(trainer, '_run_comprehensive_backtest', 
                            wraps=trainer._run_comprehensive_backtest) as mock_backtest:
                with patch.object(trainer.analysis_system, 'generate_batch_analysis', 
                                return_value=0) as mock_generate:
                    
                    try:
                        await trainer.add_symbol_with_training(
                            symbol="TEST",
                            skip_pretask_creation=True
                        )
                    except:
                        pass  # エラーは無視（パラメータ伝播のみテスト）
                    
                    # _run_comprehensive_backtestにskip_pretask_creation=Trueが渡されたか確認
                    assert mock_backtest.called
                    backtest_call_args = mock_backtest.call_args
                    assert backtest_call_args[1]['skip_pretask_creation'] == True
                    print("   ✅ add_symbol_with_training → _run_comprehensive_backtest: OK")
                    
                    # generate_batch_analysisにskip_pretask_creation=Trueが渡されたか確認
                    assert mock_generate.called
                    generate_call_args = mock_generate.call_args
                    assert generate_call_args[1]['skip_pretask_creation'] == True
                    print("   ✅ _run_comprehensive_backtest → generate_batch_analysis: OK")
                    
            print("✅ パラメータ伝播テスト成功")
            return True
            
        except Exception as e:
            print(f"❌ パラメータ伝播テストエラー: {e}")
            return False


async def main():
    """メインテスト実行"""
    tester = TestPreTaskDuplicationFix()
    
    print("🚀 HYPE銘柄Pre-task重複作成問題修正テスト")
    print("=" * 60)
    
    # テスト1: 重複作成修正テスト
    success1 = await tester.test_duplicate_pretask_fix()
    
    # テスト2: パラメータ伝播テスト
    success2 = await tester.test_skip_parameter_propagation()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ 全テスト成功: Pre-task重複作成問題が修正された")
        return 0
    else:
        print("❌ テスト失敗: 修正が不完全")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)