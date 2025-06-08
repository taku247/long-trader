"""
高精度ML予測器の簡易テスト

基本的な動作確認と精度測定を行います。
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_ml_predictor import EnhancedMLPredictor
from interfaces import SupportResistanceLevel

def quick_test():
    """簡易テスト"""
    print("🧪 高精度ML予測器 - 簡易テスト")
    print("="*50)
    
    # 1. サンプルデータ生成
    print("📊 サンプルデータ生成中...")
    np.random.seed(42)
    
    # より現実的な価格データ
    n_samples = 300
    base_price = 100.0
    returns = np.random.normal(0, 0.01, n_samples)  # 1%の日次変動
    prices = [base_price]
    
    for r in returns:
        new_price = prices[-1] * (1 + r)
        prices.append(new_price)
    
    prices = np.array(prices[1:])  # 最初の要素を除去
    
    # OHLCV データ作成
    highs = prices * (1 + np.abs(np.random.normal(0, 0.005, n_samples)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.005, n_samples)))
    volumes = np.random.uniform(1000, 10000, n_samples)
    
    data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='H'),
        'open': prices,
        'high': highs,
        'low': lows,
        'close': prices,
        'volume': volumes
    })
    
    print(f"✅ サンプルデータ作成: {len(data)}件")
    
    # 2. サンプルレベル作成
    current_price = data['close'].iloc[-1]
    
    levels = [
        SupportResistanceLevel(
            price=current_price * 0.98,  # 2%下のサポート
            strength=0.7,
            touch_count=3,
            level_type='support',
            first_touch=datetime.now(),
            last_touch=datetime.now(),
            volume_at_level=5000.0,
            distance_from_current=-0.02
        ),
        SupportResistanceLevel(
            price=current_price * 1.02,  # 2%上のレジスタンス
            strength=0.6,
            touch_count=2,
            level_type='resistance',
            first_touch=datetime.now(),
            last_touch=datetime.now(),
            volume_at_level=4000.0,
            distance_from_current=0.02
        )
    ]
    
    print(f"✅ サンプルレベル作成: {len(levels)}個")
    
    # 3. 高精度ML予測器テスト
    print("\n🤖 高精度ML予測器をテスト中...")
    
    predictor = EnhancedMLPredictor()
    
    # 特徴量生成テスト
    try:
        features = predictor.create_enhanced_features(data, levels)
        print(f"✅ 特徴量生成成功: {len(features.columns)}個の特徴量")
        
        # 特徴量の詳細
        feature_categories = {
            'basic': [col for col in features.columns if any(x in col for x in ['close', 'high', 'low', 'volume'])],
            'ma': [col for col in features.columns if any(x in col for x in ['sma', 'ema'])],
            'technical': [col for col in features.columns if any(x in col for x in ['rsi', 'macd', 'bb'])],
            'interaction': [col for col in features.columns if 'interaction' in col],
            'level': [col for col in features.columns if any(x in col for x in ['support', 'resistance', 'level'])]
        }
        
        print("\n📊 特徴量カテゴリ:")
        for category, cols in feature_categories.items():
            if cols:
                print(f"  {category}: {len(cols)}個")
        
    except Exception as e:
        print(f"❌ 特徴量生成エラー: {e}")
        return
    
    # 4. 訓練テスト
    print("\n🏋️ 訓練テスト中...")
    
    try:
        success = predictor.train_model(data, levels)
        
        if success:
            print("✅ 訓練成功!")
            
            # 精度情報取得
            accuracy = predictor.get_model_accuracy()
            if 'ensemble_auc' in accuracy:
                auc = accuracy['ensemble_auc']
                print(f"📈 アンサンブルAUC: {auc:.3f}")
                
                # 目標達成チェック
                if auc >= 0.70:
                    print("🎉 目標精度70%を達成!")
                elif auc >= 0.65:
                    print("✅ 良好な精度を達成")
                elif auc >= 0.60:
                    print("⚡ ベースラインを改善")
                else:
                    print("⚠️ さらなる改善が必要")
        else:
            print("❌ 訓練失敗")
            return
            
    except Exception as e:
        print(f"❌ 訓練エラー: {e}")
        return
    
    # 5. 予測テスト
    print("\n🎯 予測テスト中...")
    
    try:
        for i, level in enumerate(levels):
            prediction = predictor.predict_breakout(data, level)
            
            print(f"レベル{i+1} ({level.level_type}):")
            print(f"  ブレイクアウト確率: {prediction.breakout_probability:.2f}")
            print(f"  反発確率: {prediction.bounce_probability:.2f}")
            print(f"  信頼度: {prediction.prediction_confidence:.2f}")
            print(f"  モデル: {prediction.model_name}")
            
    except Exception as e:
        print(f"❌ 予測エラー: {e}")
        return
    
    print("\n🎉 簡易テスト完了!")
    print("="*50)
    
    return True

if __name__ == "__main__":
    quick_test()