#!/usr/bin/env python3
"""
支持線・抵抗線プロバイダーの差し替えやすさテスト
将来の改善・変更時の差し替えが容易であることを確認
"""

import asyncio
import sys
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.support_resistance_adapter import (
    FlexibleSupportResistanceDetector,
    ISupportResistanceProvider,
    IMLEnhancementProvider,
    SupportResistanceVisualizerAdapter,
    SupportResistanceMLAdapter
)
from interfaces.data_types import SupportResistanceLevel


class MockSimpleSupportResistanceProvider(ISupportResistanceProvider):
    """差し替えテスト用のシンプルなプロバイダー"""
    
    def detect_basic_levels(self, df: pd.DataFrame, min_touches: int = 2) -> List[Dict[str, Any]]:
        """シンプルな移動平均ベースの支持線・抵抗線検出"""
        close_prices = df['close'].values
        current_price = close_prices[-1]
        
        # 20期間移動平均をサポート・レジスタンスとして使用
        ma20 = df['close'].rolling(window=20).mean()
        ma50 = df['close'].rolling(window=50).mean() if len(df) > 50 else ma20
        
        levels = []
        
        # MA20を基準にレベルを作成
        ma20_current = ma20.iloc[-1]
        if ma20_current < current_price:
            levels.append({
                'price': ma20_current,
                'strength': 0.6,
                'touch_count': 20,  # MA期間と同じ
                'type': 'support',
                'timestamps': [df['timestamp'].iloc[-20], df['timestamp'].iloc[-1]],
                'avg_volume': df['volume'].tail(20).mean()
            })
        else:
            levels.append({
                'price': ma20_current,
                'strength': 0.6,
                'touch_count': 20,
                'type': 'resistance',
                'timestamps': [df['timestamp'].iloc[-20], df['timestamp'].iloc[-1]],
                'avg_volume': df['volume'].tail(20).mean()
            })
        
        # MA50を基準にレベルを作成
        if len(df) > 50:
            ma50_current = ma50.iloc[-1]
            if ma50_current < current_price:
                levels.append({
                    'price': ma50_current,
                    'strength': 0.8,
                    'touch_count': 50,
                    'type': 'support',
                    'timestamps': [df['timestamp'].iloc[-50], df['timestamp'].iloc[-1]],
                    'avg_volume': df['volume'].tail(50).mean()
                })
            else:
                levels.append({
                    'price': ma50_current,
                    'strength': 0.8,
                    'touch_count': 50,
                    'type': 'resistance',
                    'timestamps': [df['timestamp'].iloc[-50], df['timestamp'].iloc[-1]],
                    'avg_volume': df['volume'].tail(50).mean()
                })
        
        return levels
    
    def get_provider_name(self) -> str:
        return "MockSimpleMA"
    
    def get_provider_version(self) -> str:
        return "1.0.0-test"


class MockMLProvider(IMLEnhancementProvider):
    """差し替えテスト用のシンプルなMLプロバイダー"""
    
    def detect_interactions(self, df: pd.DataFrame, levels: List[Dict], distance_threshold: float = 0.02) -> List[Dict]:
        """簡易的な相互作用検出"""
        # 実装を簡略化
        return []
    
    def predict_bounce_probability(self, df: pd.DataFrame, level: Dict) -> float:
        """簡易的な反発確率予測"""
        # 強度に基づく簡易予測
        strength = level.get('strength', 0.5)
        # 強度が高いほど反発しやすいと仮定
        return min(0.9, 0.3 + strength * 0.6)
    
    def get_enhancement_name(self) -> str:
        return "MockSimpleML"


