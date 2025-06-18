"""
サポート・レジスタンス反発/ブレイクアウト予測モデル

機械学習による判定:
1. 抵抗線に到達時 → 反発して支持線へ戻る or 上抜ける
2. 支持線に到達時 → 反発して抵抗線へ戻る or 下抜ける

特徴量:
- レベルの強度（タッチ回数、反発履歴）
- 価格の接近速度・角度
- 出来高の変化
- モメンタム指標
- 市場のトレンド状態
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.ensemble import RandomForestClassifier
import lightgbm as lgb
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("XGBoostがインストールされていません。LightGBMとRandomForestのみ使用します。")
import joblib
import argparse
import warnings
warnings.filterwarnings('ignore')

# サポレジ検出機能をインポート
from support_resistance_visualizer import find_all_levels

def detect_level_interactions(df, levels, distance_threshold=0.02):
    """
    価格がサポート・レジスタンスレベルと相互作用した履歴を検出
    
    Returns:
        interactions: レベルとの相互作用リスト
        - timestamp: 発生時刻
        - level_price: レベル価格
        - level_type: 'support' or 'resistance'
        - outcome: 'bounce' or 'breakout'
        - strength: レベルの強度
    """
    print(f"レベルとの相互作用を検出中... (レベル数: {len(levels)})")
    interactions = []
    
    for level_idx, level in enumerate(levels):
        if level_idx % 10 == 0:
            print(f"  処理中: {level_idx + 1}/{len(levels)} レベル...")
            
            # キャンセル確認（10レベル毎にチェック）
            try:
                import sqlite3
                import os
                execution_db_path = "execution_logs.db"
                if os.path.exists(execution_db_path):
                    with sqlite3.connect(execution_db_path) as conn:
                        cursor = conn.execute('''
                            SELECT status FROM execution_logs 
                            WHERE status = 'CANCELLED' AND timestamp_end IS NULL
                            LIMIT 1
                        ''')
                        if cursor.fetchone():
                            print("キャンセルが検出されました。レベル相互作用検出を停止します。")
                            return []
            except Exception:
                pass  # キャンセル確認に失敗してもメイン処理は継続
        level_price = level['price']
        level_type = level['type']
        
        # 価格がレベルに接近したポイントを検出
        for i in range(10, len(df) - 10):  # 前後10本のバーを確認できる範囲
            current_price = df.iloc[i]['close']
            
            # レベルとの距離を計算
            distance_pct = abs(current_price - level_price) / level_price
            
            if distance_pct <= distance_threshold:
                # レベルに接近した
                
                # 次の10本のバーで何が起きたか確認
                future_prices = df.iloc[i+1:i+11]['close'].values
                future_highs = df.iloc[i+1:i+11]['high'].values
                future_lows = df.iloc[i+1:i+11]['low'].values
                
                if level_type == 'resistance':
                    # 抵抗線の場合
                    if max(future_highs) > level_price * 1.02:  # 2%以上上抜け
                        outcome = 'breakout'
                    else:
                        # 反発して下落したか確認
                        if min(future_lows) < current_price * 0.98:  # 2%以上下落
                            outcome = 'bounce'
                        else:
                            continue  # 明確な動きなし
                else:
                    # 支持線の場合
                    if min(future_lows) < level_price * 0.98:  # 2%以上下抜け
                        outcome = 'breakout'
                    else:
                        # 反発して上昇したか確認
                        if max(future_highs) > current_price * 1.02:  # 2%以上上昇
                            outcome = 'bounce'
                        else:
                            continue  # 明確な動きなし
                
                # 相互作用を記録
                interactions.append({
                    'timestamp': df.iloc[i]['timestamp'],
                    'index': i,
                    'level_price': level_price,
                    'level_type': level_type,
                    'outcome': outcome,
                    'level_strength': level['strength'],
                    'level_touch_count': level['touch_count'],
                    'level_avg_bounce': level['avg_bounce'],
                    'level_avg_volume_spike': level.get('avg_volume_spike', 1.0),
                    'level_max_volume_spike': level.get('max_volume_spike', 1.0)
                })
    
    return interactions

def calculate_approach_features(df, idx, level_price, level_type, lookback=20):
    """
    レベルへの接近時の特徴量を計算
    """
    features = {}
    
    # 基本情報
    current_price = df.iloc[idx]['close']
    features['distance_to_level'] = abs(current_price - level_price) / level_price
    features['is_above_level'] = 1 if current_price > level_price else 0
    
    # 価格の接近速度（モメンタム）
    if idx >= lookback:
        past_prices = df.iloc[idx-lookback:idx]['close'].values
        
        # 線形回帰で傾きを計算
        x = np.arange(lookback)
        slope = np.polyfit(x, past_prices, 1)[0]
        features['approach_slope'] = slope / current_price  # 正規化
        
        # 加速度（2次微分）
        if len(past_prices) >= 3:
            velocity = np.diff(past_prices)
            acceleration = np.diff(velocity)
            features['approach_acceleration'] = np.mean(acceleration[-5:]) / current_price if len(acceleration) >= 5 else 0
        else:
            features['approach_acceleration'] = 0
    else:
        features['approach_slope'] = 0
        features['approach_acceleration'] = 0
    
    # ボラティリティ
    features['volatility'] = df.iloc[max(0, idx-20):idx]['close'].std() / current_price if idx > 0 else 0
    
    # 出来高の変化
    if idx >= 10:
        recent_volume = df.iloc[idx-5:idx]['volume'].mean()
        past_volume = df.iloc[idx-10:idx-5]['volume'].mean()
        features['volume_ratio'] = recent_volume / past_volume if past_volume > 0 else 1
    else:
        features['volume_ratio'] = 1
    
    # RSI
    features['rsi'] = df.iloc[idx]['rsi_14'] if 'rsi_14' in df.columns else 50
    
    # MACD
    if 'macd' in df.columns:
        features['macd'] = df.iloc[idx]['macd']
        features['macd_signal'] = df.iloc[idx]['macd_signal'] if 'macd_signal' in df.columns else 0
        features['macd_histogram'] = df.iloc[idx]['macd_hist'] if 'macd_hist' in df.columns else 0
    else:
        features['macd'] = 0
        features['macd_signal'] = 0
        features['macd_histogram'] = 0
    
    # ボリンジャーバンドの位置
    if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
        bb_width = df.iloc[idx]['bb_upper'] - df.iloc[idx]['bb_lower']
        bb_position = (current_price - df.iloc[idx]['bb_lower']) / bb_width if bb_width > 0 else 0.5
        features['bb_position'] = bb_position
    else:
        features['bb_position'] = 0.5
    
    # トレンド強度（移動平均との乖離）
    if 'sma_20' in df.columns:
        features['ma_distance'] = (current_price - df.iloc[idx]['sma_20']) / current_price
    else:
        features['ma_distance'] = 0
    
    # 最近の高値・安値からの距離
    if idx >= 20:
        recent_high = df.iloc[idx-20:idx]['high'].max()
        recent_low = df.iloc[idx-20:idx]['low'].min()
        features['distance_from_high'] = (recent_high - current_price) / current_price
        features['distance_from_low'] = (current_price - recent_low) / current_price
    else:
        features['distance_from_high'] = 0
        features['distance_from_low'] = 0
    
    return features

def prepare_training_data(df, levels, interactions):
    """
    機械学習用のトレーニングデータを準備
    """
    print(f"トレーニングデータ準備中... (相互作用数: {len(interactions)})")
    X = []
    y = []
    
    for i, interaction in enumerate(interactions):
        if i % 50 == 0:
            print(f"  特徴量計算中: {i + 1}/{len(interactions)}...")
        idx = interaction['index']
        
        # レベル関連の特徴量
        level_features = {
            'level_strength': interaction['level_strength'],
            'level_touch_count': interaction['level_touch_count'],
            'level_avg_bounce': interaction['level_avg_bounce'],
            'level_avg_volume_spike': interaction.get('level_avg_volume_spike', 1.0),
            'level_max_volume_spike': interaction.get('level_max_volume_spike', 1.0),
            'level_type_resistance': 1 if interaction['level_type'] == 'resistance' else 0
        }
        
        # 接近時の市場状態特徴量
        approach_features = calculate_approach_features(
            df, idx, interaction['level_price'], interaction['level_type']
        )
        
        # すべての特徴量を結合
        features = {**level_features, **approach_features}
        
        X.append(features)
        y.append(1 if interaction['outcome'] == 'breakout' else 0)  # 1: ブレイクアウト, 0: 反発
    
    # DataFrameに変換
    X_df = pd.DataFrame(X)
    y_series = pd.Series(y)
    
    return X_df, y_series

def train_models(X, y):
    """
    複数のモデルを訓練
    """
    # データ分割（時系列を考慮）
    tscv = TimeSeriesSplit(n_splits=5)
    
    # スケーリング
    scaler = StandardScaler()
    
    # モデル定義
    models = {
        'RandomForest': RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            random_state=42
        ),
        'LightGBM': lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            verbosity=-1
        )
    }
    
    if HAS_XGBOOST:
        models['XGBoost'] = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
    
    results = {}
    
    for model_name, model in models.items():
        print(f"\n訓練中: {model_name}")
        
        # クロスバリデーション結果
        cv_scores = []
        cv_accuracies = []
        cv_predictions = []
        cv_probabilities = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            print(f"    Fold {fold + 1}/5 を訓練中...")
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            # スケーリング
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
            
            # 訓練
            model.fit(X_train_scaled, y_train)
            
            # 予測
            y_pred = model.predict(X_val_scaled)
            y_proba = model.predict_proba(X_val_scaled)[:, 1]
            
            # スコア計算
            auc_score = roc_auc_score(y_val, y_proba)
            accuracy = (y_pred == y_val).mean()
            cv_scores.append(auc_score)
            cv_accuracies.append(accuracy)
            
            print(f"    Fold {fold + 1} AUC: {auc_score:.4f}, 精度: {accuracy:.4f}")
        
        # 全データで再訓練
        print(f"  全データで再訓練中...")
        X_scaled = scaler.fit_transform(X)
        model.fit(X_scaled, y)
        
        mean_accuracy = np.mean(cv_accuracies)
        mean_auc = np.mean(cv_scores)
        
        results[model_name] = {
            'model': model,
            'scaler': scaler,
            'cv_scores': cv_scores,
            'cv_accuracies': cv_accuracies,
            'mean_cv_score': mean_auc,
            'mean_cv_accuracy': mean_accuracy,
            'feature_importance': None
        }
        
        print(f"  平均精度: {mean_accuracy:.4f}, 平均AUC: {mean_auc:.4f}")
        
        # 特徴量重要度
        if hasattr(model, 'feature_importances_'):
            results[model_name]['feature_importance'] = pd.DataFrame({
                'feature': X.columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
    
    return results

def visualize_results(df, levels, interactions, model_results):
    """
    予測結果の可視化
    """
    print("可視化処理を開始...")
    # 1. モデル性能比較
    print("  1. モデル性能比較グラフを作成中...")
    plt.figure(figsize=(10, 6))
    
    model_names = list(model_results.keys())
    mean_scores = [model_results[name]['mean_cv_score'] for name in model_names]
    
    plt.bar(model_names, mean_scores)
    plt.title('Model Performance Comparison (AUC Score)', fontsize=14)
    plt.ylabel('Mean CV AUC Score', fontsize=12)
    plt.ylim(0, 1)
    
    for i, score in enumerate(mean_scores):
        plt.text(i, score + 0.02, f'{score:.3f}', ha='center')
    
    plt.tight_layout()
    plt.savefig('model_performance_comparison.png')
    plt.close()
    print("  → model_performance_comparison.png を保存")
    
    # 2. 特徴量重要度（最良モデル）
    best_model_name = max(model_results.keys(), key=lambda x: model_results[x]['mean_cv_score'])
    best_model_results = model_results[best_model_name]
    
    if best_model_results['feature_importance'] is not None:
        plt.figure(figsize=(10, 8))
        
        importance_df = best_model_results['feature_importance'].head(15)
        
        plt.barh(importance_df['feature'], importance_df['importance'])
        plt.xlabel('Importance', fontsize=12)
        plt.title(f'Top 15 Feature Importances ({best_model_name})', fontsize=14)
        plt.gca().invert_yaxis()
        
        plt.tight_layout()
        plt.savefig('feature_importance.png')
        plt.close()
        print("  → feature_importance.png を保存")
    
    # 3. 予測結果のサンプル表示
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
    
    # 抵抗線での予測
    resistance_interactions = [i for i in interactions if i['level_type'] == 'resistance'][:20]
    plot_predictions(ax1, df, resistance_interactions, 'Resistance Level Predictions')
    
    # 支持線での予測
    support_interactions = [i for i in interactions if i['level_type'] == 'support'][:20]
    plot_predictions(ax2, df, support_interactions, 'Support Level Predictions')
    
    plt.tight_layout()
    plt.savefig('prediction_examples.png')
    plt.close()
    print("  → prediction_examples.png を保存")

def plot_predictions(ax, df, interactions, title):
    """
    予測結果をプロット
    """
    if not interactions:
        return
    
    # 価格データの範囲を決定
    indices = [i['index'] for i in interactions]
    min_idx = max(0, min(indices) - 50)
    max_idx = min(len(df), max(indices) + 50)
    
    # 価格チャート
    ax.plot(df.iloc[min_idx:max_idx].index, 
           df.iloc[min_idx:max_idx]['close'], 
           'k-', linewidth=1, alpha=0.7)
    
    # 相互作用ポイントをマーク
    for interaction in interactions:
        idx = interaction['index']
        color = 'red' if interaction['outcome'] == 'breakout' else 'green'
        marker = '^' if interaction['outcome'] == 'breakout' else 'v'
        
        ax.scatter(idx, df.iloc[idx]['close'], 
                  color=color, marker=marker, s=100, 
                  edgecolor='black', linewidth=1, zorder=5)
        
        # レベルライン
        level_price = interaction['level_price']
        ax.axhline(y=level_price, xmin=(idx-min_idx-20)/(max_idx-min_idx), 
                  xmax=(idx-min_idx+20)/(max_idx-min_idx),
                  color='gray', linestyle='--', alpha=0.5)
    
    ax.set_title(title, fontsize=14)
    ax.set_xlabel('Index', fontsize=12)
    ax.set_ylabel('Price', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    # 凡例
    ax.scatter([], [], color='red', marker='^', s=100, label='Breakout')
    ax.scatter([], [], color='green', marker='v', s=100, label='Bounce')
    ax.legend()

def generate_report(interactions, model_results):
    """
    分析レポートの生成
    """
    print("\n" + "="*80)
    print("サポート・レジスタンス反発/ブレイクアウト予測レポート")
    print("="*80)
    
    # 相互作用の統計
    total_interactions = len(interactions)
    resistance_interactions = len([i for i in interactions if i['level_type'] == 'resistance'])
    support_interactions = len([i for i in interactions if i['level_type'] == 'support'])
    
    breakouts = len([i for i in interactions if i['outcome'] == 'breakout'])
    bounces = len([i for i in interactions if i['outcome'] == 'bounce'])
    
    print(f"\n【検出された相互作用】")
    print(f"総数: {total_interactions}")
    print(f"- 抵抗線: {resistance_interactions}")
    print(f"- 支持線: {support_interactions}")
    print(f"\n結果分布:")
    print(f"- ブレイクアウト: {breakouts} ({breakouts/total_interactions*100:.1f}%)")
    print(f"- 反発: {bounces} ({bounces/total_interactions*100:.1f}%)")
    
    # レベルタイプ別の統計
    print(f"\n【レベルタイプ別統計】")
    
    resistance_breakouts = len([i for i in interactions if i['level_type'] == 'resistance' and i['outcome'] == 'breakout'])
    support_breakouts = len([i for i in interactions if i['level_type'] == 'support' and i['outcome'] == 'breakout'])
    
    print(f"抵抗線:")
    print(f"  - ブレイクアウト率: {resistance_breakouts/resistance_interactions*100:.1f}%")
    print(f"支持線:")
    print(f"  - ブレイクアウト率: {support_breakouts/support_interactions*100:.1f}%")
    
    # モデル性能
    print(f"\n【モデル性能】")
    for model_name, results in model_results.items():
        print(f"\n{model_name}:")
        print(f"  平均精度: {results['mean_cv_accuracy']:.4f}")
        print(f"  平均AUCスコア: {results['mean_cv_score']:.4f}")
        print(f"  CV標準偏差: {np.std(results['cv_scores']):.4f}")
    
    # 最重要特徴量
    best_model_name = max(model_results.keys(), key=lambda x: model_results[x]['mean_cv_accuracy'])
    best_model_results = model_results[best_model_name]
    
    # 精度の明示的出力（real_market_integration_fixed.pyで検索される）
    best_accuracy = best_model_results['mean_cv_accuracy']
    print(f"\n精度: {best_accuracy:.3f}")
    
    if best_model_results['feature_importance'] is not None:
        print(f"\n【最重要特徴量 TOP5 ({best_model_name})】")
        for _, row in best_model_results['feature_importance'].head(5).iterrows():
            print(f"- {row['feature']}: {row['importance']:.4f}")

def main():
    parser = argparse.ArgumentParser(description='サポート・レジスタンス反発/ブレイクアウト予測')
    parser.add_argument('--symbol', type=str, default='HYPE', help='通貨シンボル')
    parser.add_argument('--timeframe', type=str, default='15m', help='時間足')
    parser.add_argument('--min-touches', type=int, default=3, help='レベルの最小タッチ回数')
    args = parser.parse_args()
    
    # データ読み込み
    try:
        config = {
            '15m': {'days': 60},
            '1h': {'days': 90}
        }
        days = config.get(args.timeframe, {'days': 60})['days']
        
        filename = f"{args.symbol.lower()}_{args.timeframe}_{days}days_with_indicators.csv"
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        print(f"データ読み込み完了: {len(df)}行")
        
    except FileNotFoundError:
        print(f"エラー: {filename} が見つかりません")
        print("先にohlcv_by_claude.pyを実行してください")
        return
    
    # 1. サポート・レジスタンスレベルの検出
    print("\nサポート・レジスタンスレベルを検出中...")
    print(f"パラメータ: min_touches={args.min_touches}")
    levels = find_all_levels(df, min_touches=args.min_touches)
    print(f"検出されたレベル: {len(levels)}個")
    
    # 2. レベルとの相互作用を検出
    print("\nレベルとの相互作用を検出開始...")
    import time
    start_time = time.time()
    interactions = detect_level_interactions(df, levels)
    elapsed = time.time() - start_time
    print(f"検出完了: {len(interactions)}回の相互作用 (処理時間: {elapsed:.1f}秒)")
    
    if len(interactions) < 50:
        print("警告: 相互作用データが少なすぎます（50回未満）")
        print("より長い期間のデータを使用するか、min-touchesを下げてください")
        return
    
    # 3. トレーニングデータの準備
    print("\nトレーニングデータを準備中...")
    X, y = prepare_training_data(df, levels, interactions)
    print(f"特徴量数: {X.shape[1]}")
    print(f"サンプル数: {X.shape[0]}")
    
    # 4. モデルの訓練
    print("\nモデルを訓練中...")
    model_results = train_models(X, y)
    
    # 5. 結果の可視化
    print("\n結果を可視化中...")
    visualize_results(df, levels, interactions, model_results)
    
    # 6. レポート生成
    generate_report(interactions, model_results)
    
    # 7. 最良モデルの保存
    best_model_name = max(model_results.keys(), key=lambda x: model_results[x]['mean_cv_score'])
    best_model = model_results[best_model_name]['model']
    best_scaler = model_results[best_model_name]['scaler']
    
    model_filename = f"{args.symbol.lower()}_{args.timeframe}_sr_breakout_model.pkl"
    scaler_filename = f"{args.symbol.lower()}_{args.timeframe}_sr_breakout_scaler.pkl"
    
    joblib.dump(best_model, model_filename)
    joblib.dump(best_scaler, scaler_filename)
    
    print(f"\n✓ モデルを保存: {model_filename}")
    print(f"✓ スケーラーを保存: {scaler_filename}")
    
    # 相互作用データも保存
    interactions_df = pd.DataFrame(interactions)
    interactions_df.to_csv(f"{args.symbol.lower()}_{args.timeframe}_sr_interactions.csv", index=False)
    print(f"✓ 相互作用データを保存: {args.symbol.lower()}_{args.timeframe}_sr_interactions.csv")
    
    # 8. サポート・レジスタンスチャートの生成（ML予測結果付き）
    print("\nサポート・レジスタンスチャートを生成中...")
    visualize_sr_with_ml_predictions(df, levels, interactions, best_model, best_scaler, X.columns, args.symbol, args.timeframe)
    print(f"✓ チャートを保存: {args.symbol.lower()}_{args.timeframe}_ml_support_resistance_analysis.png")

def visualize_sr_with_ml_predictions(df, levels, interactions, model, scaler, feature_columns, symbol, timeframe):
    """
    ML予測結果を含むサポート・レジスタンスチャートを生成
    """
    plt.figure(figsize=(18, 12))
    
    # 現在価格
    current_price = df['close'].iloc[-1]
    
    # サブプロット1: 価格チャートとサポレジ（ML予測付き）
    ax1 = plt.subplot(2, 1, 1)
    
    # 価格チャート
    ax1.plot(df.index, df['close'], label='Close Price', 
             color='black', linewidth=1.5, alpha=0.8)
    
    # 現在価格ライン
    ax1.axhline(y=current_price, color='blue', linestyle='-', 
                linewidth=2, alpha=0.8, label=f'Current: ${current_price:.3f}')
    
    # レベルごとのブレイクアウト確率を計算
    level_predictions = {}
    for level in levels:
        # このレベルでの過去の相互作用を取得
        level_interactions = [i for i in interactions if abs(i['level_price'] - level['price']) / level['price'] < 0.001]
        
        if level_interactions:
            # ブレイクアウト率を計算
            breakout_count = sum(1 for i in level_interactions if i['outcome'] == 'breakout')
            breakout_rate = breakout_count / len(level_interactions) if level_interactions else 0
            
            # 最新の特徴量でML予測
            latest_features = calculate_approach_features(df, len(df)-1, level['price'], level['type'])
            level_features = {
                'level_strength': level['strength'],
                'level_touch_count': level['touch_count'],
                'level_avg_bounce': level['avg_bounce'],
                'level_avg_volume_spike': level.get('avg_volume_spike', 1.0),
                'level_max_volume_spike': level.get('max_volume_spike', 1.0),
                'level_type_resistance': 1 if level['type'] == 'resistance' else 0
            }
            all_features = {**level_features, **latest_features}
            
            # DataFrameに変換して予測
            X_pred = pd.DataFrame([all_features])[feature_columns]
            X_pred_scaled = scaler.transform(X_pred)
            ml_breakout_prob = model.predict_proba(X_pred_scaled)[0, 1]
            
            level_predictions[level['price']] = {
                'historical_rate': breakout_rate,
                'ml_probability': ml_breakout_prob,
                'interaction_count': len(level_interactions)
            }
    
    # サポート・レジスタンスラインを描画（ML予測に基づく色分け）
    max_strength = max([level['strength'] for level in levels]) if levels else 1
    
    for level in levels:
        # 強度に応じた線の太さ
        normalized_strength = level['strength'] / max_strength
        linewidth = 1 + normalized_strength * 3
        
        # ML予測に基づく色設定
        if level['price'] in level_predictions:
            ml_prob = level_predictions[level['price']]['ml_probability']
            # ブレイクアウト確率が高い：赤系、低い：緑系
            if level['type'] == 'resistance':
                color = plt.cm.Reds(0.3 + ml_prob * 0.7)
            else:
                color = plt.cm.Greens(0.3 + (1 - ml_prob) * 0.7)
            alpha = 0.4 + ml_prob * 0.4
        else:
            color = 'red' if level['type'] == 'resistance' else 'green'
            alpha = 0.6
        
        # 価格ライン
        ax1.axhline(y=level['price'], color=color, linestyle='-', 
                   linewidth=linewidth, alpha=alpha)
        
        # 重要なレベル（上位15）に詳細ラベル追加
        if levels.index(level) < 15 and level['price'] in level_predictions:
            pred = level_predictions[level['price']]
            distance_pct = ((level['price'] - current_price) / current_price) * 100
            
            label_text = f"${level['price']:.2f} ({distance_pct:+.1f}%)\n"
            label_text += f"ML: {pred['ml_probability']:.1%} | Hist: {pred['historical_rate']:.1%}\n"
            label_text += f"T:{level['touch_count']} S:{level['strength']:.0f}"
            
            # ラベル位置
            x_pos = len(df) - len(df)//15
            
            # 背景色をML予測に基づいて設定
            if pred['ml_probability'] > 0.7:
                bg_color = 'lightcoral'
            elif pred['ml_probability'] < 0.3:
                bg_color = 'lightgreen'
            else:
                bg_color = 'lightyellow'
            
            ax1.text(x_pos, level['price'], label_text,
                    fontsize=9, ha='left', va='center',
                    bbox=dict(boxstyle='round,pad=0.4', 
                             facecolor=bg_color, 
                             edgecolor='black',
                             alpha=0.9))
    
    # 過去の相互作用ポイントをプロット
    for interaction in interactions[-100:]:  # 最新100個のみ
        idx = interaction['index']
        if idx < len(df):
            color = 'red' if interaction['outcome'] == 'breakout' else 'green'
            marker = 'x' if interaction['outcome'] == 'breakout' else 'o'
            ax1.scatter(idx, df.iloc[idx]['close'], 
                       color=color, marker=marker, s=30, 
                       alpha=0.6, zorder=5)
    
    ax1.set_title(f'{symbol} ML-Enhanced Support/Resistance Analysis ({timeframe})', 
                  fontsize=16, pad=20)
    ax1.set_xlabel('Index', fontsize=12)
    ax1.set_ylabel('Price (USD)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=10)
    
    # サブプロット2: ブレイクアウト確率ヒートマップ
    ax2 = plt.subplot(2, 1, 2)
    
    # 現在価格付近のレベルのみ表示
    price_range = current_price * 0.1  # 現在価格の±10%
    nearby_levels = [l for l in levels if abs(l['price'] - current_price) <= price_range]
    
    if nearby_levels and level_predictions:
        # データ準備
        level_prices = []
        ml_probs = []
        hist_rates = []
        level_types = []
        
        for level in sorted(nearby_levels, key=lambda x: x['price'], reverse=True):
            if level['price'] in level_predictions:
                pred = level_predictions[level['price']]
                level_prices.append(f"${level['price']:.2f}")
                ml_probs.append(pred['ml_probability'])
                hist_rates.append(pred['historical_rate'])
                level_types.append('R' if level['type'] == 'resistance' else 'S')
        
        # ヒートマップデータ
        data = np.array([ml_probs, hist_rates]).T
        
        # ヒートマップ作成
        im = ax2.imshow(data, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=1)
        
        # 軸設定
        ax2.set_yticks(range(len(level_prices)))
        ax2.set_yticklabels([f"{price} ({t})" for price, t in zip(level_prices, level_types)])
        ax2.set_xticks([0, 1])
        ax2.set_xticklabels(['ML Prediction', 'Historical Rate'])
        
        # 値を表示
        for i in range(len(level_prices)):
            for j in range(2):
                text = ax2.text(j, i, f'{data[i, j]:.1%}',
                               ha="center", va="center", color="black", fontsize=10)
        
        # カラーバー
        cbar = plt.colorbar(im, ax=ax2)
        cbar.set_label('Breakout Probability', rotation=270, labelpad=20)
        
        ax2.set_title('Breakout Probability Analysis (Current Price ± 10%)', fontsize=14, pad=10)
    
    plt.tight_layout()
    
    # 保存
    output_filename = f"{symbol.lower()}_{timeframe}_ml_support_resistance_analysis.png"
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    main()