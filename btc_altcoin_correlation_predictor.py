"""
BTC急落時のアルトコイン連れ安予測アルゴリズム

【概要】
BTCが急落した際のアルトコインの連れ安幅を機械学習で予測するシステム。
ハイレバロングポジションの清算リスク軽減を目的とする。

【主要機能】
1. BTC-アルトコイン価格相関の分析
2. 機械学習による連れ安幅の予測
3. 複数時間軸での予測（5分〜4時間）

【使用方法】
python btc_altcoin_correlation_predictor.py --btc-drop -5.0 --symbol ETH --leverage 10
"""

import pandas as pd
import numpy as np
import argparse
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import time

# 機械学習ライブラリ
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import lightgbm as lgb
import joblib

# Hyperliquid API
from hyperliquid.info import Info
from hyperliquid.utils import constants

warnings.filterwarnings('ignore')

class BTCAltcoinCorrelationPredictor:
    """BTC-アルトコイン相関予測システム"""
    
    def __init__(self, prediction_horizons: List[int] = [5, 15, 60, 240]):
        """
        初期化
        
        Args:
            prediction_horizons: 予測時間幅（分）
        """
        self.prediction_horizons = prediction_horizons
        self.info = Info(constants.MAINNET_API_URL)
        self.models = {}
        self.scalers = {}
    
    def fetch_historical_data(self, symbol: str, timeframe: str = "1m", days: int = 30) -> pd.DataFrame:
        """過去データの取得"""
        print(f"{symbol}の過去データを取得中 ({days}日間)")
        
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            all_data = []
            
            # 1日ずつデータを取得
            for i in range(days):
                day_start = start_time + (i * 24 * 60 * 60 * 1000)
                day_end = day_start + (24 * 60 * 60 * 1000)
                
                candles = self.info.candles_snapshot(symbol, timeframe, day_start, day_end)
                
                for candle in candles:
                    all_data.append({
                        'timestamp': pd.to_datetime(candle['t'], unit='ms'),
                        'open': float(candle['o']),
                        'high': float(candle['h']),
                        'low': float(candle['l']),
                        'close': float(candle['c']),
                        'volume': float(candle['v'])
                    })
                
                # レート制限対策
                time.sleep(0.1)
            
            df = pd.DataFrame(all_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            print(f"{symbol}: {len(df)}件のデータを取得")
            return df
            
        except Exception as e:
            print(f"{symbol}のデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def calculate_features(self, btc_data: pd.DataFrame, alt_data: pd.DataFrame) -> pd.DataFrame:
        """BTC-アルトコイン相関分析用の特徴量を計算（改善版）"""
        # 価格変化率を計算
        btc_returns = btc_data['close'].pct_change().fillna(0)
        alt_returns = alt_data['close'].pct_change().fillna(0)
        
        # 時間軸を合わせる
        common_index = btc_returns.index.intersection(alt_returns.index)
        btc_returns = btc_returns.loc[common_index]
        alt_returns = alt_returns.loc[common_index]
        btc_data_aligned = btc_data.loc[common_index]
        alt_data_aligned = alt_data.loc[common_index]
        
        features = pd.DataFrame(index=common_index)
        
        # === BTC基本特徴量 ===
        features['btc_return_1m'] = btc_returns
        features['btc_return_5m'] = btc_returns.rolling(5).sum()
        features['btc_return_15m'] = btc_returns.rolling(15).sum()
        features['btc_return_60m'] = btc_returns.rolling(60).sum()
        features['btc_return_240m'] = btc_returns.rolling(240).sum()  # 4時間
        
        # === BTC価格レベル特徴量 ===
        features['btc_price'] = btc_data_aligned['close']
        features['btc_price_norm'] = features['btc_price'] / features['btc_price'].rolling(1440).mean()  # 24時間正規化
        
        # === ボラティリティ特徴量 ===
        features['btc_volatility_15m'] = btc_returns.rolling(15).std()
        features['btc_volatility_60m'] = btc_returns.rolling(60).std()
        features['btc_volatility_ratio'] = features['btc_volatility_15m'] / features['btc_volatility_60m']
        
        # === BTC出来高特徴量 ===
        features['btc_volume'] = btc_data_aligned['volume']
        features['btc_volume_ma_15m'] = features['btc_volume'].rolling(15).mean()
        features['btc_volume_ma_60m'] = features['btc_volume'].rolling(60).mean()
        features['btc_volume_ratio_15m'] = features['btc_volume'] / features['btc_volume_ma_15m']
        features['btc_volume_ratio_60m'] = features['btc_volume'] / features['btc_volume_ma_60m']
        
        # === モメンタム特徴量 ===
        # RSI
        features['btc_rsi_14'] = self._calculate_rsi(btc_data_aligned['close'], 14)
        features['btc_rsi_30'] = self._calculate_rsi(btc_data_aligned['close'], 30)
        
        # MACD
        macd_data = self._calculate_macd(btc_data_aligned['close'])
        features['btc_macd'] = macd_data['macd']
        features['btc_macd_signal'] = macd_data['signal']
        features['btc_macd_histogram'] = macd_data['histogram']
        
        # === 相関特徴量 ===
        # 過去の相関係数
        features['btc_alt_corr_60m'] = btc_returns.rolling(60).corr(alt_returns)
        features['btc_alt_corr_240m'] = btc_returns.rolling(240).corr(alt_returns)
        
        # === 市場構造特徴量 ===
        # サポート・レジスタンス距離
        features['btc_support_distance'] = self._calculate_support_distance(btc_data_aligned['close'])
        features['btc_resistance_distance'] = self._calculate_resistance_distance(btc_data_aligned['close'])
        
        # === 時間特徴量 ===
        features['hour'] = features.index.hour
        features['day_of_week'] = features.index.dayofweek
        features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
        features['is_asian_hours'] = ((features['hour'] >= 0) & (features['hour'] <= 8)).astype(int)
        features['is_us_hours'] = ((features['hour'] >= 14) & (features['hour'] <= 22)).astype(int)
        
        # === アルトコイン補助特徴量 ===
        # アルトコインの現在状態（予測に使用、ターゲットではない）
        features['alt_volatility'] = alt_returns.rolling(60).std()
        features['alt_volume_ratio'] = alt_data_aligned['volume'] / alt_data_aligned['volume'].rolling(60).mean()
        features['alt_rsi'] = self._calculate_rsi(alt_data_aligned['close'], 14)
        
        # === 相対強度 ===
        features['btc_alt_strength_ratio'] = abs(btc_returns) / (abs(alt_returns) + 1e-8)
        
        # === ターゲット（アルトコインのリターン） ===
        for horizon in self.prediction_horizons:
            features[f'alt_return_{horizon}m'] = alt_returns.rolling(horizon).sum().shift(-horizon)
        
        return features.dropna()
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """RSI計算"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """MACD計算"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        
        return {
            'macd': macd,
            'signal': macd_signal,
            'histogram': macd_histogram
        }
    
    def _calculate_support_distance(self, prices: pd.Series, window: int = 240) -> pd.Series:
        """サポートラインからの距離"""
        rolling_min = prices.rolling(window).min()
        return (prices - rolling_min) / prices
    
    def _calculate_resistance_distance(self, prices: pd.Series, window: int = 240) -> pd.Series:
        """レジスタンスラインからの距離"""
        rolling_max = prices.rolling(window).max()
        return (rolling_max - prices) / prices
    
    def train_prediction_model(self, symbol: str) -> bool:
        """指定銘柄の予測モデルを訓練"""
        print(f"\n{symbol}の予測モデルを訓練中...")
        
        # データ取得
        btc_data = self.fetch_historical_data('BTC', '1m', 30)
        alt_data = self.fetch_historical_data(symbol, '1m', 30)
        
        if btc_data.empty or alt_data.empty:
            print(f"データ取得に失敗: {symbol}")
            return False
        
        # 特徴量計算
        features = self.calculate_features(btc_data, alt_data)
        if len(features) < 1000:
            print(f"データ不足: {symbol} ({len(features)}件)")
            return False
        
        # 各予測時間幅でモデルを訓練
        self.models[symbol] = {}
        self.scalers[symbol] = {}
        
        for horizon in self.prediction_horizons:
            target_col = f'alt_return_{horizon}m'
            if target_col not in features.columns:
                continue
            
            # 特徴量とターゲットを分離
            feature_cols = [col for col in features.columns if not col.startswith('alt_return')]
            X = features[feature_cols].dropna()
            y = features[target_col].loc[X.index].dropna()
            
            # データが十分にある場合のみ訓練
            common_idx = X.index.intersection(y.index)
            if len(common_idx) < 500:
                print(f"{symbol}-{horizon}m: データ不足")
                continue
            
            X = X.loc[common_idx]
            y = y.loc[common_idx]
            
            # 時系列分割でクロスバリデーション
            tscv = TimeSeriesSplit(n_splits=5)
            
            # スケーリング
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # LightGBMモデル
            model = lgb.LGBMRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                verbosity=-1
            )
            
            # クロスバリデーション
            cv_scores = []
            for train_idx, val_idx in tscv.split(X_scaled):
                X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                
                model.fit(X_train, y_train)
                y_pred = model.predict(X_val)
                mae = mean_absolute_error(y_val, y_pred)
                cv_scores.append(mae)
            
            # 全データで再訓練
            model.fit(X_scaled, y)
            
            # モデル保存
            self.models[symbol][horizon] = model
            self.scalers[symbol][horizon] = scaler
            
            print(f"  {horizon}分予測: MAE={np.mean(cv_scores):.4f}")
        
        return True
    
    def predict_altcoin_drop(self, symbol: str, btc_drop_pct: float) -> Dict[int, float]:
        """
        アルトコインの下落幅を予測
        
        Args:
            symbol: アルトコインシンボル
            btc_drop_pct: BTCの下落率（%）
            
        Returns:
            {予測時間幅: 予測下落率} の辞書
        """
        predictions = {}
        
        if symbol not in self.models:
            print(f"警告: {symbol}のモデルが存在しません")
            return predictions
        
        try:
            # 現在の特徴量を作成（簡略化版）
            current_features = self.create_prediction_features(btc_drop_pct)
            
            for horizon in self.prediction_horizons:
                if horizon not in self.models[symbol]:
                    continue
                
                model = self.models[symbol][horizon]
                scaler = self.scalers[symbol][horizon]
                
                # 予測実行
                X_scaled = scaler.transform([current_features])
                pred_return = model.predict(X_scaled)[0]
                
                # パーセント変換
                predictions[horizon] = pred_return * 100
                
        except Exception as e:
            print(f"{symbol}の予測エラー: {e}")
        
        return predictions
    
    def create_prediction_features(self, btc_drop_pct: float, current_btc_price: float = None) -> List[float]:
        """予測用の特徴量を作成（改善版）"""
        current_time = datetime.now()
        
        # BTC下落率を複数時間軸に展開
        btc_return = btc_drop_pct / 100
        
        # 最新価格を取得（指定されていない場合）
        if current_btc_price is None:
            try:
                candles = self.info.candles_snapshot('BTC', '1m', 
                                                   int(time.time() * 1000) - 60000, 
                                                   int(time.time() * 1000))
                current_btc_price = float(candles[-1]['c']) if candles else 50000
            except:
                current_btc_price = 50000
        
        # 改善された特徴量セット（順序は calculate_features と一致させる必要がある）
        features = [
            # BTC基本特徴量
            btc_return,                                    # btc_return_1m
            btc_return,                                    # btc_return_5m
            btc_return,                                    # btc_return_15m
            btc_return,                                    # btc_return_60m
            btc_return,                                    # btc_return_240m
            
            # BTC価格レベル特徴量
            current_btc_price,                             # btc_price
            1.0,                                           # btc_price_norm (仮)
            
            # ボラティリティ特徴量
            abs(btc_return) * 2,                          # btc_volatility_15m (仮)
            abs(btc_return) * 1.5,                        # btc_volatility_60m (仮)
            1.3,                                           # btc_volatility_ratio (仮)
            
            # BTC出来高特徴量
            1000000,                                       # btc_volume (仮)
            1000000,                                       # btc_volume_ma_15m (仮)
            1000000,                                       # btc_volume_ma_60m (仮)
            2.0,                                           # btc_volume_ratio_15m (急落時は出来高増加)
            1.8,                                           # btc_volume_ratio_60m
            
            # モメンタム特徴量
            50 + btc_return * 500,                        # btc_rsi_14 (下落時は低RSI)
            50 + btc_return * 300,                        # btc_rsi_30
            btc_return * current_btc_price * 0.001,       # btc_macd (仮)
            btc_return * current_btc_price * 0.0005,      # btc_macd_signal (仮)
            btc_return * current_btc_price * 0.0005,      # btc_macd_histogram (仮)
            
            # 相関特徴量
            0.8,                                           # btc_alt_corr_60m (高相関を仮定)
            0.75,                                          # btc_alt_corr_240m
            
            # 市場構造特徴量
            0.05,                                          # btc_support_distance (仮)
            0.02,                                          # btc_resistance_distance (仮)
            
            # 時間特徴量
            current_time.hour,                             # hour
            current_time.weekday(),                        # day_of_week
            1 if current_time.weekday() >= 5 else 0,      # is_weekend
            1 if 0 <= current_time.hour <= 8 else 0,      # is_asian_hours
            1 if 14 <= current_time.hour <= 22 else 0,    # is_us_hours
            
            # アルトコイン補助特徴量
            abs(btc_return) * 1.2,                        # alt_volatility (仮)
            1.5,                                           # alt_volume_ratio (仮)
            50 + btc_return * 600,                        # alt_rsi (仮)
            
            # 相対強度
            1.0,                                           # btc_alt_strength_ratio (仮)
        ]
        
        return features
    
    def calculate_liquidation_risk(self, symbol: str, predictions: Dict[int, float], 
                                 leverage: float, current_price: float = None) -> Dict:
        """
        清算リスク計算
        
        Args:
            symbol: シンボル
            predictions: 予測下落率
            leverage: レバレッジ倍率
            current_price: 現在価格（Noneの場合は取得）
        """
        if current_price is None:
            # 現在価格取得
            try:
                candles = self.info.candles_snapshot(symbol, '1m', 
                                                   int(time.time() * 1000) - 60000, 
                                                   int(time.time() * 1000))
                current_price = float(candles[-1]['c']) if candles else 1000
            except:
                current_price = 1000  # フォールバック
        
        # 清算閾値（簡略化：90%の損失で清算）
        liquidation_threshold = -90 / leverage
        
        risk_assessment = {
            'symbol': symbol,
            'current_price': current_price,
            'leverage': leverage,
            'liquidation_threshold_pct': liquidation_threshold,
            'predictions': predictions,
            'risk_levels': {}
        }
        
        for horizon, pred_drop in predictions.items():
            # レバレッジを考慮したPnL
            leveraged_pnl = pred_drop * leverage
            
            # リスクレベル判定
            margin_to_liquidation = abs(leveraged_pnl - liquidation_threshold)
            
            if leveraged_pnl <= liquidation_threshold * 0.8:
                risk_level = "CRITICAL"
            elif leveraged_pnl <= liquidation_threshold * 0.6:
                risk_level = "HIGH"
            elif leveraged_pnl <= liquidation_threshold * 0.4:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            risk_assessment['risk_levels'][horizon] = {
                'predicted_drop_pct': pred_drop,
                'leveraged_pnl_pct': leveraged_pnl,
                'risk_level': risk_level,
                'margin_to_liquidation': margin_to_liquidation
            }
        
        return risk_assessment
    
    def save_model(self, symbol: str, filepath: str = None):
        """モデル保存"""
        if filepath is None:
            filepath = f"{symbol.lower()}_correlation_model.pkl"
        
        if symbol in self.models:
            model_data = {
                'models': self.models[symbol],
                'scalers': self.scalers[symbol],
                'symbol': symbol,
                'prediction_horizons': self.prediction_horizons
            }
            joblib.dump(model_data, filepath)
            print(f"モデルを保存: {filepath}")
    
    def load_model(self, symbol: str, filepath: str = None) -> bool:
        """モデル読み込み"""
        if filepath is None:
            filepath = f"{symbol.lower()}_correlation_model.pkl"
        
        try:
            model_data = joblib.load(filepath)
            self.models[symbol] = model_data['models']
            self.scalers[symbol] = model_data['scalers']
            print(f"モデルを読み込み: {filepath}")
            return True
        except Exception as e:
            print(f"モデル読み込みエラー: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='BTC-アルトコイン連れ安予測')
    parser.add_argument('--symbol', type=str, required=True, 
                       help='アルトコインシンボル (例: ETH, SOL, HYPE)')
    parser.add_argument('--btc-drop', type=float, required=True,
                       help='BTC下落率% (例: -5.0)')
    parser.add_argument('--leverage', type=float, default=10.0,
                       help='レバレッジ倍率 (デフォルト: 10)')
    parser.add_argument('--train', action='store_true',
                       help='モデルを訓練')
    parser.add_argument('--model-file', type=str,
                       help='モデルファイルパス')
    
    args = parser.parse_args()
    
    # システム初期化
    predictor = BTCAltcoinCorrelationPredictor()
    
    symbol = args.symbol.upper()
    
    # モデル読み込みまたは訓練
    model_file = args.model_file or f"{symbol.lower()}_correlation_model.pkl"
    
    if args.train:
        print("モデルを訓練中...")
        success = predictor.train_prediction_model(symbol)
        if success:
            predictor.save_model(symbol, model_file)
            print("✅ モデル訓練完了")
        else:
            print("❌ モデル訓練失敗")
            return
    else:
        print("モデルを読み込み中...")
        if not predictor.load_model(symbol, model_file):
            print("モデルが見つかりません。--trainで訓練してください")
            return
    
    # 予測実行
    print(f"\n🔍 BTC{args.btc_drop}%下落時の{symbol}連れ安予測")
    print("=" * 50)
    
    predictions = predictor.predict_altcoin_drop(symbol, args.btc_drop)
    
    if not predictions:
        print("予測を実行できませんでした")
        return
    
    # 結果表示
    print(f"\n📊 予測結果:")
    for horizon, pred_drop in predictions.items():
        print(f"  {horizon:3d}分後: {pred_drop:+6.2f}%")
    
    # リスク評価
    print(f"\n⚠️  清算リスク評価 (レバレッジ: {args.leverage}x)")
    risk_assessment = predictor.calculate_liquidation_risk(symbol, predictions, args.leverage)
    
    for horizon, risk in risk_assessment['risk_levels'].items():
        risk_icon = {
            'LOW': '🟢',
            'MEDIUM': '🔶',
            'HIGH': '🔴',
            'CRITICAL': '❌'
        }.get(risk['risk_level'], '⚪')
        
        print(f"  {horizon:3d}分: {risk_icon} {risk['risk_level']} "
              f"(PnL: {risk['leveraged_pnl_pct']:+6.2f}%, "
              f"清算まで: {risk['margin_to_liquidation']:.1f}%)")
    
    print(f"\n💡 清算閾値: {risk_assessment['liquidation_threshold_pct']:.1f}%")

if __name__ == "__main__":
    main()