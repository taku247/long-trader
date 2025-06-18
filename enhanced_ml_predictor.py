"""
高精度ML予測システム

現在57%の精度を70%以上に改善する新しい予測システム。
主要改善点:
1. 重要な基本特徴量の復活
2. 改善されたハイパーパラメータ
3. 時系列的特徴量の追加
4. シンプルアンサンブル手法
"""

import pandas as pd
import numpy as np
import warnings
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.ensemble import RandomForestClassifier
import lightgbm as lgb

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("⚠️ XGBoostが利用できません。LightGBMとRandomForestを使用します。")

import joblib
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# インターフェースをインポート
from interfaces import IBreakoutPredictor, SupportResistanceLevel, BreakoutPrediction

warnings.filterwarnings('ignore')

class EnhancedMLPredictor(IBreakoutPredictor):
    """
    高精度ML予測器
    
    改善点:
    - 基本特徴量の復活（close, high, low等）
    - 改善されたハイパーパラメータ
    - 時系列的特徴量
    - アンサンブル手法
    """
    
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = []
        self.accuracy_metrics = {}
        
        # 改善されたハイパーパラメータ
        self.model_params = {
            'xgb': {
                'n_estimators': 300,
                'max_depth': 8,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1,
                'objective': 'binary:logistic',
                'eval_metric': 'auc',
                'random_state': 42
            },
            'lgb': {
                'n_estimators': 400,
                'max_depth': 10,
                'learning_rate': 0.03,
                'num_leaves': 64,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1,
                'objective': 'binary',
                'metric': 'auc',
                'random_state': 42,
                'verbosity': -1
            },
            'rf': {
                'n_estimators': 200,
                'max_depth': 12,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'max_features': 'sqrt',
                'random_state': 42
            }
        }
    
    def create_enhanced_features(self, data: pd.DataFrame, levels: List[SupportResistanceLevel]) -> pd.DataFrame:
        """
        改善された特徴量エンジニアリング
        
        重要な改善点:
        1. 基本特徴量の復活
        2. 時系列的特徴量の追加
        3. 相互作用特徴量の追加
        """
        
        features = data.copy()
        
        # === 1. 基本特徴量の復活（過度に削除されていた重要特徴量） ===
        if 'close' not in features.columns:
            print("⚠️ 基本価格情報が不足しています")
            return pd.DataFrame()
        
        # 基本価格特徴量
        features['price_return'] = features['close'].pct_change()
        features['log_return'] = np.log(features['close'] / features['close'].shift(1))
        
        # 移動平均（復活）
        features['sma_5'] = features['close'].rolling(5).mean()
        features['sma_10'] = features['close'].rolling(10).mean()
        features['sma_20'] = features['close'].rolling(20).mean()
        features['ema_5'] = features['close'].ewm(span=5).mean()
        features['ema_10'] = features['close'].ewm(span=10).mean()
        features['ema_20'] = features['close'].ewm(span=20).mean()
        
        # 移動平均乖離率（復活）
        features['sma_5_deviation'] = (features['close'] - features['sma_5']) / features['sma_5']
        features['sma_20_deviation'] = (features['close'] - features['sma_20']) / features['sma_20']
        features['ema_20_deviation'] = (features['close'] - features['ema_20']) / features['ema_20']
        
        # === 2. 技術的指標の改善版 ===
        # RSI（改良版）
        features['rsi_14'] = self._calculate_rsi(features['close'], 14)
        features['rsi_7'] = self._calculate_rsi(features['close'], 7)
        features['rsi_21'] = self._calculate_rsi(features['close'], 21)
        
        # MACD（改良版）
        macd_data = self._calculate_macd(features['close'])
        features['macd'] = macd_data['macd']
        features['macd_signal'] = macd_data['signal']
        features['macd_histogram'] = macd_data['histogram']
        features['macd_divergence'] = features['macd'] - features['macd_signal']
        
        # ボリンジャーバンド（復活）
        bb_data = self._calculate_bollinger_bands(features['close'])
        features['bb_upper'] = bb_data['upper']
        features['bb_middle'] = bb_data['middle']
        features['bb_lower'] = bb_data['lower']
        features['bb_position'] = (features['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        features['bb_squeeze'] = (features['bb_upper'] - features['bb_lower']) / features['bb_middle']
        
        # === 3. 時系列的特徴量（新規追加） ===
        # 価格の加速度（2次微分）
        features['price_acceleration'] = features['close'].diff().diff()
        features['volume_acceleration'] = features['volume'].diff().diff()
        
        # トレンド強度
        features['trend_strength'] = self._calculate_trend_strength(features['close'])
        
        # 出来高パターン
        features['volume_sma_ratio'] = features['volume'] / features['volume'].rolling(20).mean()
        features['volume_trend'] = features['volume'].rolling(5).apply(lambda x: np.polyfit(range(5), x, 1)[0] if len(x) == 5 else 0)
        
        # === 4. レベル特異的特徴量 ===
        if levels:
            level_features = self._add_level_features(features, levels)
            # レベル特徴量の追加に失敗した場合はシグナルスキップ
            if level_features is None:
                return None  # シグナル検知スキップ
            features = level_features
        else:
            # レベルが空の場合はシグナルスキップ
            print("⚠️ サポート・レジスタンスレベルが提供されていません - シグナル検知をスキップ")
            return None  # シグナル検知スキップ
        
        # === 5. 基本的な価格レンジ特徴量（必要な特徴量を先に作成） ===
        features['high_low_ratio'] = (features['high'] - features['low']) / features['close']
        features['close_location'] = (features['close'] - features['low']) / (features['high'] - features['low'])
        
        # === 6. 相互作用特徴量（新規追加） ===
        features['rsi_volume_interaction'] = features['rsi_14'] * features['volume_sma_ratio']
        features['macd_volatility_interaction'] = features['macd_histogram'] * features['high_low_ratio']
        features['price_volume_interaction'] = features['price_return'] * features['volume_trend']
        
        # === 7. 統計的特徴量 ===
        # 価格の統計（短期・中期・長期）
        for window in [5, 10, 20]:
            features[f'price_std_{window}'] = features['close'].rolling(window).std()
            features[f'price_skew_{window}'] = features['close'].rolling(window).skew()
            features[f'volume_std_{window}'] = features['volume'].rolling(window).std()
        
        # === 8. ラグ特徴量（時系列情報） ===
        for lag in [1, 2, 3, 5]:
            features[f'close_lag_{lag}'] = features['close'].shift(lag)
            features[f'volume_lag_{lag}'] = features['volume'].shift(lag)
            features[f'rsi_lag_{lag}'] = features['rsi_14'].shift(lag)
        
        # NaN値の処理
        features = features.fillna(method='ffill').fillna(method='bfill')
        
        print(f"✅ 拡張特徴量生成完了: {len(features.columns)}個の特徴量")
        return features
    
    def _add_level_features(self, features: pd.DataFrame, levels: List[SupportResistanceLevel]) -> pd.DataFrame:
        """レベル特異的特徴量を追加"""
        
        current_price = features['close'].iloc[-1]
        
        # 最も近いサポート・レジスタンス
        supports = [l for l in levels if l.level_type == 'support' and l.price < current_price]
        resistances = [l for l in levels if l.level_type == 'resistance' and l.price > current_price]
        
        if supports:
            nearest_support = min(supports, key=lambda x: abs(x.price - current_price))
            features['support_distance'] = (current_price - nearest_support.price) / current_price
            features['support_strength'] = nearest_support.strength
            features['support_touches'] = nearest_support.touch_count
        else:
            # 実データが利用できない場合はNoneを返してシグナルスキップを促す
            return None  # シグナル検知スキップ
        
        if resistances:
            nearest_resistance = min(resistances, key=lambda x: abs(x.price - current_price))
            features['resistance_distance'] = (nearest_resistance.price - current_price) / current_price
            features['resistance_strength'] = nearest_resistance.strength
            features['resistance_touches'] = nearest_resistance.touch_count
        else:
            # 実データが利用できない場合はNoneを返してシグナルスキップを促す
            return None  # シグナル検知スキップ
        
        # レベル間ポジション
        if supports and resistances:
            total_range = resistances[0].price - supports[0].price
            current_position = (current_price - supports[0].price) / total_range
            features['level_position'] = current_position
        else:
            # サポートまたはレジスタンスが検出できない場合はシグナルスキップ
            return None  # シグナル検知スキップ
        
        return features
    
    def train_model(self, data: pd.DataFrame, levels: List[SupportResistanceLevel]) -> bool:
        """
        改善されたモデル訓練
        """
        try:
            print("🏋️ 高精度ML予測モデルを訓練中...")
            
            # 特徴量エンジニアリング
            features = self.create_enhanced_features(data, levels)
            
            # 実データが利用できない場合は訓練失敗
            if features is None:
                print("❌ サポート・レジスタンスの実データが不足しているため、ML訓練をスキップ")
                return False
            
            if len(features) < 200:
                print("⚠️ 訓練データが不足しています（200件未満）")
                return False
            
            # 訓練データとラベルの作成
            X, y = self._create_training_data(features, levels)
            
            if len(X) < 30:
                print("⚠️ ラベル付きデータが不足しています（30件未満）")
                return False
            elif len(X) < 100:
                print(f"⚠️ 訓練データが少なめです（{len(X)}件）。精度に影響する可能性があります。")
            
            print(f"📊 訓練データ: {len(X)}件, ポジティブ比率: {y.mean():.2f}")
            
            # 特徴量の標準化
            X_scaled = self.scaler.fit_transform(X)
            self.feature_columns = X.columns.tolist()
            
            # モデル訓練
            self.models = {}
            cv_scores = {}
            
            # XGBoost
            if HAS_XGBOOST:
                print("  🚀 XGBoost訓練中...")
                self.models['xgb'] = xgb.XGBClassifier(**self.model_params['xgb'])
                self.models['xgb'].fit(X_scaled, y)
                cv_scores['xgb'] = self._cross_validate(self.models['xgb'], X_scaled, y)
            
            # LightGBM
            print("  ⚡ LightGBM訓練中...")
            self.models['lgb'] = lgb.LGBMClassifier(**self.model_params['lgb'])
            self.models['lgb'].fit(X_scaled, y)
            cv_scores['lgb'] = self._cross_validate(self.models['lgb'], X_scaled, y)
            
            # RandomForest
            print("  🌲 RandomForest訓練中...")
            self.models['rf'] = RandomForestClassifier(**self.model_params['rf'])
            self.models['rf'].fit(X_scaled, y)
            cv_scores['rf'] = self._cross_validate(self.models['rf'], X_scaled, y)
            
            # アンサンブル重みの計算
            self.ensemble_weights = self._calculate_ensemble_weights(cv_scores)
            
            # 精度評価
            ensemble_score = np.average(list(cv_scores.values()), weights=list(self.ensemble_weights.values()))
            
            self.accuracy_metrics = {
                'ensemble_auc': ensemble_score,
                'individual_scores': cv_scores,
                'ensemble_weights': self.ensemble_weights
            }
            
            self.is_trained = True
            print(f"✅ 訓練完了! アンサンブルAUC: {ensemble_score:.3f}")
            
            # 個別モデルスコア表示
            for model_name, score in cv_scores.items():
                weight = self.ensemble_weights[model_name]
                print(f"  {model_name}: AUC={score:.3f}, 重み={weight:.2f}")
            
            return True
            
        except Exception as e:
            print(f"❌ 訓練エラー: {e}")
            return False
    
    def predict_breakout(self, current_data: pd.DataFrame, level: SupportResistanceLevel) -> BreakoutPrediction:
        """
        アンサンブル予測によるブレイクアウト確率予測
        """
        try:
            if not self.is_trained:
                print("⚠️ モデルが訓練されていません")
                return self._create_default_prediction(level)
            
            # 特徴量作成
            features = self.create_enhanced_features(current_data, [level])
            
            # 実データが利用できない場合はシグナルスキップ
            if features is None:
                print("⚠️ サポート・レジスタンスの実データが不足 - シグナル検知をスキップ")
                return None  # シグナルスキップ
            
            if features.empty or len(features) < 10:
                print("⚠️ 十分な特徴量データがありません - シグナル検知をスキップ")
                return None  # シグナルスキップ
            
            # 最新データポイントを使用
            X = features[self.feature_columns].iloc[-1:].fillna(0)
            X_scaled = self.scaler.transform(X)
            
            # アンサンブル予測
            predictions = {}
            for model_name, model in self.models.items():
                if hasattr(model, 'predict_proba'):
                    pred = model.predict_proba(X_scaled)[0, 1]
                else:
                    pred = model.predict(X_scaled)[0]
                predictions[model_name] = pred
            
            # 重み付きアンサンブル
            breakout_prob = np.average(
                list(predictions.values()), 
                weights=[self.ensemble_weights[name] for name in predictions.keys()]
            )
            
            bounce_prob = 1.0 - breakout_prob
            
            # 信頼度計算（予測の一致度に基づく）
            prediction_std = np.std(list(predictions.values()))
            confidence = max(0.1, 1.0 - prediction_std * 2)
            
            # 価格ターゲット計算
            current_price = current_data['close'].iloc[-1]
            if level.level_type == 'resistance':
                target_price = level.price * 1.015  # 1.5%上
            else:
                target_price = level.price * 0.985  # 1.5%下
            
            return BreakoutPrediction(
                level=level,
                breakout_probability=float(breakout_prob),
                bounce_probability=float(bounce_prob),
                prediction_confidence=float(confidence),
                predicted_price_target=float(target_price),
                time_horizon_minutes=30,  # 30分予測
                model_name=f"EnhancedEnsemble_AUC{self.accuracy_metrics.get('ensemble_auc', 0.5):.2f}"
            )
            
        except Exception as e:
            print(f"❌ 予測エラー: {e}")
            return self._create_default_prediction(level)
    
    def _create_training_data(self, features: pd.DataFrame, levels: List[SupportResistanceLevel]) -> Tuple[pd.DataFrame, pd.Series]:
        """
        改善されたラベル作成ロジック
        
        改善点:
        - 距離閾値を2%から1%に変更
        - 連続的相互作用の除去
        - より厳密なブレイクアウト判定
        """
        
        interactions = []
        
        for level in levels:
            level_price = level.price
            
            # 価格がレベルに接近した時点を検出（距離閾値1%）
            distance_threshold = 0.01  # 2%から1%に改善
            
            if level.level_type == 'resistance':
                near_level = features['close'] >= level_price * (1 - distance_threshold)
            else:  # support
                near_level = features['close'] <= level_price * (1 + distance_threshold)
            
            near_indices = features[near_level].index
            
            # インデックスが数値型でない場合は数値インデックスに変換
            if len(near_indices) > 0 and not isinstance(near_indices[0], (int, float)):
                # 元のDataFrameの位置インデックスを取得
                near_indices = features.reset_index().index[near_level.values]
            
            if len(near_indices) < 2:
                continue
            
            # 連続する接触を除去（改善点）
            filtered_indices = self._remove_consecutive_touches(near_indices)
            
            for idx in filtered_indices:
                if idx + 10 >= len(features):  # 未来のデータが必要
                    continue
                
                # 10期間後の価格変化を確認
                current_price = features.loc[idx, 'close']
                future_price = features.iloc[idx + 10]['close']
                price_change = (future_price - current_price) / current_price
                
                # より厳密なブレイクアウト判定（改善点）
                if level.level_type == 'resistance':
                    # 上抜けの場合：1.5%以上の上昇をブレイクアウトとする
                    breakout = price_change > 0.015
                else:  # support
                    # 下抜けの場合：1.5%以上の下落をブレイクアウトとする
                    breakout = price_change < -0.015
                
                interactions.append({
                    'index': idx,
                    'breakout': breakout,
                    'price_change': price_change,
                    'level_type': level.level_type,
                    'level_strength': level.strength
                })
        
        if not interactions:
            print("⚠️ レベル相互作用が検出されませんでした")
            return pd.DataFrame(), pd.Series()
        
        # 特徴量とラベルを結合
        interaction_df = pd.DataFrame(interactions)
        indices = interaction_df['index'].values
        
        X = features.iloc[indices][self._get_feature_columns(features)]
        y = interaction_df['breakout'].astype(int)
        
        print(f"📊 作成されたラベル: 総数{len(y)}, ブレイクアウト{y.sum()}件 ({y.mean():.2%})")
        
        return X, y
    
    def _remove_consecutive_touches(self, indices: pd.Index) -> List[int]:
        """連続する接触を除去"""
        if len(indices) <= 1:
            return list(indices)
        
        # インデックスを整数に変換
        indices_list = indices.tolist()
        filtered = [indices_list[0]]
        
        for i in range(1, len(indices_list)):
            # 型安全な比較
            current_idx = indices_list[i]
            last_idx = filtered[-1]
            
            # 両方とも数値型かどうかチェック
            if isinstance(current_idx, (int, float)) and isinstance(last_idx, (int, float)):
                if current_idx - last_idx > 5:  # 5期間以上離れている場合のみ採用
                    filtered.append(current_idx)
            else:
                # 数値でない場合はそのまま追加（安全側に倒す）
                filtered.append(current_idx)
        
        return filtered
    
    def _get_feature_columns(self, features: pd.DataFrame) -> List[str]:
        """予測に使用する特徴量カラムを取得"""
        exclude_cols = ['timestamp', 'trades']
        return [col for col in features.columns if col not in exclude_cols]
    
    def _cross_validate(self, model, X, y, n_splits=5):
        """時系列クロスバリデーション"""
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model.fit(X_train, y_train)
            y_pred = model.predict_proba(X_val)[:, 1]
            score = roc_auc_score(y_val, y_pred)
            scores.append(score)
        
        return np.mean(scores)
    
    def _calculate_ensemble_weights(self, cv_scores: Dict[str, float]) -> Dict[str, float]:
        """CV結果に基づく動的重み計算"""
        # 性能に基づく重み付け
        total_score = sum(cv_scores.values())
        weights = {name: score / total_score for name, score in cv_scores.items()}
        
        # 重みの正規化
        total_weight = sum(weights.values())
        weights = {name: weight / total_weight for name, weight in weights.items()}
        
        return weights
    
    def _create_default_prediction(self, level: SupportResistanceLevel) -> BreakoutPrediction:
        """デフォルト予測を作成"""
        return BreakoutPrediction(
            level=level,
            breakout_probability=0.5,
            bounce_probability=0.5,
            prediction_confidence=0.3,
            predicted_price_target=None,
            time_horizon_minutes=30,
            model_name="EnhancedEnsemble_Default"
        )
    
    # ヘルパー関数
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
    
    def _calculate_bollinger_bands(self, prices: pd.Series, window: int = 20, std_dev: float = 2) -> Dict:
        """ボリンジャーバンド計算"""
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower
        }
    
    def _calculate_trend_strength(self, prices: pd.Series, window: int = 20) -> pd.Series:
        """トレンド強度計算"""
        returns = prices.pct_change()
        trend_strength = returns.rolling(window=window).apply(
            lambda x: np.sum(np.sign(x) == np.sign(x).iloc[-1]) / len(x)
        )
        return trend_strength
    
    def get_model_accuracy(self) -> Dict[str, float]:
        """モデル精度を取得"""
        return self.accuracy_metrics
    
    def save_model(self, filepath: str) -> bool:
        """モデル保存"""
        try:
            model_data = {
                'models': self.models,
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'ensemble_weights': self.ensemble_weights,
                'accuracy_metrics': self.accuracy_metrics,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, filepath)
            print(f"✅ モデル保存完了: {filepath}")
            return True
        except Exception as e:
            print(f"❌ モデル保存エラー: {e}")
            return False
    
    def load_model(self, filepath: str) -> bool:
        """モデル読み込み"""
        try:
            model_data = joblib.load(filepath)
            self.models = model_data['models']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.ensemble_weights = model_data['ensemble_weights']
            self.accuracy_metrics = model_data['accuracy_metrics']
            self.is_trained = model_data['is_trained']
            print(f"✅ モデル読み込み完了: {filepath}")
            return True
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {e}")
            return False

# テスト実行
if __name__ == "__main__":
    print("🧪 Enhanced ML Predictor テスト")
    
    # サンプルデータでテスト
    sample_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=1000, freq='H'),
        'close': np.random.randn(1000).cumsum() + 100,
        'high': np.random.randn(1000).cumsum() + 105,
        'low': np.random.randn(1000).cumsum() + 95,
        'volume': np.random.uniform(1000, 10000, 1000)
    })
    
    # サンプルレベル
    from interfaces import SupportResistanceLevel
    sample_level = SupportResistanceLevel(
        price=100.0,
        strength=0.8,
        touch_count=3,
        level_type='resistance',
        first_touch=datetime.now(),
        last_touch=datetime.now(),
        volume_at_level=5000.0,
        distance_from_current=0.02
    )
    
    predictor = EnhancedMLPredictor()
    
    # 特徴量生成テスト
    features = predictor.create_enhanced_features(sample_data, [sample_level])
    print(f"✅ 特徴量生成テスト: {len(features.columns)}個の特徴量")
    
    print("🎉 Enhanced ML Predictor実装完了!")