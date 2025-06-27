#!/usr/bin/env python3
"""
サポート・レジスタンス検出の詳細診断テストシステム

各処理段階での成功/失敗を詳細に追跡し、
複数銘柄・時間帯・パラメータの組み合わせで原因を特定する。
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import asyncio
from pathlib import Path
import traceback

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

@dataclass
class TestCase:
    """テストケース定義"""
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    parameters: Dict[str, Any]
    description: str

@dataclass
class StageResult:
    """各段階の結果"""
    stage_name: str
    success: bool
    execution_time_ms: float
    data_points: int
    result_data: Any
    error_message: str = ""
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

@dataclass
class DiagnosisResult:
    """診断結果"""
    test_case: TestCase
    stages: List[StageResult]
    overall_success: bool
    total_time_ms: float
    final_support_count: int
    final_resistance_count: int

class SupportResistanceDiagnoser:
    """サポート・レジスタンス検出診断システム"""
    
    def __init__(self):
        self.results: List[DiagnosisResult] = []
        
    def create_test_cases(self) -> List[TestCase]:
        """テストケース生成"""
        test_cases = []
        
        # 🎯 銘柄セット（流動性・データ量が異なる）
        symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "LINK"]
        
        # 🕐 時間帯セット（異なる市場条件）
        time_periods = [
            ("2024-12-01", "2024-12-15"),  # 最近の安定期
            ("2024-11-15", "2024-11-30"),  # 高ボラティリティ期
            ("2024-10-01", "2024-10-15"),  # 中間期
        ]
        
        # ⚙️ パラメータセット（厳格→緩い）
        parameter_sets = [
            {
                "name": "ultra_strict",
                "min_touches": 3,
                "tolerance_pct": 0.01,
                "fractal_window": 7,
                "min_strength": 0.8,
                "description": "極厳格パラメータ"
            },
            {
                "name": "strict", 
                "min_touches": 2,
                "tolerance_pct": 0.02,
                "fractal_window": 5,
                "min_strength": 0.6,
                "description": "厳格パラメータ（デフォルト）"
            },
            {
                "name": "moderate",
                "min_touches": 2,
                "tolerance_pct": 0.05,
                "fractal_window": 3,
                "min_strength": 0.4,
                "description": "中程度パラメータ"
            },
            {
                "name": "relaxed",
                "min_touches": 1,
                "tolerance_pct": 0.1,
                "fractal_window": 3,
                "min_strength": 0.3,
                "description": "緩いパラメータ"
            },
            {
                "name": "ultra_relaxed",
                "min_touches": 1,
                "tolerance_pct": 0.2,
                "fractal_window": 2,
                "min_strength": 0.1,
                "description": "極緩パラメータ"
            }
        ]
        
        # 時間足（処理負荷が異なる）
        timeframes = ["1h", "15m", "5m"]
        
        # 🎯 重要度順にテストケース作成
        priority_combinations = [
            # 優先度1: 主要銘柄 × 最近期間 × 重要パラメータ
            ("BTC", "1h", time_periods[0], ["strict", "moderate", "relaxed"]),
            ("ETH", "1h", time_periods[0], ["strict", "moderate", "relaxed"]),
            ("SOL", "1h", time_periods[0], ["strict", "moderate", "relaxed"]),
            
            # 優先度2: 短時間足での動作確認
            ("BTC", "15m", time_periods[0], ["moderate", "relaxed"]),
            ("ETH", "15m", time_periods[0], ["moderate", "relaxed"]),
            
            # 優先度3: 異なる時期での動作確認
            ("BTC", "1h", time_periods[1], ["moderate", "relaxed"]),
            ("SOL", "1h", time_periods[1], ["moderate", "relaxed"]),
            
            # 優先度4: 極端パラメータでの限界テスト
            ("BTC", "1h", time_periods[0], ["ultra_strict", "ultra_relaxed"]),
            
            # 優先度5: その他銘柄
            ("DOGE", "1h", time_periods[0], ["moderate", "relaxed"]),
            ("ADA", "1h", time_periods[0], ["moderate", "relaxed"]),
            ("LINK", "1h", time_periods[0], ["moderate", "relaxed"]),
        ]
        
        case_id = 1
        for symbol, timeframe, period, param_names in priority_combinations:
            for param_name in param_names:
                param_set = next(p for p in parameter_sets if p["name"] == param_name)
                test_cases.append(TestCase(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=period[0],
                    end_date=period[1],
                    parameters=param_set,
                    description=f"Case-{case_id:02d}: {symbol} {timeframe} {period[0]}~{period[1]} {param_set['description']}"
                ))
                case_id += 1
        
        return test_cases
    
    async def diagnose_single_case(self, test_case: TestCase) -> DiagnosisResult:
        """単一テストケースの診断実行"""
        stages = []
        start_time = datetime.now()
        
        print(f"\n🔍 診断開始: {test_case.description}")
        
        try:
            # ステージ1: データ取得
            stage1_result = await self._stage1_data_acquisition(test_case)
            stages.append(stage1_result)
            
            if not stage1_result.success:
                return self._create_failed_result(test_case, stages, start_time)
            
            # ステージ2: データ前処理
            stage2_result = await self._stage2_data_preprocessing(test_case, stage1_result.result_data)
            stages.append(stage2_result)
            
            if not stage2_result.success:
                return self._create_failed_result(test_case, stages, start_time)
            
            # ステージ3: Fractal検出
            stage3_result = await self._stage3_fractal_detection(test_case, stage2_result.result_data)
            stages.append(stage3_result)
            
            if not stage3_result.success:
                return self._create_failed_result(test_case, stages, start_time)
            
            # ステージ4: サポート・レジスタンスレベル計算
            stage4_result = await self._stage4_level_calculation(test_case, stage3_result.result_data)
            stages.append(stage4_result)
            
            if not stage4_result.success:
                return self._create_failed_result(test_case, stages, start_time)
            
            # ステージ5: フィルタリング・強度計算
            stage5_result = await self._stage5_filtering_and_strength(test_case, stage4_result.result_data)
            stages.append(stage5_result)
            
            # 最終結果作成
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            final_levels = stage5_result.result_data if stage5_result.success else {"supports": [], "resistances": []}
            
            return DiagnosisResult(
                test_case=test_case,
                stages=stages,
                overall_success=stage5_result.success,
                total_time_ms=total_time,
                final_support_count=len(final_levels.get("supports", [])),
                final_resistance_count=len(final_levels.get("resistances", []))
            )
            
        except Exception as e:
            error_stage = StageResult(
                stage_name="unexpected_error",
                success=False,
                execution_time_ms=0,
                data_points=0,
                result_data=None,
                error_message=f"予期しないエラー: {str(e)}\n{traceback.format_exc()}"
            )
            stages.append(error_stage)
            return self._create_failed_result(test_case, stages, start_time)
    
    async def _stage1_data_acquisition(self, test_case: TestCase) -> StageResult:
        """ステージ1: データ取得"""
        stage_start = datetime.now()
        
        try:
            # 実際のシステムで使用されているAPI経由でのデータ取得
            from hyperliquid_api_client import MultiExchangeAPIClient
            
            client = MultiExchangeAPIClient(exchange_type='hyperliquid')
            
            # 日付文字列をdatetimeに変換
            from datetime import datetime as dt
            start_datetime = dt.fromisoformat(test_case.start_date).replace(tzinfo=timezone.utc)
            end_datetime = dt.fromisoformat(test_case.end_date).replace(tzinfo=timezone.utc)
            
            # 実際のシステムで使用されているメソッドを呼び出し
            df = await client.get_ohlcv_data(
                symbol=test_case.symbol,
                timeframe=test_case.timeframe,
                start_time=start_datetime,
                end_time=end_datetime
            )
            
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            
            if df is None or len(df) < 10:
                return StageResult(
                    stage_name="data_acquisition",
                    success=False,
                    execution_time_ms=execution_time,
                    data_points=len(df) if df is not None else 0,
                    result_data=None,
                    error_message=f"データ不足: {len(df) if df is not None else 0}本（最低10本必要）"
                )
            
            # データフレームは既に適切な形式で返される
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return StageResult(
                    stage_name="data_acquisition",
                    success=False,
                    execution_time_ms=execution_time,
                    data_points=len(df),
                    result_data=None,
                    error_message=f"必要カラム不足: {missing_columns}"
                )
            
            warnings = []
            if len(df) < 50:
                warnings.append(f"データ量少: {len(df)}本（推奨50本以上）")
            
            return StageResult(
                stage_name="data_acquisition",
                success=True,
                execution_time_ms=execution_time,
                data_points=len(df),
                result_data=df,
                warnings=warnings
            )
            
        except Exception as e:
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            return StageResult(
                stage_name="data_acquisition",
                success=False,
                execution_time_ms=execution_time,
                data_points=0,
                result_data=None,
                error_message=f"データ取得エラー: {str(e)}"
            )
    
    async def _stage2_data_preprocessing(self, test_case: TestCase, df: pd.DataFrame) -> StageResult:
        """ステージ2: データ前処理"""
        stage_start = datetime.now()
        
        try:
            # データ型変換
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # NaN値チェック
            nan_counts = df[numeric_columns].isnull().sum()
            total_nans = nan_counts.sum()
            
            if total_nans > len(df) * 0.1:  # 10%以上がNaN
                execution_time = (datetime.now() - stage_start).total_seconds() * 1000
                return StageResult(
                    stage_name="data_preprocessing",
                    success=False,
                    execution_time_ms=execution_time,
                    data_points=len(df),
                    result_data=None,
                    error_message=f"NaN値過多: {total_nans}個 ({total_nans/len(df)*100:.1f}%)"
                )
            
            # NaN値がある場合は前方埋め
            if total_nans > 0:
                df = df.fillna(method='ffill').dropna()
            
            # 価格データの妥当性チェック
            price_columns = ['open', 'high', 'low', 'close']
            invalid_prices = 0
            
            for _, row in df.iterrows():
                if not (row['low'] <= row['open'] <= row['high'] and 
                       row['low'] <= row['close'] <= row['high']):
                    invalid_prices += 1
            
            warnings = []
            if invalid_prices > 0:
                warnings.append(f"価格データ異常: {invalid_prices}本")
            
            if total_nans > 0:
                warnings.append(f"NaN値補正: {total_nans}個")
            
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            
            return StageResult(
                stage_name="data_preprocessing",
                success=True,
                execution_time_ms=execution_time,
                data_points=len(df),
                result_data=df,
                warnings=warnings
            )
            
        except Exception as e:
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            return StageResult(
                stage_name="data_preprocessing",
                success=False,
                execution_time_ms=execution_time,
                data_points=len(df) if 'df' in locals() else 0,
                result_data=None,
                error_message=f"前処理エラー: {str(e)}"
            )
    
    async def _stage3_fractal_detection(self, test_case: TestCase, df: pd.DataFrame) -> StageResult:
        """ステージ3: Fractal検出"""
        stage_start = datetime.now()
        
        try:
            from engines.support_resistance_detector import SupportResistanceDetector
            
            # テストケースのパラメータを使用
            fractal_window = test_case.parameters.get('fractal_window', 5)
            
            detector = SupportResistanceDetector(
                min_touches=test_case.parameters.get('min_touches', 2),
                tolerance_pct=test_case.parameters.get('tolerance_pct', 0.02),
                fractal_window=fractal_window
            )
            
            # Fractal検出の実行
            highs = df['high'].values
            lows = df['low'].values
            
            # Fractal計算
            fractal_highs = []
            fractal_lows = []
            
            for i in range(fractal_window, len(highs) - fractal_window):
                # High fractal: 前後N本より高い
                if all(highs[i] >= highs[j] for j in range(i-fractal_window, i+fractal_window+1) if j != i):
                    if all(highs[i] > highs[j] for j in [i-1, i+1]):  # 隣接は厳密に大きい
                        fractal_highs.append((i, highs[i]))
                
                # Low fractal: 前後N本より低い
                if all(lows[i] <= lows[j] for j in range(i-fractal_window, i+fractal_window+1) if j != i):
                    if all(lows[i] < lows[j] for j in [i-1, i+1]):  # 隣接は厳密に小さい
                        fractal_lows.append((i, lows[i]))
            
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            
            warnings = []
            if len(fractal_highs) < 2:
                warnings.append(f"High fractal不足: {len(fractal_highs)}個")
            if len(fractal_lows) < 2:
                warnings.append(f"Low fractal不足: {len(fractal_lows)}個")
            
            result_data = {
                "fractal_highs": fractal_highs,
                "fractal_lows": fractal_lows,
                "df": df,
                "detector": detector
            }
            
            return StageResult(
                stage_name="fractal_detection",
                success=True,
                execution_time_ms=execution_time,
                data_points=len(fractal_highs) + len(fractal_lows),
                result_data=result_data,
                warnings=warnings
            )
            
        except Exception as e:
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            return StageResult(
                stage_name="fractal_detection",
                success=False,
                execution_time_ms=execution_time,
                data_points=0,
                result_data=None,
                error_message=f"Fractal検出エラー: {str(e)}"
            )
    
    async def _stage4_level_calculation(self, test_case: TestCase, stage3_data: Dict) -> StageResult:
        """ステージ4: サポート・レジスタンスレベル計算"""
        stage_start = datetime.now()
        
        try:
            fractal_highs = stage3_data["fractal_highs"]
            fractal_lows = stage3_data["fractal_lows"]
            detector = stage3_data["detector"]
            df = stage3_data["df"]
            
            # 現在価格（最新価格）
            current_price = df['close'].iloc[-1]
            
            # 実際のdetector.detect_levels_from_ohlcv()を呼び出し
            supports, resistances = detector.detect_levels_from_ohlcv(df, current_price)
            
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            
            warnings = []
            if len(supports) == 0:
                warnings.append("サポートレベル未検出")
            if len(resistances) == 0:
                warnings.append("レジスタンスレベル未検出")
            
            result_data = {
                "supports": supports,
                "resistances": resistances,
                "current_price": current_price,
                "total_levels": len(supports) + len(resistances)
            }
            
            return StageResult(
                stage_name="level_calculation",
                success=True,
                execution_time_ms=execution_time,
                data_points=len(supports) + len(resistances),
                result_data=result_data,
                warnings=warnings
            )
            
        except Exception as e:
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            return StageResult(
                stage_name="level_calculation",
                success=False,
                execution_time_ms=execution_time,
                data_points=0,
                result_data=None,
                error_message=f"レベル計算エラー: {str(e)}"
            )
    
    async def _stage5_filtering_and_strength(self, test_case: TestCase, stage4_data: Dict) -> StageResult:
        """ステージ5: フィルタリング・強度計算"""
        stage_start = datetime.now()
        
        try:
            supports = stage4_data["supports"]
            resistances = stage4_data["resistances"]
            min_strength = test_case.parameters.get('min_strength', 0.6)
            
            # 強度によるフィルタリング
            valid_supports = [s for s in supports if hasattr(s, 'strength') and s.strength >= min_strength]
            valid_resistances = [r for r in resistances if hasattr(r, 'strength') and r.strength >= min_strength]
            
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            
            warnings = []
            if len(valid_supports) < len(supports):
                warnings.append(f"サポート強度フィルタ: {len(supports)}→{len(valid_supports)}")
            if len(valid_resistances) < len(resistances):
                warnings.append(f"レジスタンス強度フィルタ: {len(resistances)}→{len(valid_resistances)}")
            
            success = len(valid_supports) > 0 or len(valid_resistances) > 0
            
            result_data = {
                "supports": valid_supports,
                "resistances": valid_resistances,
                "original_support_count": len(supports),
                "original_resistance_count": len(resistances)
            }
            
            return StageResult(
                stage_name="filtering_and_strength",
                success=success,
                execution_time_ms=execution_time,
                data_points=len(valid_supports) + len(valid_resistances),
                result_data=result_data,
                warnings=warnings,
                error_message="" if success else "フィルタリング後に有効なレベルが0個"
            )
            
        except Exception as e:
            execution_time = (datetime.now() - stage_start).total_seconds() * 1000
            return StageResult(
                stage_name="filtering_and_strength",
                success=False,
                execution_time_ms=execution_time,
                data_points=0,
                result_data=None,
                error_message=f"フィルタリングエラー: {str(e)}"
            )
    
    def _create_failed_result(self, test_case: TestCase, stages: List[StageResult], start_time: datetime) -> DiagnosisResult:
        """失敗結果の作成"""
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        return DiagnosisResult(
            test_case=test_case,
            stages=stages,
            overall_success=False,
            total_time_ms=total_time,
            final_support_count=0,
            final_resistance_count=0
        )
    
    async def run_full_diagnosis(self, max_cases: int = 20) -> None:
        """全診断の実行"""
        test_cases = self.create_test_cases()
        
        print(f"📋 診断テスト開始: {len(test_cases)}ケース（最大{max_cases}ケース実行）")
        
        executed_cases = 0
        for i, test_case in enumerate(test_cases):
            if executed_cases >= max_cases:
                print(f"\n⏹️ 最大実行数{max_cases}に到達、診断を終了")
                break
                
            print(f"\n{'='*60}")
            print(f"🎯 テストケース {i+1}/{min(len(test_cases), max_cases)}")
            
            result = await self.diagnose_single_case(test_case)
            self.results.append(result)
            executed_cases += 1
            
            # 結果の即座表示
            self._print_case_summary(result)
            
            # 連続実行の間隔
            if executed_cases < max_cases:
                await asyncio.sleep(0.5)
        
        # 最終レポート
        self._generate_final_report()
    
    def _print_case_summary(self, result: DiagnosisResult) -> None:
        """ケース結果のサマリー表示"""
        status = "✅ 成功" if result.overall_success else "❌ 失敗"
        print(f"\n{status} | {result.test_case.symbol} {result.test_case.timeframe} | "
              f"サポート:{result.final_support_count} レジスタンス:{result.final_resistance_count} | "
              f"{result.total_time_ms:.0f}ms")
        
        # 各ステージの状況
        for stage in result.stages:
            stage_status = "✅" if stage.success else "❌"
            print(f"  {stage_status} {stage.stage_name}: {stage.data_points}pts {stage.execution_time_ms:.0f}ms")
            if stage.error_message:
                print(f"     エラー: {stage.error_message}")
            if stage.warnings:
                for warning in stage.warnings:
                    print(f"     ⚠️ {warning}")
    
    def _generate_final_report(self) -> None:
        """最終レポート生成"""
        print(f"\n{'='*80}")
        print("📊 最終診断レポート")
        print(f"{'='*80}")
        
        total_cases = len(self.results)
        successful_cases = sum(1 for r in self.results if r.overall_success)
        
        print(f"\n📈 全体統計:")
        print(f"  総ケース数: {total_cases}")
        print(f"  成功ケース: {successful_cases} ({successful_cases/total_cases*100:.1f}%)")
        print(f"  失敗ケース: {total_cases-successful_cases} ({(total_cases-successful_cases)/total_cases*100:.1f}%)")
        
        # 銘柄別成功率
        symbol_stats = {}
        for result in self.results:
            symbol = result.test_case.symbol
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {"total": 0, "success": 0}
            symbol_stats[symbol]["total"] += 1
            if result.overall_success:
                symbol_stats[symbol]["success"] += 1
        
        print(f"\n📊 銘柄別成功率:")
        for symbol, stats in sorted(symbol_stats.items()):
            rate = stats["success"] / stats["total"] * 100
            print(f"  {symbol}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
        
        # パラメータ別成功率
        param_stats = {}
        for result in self.results:
            param_name = result.test_case.parameters["name"]
            if param_name not in param_stats:
                param_stats[param_name] = {"total": 0, "success": 0}
            param_stats[param_name]["total"] += 1
            if result.overall_success:
                param_stats[param_name]["success"] += 1
        
        print(f"\n⚙️ パラメータ別成功率:")
        for param_name, stats in sorted(param_stats.items()):
            rate = stats["success"] / stats["total"] * 100
            print(f"  {param_name}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
        
        # 失敗ケースの詳細分析
        failed_cases = [r for r in self.results if not r.overall_success]
        if failed_cases:
            print(f"\n❌ 失敗ケース詳細分析:")
            
            # ステージ別失敗統計
            stage_failures = {}
            for result in failed_cases:
                for stage in result.stages:
                    if not stage.success:
                        if stage.stage_name not in stage_failures:
                            stage_failures[stage.stage_name] = []
                        stage_failures[stage.stage_name].append(result.test_case.symbol)
            
            for stage_name, symbols in stage_failures.items():
                print(f"  {stage_name}失敗: {len(symbols)}ケース ({', '.join(set(symbols))})")
        
        # 成功ケースのレベル検出統計
        successful_results = [r for r in self.results if r.overall_success]
        if successful_results:
            support_counts = [r.final_support_count for r in successful_results]
            resistance_counts = [r.final_resistance_count for r in successful_results]
            
            print(f"\n✅ 成功ケースの検出統計:")
            print(f"  サポートレベル: 平均{np.mean(support_counts):.1f} (最大{max(support_counts)}, 最小{min(support_counts)})")
            print(f"  レジスタンスレベル: 平均{np.mean(resistance_counts):.1f} (最大{max(resistance_counts)}, 最小{min(resistance_counts)})")
        
        # JSON結果ファイル保存
        self._save_detailed_results()
    
    def _save_detailed_results(self) -> None:
        """詳細結果をJSONファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"support_resistance_diagnosis_{timestamp}.json"
        
        # 結果をシリアライズ可能な形式に変換
        serializable_results = []
        for result in self.results:
            # StageResultのresult_dataはシリアライズ困難なので除外
            serializable_stages = []
            for stage in result.stages:
                serializable_stages.append({
                    "stage_name": stage.stage_name,
                    "success": stage.success,
                    "execution_time_ms": stage.execution_time_ms,
                    "data_points": stage.data_points,
                    "error_message": stage.error_message,
                    "warnings": stage.warnings
                })
            
            serializable_results.append({
                "test_case": asdict(result.test_case),
                "stages": serializable_stages,
                "overall_success": result.overall_success,
                "total_time_ms": result.total_time_ms,
                "final_support_count": result.final_support_count,
                "final_resistance_count": result.final_resistance_count
            })
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 詳細結果を保存: {filename}")
        except Exception as e:
            print(f"\n⚠️ 結果保存エラー: {e}")

async def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='サポート・レジスタンス検出診断システム')
    parser.add_argument('--max-cases', type=int, default=15, help='最大実行ケース数 (デフォルト: 15)')
    parser.add_argument('--quick', action='store_true', help='クイックモード (最大5ケース)')
    
    args = parser.parse_args()
    
    max_cases = 5 if args.quick else args.max_cases
    
    print("🔍 サポート・レジスタンス検出診断システム")
    print(f"最大実行ケース数: {max_cases}")
    
    diagnoser = SupportResistanceDiagnoser()
    await diagnoser.run_full_diagnosis(max_cases=max_cases)

if __name__ == "__main__":
    asyncio.run(main())