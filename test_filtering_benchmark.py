#!/usr/bin/env python3
"""
フィルタリングシステムベンチマークテスト

パフォーマンス計測とフィルタリング効果の定量評価
"""

import asyncio
import sys
import os
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class FilteringBenchmark:
    """フィルタリングシステムのベンチマークテスト"""
    
    def __init__(self):
        self.results = {}
        self.test_symbols = ["BTC", "ETH", "SOL"]  # 安全な実銘柄
        self.test_configs = [
            {'timeframe': '1m', 'strategy': 'Conservative_ML'},
            {'timeframe': '5m', 'strategy': 'Conservative_ML'},
            {'timeframe': '15m', 'strategy': 'Conservative_ML'},
            {'timeframe': '30m', 'strategy': 'Full_ML'},
            {'timeframe': '1h', 'strategy': 'Aggressive_Traditional'},
            {'timeframe': '4h', 'strategy': 'Full_ML'},
            {'timeframe': '1d', 'strategy': 'Conservative_ML'},
        ]
    
    async def run_benchmark(self):
        """ベンチマーク実行"""
        print("🔥 フィルタリングシステムベンチマークテスト開始")
        print("=" * 80)
        
        from auto_symbol_training import AutoSymbolTrainer
        trainer = AutoSymbolTrainer()
        
        benchmark_results = {}
        
        for symbol in self.test_symbols:
            print(f"\n🎯 ベンチマーク対象: {symbol}")
            print("-" * 50)
            
            symbol_result = await self._benchmark_symbol(trainer, symbol)
            benchmark_results[symbol] = symbol_result
            
            # 即座に結果表示
            self._print_symbol_results(symbol, symbol_result)
        
        # 全体統計の計算と表示
        self._print_overall_statistics(benchmark_results)
        
        return benchmark_results
    
    async def _benchmark_symbol(self, trainer, symbol: str) -> Dict[str, Any]:
        """銘柄別ベンチマーク"""
        result = {
            'symbol': symbol,
            'early_fail_time': 0.0,
            'early_fail_success': False,
            'filtering_time': 0.0,
            'total_configs': len(self.test_configs),
            'passed_configs': 0,
            'excluded_configs': 0,
            'exclusion_rate': 0.0,
            'error_occurred': False,
            'error_message': ""
        }
        
        try:
            # Phase 1: Early Fail検証のベンチマーク
            print(f"  🔍 Early Fail検証ベンチマーク...")
            early_fail_start = time.time()
            
            early_fail_result = await trainer._run_early_fail_validation(symbol)
            result['early_fail_time'] = time.time() - early_fail_start
            result['early_fail_success'] = early_fail_result.passed
            
            if not early_fail_result.passed:
                result['error_occurred'] = True
                result['error_message'] = f"Early Fail: {early_fail_result.fail_reason}"
                return result
            
            # Phase 2: FilteringFrameworkのベンチマーク
            print(f"  🚀 FilteringFramework事前検証ベンチマーク...")
            
            # テスト設定を準備
            test_configs = [
                {**config, 'symbol': symbol} 
                for config in self.test_configs
            ]
            
            filtering_start = time.time()
            filtered_configs = await trainer._apply_filtering_framework(
                test_configs, symbol, f"benchmark-{symbol}-{int(time.time())}"
            )
            result['filtering_time'] = time.time() - filtering_start
            
            result['passed_configs'] = len(filtered_configs)
            result['excluded_configs'] = len(test_configs) - len(filtered_configs)
            result['exclusion_rate'] = (result['excluded_configs'] / len(test_configs)) * 100
            
        except Exception as e:
            result['error_occurred'] = True
            result['error_message'] = str(e)
            print(f"  ❌ エラー: {str(e)}")
        
        return result
    
    def _print_symbol_results(self, symbol: str, result: Dict[str, Any]):
        """銘柄別結果表示"""
        print(f"\n📊 {symbol} ベンチマーク結果:")
        
        if result['error_occurred']:
            print(f"  ❌ エラー: {result['error_message']}")
            return
        
        print(f"  ✅ Early Fail検証: {result['early_fail_time']:.2f}秒")
        print(f"  ✅ フィルタリング: {result['filtering_time']:.2f}秒")
        print(f"  📈 通過設定: {result['passed_configs']}/{result['total_configs']}")
        print(f"  📉 除外率: {result['exclusion_rate']:.1f}%")
        print(f"  💰 推定節約: 約{result['exclusion_rate']:.0f}%の計算リソース")
    
    def _print_overall_statistics(self, benchmark_results: Dict[str, Dict[str, Any]]):
        """全体統計表示"""
        print("\n" + "=" * 80)
        print("📊 ベンチマーク全体統計")
        print("=" * 80)
        
        successful_results = [
            result for result in benchmark_results.values() 
            if not result['error_occurred']
        ]
        
        if not successful_results:
            print("❌ 成功したテストがありません")
            return
        
        # 時間統計
        early_fail_times = [r['early_fail_time'] for r in successful_results]
        filtering_times = [r['filtering_time'] for r in successful_results]
        exclusion_rates = [r['exclusion_rate'] for r in successful_results]
        
        print(f"🕐 Early Fail検証時間:")
        print(f"   平均: {statistics.mean(early_fail_times):.2f}秒")
        print(f"   最小: {min(early_fail_times):.2f}秒")
        print(f"   最大: {max(early_fail_times):.2f}秒")
        
        print(f"\n⚡ フィルタリング時間:")
        print(f"   平均: {statistics.mean(filtering_times):.3f}秒")
        print(f"   最小: {min(filtering_times):.3f}秒")
        print(f"   最大: {max(filtering_times):.3f}秒")
        
        print(f"\n📊 フィルタリング効果:")
        print(f"   平均除外率: {statistics.mean(exclusion_rates):.1f}%")
        print(f"   最小除外率: {min(exclusion_rates):.1f}%")
        print(f"   最大除外率: {max(exclusion_rates):.1f}%")
        
        # パフォーマンス評価
        avg_exclusion = statistics.mean(exclusion_rates)
        avg_filtering_time = statistics.mean(filtering_times)
        
        print(f"\n🎯 パフォーマンス評価:")
        print(f"   フィルタリング効果: {'優秀' if avg_exclusion > 20 else '良好' if avg_exclusion > 10 else '要改善'}")
        print(f"   フィルタリング速度: {'高速' if avg_filtering_time < 0.1 else '普通' if avg_filtering_time < 1.0 else '改善必要'}")
        
        # 推定削減効果
        if avg_exclusion > 0:
            estimated_time_savings = f"約{avg_exclusion:.0f}%の処理時間削減"
            estimated_resource_savings = f"約{avg_exclusion:.0f}%のリソース節約"
            print(f"   推定効果: {estimated_time_savings}")
            print(f"   リソース効果: {estimated_resource_savings}")
        
        print(f"\n✅ ベンチマーク完了: {len(successful_results)}/{len(benchmark_results)}銘柄で成功")

async def main():
    """メイン実行"""
    benchmark = FilteringBenchmark()
    
    start_time = time.time()
    results = await benchmark.run_benchmark()
    total_time = time.time() - start_time
    
    print(f"\n🏁 総実行時間: {total_time:.2f}秒")
    
    # 成功率
    successful_count = sum(1 for r in results.values() if not r['error_occurred'])
    success_rate = (successful_count / len(results)) * 100
    
    print(f"🎯 ベンチマーク成功率: {success_rate:.1f}% ({successful_count}/{len(results)})")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(main())
    exit(0)