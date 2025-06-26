"""
ハイレバボット統括システム

memo記載の核心目的「今このタイミングで対象のトークンに対してハイレバのロング何倍かけて大丈夫か判定するbot」
を実装する統括クラス。全てのプラグインを統合してハイレバレッジ判定を実行します。
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import warnings

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interfaces import (
    IHighLeverageBotOrchestrator, ISupportResistanceAnalyzer, IBreakoutPredictor,
    IBTCCorrelationAnalyzer, IMarketContextAnalyzer, ILeverageDecisionEngine,
    IStopLossTakeProfitCalculator, LeverageRecommendation, MarketContext
)

from adapters import (
    ExistingSupportResistanceAdapter, ExistingMLPredictorAdapter, ExistingBTCCorrelationAdapter
)

from .leverage_decision_engine import CoreLeverageDecisionEngine, SimpleMarketContextAnalyzer

warnings.filterwarnings('ignore')

class HighLeverageBotOrchestrator(IHighLeverageBotOrchestrator):
    """
    ハイレバボット統括システム
    
    【memo記載の核心機能】
    「今このタイミングで対象のトークンに対してハイレバのロング何倍かけて大丈夫か判定するbot」
    
    【統合要素】
    1. サポート・レジスタンス分析 (support_resistance_visualizer.py)
    2. ML予測システム (support_resistance_ml.py)  
    3. BTC相関分析 (btc_altcoin_correlation_predictor.py)
    4. レバレッジ判定エンジン (新規実装)
    
    【判定フロー】
    データ取得 → サポレジ分析 → ML予測 → BTC相関分析 → 統合判定 → レバレッジ推奨
    """
    
    def __init__(self, use_default_plugins: bool = True, exchange: str = None):
        """
        初期化
        
        Args:
            use_default_plugins: デフォルトプラグインを使用するか
            exchange: 使用する取引所 (hyperliquid, gateio)
        """
        
        # 取引所設定を保存
        self.exchange = exchange
        
        # プラグインの初期化
        self.support_resistance_analyzer: Optional[ISupportResistanceAnalyzer] = None
        self.breakout_predictor: Optional[IBreakoutPredictor] = None
        self.btc_correlation_analyzer: Optional[IBTCCorrelationAnalyzer] = None
        self.market_context_analyzer: Optional[IMarketContextAnalyzer] = None
        self.leverage_decision_engine: Optional[ILeverageDecisionEngine] = None
        
        # デフォルトプラグインの設定
        if use_default_plugins:
            self._initialize_default_plugins()
    
    def _initialize_default_plugins(self):
        """デフォルトプラグインを初期化"""
        
        try:
            print("🔧 デフォルトプラグインを初期化中...")
            
            # 既存システムのアダプターを使用
            self.support_resistance_analyzer = ExistingSupportResistanceAdapter()
            print("✅ サポート・レジスタンス分析器を初期化")
            
            self.breakout_predictor = ExistingMLPredictorAdapter()
            print("✅ ブレイクアウト予測器を初期化")
            
            self.btc_correlation_analyzer = ExistingBTCCorrelationAdapter()
            print("✅ BTC相関分析器を初期化")
            
            self.market_context_analyzer = SimpleMarketContextAnalyzer()
            print("✅ 市場コンテキスト分析器を初期化")
            
            # 現在の分析対象に応じてレバレッジエンジンを初期化
            # Note: timeframeとsymbol_categoryは分析時に決定されるため、後で更新可能
            self.leverage_decision_engine = CoreLeverageDecisionEngine()
            print("✅ レバレッジ判定エンジンを初期化（デフォルト設定）")
            
            print("🎉 全てのプラグインが正常に初期化されました")
            
        except Exception as e:
            print(f"❌ プラグイン初期化エラー: {e}")
            print("🔄 基本的なフォールバックシステムを使用します")
    
    def analyze_leverage_opportunity(self, symbol: str, timeframe: str = "1h", is_backtest: bool = False, target_timestamp: datetime = None, custom_period_settings: dict = None, execution_id: str = None) -> LeverageRecommendation:
        # execution_idが渡されていない場合は環境変数から取得
        if not execution_id:
            import os
            env_execution_id = os.environ.get('CURRENT_EXECUTION_ID')
            if env_execution_id:
                execution_id = env_execution_id
                print(f"📝 環境変数からexecution_id取得: {execution_id}")
        """
        ハイレバレッジ機会を総合分析
        
        【memo記載の判定プロセス】
        1. データ取得
        2. サポート・レジスタンス分析  
        3. ML予測によるブレイクアウト/反発確率算出
        4. BTC相関リスク評価
        5. 市場コンテキスト分析
        6. 統合レバレッジ判定
        
        Args:
            symbol: 分析対象シンボル (例: 'HYPE', 'SOL', 'WIF')
            timeframe: 時間足 (例: '1h', '15m', '5m')
            
        Returns:
            LeverageRecommendation: レバレッジ推奨結果
        """
        
        try:
            print(f"\n🎯 ハイレバレッジ機会分析開始: {symbol} ({timeframe})")
            if execution_id:
                print(f"🆔 Execution ID: {execution_id}")
            print("=" * 60)
            
            # 銘柄カテゴリの判定
            symbol_category = self._determine_symbol_category(symbol)
            print(f"📊 銘柄カテゴリ: {symbol_category}")
            
            # レバレッジエンジンを時間足・銘柄カテゴリに応じて再初期化
            try:
                self.leverage_decision_engine = CoreLeverageDecisionEngine(
                    timeframe=timeframe, 
                    symbol_category=symbol_category
                )
                print(f"🔧 レバレッジエンジンを調整済み設定で初期化")
            except Exception as e:
                print(f"⚠️ レバレッジエンジン再初期化エラー: {e}, デフォルト設定を継続使用")
            
            # 短期間足の場合は時間軸に応じた最適化を適用
            is_short_timeframe = timeframe in ['1m', '3m', '5m']
            if is_short_timeframe:
                print(f"⚡ 短期取引モード: {timeframe}足の最適化を適用")
            
            # === STEP 1: データ取得 ===
            market_data = self._fetch_market_data(symbol, timeframe, custom_period_settings)
            
            if market_data.empty:
                raise Exception(f"{symbol}の市場データ取得に失敗 - 実データが必要です")
            
            print(f"📊 データ取得完了: {len(market_data)}件")
            
            # === STEP 2: サポート・レジスタンス分析 ===
            print("\n🔍 サポート・レジスタンス分析中...")
            support_levels, resistance_levels = self._analyze_support_resistance(
                market_data, 
                is_short_timeframe=is_short_timeframe,
                execution_id=execution_id
            )
            
            print(f"📍 検出レベル: サポート{len(support_levels)}件, レジスタンス{len(resistance_levels)}件")
            
            # === STEP 3: ML予測 ===
            print("\n🤖 ML予測分析中...")
            breakout_predictions = self._predict_breakouts(market_data, support_levels + resistance_levels)
            
            print(f"🎯 予測完了: {len(breakout_predictions)}件")
            
            # === STEP 4: BTC相関分析 ===
            print("\n₿ BTC相関リスク分析中...")
            btc_correlation_risk = self._analyze_btc_correlation(symbol)
            
            if btc_correlation_risk:
                print(f"⚠️ BTC相関リスク: {btc_correlation_risk.risk_level}")
            
            # === STEP 5: 市場コンテキスト分析 ===
            print("\n📈 市場コンテキスト分析中...")
            # バックテスト時は各時点の価格、リアルタイム時は現在価格を使用
            market_context = self._analyze_market_context(
                market_data, 
                is_realtime=not is_backtest,
                target_timestamp=target_timestamp
            )
            
            print(f"🎪 市場状況: {market_context.trend_direction} / {market_context.market_phase}")
            
            # === STEP 6: 統合レバレッジ判定 ===
            print("\n⚖️ レバレッジ判定実行中...")
            
            if not self.leverage_decision_engine:
                raise Exception("レバレッジ判定エンジンが初期化されていません - 銘柄追加を中止")
            
            leverage_recommendation = self.leverage_decision_engine.calculate_safe_leverage(
                symbol=symbol,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                breakout_predictions=breakout_predictions,
                btc_correlation_risk=btc_correlation_risk,
                market_context=market_context
            )
            
            # === 結果サマリー表示 ===
            self._display_analysis_summary(leverage_recommendation)
            
            return leverage_recommendation
            
        except Exception as e:
            print(f"❌ 分析エラー: {e}")
            raise Exception(f"分析中にエラーが発生: {str(e)} - フォールバックは使用しません")
    
    def _fetch_market_data(self, symbol: str, timeframe: str, custom_period_settings: dict = None) -> pd.DataFrame:
        """市場データを取得（マルチ取引所APIクライアントを使用）"""
        
        # キャッシュされたデータがあれば使用
        if hasattr(self, '_cached_data') and not self._cached_data.empty:
            return self._cached_data
        
        try:
            # マルチ取引所APIクライアントを使用
            from hyperliquid_api_client import MultiExchangeAPIClient
            import asyncio
            
            # 取引所設定を読み込んでクライアントを初期化
            api_client = MultiExchangeAPIClient()
            
            # カスタム期間設定またはデフォルト90日間のデータ取得期間を決定
            if custom_period_settings and custom_period_settings.get('mode') == 'custom':
                # カスタム期間設定使用
                from datetime import datetime as dt
                import dateutil.parser
                
                start_date_str = custom_period_settings.get('start_date')
                end_date_str = custom_period_settings.get('end_date')
                
                try:
                    # ISO形式の日時文字列をパース
                    start_time = dateutil.parser.parse(start_date_str).replace(tzinfo=timezone.utc)
                    end_time = dateutil.parser.parse(end_date_str).replace(tzinfo=timezone.utc)
                    
                    # 200本前データを考慮した期間調整
                    timeframe_minutes = {
                        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, 
                        '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720, '1d': 1440
                    }
                    
                    if timeframe in timeframe_minutes:
                        pre_period_minutes = 200 * timeframe_minutes[timeframe]
                        start_time = start_time - timedelta(minutes=pre_period_minutes)
                        print(f"📅 カスタム期間設定使用: {start_time.strftime('%Y-%m-%d %H:%M')} ～ {end_time.strftime('%Y-%m-%d %H:%M')} (200本前データ含む)")
                    else:
                        print(f"📅 カスタム期間設定使用: {start_time.strftime('%Y-%m-%d %H:%M')} ～ {end_time.strftime('%Y-%m-%d %H:%M')}")
                        
                except Exception as e:
                    print(f"⚠️ カスタム期間設定パースエラー: {e}")
                    # フォールバック: デフォルト90日間
                    end_time = datetime.now(timezone.utc)
                    start_time = end_time - timedelta(days=90)
                    print(f"📅 デフォルト期間使用: 90日間")
            else:
                # デフォルト90日間のデータを取得（UTC時刻を使用）
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=90)
                print(f"📅 デフォルト期間使用: 90日間")
            
            # 非同期でデータを取得
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                data = loop.run_until_complete(
                    api_client.get_ohlcv_data(symbol, timeframe, start_time, end_time)
                )
            finally:
                loop.close()
            
            if data is not None and not data.empty:
                return data
            else:
                raise Exception(f"{symbol}のOHLCVデータが空です - 実データが必要です")
            
        except Exception as e:
            print(f"データ取得エラー: {e}")
            # フォールバックは使用せず、例外を再発生
            raise Exception(f"市場データ取得に失敗: {e} - 実データが必要です")
    
    def _analyze_support_resistance(self, data: pd.DataFrame, is_short_timeframe: bool = False, execution_id: str = None) -> tuple:
        """サポート・レジスタンス分析"""
        
        support_levels = []
        resistance_levels = []
        
        try:
            current_price = data['close'].iloc[-1] if not data.empty else 0
            data_length = len(data)
            
            print(f"  📊 サポレジ検出開始: データ{data_length}本, 現在価格{current_price:.4f}")
            
            # 進捗更新（Webダッシュボード用）
            if execution_id:
                try:
                    from web_dashboard.analysis_progress import progress_tracker, SupportResistanceResult
                    print(f"  📊 progress_tracker更新開始: execution_id={execution_id}")
                    progress_tracker.update_stage(execution_id, "support_resistance")
                    progress_tracker.update_support_resistance(execution_id, 
                        SupportResistanceResult(status="running"))
                    print(f"  ✅ progress_tracker更新成功")
                except ImportError as e:
                    print(f"  ⚠️ progress_trackerインポートエラー: {e}")
                except Exception as e:
                    print(f"  ❌ progress_tracker更新エラー: {e}")
                    import traceback
                    traceback.print_exc()
            
            # デバッグログをファイルに出力（並列プロセス対応）
            import os
            from datetime import datetime
            debug_mode = os.environ.get('SUPPORT_RESISTANCE_DEBUG', 'false').lower() == 'true'
            debug_log_path = None
            if debug_mode:
                debug_log_path = f"/tmp/sr_debug_{os.getpid()}.log"
                with open(debug_log_path, 'a') as f:
                    f.write(f"\n=== Support/Resistance Debug Log (PID: {os.getpid()}) ===\n")
                    f.write(f"Data: {data_length} candles, Current price: {current_price:.4f}\n")
                    f.write(f"Starting analysis at {datetime.now()}\n")
            
            if self.support_resistance_analyzer:
                # 短期間足の場合はより敏感なパラメータを使用
                if is_short_timeframe:
                    kwargs = {
                        'window': 3,         # より小さなウィンドウ
                        'min_touches': 2,    # タッチ回数は維持
                        'tolerance': 0.005   # より厳密な許容範囲
                    }
                    print("  ⚡ 短期取引用パラメータ適用: window=3, min_touches=2, tolerance=0.5%")
                    if debug_mode:
                        with open(debug_log_path, 'a') as f:
                            f.write(f"Parameters: window=3, min_touches=2, tolerance=0.5% (short timeframe)\n")
                else:
                    kwargs = {
                        'window': 5,         # 標準ウィンドウ
                        'min_touches': 2,    # 標準タッチ回数
                        'tolerance': 0.01    # 標準許容範囲
                    }
                    print("  📐 標準パラメータ適用: window=5, min_touches=2, tolerance=1.0%")
                    if debug_mode:
                        with open(debug_log_path, 'a') as f:
                            f.write(f"Parameters: window=5, min_touches=2, tolerance=1.0% (standard)\n")
                
                print(f"  🔍 アナライザーによるレベル検出実行中...")
                if debug_mode:
                    with open(debug_log_path, 'a') as f:
                        f.write(f"Starting level detection with analyzer...\n")
                
                all_levels = self.support_resistance_analyzer.find_levels(data, **kwargs)
                print(f"  📊 検出完了: 総レベル数{len(all_levels)}個")
                
                if debug_mode:
                    with open(debug_log_path, 'a') as f:
                        f.write(f"Detection completed: {len(all_levels)} total levels\n")
                        if all_levels:
                            f.write(f"First 3 levels:\n")
                            for i, level in enumerate(all_levels[:3]):
                                f.write(f"  Level {i+1}: {level.level_type} {level.price:.4f} (strength {level.strength:.3f})\n")
                        else:
                            f.write(f"No levels detected - possible reasons:\n")
                            f.write(f"  - Insufficient fractal points\n")
                            f.write(f"  - Clustering failed to meet min_touches requirement\n")
                            f.write(f"  - Strength calculation resulted in 0.0\n")
                
                # 詳細ログ: 検出されたレベルの分析
                if not all_levels:
                    print("  ⚠️ 検出結果: レベル数0個 → シグナルなし確定")
                    print("  📋 考えられる原因:")
                    print("    - フラクタル分析で局所最高値・最安値が不足")
                    print("    - クラスタリング後にmin_touches=2の条件を満たすレベルなし") 
                    print("    - 強度計算でraw_strength/200が0.0になった")
                    if debug_mode:
                        with open(debug_log_path, 'a') as f:
                            f.write(f"❌ FAILURE ANALYSIS:\n")
                            f.write(f"  No levels detected (0 levels)\n")
                            f.write(f"  Possible reasons:\n")
                            f.write(f"    1. Fractal analysis insufficient local max/min\n")
                            f.write(f"    2. Clustering failed min_touches=2 requirement\n")
                            f.write(f"    3. Strength calculation resulted in 0.0 (raw_strength/200)\n")
                            f.write(f"  Data characteristics:\n")
                            f.write(f"    - Price range: {data['close'].min():.4f} - {data['close'].max():.4f}\n")
                            f.write(f"    - Volatility: {(data['close'].max() - data['close'].min()) / data['close'].mean() * 100:.1f}%\n")
                else:
                    print(f"  📋 レベル詳細分析:")
                    for i, level in enumerate(all_levels[:10]):  # 上位10個のみ表示
                        distance_pct = abs(level.price - current_price) / current_price * 100
                        print(f"    {i+1}. {level.level_type} {level.price:.4f} (強度{level.strength:.3f}, タッチ{level.touch_count}回, 距離{distance_pct:.1f}%)")
                    
                    if debug_mode:
                        with open(debug_log_path, 'a') as f:
                            f.write(f"✅ LEVEL ANALYSIS DETAILS:\n")
                            for i, level in enumerate(all_levels):
                                distance_pct = abs(level.price - current_price) / current_price * 100
                                f.write(f"  Level {i+1}: {level.level_type} {level.price:.4f} (strength {level.strength:.3f}, touches {level.touch_count}, distance {distance_pct:.1f}%)\n")
                
                # サポートとレジスタンスに分離
                support_count = 0
                resistance_count = 0
                for level in all_levels:
                    if level.level_type == 'support' and level.price < current_price:
                        support_levels.append(level)
                        support_count += 1
                    elif level.level_type == 'resistance' and level.price > current_price:
                        resistance_levels.append(level)
                        resistance_count += 1
                
                print(f"  📍 現在価格フィルタ後: 有効支持線{support_count}個, 有効抵抗線{resistance_count}個")
                
                if debug_mode:
                    with open(debug_log_path, 'a') as f:
                        f.write(f"Current price filter results:\n")
                        f.write(f"  Valid supports: {support_count}, valid resistances: {resistance_count}\n")
                        f.write(f"  Current price: {current_price:.4f}\n")
                        if support_levels:
                            f.write(f"  Supports:\n")
                            for i, level in enumerate(support_levels[:5]):
                                f.write(f"    {i+1}. {level.price:.4f} (strength {level.strength:.3f})\n")
                        if resistance_levels:
                            f.write(f"  Resistances:\n")
                            for i, level in enumerate(resistance_levels[:5]):
                                f.write(f"    {i+1}. {level.price:.4f} (strength {level.strength:.3f})\n")
            else:
                print("  ❌ support_resistance_analyzerが初期化されていません")
                raise Exception("サポレジアナライザーが利用できません")
            
            # 現在価格に近い順にソート
            if data.empty:
                raise Exception("市場データが空のためサポレジ分析できません")
            
            support_levels.sort(key=lambda x: abs(x.price - current_price))
            resistance_levels.sort(key=lambda x: abs(x.price - current_price))
            
            # 短期間足の場合はより多くのレベルを使用
            max_levels = 7 if is_short_timeframe else 5
            final_supports = support_levels[:max_levels]
            final_resistances = resistance_levels[:max_levels]
            
            print(f"  🎯 最終選択: 支持線{len(final_supports)}個, 抵抗線{len(final_resistances)}個 (上限{max_levels}個)")
            
            # 最終選択されたレベルの詳細
            if final_supports:
                print(f"  📍 選択された支持線:")
                for i, level in enumerate(final_supports):
                    distance_pct = (current_price - level.price) / current_price * 100
                    print(f"    {i+1}. {level.price:.4f} (強度{level.strength:.3f}, {distance_pct:.1f}%下)")
            
            if final_resistances:
                print(f"  📍 選択された抵抗線:")
                for i, level in enumerate(final_resistances):
                    distance_pct = (level.price - current_price) / current_price * 100
                    print(f"    {i+1}. {level.price:.4f} (強度{level.strength:.3f}, {distance_pct:.1f}%上)")
            
            if not final_supports and not final_resistances:
                print("  🚨 最終結果: 有効なサポレジレベルが0個 → シグナルなし")
            
            if debug_mode:
                with open(debug_log_path, 'a') as f:
                    f.write(f"\n🎯 FINAL SELECTION RESULTS:\n")
                    f.write(f"  Selected supports: {len(final_supports)}, resistances: {len(final_resistances)} (max {max_levels})\n")
                    
                    if final_supports:
                        f.write(f"  Final Supports:\n")
                        for i, level in enumerate(final_supports):
                            distance_pct = (current_price - level.price) / current_price * 100
                            f.write(f"    {i+1}. {level.price:.4f} (strength {level.strength:.3f}, {distance_pct:.1f}% below)\n")
                    
                    if final_resistances:
                        f.write(f"  Final Resistances:\n")
                        for i, level in enumerate(final_resistances):
                            distance_pct = (level.price - current_price) / current_price * 100
                            f.write(f"    {i+1}. {level.price:.4f} (strength {level.strength:.3f}, {distance_pct:.1f}% above)\n")
                    
                    if not final_supports and not final_resistances:
                        f.write(f"  ❌ FINAL RESULT: 0 valid levels → No signal\n")
                    
                    f.write(f"Analysis completed at {datetime.now()}\n")
                    f.write(f"="*60 + "\n")
            
            # 進捗更新（成功時）
            if execution_id:
                try:
                    import sys
                    import os
                    # パス追加（ProcessPoolExecutor環境用）
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    
                    from web_dashboard.analysis_progress import progress_tracker, SupportResistanceResult
                    print(f"  📊 progress_tracker インポート成功: execution_id={execution_id}")
                    supports_data = [{"price": level.price, "strength": level.strength, "touch_count": level.touch_count} 
                                   for level in final_supports]
                    resistances_data = [{"price": level.price, "strength": level.strength, "touch_count": level.touch_count} 
                                      for level in final_resistances]
                    
                    print(f"  📊 progress_tracker最終更新: supports={len(final_supports)}, resistances={len(final_resistances)}")
                    
                    progress_tracker.update_support_resistance(execution_id, 
                        SupportResistanceResult(
                            status="success" if (final_supports or final_resistances) else "failed",
                            supports_count=len(final_supports),
                            resistances_count=len(final_resistances),
                            supports=supports_data,
                            resistances=resistances_data,
                            error_message="" if (final_supports or final_resistances) else "No valid levels detected"
                        ))
                    print(f"  ✅ progress_tracker最終更新成功")
                except ImportError as e:
                    print(f"  ⚠️ progress_trackerインポートエラー: {e}")
                except Exception as e:
                    print(f"  ❌ progress_tracker最終更新エラー: {e}")
                    import traceback
                    traceback.print_exc()
            
            return final_supports, final_resistances
            
        except Exception as e:
            print(f"🚨 サポレジ分析で致命的エラーが発生: {e}")
            print(f"  📊 データ状態: 長さ{len(data)}本, 空={data.empty}")
            if not data.empty:
                print(f"  💰 価格範囲: {data['close'].min():.4f} - {data['close'].max():.4f}")
            import traceback
            print(f"スタックトレース: {traceback.format_exc()}")
            
            # 進捗更新（エラー時）
            if execution_id:
                try:
                    from web_dashboard.analysis_progress import progress_tracker, SupportResistanceResult
                    print(f"  📊 progress_trackerエラー更新: {str(e)[:100]}")
                    progress_tracker.update_support_resistance(execution_id, 
                        SupportResistanceResult(status="failed", error_message=str(e)))
                    print(f"  ✅ progress_trackerエラー更新成功")
                except ImportError as ie:
                    print(f"  ⚠️ progress_trackerインポートエラー: {ie}")
                except Exception as ue:
                    print(f"  ❌ progress_trackerエラー更新エラー: {ue}")
                    import traceback
                    traceback.print_exc()
            
            raise Exception(f"サポート・レジスタンス分析に失敗: {e} - 不完全なデータでの分析は危険です")
    
    def _predict_breakouts(self, data: pd.DataFrame, levels: list) -> list:
        """ブレイクアウト予測"""
        
        predictions = []
        
        try:
            if self.breakout_predictor and levels:
                
                # モデルが訓練されていない場合は訓練を試行
                if not hasattr(self.breakout_predictor, 'is_trained') or not self.breakout_predictor.is_trained:
                    print("🏋️ MLモデル訓練中...")
                    self.breakout_predictor.train_model(data, levels)
                
                # 各レベルに対して予測実行
                for level in levels:
                    try:
                        prediction = self.breakout_predictor.predict_breakout(data, level)
                        # Noneの場合はシグナルスキップとして処理
                        if prediction is not None:
                            predictions.append(prediction)
                        else:
                            print(f"レベル{level.price}のシグナル検知をスキップ（実データ不足）")
                    except Exception as e:
                        print(f"レベル{level.price}の予測エラー: {e}")
                        continue
            
        except Exception as e:
            print(f"ブレイクアウト予測エラー: {e}")
        
        return predictions
    
    def _analyze_btc_correlation(self, symbol: str):
        """BTC相関分析"""
        
        try:
            if self.btc_correlation_analyzer:
                # BTC 5%下落のシナリオで分析
                return self.btc_correlation_analyzer.predict_altcoin_impact(symbol, -5.0)
            
        except Exception as e:
            print(f"BTC相関分析エラー: {e}")
        
        return None
    
    def _analyze_market_context(self, data: pd.DataFrame, target_timestamp: datetime = None, is_realtime: bool = True) -> MarketContext:
        """市場コンテキスト分析
        
        Args:
            data: OHLCVデータ
            target_timestamp: 分析対象の時刻（バックテストの場合）
            is_realtime: リアルタイム分析かどうか
        """
        
        try:
            if self.market_context_analyzer:
                return self.market_context_analyzer.analyze_market_phase(
                    data, 
                    target_timestamp=target_timestamp,
                    is_realtime=is_realtime
                )
            
        except Exception as e:
            print(f"市場コンテキスト分析エラー: {e}")
            raise Exception(f"市場コンテキスト分析に失敗: {e} - 銘柄追加を中止")
        
        # データ検証（フォールバック値は使用しない）
        if data.empty:
            raise Exception("市場データが空のためコンテキスト分析できません")
        
        # 実データが取得できているがアナライザーが利用できない場合もエラー
        raise Exception("市場コンテキストアナライザーが初期化されていません - 銘柄追加を中止")
    
    def _display_analysis_summary(self, recommendation: LeverageRecommendation):
        """分析結果サマリーを表示"""
        
        print("\n" + "=" * 60)
        print("🎯 ハイレバレッジ判定結果")
        print("=" * 60)
        
        print(f"\n💰 現在価格: {recommendation.market_conditions.current_price:.4f}")
        print(f"🎪 推奨レバレッジ: {recommendation.recommended_leverage:.1f}x")
        print(f"🛡️ 最大安全レバレッジ: {recommendation.max_safe_leverage:.1f}x")
        print(f"⚖️ リスクリワード比: {recommendation.risk_reward_ratio:.2f}")
        print(f"🎯 信頼度: {recommendation.confidence_level*100:.1f}%")
        
        print(f"\n📍 損切りライン: {recommendation.stop_loss_price:.4f}")
        print(f"🎯 利確ライン: {recommendation.take_profit_price:.4f}")
        
        print("\n📝 判定理由:")
        for i, reason in enumerate(recommendation.reasoning, 1):
            print(f"  {i}. {reason}")
        
        print("\n" + "=" * 60)
    
    # def _create_error_recommendation(self, error_message: str, current_price: float) -> LeverageRecommendation:
    #     """エラー時の保守的推奨を作成 - 使用停止（フォールバック値除去のため）"""
    #     
    #     # フォールバック値を含むため使用停止
    #     # エラー時は例外を発生させて銘柄追加を失敗させる方針に変更
    #     raise Exception(f"エラー時推奨作成は廃止されました: {error_message}")
    
    def _determine_symbol_category(self, symbol: str) -> str:
        """
        銘柄カテゴリを判定
        
        Args:
            symbol: 銘柄シンボル
            
        Returns:
            str: 銘柄カテゴリ ('large_cap', 'mid_cap', 'small_cap', 'meme_coin')
        """
        symbol_upper = symbol.upper()
        
        # 大型銘柄
        large_cap_symbols = ['BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'AVAX', 'LINK', 'MATIC']
        if symbol_upper in large_cap_symbols:
            return 'large_cap'
        
        # ミームコイン
        meme_symbols = ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'BRETT', 'POPCAT']
        if symbol_upper in meme_symbols:
            return 'meme_coin'
        
        # 中型銘柄（主要アルトコイン）
        mid_cap_symbols = [
            'UNI', 'ATOM', 'LTC', 'BCH', 'ETC', 'FIL', 'AAVE', 'SUSHI', 'COMP', 'YFI',
            'SNX', 'MKR', 'CRV', 'BAL', 'ALPHA', 'CAKE', 'BAKE', 'AUTO', 'BELT'
        ]
        if symbol_upper in mid_cap_symbols:
            return 'mid_cap'
        
        # デフォルトは小型銘柄
        return 'small_cap'
    
    # _generate_sample_data method removed - no fallback data allowed
    
    def analyze_symbol(self, symbol: str, timeframe: str = "1h", strategy: str = "Conservative_ML", is_backtest: bool = False, target_timestamp: datetime = None, custom_period_settings: dict = None, execution_id: str = None) -> Dict:
        """
        シンボル分析（リアルタイム監視システム用）
        
        Args:
            symbol: 分析対象シンボル
            timeframe: 時間足
            strategy: 戦略名
            
        Returns:
            Dict: 分析結果辞書
        """
        
        recommendation = self.analyze_leverage_opportunity(symbol, timeframe, is_backtest, target_timestamp, custom_period_settings, execution_id)
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': strategy,
            'leverage': recommendation.recommended_leverage,
            'confidence': recommendation.confidence_level * 100,  # パーセント変換
            'current_price': recommendation.market_conditions.current_price,
            'entry_price': recommendation.market_conditions.current_price,
            'target_price': recommendation.take_profit_price,
            'stop_loss': recommendation.stop_loss_price,
            'risk_reward_ratio': recommendation.risk_reward_ratio,
            'timestamp': datetime.now(timezone.utc),
            'position_size': 100.0,  # デフォルト
            'risk_level': max(0, 100 - recommendation.confidence_level * 100)  # リスクレベル
        }
    
    # === プラグイン設定メソッド ===
    
    def set_support_resistance_analyzer(self, analyzer: ISupportResistanceAnalyzer):
        """サポレジ分析器を設定"""
        self.support_resistance_analyzer = analyzer
        print("✅ サポレジ分析器を更新しました")
    
    def set_breakout_predictor(self, predictor: IBreakoutPredictor):
        """ブレイクアウト予測器を設定"""
        self.breakout_predictor = predictor
        print("✅ ブレイクアウト予測器を更新しました")
    
    def set_btc_correlation_analyzer(self, analyzer: IBTCCorrelationAnalyzer):
        """BTC相関分析器を設定"""
        self.btc_correlation_analyzer = analyzer
        print("✅ BTC相関分析器を更新しました")
    
    def set_market_context_analyzer(self, analyzer: IMarketContextAnalyzer):
        """市場コンテキスト分析器を設定"""
        self.market_context_analyzer = analyzer
        print("✅ 市場コンテキスト分析器を更新しました")
    
    def set_leverage_decision_engine(self, engine: ILeverageDecisionEngine):
        """レバレッジ判定エンジンを設定"""
        self.leverage_decision_engine = engine
        print("✅ レバレッジ判定エンジンを更新しました")
    
    def set_stop_loss_take_profit_calculator(self, calculator: IStopLossTakeProfitCalculator):
        """損切り・利確計算器を設定"""
        # レバレッジ判定エンジンが未初期化の場合は初期化
        if self.leverage_decision_engine is None:
            self.leverage_decision_engine = CoreLeverageDecisionEngine()
            print("🔧 レバレッジ判定エンジンを自動初期化しました")
        
        if hasattr(self.leverage_decision_engine, 'set_stop_loss_take_profit_calculator'):
            self.leverage_decision_engine.set_stop_loss_take_profit_calculator(calculator)
            print("✅ 損切り・利確計算器を更新しました")
        else:
            print("⚠️ 現在のレバレッジ判定エンジンは損切り・利確計算器の設定をサポートしていません")

# === 便利な実行関数 ===

def analyze_leverage_for_symbol(symbol: str, timeframe: str = "1h") -> LeverageRecommendation:
    """
    シンボルのハイレバレッジ機会を分析（便利関数）
    
    Args:
        symbol: 分析対象シンボル (例: 'HYPE', 'SOL')
        timeframe: 時間足 (例: '1h', '15m')
        
    Returns:
        LeverageRecommendation: レバレッジ推奨結果
    """
    
    orchestrator = HighLeverageBotOrchestrator()
    return orchestrator.analyze_leverage_opportunity(symbol, timeframe)

def quick_leverage_check(symbol: str) -> str:
    """
    クイックレバレッジチェック（簡易版）
    
    Args:
        symbol: 分析対象シンボル
        
    Returns:
        str: 簡易判定結果
    """
    
    try:
        recommendation = analyze_leverage_for_symbol(symbol)
        
        leverage = recommendation.recommended_leverage
        confidence = recommendation.confidence_level
        
        if leverage >= 10 and confidence >= 0.7:
            return f"🚀 高レバ推奨: {leverage:.1f}x (信頼度: {confidence*100:.0f}%)"
        elif leverage >= 5 and confidence >= 0.5:
            return f"⚡ 中レバ推奨: {leverage:.1f}x (信頼度: {confidence*100:.0f}%)"
        elif leverage >= 2:
            return f"🐌 低レバ推奨: {leverage:.1f}x (信頼度: {confidence*100:.0f}%)"
        else:
            return f"🛑 レバレッジ非推奨: {leverage:.1f}x (信頼度: {confidence*100:.0f}%)"
            
    except Exception as e:
        return f"❌ 分析エラー: {str(e)}"