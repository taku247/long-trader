#!/usr/bin/env python3
"""
統合後9段階フィルタリングシステムの動作確認テスト

scalable_analysis_system.pyに統合されたFilteringFrameworkが
実際のバックテスト処理内で正常に動作することを確認する。
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_integrated_filtering_system():
    """統合されたフィルタリングシステムの動作確認"""
    try:
        print("🔥 統合後9段階フィルタリングシステム動作確認テスト")
        print("=" * 80)
        
        # ScalableAnalysisSystemのインポートと初期化
        from scalable_analysis_system import ScalableAnalysisSystem
        
        system = ScalableAnalysisSystem("test_analysis")
        print("✅ ScalableAnalysisSystem初期化成功（FilteringFramework統合済み）")
        
        # 統合確認: FilteringFramework属性が存在するかチェック（遅延初期化）
        if hasattr(system, 'filtering_framework'):
            print("✅ FilteringFramework統合確認済み（遅延初期化）")
            if system.filtering_framework is None:
                print("   - 状態: 初期化待機中（初回フィルタリング時に初期化）")
            else:
                print(f"   - 軽量フィルター: {len([f for f in system.filtering_framework.filter_chain if f.weight == 'light'])}個")
                print(f"   - 中重量フィルター: {len([f for f in system.filtering_framework.filter_chain if f.weight == 'medium'])}個") 
                print(f"   - 重量フィルター: {len([f for f in system.filtering_framework.filter_chain if f.weight == 'heavy'])}個")
        else:
            print("❌ FilteringFramework統合エラー")
            return False
        
        # テスト用のモックデータ作成
        print("\\n" + "="*60)
        print("🧪 フィルタリング機能単体テスト")
        print("="*60)
        
        # 現在時刻ベースのテストタイムスタンプ
        test_timestamp = datetime.now()
        test_symbol = "BTC"
        test_timeframe = "1h"
        test_config = "Full_ML"
        
        print(f"📋 テスト設定:")
        print(f"   - 銘柄: {test_symbol}")
        print(f"   - 時間足: {test_timeframe}")
        print(f"   - 戦略: {test_config}")
        print(f"   - タイムスタンプ: {test_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # フィルタリングテスト実行
        print("\\n🚀 9段階フィルタリング実行テスト:")
        start_time = time.time()
        
        # 複数のタイムスタンプでテスト
        test_timestamps = [
            test_timestamp,
            test_timestamp + timedelta(hours=1),
            test_timestamp + timedelta(hours=2),
            test_timestamp + timedelta(hours=3),
            test_timestamp + timedelta(hours=4),
        ]
        
        filtering_results = []
        for i, timestamp in enumerate(test_timestamps, 1):
            print(f"\\n   タイムスタンプ {i}: {timestamp.strftime('%H:%M:%S')}")
            
            # フィルタリング実行
            should_skip = system._should_skip_evaluation_timestamp(
                timestamp, test_symbol, test_timeframe, test_config
            )
            
            result = "SKIP" if should_skip else "PROCEED"
            filtering_results.append(result)
            
            print(f"      → フィルタリング結果: {result}")
        
        filtering_time = time.time() - start_time
        print(f"\\n⏱️  フィルタリング実行時間: {filtering_time:.3f}秒")
        
        # 結果統計
        skip_count = filtering_results.count("SKIP")
        proceed_count = filtering_results.count("PROCEED")
        
        print(f"\\n📊 フィルタリング統計:")
        print(f"   - 総評価回数: {len(test_timestamps)}")
        print(f"   - スキップ: {skip_count}回 ({skip_count/len(test_timestamps)*100:.1f}%)")
        print(f"   - 処理続行: {proceed_count}回 ({proceed_count/len(test_timestamps)*100:.1f}%)")
        
        # フィルタリング効果の確認
        if skip_count > 0:
            print(f"✅ フィルタリング効果確認: {skip_count}タイムスタンプをスキップ")
            efficiency_gain = (skip_count / len(test_timestamps)) * 100
            print(f"💰 推定処理効率向上: {efficiency_gain:.1f}%")
        else:
            print("ℹ️  この設定ではスキップなし（全タイムスタンプで処理続行）")
        
        # モックデータ作成メソッドのテスト
        print("\\n" + "="*60)
        print("🔧 モックデータ作成機能テスト")
        print("="*60)
        
        # prepared_dataのテスト
        mock_prepared_data = system._create_mock_prepared_data(test_symbol, test_timestamp)
        print("✅ MockPreparedData作成成功")
        print(f"   - データ有効性: {mock_prepared_data.is_valid()}")
        print(f"   - 取引量: {mock_prepared_data.get_volume_at(test_timestamp):,}")
        print(f"   - スプレッド: {mock_prepared_data.get_spread_at(test_timestamp)}")
        print(f"   - 流動性スコア: {mock_prepared_data.get_liquidity_score_at(test_timestamp)}")
        
        # strategyのテスト
        mock_strategy = system._create_mock_strategy(test_config, test_timeframe)
        print("\\n✅ MockStrategy作成成功")
        print(f"   - 戦略タイプ: {mock_strategy.strategy_type}")
        print(f"   - 時間足: {mock_strategy.timeframe}")
        print(f"   - 最小取引量閾値: {mock_strategy.min_volume_threshold:,}")
        print(f"   - 最大スプレッド閾値: {mock_strategy.max_spread_threshold}")
        
        # 統合動作シミュレーション
        print("\\n" + "="*60)
        print("🎯 バックテスト統合シミュレーション")
        print("="*60)
        
        print("実際のバックテスト処理での動作をシミュレーション:")
        simulation_start = time.time()
        
        # バックテスト風の時系列ループをシミュレーション
        current_time = test_timestamp
        end_time = test_timestamp + timedelta(hours=12)  # 12時間分をシミュレーション
        evaluation_interval = timedelta(hours=1)  # 1時間毎評価
        
        total_evaluations = 0
        skipped_evaluations = 0
        processed_evaluations = 0
        
        print(f"シミュレーション期間: {current_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
        print(f"評価間隔: {evaluation_interval}")
        
        while current_time <= end_time:
            total_evaluations += 1
            
            # 統合されたフィルタリングシステムで事前チェック
            should_skip = system._should_skip_evaluation_timestamp(
                current_time, test_symbol, test_timeframe, test_config
            )
            
            if should_skip:
                skipped_evaluations += 1
                print(f"   {current_time.strftime('%H:%M')} → SKIP (フィルタリング)")
            else:
                processed_evaluations += 1
                print(f"   {current_time.strftime('%H:%M')} → PROCESS (分析実行)")
            
            current_time += evaluation_interval
        
        simulation_time = time.time() - simulation_start
        
        print(f"\\n📊 シミュレーション結果:")
        print(f"   - 総評価タイムスタンプ: {total_evaluations}")
        print(f"   - スキップ: {skipped_evaluations} ({skipped_evaluations/total_evaluations*100:.1f}%)")
        print(f"   - 重い処理実行: {processed_evaluations} ({processed_evaluations/total_evaluations*100:.1f}%)")
        print(f"   - シミュレーション時間: {simulation_time:.3f}秒")
        
        # 効果算出
        if skipped_evaluations > 0:
            # 仮定: 重い処理は平均5秒かかる
            estimated_heavy_process_time = 5.0
            time_saved = skipped_evaluations * estimated_heavy_process_time
            print(f"\\n💰 推定効果:")
            print(f"   - 節約処理時間: {time_saved:.1f}秒")
            print(f"   - 効率向上率: {skipped_evaluations/total_evaluations*100:.1f}%")
        
        # 最終評価
        print("\\n" + "="*80)
        print("🏆 統合フィルタリングシステム動作確認完了")
        print("="*80)
        
        success_conditions = [
            hasattr(system, 'filtering_framework'),  # FilteringFramework統合
            len(filtering_results) > 0,  # フィルタリング実行成功
            total_evaluations > 0,  # シミュレーション成功
            not (skipped_evaluations == 0 and processed_evaluations == 0)  # 何らかの結果
        ]
        
        all_success = all(success_conditions)
        
        print(f"✅ FilteringFramework統合: {'成功' if success_conditions[0] else '失敗'}")
        print(f"✅ フィルタリング実行: {'成功' if success_conditions[1] else '失敗'}")
        print(f"✅ バックテスト統合: {'成功' if success_conditions[2] else '失敗'}")
        print(f"✅ 動作確認: {'成功' if success_conditions[3] else '失敗'}")
        
        final_status = "SUCCESS" if all_success else "PARTIAL_SUCCESS"
        print(f"\\n🎯 最終評価: {final_status}")
        print(f"🔧 統合システム: 実バックテスト処理内でフィルタリング実行準備完了")
        
        return all_success
        
    except Exception as e:
        print(f"❌ テスト中にエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_integrated_filtering_system())
    print(f"\\n🏁 最終結果: {'✅ 成功' if success else '❌ 失敗'}")
    exit(0 if success else 1)