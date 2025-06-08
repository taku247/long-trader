"""
BTC-アルトコイン連れ安予測システム - バックテスト・チューニング機能

【概要】
過去のBTC急落イベントを抽出し、予測モデルの精度検証とパラメータチューニングを行う。
実用的な清算回避システムの構築を目的とする。

【主要機能】
1. 過去の急落イベント抽出
2. Walk-forward バックテスト
3. 予測精度の多角的評価
4. ハイパーパラメータ最適化
5. 清算回避効果の測定
6. 結果可視化

【使用方法】
python btc_altcoin_backtester.py --symbol ETH --backtest-days 365 --optimize
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import time
import json
from dataclasses import dataclass

# 機械学習ライブラリ
from sklearn.model_selection import TimeSeriesSplit, ParameterGrid
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb
import joblib

# Hyperliquid API
from hyperliquid.info import Info
from hyperliquid.utils import constants

# 既存のモジュールをインポート
from btc_altcoin_correlation_predictor import BTCAltcoinCorrelationPredictor

warnings.filterwarnings('ignore')

@dataclass
class BTCDropEvent:
    """BTC急落イベントの情報"""
    timestamp: datetime
    drop_pct: float
    duration_minutes: int
    volume_spike: float
    prior_trend: str  # 'up', 'down', 'sideways'
    market_hour: int
    is_weekend: bool

@dataclass
class BacktestResult:
    """バックテスト結果"""
    symbol: str
    total_events: int
    prediction_accuracy: Dict[int, float]  # {horizon: mae}
    direction_accuracy: Dict[int, float]   # {horizon: correct_direction_pct}
    liquidation_avoidance: Dict[str, float]  # 清算回避効果
    optimal_thresholds: Dict[int, float]   # 最適閾値
    feature_importance: pd.DataFrame
    
class BTCAltcoinBacktester:
    """BTC-アルトコイン予測システムのバックテスター"""
    
    def __init__(self, 
                 btc_drop_threshold: float = -3.0,
                 prediction_horizons: List[int] = [5, 15, 60, 240],
                 leverage_levels: List[float] = [5, 10, 20, 50]):
        """
        初期化
        
        Args:
            btc_drop_threshold: BTC急落検知閾値（%）
            prediction_horizons: 予測時間幅（分）
            leverage_levels: テスト対象のレバレッジ
        """
        self.btc_drop_threshold = btc_drop_threshold
        self.prediction_horizons = prediction_horizons
        self.leverage_levels = leverage_levels
        
        self.info = Info(constants.MAINNET_API_URL)
        self.predictor = BTCAltcoinCorrelationPredictor(prediction_horizons)
        
        # バックテスト結果保存用
        self.btc_drop_events = []
        self.backtest_results = {}
        
    def extract_btc_drop_events(self, days: int = 365) -> List[BTCDropEvent]:
        """
        過去のBTC急落イベントを抽出
        
        Args:
            days: 遡る日数
            
        Returns:
            急落イベントのリスト
        """
        print(f"過去{days}日間のBTC急落イベントを抽出中...")
        
        # BTCデータ取得
        btc_data = self.predictor.fetch_historical_data('BTC', '1m', days)
        if btc_data.empty:
            print("BTCデータ取得に失敗")
            return []
        
        events = []
        returns = btc_data['close'].pct_change()
        
        # 15分間のローリング下落率を計算
        rolling_returns = returns.rolling(15).sum() * 100
        
        # ボラティリティベースの閾値調整
        volatility = returns.rolling(1440).std()  # 24時間ボラティリティ
        median_vol = volatility.median()
        
        # 急落イベント検出
        for i in range(len(rolling_returns)):
            if pd.isna(rolling_returns.iloc[i]):
                continue
                
            drop_pct = rolling_returns.iloc[i]
            current_vol = volatility.iloc[i] if not pd.isna(volatility.iloc[i]) else median_vol
            
            # ボラティリティ調整閾値
            adjusted_threshold = self.btc_drop_threshold * (current_vol / median_vol)
            
            if drop_pct <= adjusted_threshold:
                timestamp = btc_data.index[i]
                
                # 急落の詳細情報を計算
                start_idx = max(0, i - 15)
                end_idx = min(len(btc_data), i + 60)  # 1時間後まで
                
                # 出来高スパイク
                volume_ma = btc_data['volume'].rolling(60).mean().iloc[i]
                current_volume = btc_data['volume'].iloc[i]
                volume_spike = current_volume / volume_ma if volume_ma > 0 else 1.0
                
                # 事前トレンド
                if i >= 240:  # 4時間前のデータがある場合
                    trend_data = btc_data['close'].iloc[i-240:i]
                    trend_slope = np.polyfit(range(len(trend_data)), trend_data.values, 1)[0]
                    if trend_slope > 0.1:
                        prior_trend = 'up'
                    elif trend_slope < -0.1:
                        prior_trend = 'down'
                    else:
                        prior_trend = 'sideways'
                else:
                    prior_trend = 'unknown'
                
                # 急落の持続時間
                duration = 15  # 最低15分
                for j in range(i + 1, min(len(returns), i + 120)):  # 最大2時間
                    if returns.iloc[j] >= 0:  # プラス転換で終了
                        break
                    duration += 1
                
                event = BTCDropEvent(
                    timestamp=timestamp,
                    drop_pct=drop_pct,
                    duration_minutes=duration,
                    volume_spike=volume_spike,
                    prior_trend=prior_trend,
                    market_hour=timestamp.hour,
                    is_weekend=timestamp.weekday() >= 5
                )
                
                events.append(event)
        
        # 重複除去（30分以内の連続イベント）
        filtered_events = []
        for event in events:
            if not filtered_events or (event.timestamp - filtered_events[-1].timestamp).total_seconds() > 1800:
                filtered_events.append(event)
        
        print(f"検出された急落イベント: {len(filtered_events)}件")
        
        # イベント分析
        self._analyze_drop_events(filtered_events)
        
        return filtered_events
    
    def _analyze_drop_events(self, events: List[BTCDropEvent]):
        """急落イベントの統計分析"""
        if not events:
            return
            
        drops = [e.drop_pct for e in events]
        volumes = [e.volume_spike for e in events]
        durations = [e.duration_minutes for e in events]
        
        print(f"\n=== BTC急落イベント分析 ===")
        print(f"下落率: 平均 {np.mean(drops):.2f}%, 中央値 {np.median(drops):.2f}%")
        print(f"最大下落: {min(drops):.2f}%")
        print(f"出来高倍率: 平均 {np.mean(volumes):.2f}x")
        print(f"持続時間: 平均 {np.mean(durations):.1f}分")
        
        # 時間帯分析
        hours = [e.market_hour for e in events]
        weekend_count = sum(1 for e in events if e.is_weekend)
        print(f"週末発生率: {weekend_count/len(events)*100:.1f}%")
        print(f"最多発生時間: {max(set(hours), key=hours.count)}時")
    
    def run_backtest(self, symbol: str, events: List[BTCDropEvent]) -> BacktestResult:
        """
        指定銘柄のバックテスト実行
        
        Args:
            symbol: アルトコインシンボル
            events: BTC急落イベントリスト
            
        Returns:
            バックテスト結果
        """
        print(f"\n{symbol}のバックテストを実行中...")
        
        # アルトコインデータ取得
        alt_data = self.predictor.fetch_historical_data(symbol, '1m', 365)
        if alt_data.empty:
            print(f"{symbol}のデータ取得に失敗")
            return None
        
        # 予測精度評価用
        predictions_vs_actual = {horizon: {'pred': [], 'actual': []} for horizon in self.prediction_horizons}
        liquidation_stats = {lev: {'total': 0, 'avoided': 0} for lev in self.leverage_levels}
        
        # Walk-forward validation
        train_window = 30  # 30日間のデータで訓練
        
        for i, event in enumerate(events):
            if i % 10 == 0:
                print(f"  イベント処理中: {i+1}/{len(events)}")
            
            # 訓練期間設定
            train_start = event.timestamp - timedelta(days=train_window)
            train_end = event.timestamp - timedelta(hours=1)  # 1時間前まで
            
            # 訓練データ取得
            train_btc = self._get_data_slice(self.predictor.fetch_historical_data('BTC', '1m', train_window), 
                                           train_start, train_end)
            train_alt = self._get_data_slice(alt_data, train_start, train_end)
            
            if len(train_btc) < 1000 or len(train_alt) < 1000:
                continue
            
            # モデル訓練
            try:
                features = self.predictor.calculate_features(train_btc, train_alt)
                if len(features) < 500:
                    continue
                
                # 各時間軸でモデル訓練・予測
                for horizon in self.prediction_horizons:
                    model, scaler = self._train_model(features, horizon)
                    if model is None:
                        continue
                    
                    # 予測実行
                    pred_features = self.predictor.create_prediction_features(event.drop_pct)
                    X_scaled = scaler.transform([pred_features])
                    predicted_drop = model.predict(X_scaled)[0] * 100
                    
                    # 実際の下落幅取得
                    actual_drop = self._get_actual_drop(alt_data, event.timestamp, horizon)
                    if actual_drop is not None:
                        predictions_vs_actual[horizon]['pred'].append(predicted_drop)
                        predictions_vs_actual[horizon]['actual'].append(actual_drop)
                    
                    # 清算回避効果評価
                    for leverage in self.leverage_levels:
                        liquidation_stats[leverage]['total'] += 1
                        
                        # 予測ベースの判定
                        predicted_loss = predicted_drop * leverage
                        liquidation_threshold = -90 / leverage
                        
                        if predicted_loss <= liquidation_threshold * 0.8:  # 80%で警告
                            # 早期損切りを実行したと仮定
                            actual_loss = actual_drop * leverage
                            if actual_loss <= liquidation_threshold:
                                liquidation_stats[leverage]['avoided'] += 1
                
            except Exception as e:
                print(f"  イベント{i}でエラー: {e}")
                continue
        
        # 結果集計
        prediction_accuracy = {}
        direction_accuracy = {}
        
        for horizon in self.prediction_horizons:
            if len(predictions_vs_actual[horizon]['pred']) > 0:
                pred = np.array(predictions_vs_actual[horizon]['pred'])
                actual = np.array(predictions_vs_actual[horizon]['actual'])
                
                # 予測精度
                mae = mean_absolute_error(actual, pred)
                prediction_accuracy[horizon] = mae
                
                # 方向性精度
                pred_direction = pred < 0
                actual_direction = actual < 0
                direction_acc = np.mean(pred_direction == actual_direction) * 100
                direction_accuracy[horizon] = direction_acc
        
        # 清算回避率
        liquidation_avoidance = {}
        for leverage in self.leverage_levels:
            stats = liquidation_stats[leverage]
            if stats['total'] > 0:
                avoidance_rate = stats['avoided'] / stats['total'] * 100
                liquidation_avoidance[f"{leverage}x"] = avoidance_rate
        
        result = BacktestResult(
            symbol=symbol,
            total_events=len(events),
            prediction_accuracy=prediction_accuracy,
            direction_accuracy=direction_accuracy,
            liquidation_avoidance=liquidation_avoidance,
            optimal_thresholds={},  # 後で計算
            feature_importance=pd.DataFrame()  # 後で計算
        )
        
        return result
    
    def _get_data_slice(self, data: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
        """指定期間のデータを取得"""
        return data[(data.index >= start) & (data.index <= end)]
    
    def _train_model(self, features: pd.DataFrame, horizon: int):
        """単一時間軸のモデル訓練"""
        target_col = f'alt_return_{horizon}m'
        if target_col not in features.columns:
            return None, None
        
        feature_cols = [col for col in features.columns if not col.startswith('alt_return')]
        X = features[feature_cols].dropna()
        y = features[target_col].loc[X.index].dropna()
        
        common_idx = X.index.intersection(y.index)
        if len(common_idx) < 100:
            return None, None
        
        X = X.loc[common_idx]
        y = y.loc[common_idx]
        
        # スケーリング
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # モデル訓練
        model = lgb.LGBMRegressor(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
            verbosity=-1
        )
        model.fit(X_scaled, y)
        
        return model, scaler
    
    def _get_actual_drop(self, alt_data: pd.DataFrame, event_time: datetime, horizon: int) -> Optional[float]:
        """実際の下落幅を取得"""
        try:
            start_idx = alt_data.index.get_indexer([event_time], method='nearest')[0]
            end_time = event_time + timedelta(minutes=horizon)
            end_idx = alt_data.index.get_indexer([end_time], method='nearest')[0]
            
            if start_idx >= 0 and end_idx >= 0 and end_idx < len(alt_data):
                start_price = alt_data['close'].iloc[start_idx]
                end_price = alt_data['close'].iloc[end_idx]
                drop_pct = ((end_price - start_price) / start_price) * 100
                return drop_pct
        except:
            pass
        return None
    
    def optimize_hyperparameters(self, symbol: str, features: pd.DataFrame) -> Dict:
        """
        ハイパーパラメータ最適化
        """
        print(f"{symbol}のハイパーパラメータ最適化中...")
        
        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 4, 6],
            'learning_rate': [0.05, 0.1, 0.2],
            'min_child_samples': [10, 20, 50]
        }
        
        best_params = {}
        
        for horizon in self.prediction_horizons:
            target_col = f'alt_return_{horizon}m'
            if target_col not in features.columns:
                continue
            
            feature_cols = [col for col in features.columns if not col.startswith('alt_return')]
            X = features[feature_cols].dropna()
            y = features[target_col].loc[X.index].dropna()
            
            if len(X) < 500:
                continue
            
            # 時系列分割
            tscv = TimeSeriesSplit(n_splits=3)
            best_score = float('inf')
            best_param = None
            
            for params in ParameterGrid(param_grid):
                cv_scores = []
                
                for train_idx, val_idx in tscv.split(X):
                    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                    
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_val_scaled = scaler.transform(X_val)
                    
                    model = lgb.LGBMRegressor(**params, random_state=42, verbosity=-1)
                    model.fit(X_train_scaled, y_train)
                    
                    y_pred = model.predict(X_val_scaled)
                    mae = mean_absolute_error(y_val, y_pred)
                    cv_scores.append(mae)
                
                mean_score = np.mean(cv_scores)
                if mean_score < best_score:
                    best_score = mean_score
                    best_param = params
            
            best_params[horizon] = best_param
            print(f"  {horizon}分: 最適パラメータ見つかりました (MAE: {best_score:.4f})")
        
        return best_params
    
    def visualize_results(self, results: Dict[str, BacktestResult]):
        """バックテスト結果の可視化"""
        print("\nバックテスト結果を可視化中...")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 予測精度比較
        ax1 = axes[0, 0]
        symbols = list(results.keys())
        horizons = self.prediction_horizons
        
        accuracy_data = []
        for symbol in symbols:
            for horizon in horizons:
                if horizon in results[symbol].prediction_accuracy:
                    accuracy_data.append({
                        'Symbol': symbol,
                        'Horizon': f'{horizon}m',
                        'MAE': results[symbol].prediction_accuracy[horizon]
                    })
        
        if accuracy_data:
            df_acc = pd.DataFrame(accuracy_data)
            pivot_acc = df_acc.pivot(index='Symbol', columns='Horizon', values='MAE')
            sns.heatmap(pivot_acc, annot=True, fmt='.3f', ax=ax1, cmap='RdYlBu_r')
            ax1.set_title('Prediction Accuracy (MAE)')
        
        # 2. 方向性精度
        ax2 = axes[0, 1]
        direction_data = []
        for symbol in symbols:
            for horizon in horizons:
                if horizon in results[symbol].direction_accuracy:
                    direction_data.append({
                        'Symbol': symbol,
                        'Horizon': f'{horizon}m',
                        'Accuracy': results[symbol].direction_accuracy[horizon]
                    })
        
        if direction_data:
            df_dir = pd.DataFrame(direction_data)
            pivot_dir = df_dir.pivot(index='Symbol', columns='Horizon', values='Accuracy')
            sns.heatmap(pivot_dir, annot=True, fmt='.1f', ax=ax2, cmap='RdYlGn')
            ax2.set_title('Direction Accuracy (%)')
        
        # 3. 清算回避率
        ax3 = axes[1, 0]
        avoidance_data = []
        for symbol in symbols:
            for leverage, rate in results[symbol].liquidation_avoidance.items():
                avoidance_data.append({
                    'Symbol': symbol,
                    'Leverage': leverage,
                    'Avoidance_Rate': rate
                })
        
        if avoidance_data:
            df_avoid = pd.DataFrame(avoidance_data)
            pivot_avoid = df_avoid.pivot(index='Symbol', columns='Leverage', values='Avoidance_Rate')
            sns.heatmap(pivot_avoid, annot=True, fmt='.1f', ax=ax3, cmap='RdYlGn')
            ax3.set_title('Liquidation Avoidance Rate (%)')
        
        # 4. 総合スコア
        ax4 = axes[1, 1]
        score_data = []
        for symbol in symbols:
            # 総合スコア計算（方向性精度 + 清算回避率の平均）
            dir_scores = list(results[symbol].direction_accuracy.values())
            avoid_scores = list(results[symbol].liquidation_avoidance.values())
            
            if dir_scores and avoid_scores:
                total_score = (np.mean(dir_scores) + np.mean(avoid_scores)) / 2
                score_data.append({'Symbol': symbol, 'Total_Score': total_score})
        
        if score_data:
            df_score = pd.DataFrame(score_data)
            bars = ax4.bar(df_score['Symbol'], df_score['Total_Score'])
            ax4.set_title('Overall Performance Score')
            ax4.set_ylabel('Score (%)')
            
            # バーに数値表示
            for bar, score in zip(bars, df_score['Total_Score']):
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{score:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig('backtest_results.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        print("✅ 結果を可視化: backtest_results.png")
    
    def save_results(self, results: Dict[str, BacktestResult], filename: str = "backtest_results.json"):
        """バックテスト結果の保存"""
        serializable_results = {}
        
        for symbol, result in results.items():
            serializable_results[symbol] = {
                'symbol': result.symbol,
                'total_events': result.total_events,
                'prediction_accuracy': result.prediction_accuracy,
                'direction_accuracy': result.direction_accuracy,
                'liquidation_avoidance': result.liquidation_avoidance,
                'optimal_thresholds': result.optimal_thresholds
            }
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"✅ 結果を保存: {filename}")

def main():
    parser = argparse.ArgumentParser(description='BTC-アルトコイン予測システム バックテスト')
    parser.add_argument('--symbols', type=str, default='ETH,SOL,HYPE', 
                       help='テスト対象銘柄（カンマ区切り）')
    parser.add_argument('--backtest-days', type=int, default=365,
                       help='バックテスト期間（日数）')
    parser.add_argument('--btc-threshold', type=float, default=-3.0,
                       help='BTC急落検知閾値（%）')
    parser.add_argument('--optimize', action='store_true',
                       help='ハイパーパラメータ最適化を実行')
    
    args = parser.parse_args()
    
    symbols = [s.strip().upper() for s in args.symbols.split(',')]
    
    # バックテスター初期化
    backtester = BTCAltcoinBacktester(btc_drop_threshold=args.btc_threshold)
    
    # 急落イベント抽出
    btc_events = backtester.extract_btc_drop_events(args.backtest_days)
    
    if len(btc_events) < 10:
        print("急落イベントが少なすぎます。閾値を調整してください。")
        return
    
    # 各銘柄でバックテスト実行
    results = {}
    
    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"{symbol} バックテスト開始")
        print(f"{'='*50}")
        
        result = backtester.run_backtest(symbol, btc_events)
        if result:
            results[symbol] = result
            
            # 結果サマリー表示
            print(f"\n{symbol} バックテスト結果:")
            print(f"  総イベント数: {result.total_events}")
            
            if result.prediction_accuracy:
                print(f"  予測精度 (MAE):")
                for horizon, mae in result.prediction_accuracy.items():
                    print(f"    {horizon}分: {mae:.3f}%")
            
            if result.direction_accuracy:
                print(f"  方向性精度:")
                for horizon, acc in result.direction_accuracy.items():
                    print(f"    {horizon}分: {acc:.1f}%")
            
            if result.liquidation_avoidance:
                print(f"  清算回避率:")
                for leverage, rate in result.liquidation_avoidance.items():
                    print(f"    {leverage}: {rate:.1f}%")
    
    if results:
        # 結果可視化
        backtester.visualize_results(results)
        
        # 結果保存
        backtester.save_results(results)
        
        print(f"\n🎉 バックテスト完了!")
        print(f"対象銘柄: {', '.join(symbols)}")
        print(f"検証期間: {args.backtest_days}日間")
        print(f"急落イベント: {len(btc_events)}件")

if __name__ == "__main__":
    main()