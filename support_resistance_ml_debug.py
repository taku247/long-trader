"""
サポート・レジスタンス反発/ブレイクアウト予測モデル (デバッグ版)

デバッグ機能:
1. 詳細なログ出力
2. データ品質検証
3. モデル精度の詳細計算
4. 分割統計の可視化
5. 予測確率の分布分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (classification_report, confusion_matrix, roc_auc_score, 
                           accuracy_score, precision_score, recall_score, f1_score)
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
import logging
warnings.filterwarnings('ignore')

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# サポレジ検出機能をインポート
from support_resistance_visualizer import find_all_levels

def validate_data_quality(df, interactions):
    """データ品質を詳細に検証"""
    logger.info("=== データ品質検証開始 ===")
    
    quality_report = {
        'data_completeness': {},
        'interaction_analysis': {},
        'feature_statistics': {},
        'issues': []
    }
    
    # 1. データ完全性チェック
    total_cells = len(df) * len(df.columns)
    missing_cells = df.isnull().sum().sum()
    completeness = 1 - (missing_cells / total_cells)
    
    quality_report['data_completeness'] = {
        'total_records': len(df),
        'total_features': len(df.columns),
        'missing_values': int(missing_cells),
        'completeness_rate': completeness
    }
    
    logger.info(f"データ完全性: {completeness:.3%} ({len(df)}行, {len(df.columns)}列)")
    
    if completeness < 0.95:
        quality_report['issues'].append(f"データ欠損率が高い: {1-completeness:.1%}")
    
    # 2. 相互作用データ分析
    if interactions:
        outcomes = [i['outcome'] for i in interactions]
        breakout_rate = outcomes.count('breakout') / len(outcomes)
        
        quality_report['interaction_analysis'] = {
            'total_interactions': len(interactions),
            'breakout_count': outcomes.count('breakout'),
            'bounce_count': outcomes.count('bounce'),
            'breakout_rate': breakout_rate
        }
        
        logger.info(f"相互作用分析: {len(interactions)}件, ブレイクアウト率={breakout_rate:.1%}")
        
        # クラス不均衡チェック
        if breakout_rate < 0.1 or breakout_rate > 0.9:
            quality_report['issues'].append(f"クラス不均衡: ブレイクアウト率={breakout_rate:.1%}")
            
    # 3. 特徴量統計
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 0:
        stats = df[numeric_columns].describe()
        
        # 異常値チェック（IQR方式）
        outlier_counts = {}
        for col in numeric_columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))).sum()
            outlier_counts[col] = outliers
            
        quality_report['feature_statistics'] = {
            'numeric_features': len(numeric_columns),
            'outlier_counts': outlier_counts
        }
        
        high_outlier_features = [col for col, count in outlier_counts.items() if count > len(df) * 0.05]
        if high_outlier_features:
            quality_report['issues'].append(f"高異常値特徴量: {high_outlier_features}")
    
    # 結果表示
    logger.info("=== データ品質サマリー ===")
    logger.info(f"✓ データ完全性: {completeness:.1%}")
    logger.info(f"✓ 相互作用データ: {len(interactions)}件")
    if quality_report['issues']:
        logger.warning("⚠️ 検出された問題:")
        for issue in quality_report['issues']:
            logger.warning(f"  - {issue}")
    else:
        logger.info("✓ 重大な品質問題は検出されませんでした")
    
    return quality_report

def detect_level_interactions(df, levels, distance_threshold=0.02):
    """
    価格がサポート・レジスタンスレベルと相互作用した履歴を検出
    """
    logger.info(f"レベルとの相互作用を検出中... (レベル数: {len(levels)})")
    interactions = []
    
    for level_idx, level in enumerate(levels):
        if level_idx % 10 == 0:
            logger.info(f"  処理中: {level_idx + 1}/{len(levels)} レベル...")
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
    
    logger.info(f"相互作用検出完了: {len(interactions)}件")
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
    logger.info(f"トレーニングデータ準備中... (相互作用数: {len(interactions)})")
    X = []
    y = []
    
    for i, interaction in enumerate(interactions):
        if i % 50 == 0:
            logger.info(f"  特徴量計算中: {i + 1}/{len(interactions)}...")
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
    
    logger.info(f"✓ 特徴量データ準備完了: {X_df.shape[0]}サンプル × {X_df.shape[1]}特徴量")
    
    return X_df, y_series

def calculate_detailed_metrics(y_true, y_pred, y_proba):
    """詳細な評価指標を計算"""
    metrics = {}
    
    # 基本的な分類指標
    metrics['accuracy'] = accuracy_score(y_true, y_pred)
    metrics['precision'] = precision_score(y_true, y_pred, zero_division=0)
    metrics['recall'] = recall_score(y_true, y_pred, zero_division=0)
    metrics['f1_score'] = f1_score(y_true, y_pred, zero_division=0)
    metrics['auc_score'] = roc_auc_score(y_true, y_proba) if len(np.unique(y_true)) > 1 else 0.5
    
    # 混同行列
    cm = confusion_matrix(y_true, y_pred)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        metrics['true_negatives'] = int(tn)
        metrics['false_positives'] = int(fp)
        metrics['false_negatives'] = int(fn)
        metrics['true_positives'] = int(tp)
        metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
    
    return metrics

def train_models_with_debug(X, y):
    """
    複数のモデルを訓練（デバッグ情報付き）
    """
    logger.info("=== モデル訓練開始 ===")
    
    # クラス分布確認
    class_counts = y.value_counts()
    logger.info(f"クラス分布: 反発(0)={class_counts.get(0, 0)}, ブレイクアウト(1)={class_counts.get(1, 0)}")
    
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
        logger.info(f"\n--- {model_name} 訓練中 ---")
        
        # クロスバリデーション結果
        cv_metrics = {
            'accuracy': [],
            'precision': [],
            'recall': [],
            'f1_score': [],
            'auc_score': []
        }
        
        all_y_true = []
        all_y_pred = []
        all_y_proba = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            logger.info(f"  Fold {fold + 1}/5 を訓練中...")
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            # フォールド内のクラス分布確認
            train_class_counts = y_train.value_counts()
            val_class_counts = y_val.value_counts()
            logger.info(f"    訓練データ: 反発={train_class_counts.get(0, 0)}, ブレイクアウト={train_class_counts.get(1, 0)}")
            logger.info(f"    検証データ: 反発={val_class_counts.get(0, 0)}, ブレイクアウト={val_class_counts.get(1, 0)}")
            
            # スケーリング
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
            
            # 訓練
            model.fit(X_train_scaled, y_train)
            
            # 予測
            y_pred = model.predict(X_val_scaled)
            y_proba = model.predict_proba(X_val_scaled)[:, 1]
            
            # 詳細指標計算
            fold_metrics = calculate_detailed_metrics(y_val, y_pred, y_proba)
            
            # 結果記録
            for metric_name, value in fold_metrics.items():
                if metric_name in cv_metrics:
                    cv_metrics[metric_name].append(value)
            
            all_y_true.extend(y_val.tolist())
            all_y_pred.extend(y_pred.tolist())
            all_y_proba.extend(y_proba.tolist())
            
            logger.info(f"    Fold {fold + 1} - 精度: {fold_metrics['accuracy']:.4f}, AUC: {fold_metrics['auc_score']:.4f}")
        
        # 全体統計計算
        overall_metrics = calculate_detailed_metrics(all_y_true, all_y_pred, all_y_proba)
        
        # 全データで再訓練
        logger.info(f"  全データで再訓練中...")
        X_scaled = scaler.fit_transform(X)
        model.fit(X_scaled, y)
        
        # 結果保存
        results[model_name] = {
            'model': model,
            'scaler': scaler,
            'cv_metrics': cv_metrics,
            'overall_metrics': overall_metrics,
            'mean_cv_accuracy': np.mean(cv_metrics['accuracy']),
            'mean_cv_auc': np.mean(cv_metrics['auc_score']),
            'feature_importance': None
        }
        
        # 特徴量重要度
        if hasattr(model, 'feature_importances_'):
            results[model_name]['feature_importance'] = pd.DataFrame({
                'feature': X.columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
        
        # 結果表示
        logger.info(f"  ✓ {model_name} 完了:")
        logger.info(f"    平均精度: {results[model_name]['mean_cv_accuracy']:.4f}")
        logger.info(f"    平均AUC: {results[model_name]['mean_cv_auc']:.4f}")
        logger.info(f"    全体精度: {overall_metrics['accuracy']:.4f}")
        logger.info(f"    全体AUC: {overall_metrics['auc_score']:.4f}")
    
    return results

def visualize_debug_results(df, levels, interactions, model_results, symbol, timeframe):
    """
    デバッグ結果の可視化
    """
    logger.info("=== デバッグ結果可視化開始 ===")
    
    # 1. モデル性能比較（精度とAUC両方）
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    model_names = list(model_results.keys())
    accuracies = [model_results[name]['mean_cv_accuracy'] for name in model_names]
    aucs = [model_results[name]['mean_cv_auc'] for name in model_names]
    
    # 精度比較
    bars1 = ax1.bar(model_names, accuracies, alpha=0.7, color='skyblue')
    ax1.set_title('Model Accuracy Comparison', fontsize=14)
    ax1.set_ylabel('Mean CV Accuracy', fontsize=12)
    ax1.set_ylim(0, 1)
    
    for i, acc in enumerate(accuracies):
        ax1.text(i, acc + 0.02, f'{acc:.3f}', ha='center', fontweight='bold')
    
    # AUC比較
    bars2 = ax2.bar(model_names, aucs, alpha=0.7, color='lightcoral')
    ax2.set_title('Model AUC Comparison', fontsize=14)
    ax2.set_ylabel('Mean CV AUC Score', fontsize=12)
    ax2.set_ylim(0, 1)
    
    for i, auc in enumerate(aucs):
        ax2.text(i, auc + 0.02, f'{auc:.3f}', ha='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{symbol.lower()}_{timeframe}_debug_model_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    logger.info("  ✓ モデル比較チャート保存完了")
    
    # 2. クラス分布分析
    plt.figure(figsize=(12, 8))
    
    # サブプロット1: 全体のクラス分布
    plt.subplot(2, 2, 1)
    outcomes = [i['outcome'] for i in interactions]
    outcome_counts = pd.Series(outcomes).value_counts()
    plt.pie(outcome_counts.values, labels=outcome_counts.index, autopct='%1.1f%%')
    plt.title('Overall Outcome Distribution')
    
    # サブプロット2: レベルタイプ別分布
    plt.subplot(2, 2, 2)
    resistance_outcomes = [i['outcome'] for i in interactions if i['level_type'] == 'resistance']
    support_outcomes = [i['outcome'] for i in interactions if i['level_type'] == 'support']
    
    level_data = {
        'Resistance Breakout': resistance_outcomes.count('breakout'),
        'Resistance Bounce': resistance_outcomes.count('bounce'),
        'Support Breakout': support_outcomes.count('breakout'),
        'Support Bounce': support_outcomes.count('bounce')
    }
    
    plt.bar(level_data.keys(), level_data.values())
    plt.title('Outcomes by Level Type')
    plt.xticks(rotation=45)
    
    # サブプロット3: 時系列でのブレイクアウト率
    plt.subplot(2, 2, 3)
    interactions_df = pd.DataFrame(interactions)
    interactions_df['timestamp'] = pd.to_datetime(interactions_df['timestamp'])
    interactions_df['breakout'] = (interactions_df['outcome'] == 'breakout').astype(int)
    
    # 30日間の移動平均でブレイクアウト率を計算
    interactions_df = interactions_df.sort_values('timestamp')
    interactions_df['breakout_rate_30d'] = interactions_df['breakout'].rolling(window=min(30, len(interactions_df)), center=True).mean()
    
    plt.plot(interactions_df['timestamp'], interactions_df['breakout_rate_30d'])
    plt.title('Breakout Rate Over Time (30-day MA)')
    plt.ylabel('Breakout Rate')
    plt.xticks(rotation=45)
    
    # サブプロット4: レベル強度と結果の関係
    plt.subplot(2, 2, 4)
    strength_breakout = [i['level_strength'] for i in interactions if i['outcome'] == 'breakout']
    strength_bounce = [i['level_strength'] for i in interactions if i['outcome'] == 'bounce']
    
    plt.hist([strength_breakout, strength_bounce], bins=20, alpha=0.7, label=['Breakout', 'Bounce'])
    plt.xlabel('Level Strength')
    plt.ylabel('Frequency')
    plt.title('Level Strength vs Outcome')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(f'{symbol.lower()}_{timeframe}_debug_class_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    logger.info("  ✓ クラス分析チャート保存完了")
    
    # 3. 最良モデルの詳細分析
    best_model_name = max(model_results.keys(), key=lambda x: model_results[x]['mean_cv_accuracy'])
    best_results = model_results[best_model_name]
    
    plt.figure(figsize=(15, 10))
    
    # 特徴量重要度
    if best_results['feature_importance'] is not None:
        plt.subplot(2, 2, 1)
        importance_df = best_results['feature_importance'].head(10)
        plt.barh(importance_df['feature'], importance_df['importance'])
        plt.title(f'Top 10 Feature Importances ({best_model_name})')
        plt.gca().invert_yaxis()
    
    # CVスコアの分布
    plt.subplot(2, 2, 2)
    cv_scores = best_results['cv_metrics']
    metrics_names = list(cv_scores.keys())
    box_data = [cv_scores[metric] for metric in metrics_names]
    plt.boxplot(box_data, labels=metrics_names)
    plt.title(f'CV Score Distribution ({best_model_name})')
    plt.xticks(rotation=45)
    
    # 混同行列（全体データ）
    plt.subplot(2, 2, 3)
    overall = best_results['overall_metrics']
    if all(key in overall for key in ['true_negatives', 'false_positives', 'false_negatives', 'true_positives']):
        cm_data = np.array([[overall['true_negatives'], overall['false_positives']], 
                           [overall['false_negatives'], overall['true_positives']]])
        sns.heatmap(cm_data, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Predicted Bounce', 'Predicted Breakout'],
                   yticklabels=['Actual Bounce', 'Actual Breakout'])
        plt.title(f'Confusion Matrix ({best_model_name})')
    
    # 指標比較
    plt.subplot(2, 2, 4)
    metric_names = ['accuracy', 'precision', 'recall', 'f1_score', 'auc_score']
    metric_values = [overall.get(metric, 0) for metric in metric_names]
    
    plt.bar(metric_names, metric_values)
    plt.title(f'Performance Metrics ({best_model_name})')
    plt.ylabel('Score')
    plt.xticks(rotation=45)
    
    for i, v in enumerate(metric_values):
        plt.text(i, v + 0.02, f'{v:.3f}', ha='center')
    
    plt.tight_layout()
    plt.savefig(f'{symbol.lower()}_{timeframe}_debug_best_model_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    logger.info("  ✓ 最良モデル分析チャート保存完了")

def generate_debug_report(interactions, model_results, data_quality):
    """
    詳細なデバッグレポートの生成
    """
    logger.info("=== デバッグレポート生成 ===")
    
    print("\n" + "="*80)
    print("サポート・レジスタンス ML デバッグレポート")
    print("="*80)
    
    # データ品質サマリー
    print(f"\n【データ品質】")
    quality = data_quality['data_completeness']
    print(f"データ完全性: {quality['completeness_rate']:.1%}")
    print(f"レコード数: {quality['total_records']:,}")
    print(f"特徴量数: {quality['total_features']}")
    print(f"欠損値: {quality['missing_values']:,}")
    
    if data_quality['issues']:
        print(f"\n⚠️ 検出された問題:")
        for issue in data_quality['issues']:
            print(f"  - {issue}")
    
    # 相互作用の統計
    total_interactions = len(interactions)
    resistance_interactions = len([i for i in interactions if i['level_type'] == 'resistance'])
    support_interactions = len([i for i in interactions if i['level_type'] == 'support'])
    
    breakouts = len([i for i in interactions if i['outcome'] == 'breakout'])
    bounces = len([i for i in interactions if i['outcome'] == 'bounce'])
    
    print(f"\n【検出された相互作用】")
    print(f"総数: {total_interactions:,}")
    print(f"- 抵抗線: {resistance_interactions:,}")
    print(f"- 支持線: {support_interactions:,}")
    print(f"\n結果分布:")
    print(f"- ブレイクアウト: {breakouts:,} ({breakouts/total_interactions*100:.1f}%)")
    print(f"- 反発: {bounces:,} ({bounces/total_interactions*100:.1f}%)")
    
    # レベルタイプ別の統計
    print(f"\n【レベルタイプ別統計】")
    
    resistance_breakouts = len([i for i in interactions if i['level_type'] == 'resistance' and i['outcome'] == 'breakout'])
    support_breakouts = len([i for i in interactions if i['level_type'] == 'support' and i['outcome'] == 'breakout'])
    
    resistance_breakout_rate = resistance_breakouts/resistance_interactions if resistance_interactions > 0 else 0
    support_breakout_rate = support_breakouts/support_interactions if support_interactions > 0 else 0
    
    print(f"抵抗線:")
    print(f"  - ブレイクアウト率: {resistance_breakout_rate*100:.1f}%")
    print(f"支持線:")
    print(f"  - ブレイクアウト率: {support_breakout_rate*100:.1f}%")
    
    # モデル性能（詳細）
    print(f"\n【モデル性能詳細】")
    for model_name, results in model_results.items():
        print(f"\n{model_name}:")
        
        # CV平均スコア
        cv_metrics = results['cv_metrics']
        print(f"  CV平均精度: {results['mean_cv_accuracy']:.4f} ± {np.std(cv_metrics['accuracy']):.4f}")
        print(f"  CV平均AUC: {results['mean_cv_auc']:.4f} ± {np.std(cv_metrics['auc_score']):.4f}")
        print(f"  CV平均適合率: {np.mean(cv_metrics['precision']):.4f}")
        print(f"  CV平均再現率: {np.mean(cv_metrics['recall']):.4f}")
        print(f"  CV平均F1: {np.mean(cv_metrics['f1_score']):.4f}")
        
        # 全体スコア
        overall = results['overall_metrics']
        print(f"  全体精度: {overall['accuracy']:.4f}")
        print(f"  全体AUC: {overall['auc_score']:.4f}")
    
    # 最重要特徴量
    best_model_name = max(model_results.keys(), key=lambda x: model_results[x]['mean_cv_accuracy'])
    best_model_results = model_results[best_model_name]
    
    print(f"\n【最重要特徴量 TOP10 ({best_model_name})】")
    if best_model_results['feature_importance'] is not None:
        for _, row in best_model_results['feature_importance'].head(10).iterrows():
            print(f"- {row['feature']}: {row['importance']:.4f}")
    
    # 精度に関する結論
    print(f"\n【精度分析結論】")
    best_accuracy = best_model_results['mean_cv_accuracy']
    best_auc = best_model_results['mean_cv_auc']
    
    if best_accuracy > 0.6:
        accuracy_assessment = "良好"
    elif best_accuracy > 0.5:
        accuracy_assessment = "平均的"
    else:
        accuracy_assessment = "要改善"
    
    if best_auc > 0.6:
        auc_assessment = "良好"
    elif best_auc > 0.5:
        auc_assessment = "平均的"
    else:
        auc_assessment = "要改善"
    
    print(f"最良モデルの精度: {best_accuracy:.1%} ({accuracy_assessment})")
    print(f"最良モデルのAUC: {best_auc:.3f} ({auc_assessment})")
    
    # 日本語での精度出力（real_market_integration_fixed.pyで検索される）
    print(f"\n精度: {best_accuracy:.3f}")  # これが検索される行
    
    if best_accuracy < 0.55:
        print(f"\n⚠️ 精度改善の提案:")
        print(f"  - より多くのデータ収集")
        print(f"  - 特徴量エンジニアリング")
        print(f"  - ハイパーパラメータ調整")
        print(f"  - アンサンブル手法の採用")

def main():
    parser = argparse.ArgumentParser(description='サポート・レジスタンス反発/ブレイクアウト予測（デバッグ版）')
    parser.add_argument('--symbol', type=str, default='HYPE', help='通貨シンボル')
    parser.add_argument('--timeframe', type=str, default='1h', help='時間足')
    parser.add_argument('--min-touches', type=int, default=3, help='レベルの最小タッチ回数')
    args = parser.parse_args()
    
    logger.info("=== デバッグモード: サポート・レジスタンス ML分析開始 ===")
    logger.info(f"対象: {args.symbol} {args.timeframe}")
    
    # データ読み込み
    try:
        config = {
            '15m': {'days': 60},
            '1h': {'days': 90},
            '4h': {'days': 180},
            '1d': {'days': 365}
        }
        days = config.get(args.timeframe, {'days': 60})['days']
        
        filename = f"{args.symbol.lower()}_{args.timeframe}_{days}days_with_indicators.csv"
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        logger.info(f"✓ データ読み込み完了: {len(df)}行 × {len(df.columns)}列")
        
    except FileNotFoundError:
        logger.error(f"エラー: {filename} が見つかりません")
        logger.error("先にohlcv_by_claude.pyを実行してください")
        return
    
    # 1. サポート・レジスタンスレベルの検出
    logger.info("=== ステップ1: サポート・レジスタンスレベル検出 ===")
    levels = find_all_levels(df, min_touches=args.min_touches)
    logger.info(f"✓ 検出されたレベル: {len(levels)}個")
    
    # 2. レベルとの相互作用を検出
    logger.info("=== ステップ2: レベル相互作用検出 ===")
    import time
    start_time = time.time()
    interactions = detect_level_interactions(df, levels)
    elapsed = time.time() - start_time
    logger.info(f"✓ 検出完了: {len(interactions)}回の相互作用 (処理時間: {elapsed:.1f}秒)")
    
    if len(interactions) < 50:
        logger.warning("⚠️ 警告: 相互作用データが少なすぎます（50回未満）")
        logger.warning("より長い期間のデータを使用するか、min-touchesを下げてください")
        return
    
    # 3. データ品質検証
    logger.info("=== ステップ3: データ品質検証 ===")
    data_quality = validate_data_quality(df, interactions)
    
    # 4. トレーニングデータの準備
    logger.info("=== ステップ4: トレーニングデータ準備 ===")
    X, y = prepare_training_data(df, levels, interactions)
    logger.info(f"✓ 特徴量数: {X.shape[1]}, サンプル数: {X.shape[0]}")
    
    # 5. モデルの訓練（デバッグ版）
    logger.info("=== ステップ5: モデル訓練（デバッグ版）===")
    model_results = train_models_with_debug(X, y)
    
    # 6. デバッグ結果の可視化
    logger.info("=== ステップ6: デバッグ結果可視化 ===")
    visualize_debug_results(df, levels, interactions, model_results, args.symbol, args.timeframe)
    
    # 7. デバッグレポート生成
    logger.info("=== ステップ7: デバッグレポート生成 ===")
    generate_debug_report(interactions, model_results, data_quality)
    
    # 8. 最良モデルの保存
    best_model_name = max(model_results.keys(), key=lambda x: model_results[x]['mean_cv_accuracy'])
    best_model = model_results[best_model_name]['model']
    best_scaler = model_results[best_model_name]['scaler']
    
    model_filename = f"{args.symbol.lower()}_{args.timeframe}_sr_breakout_model_debug.pkl"
    scaler_filename = f"{args.symbol.lower()}_{args.timeframe}_sr_breakout_scaler_debug.pkl"
    
    joblib.dump(best_model, model_filename)
    joblib.dump(best_scaler, scaler_filename)
    
    logger.info(f"✓ デバッグモデルを保存: {model_filename}")
    logger.info(f"✓ デバッグスケーラーを保存: {scaler_filename}")
    
    # 相互作用データも保存
    interactions_df = pd.DataFrame(interactions)
    interactions_df.to_csv(f"{args.symbol.lower()}_{args.timeframe}_sr_interactions_debug.csv", index=False)
    logger.info(f"✓ デバッグ相互作用データを保存: {args.symbol.lower()}_{args.timeframe}_sr_interactions_debug.csv")
    
    logger.info("=== デバッグ分析完了 ===")

if __name__ == "__main__":
    main()