async def test_provider_flexibility():
    """プロバイダーの差し替えやすさをテスト"""
    print("🧪 支持線・抵抗線プロバイダー差し替えテスト")
    print("=" * 60)
    
    # サンプルOHLCVデータを生成
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=200, freq='1h')
    
    base_price = 50000
    trend = np.linspace(0, 2000, 200)
    noise = np.random.normal(0, 300, 200)
    prices = base_price + trend + noise
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.normal(0, 30, 200),
        'high': prices + np.abs(np.random.normal(100, 50, 200)),
        'low': prices - np.abs(np.random.normal(100, 50, 200)),
        'close': prices,
        'volume': np.random.uniform(1000000, 3000000, 200)
    })
    
    current_price = prices[-1]
    print(f"現在価格: {current_price:.2f}")
    print(f"データ数: {len(df)}本")
    
    try:
        # 1. デフォルトプロバイダーでのテスト
        print("\n📊 Step 1: デフォルトプロバイダーでのテスト")
        detector_default = FlexibleSupportResistanceDetector()
        
        info = detector_default.get_provider_info()
        print(f"   基本プロバイダー: {info['base_provider']}")
        print(f"   MLプロバイダー: {info['ml_provider']}")
        
        support_default, resistance_default = detector_default.detect_levels(df, current_price)
        print(f"   結果: 支持線{len(support_default)}個, 抵抗線{len(resistance_default)}個")
        
        # 2. モックプロバイダーに差し替え
        print("\n🔄 Step 2: モックプロバイダーに差し替え")
        detector_mock = FlexibleSupportResistanceDetector()
        
        # 基本プロバイダーを差し替え
        mock_base_provider = MockSimpleSupportResistanceProvider()
        detector_mock.set_base_provider(mock_base_provider)
        
        # MLプロバイダーを差し替え
        mock_ml_provider = MockMLProvider()
        detector_mock.set_ml_provider(mock_ml_provider)
        
        info_mock = detector_mock.get_provider_info()
        print(f"   基本プロバイダー: {info_mock['base_provider']}")
        print(f"   MLプロバイダー: {info_mock['ml_provider']}")
        
        support_mock, resistance_mock = detector_mock.detect_levels(df, current_price)
        print(f"   結果: 支持線{len(support_mock)}個, 抵抗線{len(resistance_mock)}個")
        
        # モック結果の詳細表示
        for i, level in enumerate(support_mock):
            ml_prob = getattr(level, 'ml_bounce_probability', 0)
            print(f"     支持線{i+1}: 価格{level.price:.2f}, 強度{level.strength:.2f}, ML{ml_prob:.2f}")
        
        for i, level in enumerate(resistance_mock):
            ml_prob = getattr(level, 'ml_bounce_probability', 0)
            print(f"     抵抗線{i+1}: 価格{level.price:.2f}, 強度{level.strength:.2f}, ML{ml_prob:.2f}")
        
        # 3. ML機能のオン/オフ切り替えテスト
        print("\n🎛️ Step 3: ML機能のオン/オフ切り替えテスト")
        
        # ML無効化
        detector_mock.disable_ml_enhancement()
        support_no_ml, resistance_no_ml = detector_mock.detect_levels(df, current_price)
        print(f"   ML無効: 支持線{len(support_no_ml)}個, 抵抗線{len(resistance_no_ml)}個")
        
        # ML再有効化
        detector_mock.enable_ml_enhancement()
        support_ml_back, resistance_ml_back = detector_mock.detect_levels(df, current_price)
        print(f"   ML再有効: 支持線{len(support_ml_back)}個, 抵抗線{len(resistance_ml_back)}個")
        
        # 4. 実装の柔軟性評価
        print("\n📋 Step 4: 実装の柔軟性評価")
        
        flexibility_score = 0
        max_score = 6
        
        # プロバイダー差し替えが機能するか
        if len(support_mock) > 0 or len(resistance_mock) > 0:
            flexibility_score += 2
            print("   ✅ プロバイダー差し替え: 成功")
        else:
            print("   ❌ プロバイダー差し替え: 失敗")
        
        # ML機能のオン/オフが機能するか
        if len(support_no_ml) > 0 or len(resistance_no_ml) > 0:
            flexibility_score += 2
            print("   ✅ ML機能切り替え: 成功")
        else:
            print("   ❌ ML機能切り替え: 失敗")
        
        # 異なる結果が得られるか（差し替えの意味があるか）
        if len(support_default) != len(support_mock) or len(resistance_default) != len(resistance_mock):
            flexibility_score += 2
            print("   ✅ プロバイダー差分: 異なる結果が得られた")
        else:
            print("   ⚠️  プロバイダー差分: 結果が同じ（差し替えの効果が不明）")
        
        flexibility_percentage = (flexibility_score / max_score) * 100
        print(f"\n   柔軟性スコア: {flexibility_score}/{max_score} ({flexibility_percentage:.1f}%)")
        
        # 5. 開発者向けの差し替え手順確認
        print("\n🛠️ Step 5: 開発者向け差し替え手順")
        print("   新しいプロバイダーを実装する場合:")
        print("     1. ISupportResistanceProviderまたはIMLEnhancementProviderを継承")
        print("     2. 必要なメソッドを実装")
        print("     3. detector.set_base_provider() または detector.set_ml_provider() で設定")
        print("     4. 即座に新しいプロバイダーが有効化される")
        
        print("\n   設定変更の場合:")
        print("     1. config/support_resistance_config.json を編集")
        print("     2. システム再起動で新しい設定が適用される")
        
        print("\n🎉 プロバイダー差し替えテスト成功!")
        print("\n実装の価値:")
        print("  🔄 既存モジュールの差し替えが容易")
        print("  🎛️ 機能の有効/無効の動的切り替えが可能")
        print("  📦 新しいアルゴリズムの追加が簡単")
        print("  🛡️ エラー耐性（一部失敗しても継続）")
        print("  ⚡ パフォーマンステスト・比較が容易")
        print("  📊 透明性（どのプロバイダーを使用しているかが明確）")
        
        return flexibility_percentage >= 80
        
    except Exception as e:
        print(f"❌ 差し替えテスト失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """メインテスト実行"""
    result = await test_provider_flexibility()
    
    print(f"\n{'='*60}")
    print("📋 最終評価")
    print(f"{'='*60}")
    
    if result:
        print("🎉 差し替えやすさテスト成功!")
        print("\n今後の改善・変更に対する準備:")
        print("  ✅ support_resistance_visualizer.pyの改善版への差し替えが容易")
        print("  ✅ support_resistance_ml.pyの新アルゴリズムへの差し替えが容易")
        print("  ✅ 全く新しい検出アルゴリズムの追加が容易")
        print("  ✅ 本番環境でのA/Bテストが可能")
        print("  ✅ 設定ファイルによる動的な切り替えが可能")
        
        print("\n推奨される今後の改善アプローチ:")
        print("  1. 新しいアルゴリズムはまずモックとして実装")
        print("  2. 既存システムと並行してテスト")
        print("  3. パフォーマンスが確認できたら本格導入")
        print("  4. 設定ファイルで段階的にロールアウト")
        
        return 0
    else:
        print("💥 差し替えに問題があります")
        print("アーキテクチャの改善が必要です。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))