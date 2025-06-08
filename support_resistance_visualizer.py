"""
サポート・レジスタンス強度可視化ツール
強い抵抗線・支持線の検出と視覚的な強度表示

特徴:
1. フラクタル分析による価格レベルの検出
2. タッチ回数・反発強度・持続期間による強度評価
3. ヒートマップ形式での強度可視化
4. 現在価格に近い重要レベルのハイライト
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import argparse
from scipy.signal import argrelextrema
from matplotlib.colors import LinearSegmentedColormap
import warnings
warnings.filterwarnings('ignore')

def detect_fractal_levels(df, window=5):
    """
    フラクタル分析による局所最高値・最安値の検出
    """
    high = df['high']
    low = df['low']
    
    # 局所最高値（抵抗線候補）
    resistance_indices = argrelextrema(high.values, np.greater, order=window)[0]
    resistance_levels = [(df.iloc[i]['timestamp'], high.iloc[i]) for i in resistance_indices]
    
    # 局所最安値（支持線候補）
    support_indices = argrelextrema(low.values, np.less, order=window)[0]
    support_levels = [(df.iloc[i]['timestamp'], low.iloc[i]) for i in support_indices]
    
    return resistance_levels, support_levels

def cluster_price_levels(levels, tolerance_pct=0.01):
    """
    近い価格レベルをクラスタリング
    tolerance_pct: 価格の何%以内を同じレベルとみなすか
    """
    if not levels:
        return []
    
    # 価格でソート
    sorted_levels = sorted(levels, key=lambda x: x[1])
    clusters = []
    current_cluster = [sorted_levels[0]]
    
    for i in range(1, len(sorted_levels)):
        current_price = sorted_levels[i][1]
        cluster_avg = np.mean([level[1] for level in current_cluster])
        
        # 許容範囲内なら同じクラスタに追加
        if abs(current_price - cluster_avg) / cluster_avg <= tolerance_pct:
            current_cluster.append(sorted_levels[i])
        else:
            # 新しいクラスタを開始
            clusters.append(current_cluster)
            current_cluster = [sorted_levels[i]]
    
    clusters.append(current_cluster)
    return clusters

def calculate_level_details(cluster, df, window=10):
    """
    各レベルの詳細情報を計算（出来高考慮版）
    """
    if len(cluster) < 1:
        return None
    
    touch_count = len(cluster)
    level_price = np.mean([level[1] for level in cluster])
    timestamps = [level[0] for level in cluster]
    
    # 反発の強さと出来高を計算
    bounce_strengths = []
    bounce_details = []
    volume_at_touches = []
    volume_spikes = []
    
    for timestamp in timestamps:
        try:
            idx = df[df['timestamp'] == timestamp].index[0]
            start_idx = max(0, idx - window//2)
            end_idx = min(len(df), idx + window//2 + 1)
            
            local_data = df.iloc[start_idx:end_idx]
            if len(local_data) > 0:
                # 反発の詳細を計算
                high_range = local_data['high'].max() - local_data['high'].min()
                low_range = local_data['low'].max() - local_data['low'].min()
                price_range = max(high_range, low_range)
                bounce_strength = price_range / level_price if level_price > 0 else 0
                
                # 出来高関連の計算
                touch_volume = df.iloc[idx]['volume']
                volume_at_touches.append(touch_volume)
                
                # 出来高スパイク（平均出来高との比率）
                avg_volume = df['volume'].rolling(window=20).mean().iloc[idx]
                volume_spike = touch_volume / avg_volume if avg_volume > 0 else 1
                volume_spikes.append(volume_spike)
                
                bounce_strengths.append(bounce_strength)
                bounce_details.append({
                    'timestamp': timestamp,
                    'strength': bounce_strength,
                    'price_range': price_range,
                    'volume': touch_volume,
                    'volume_spike': volume_spike
                })
        except:
            continue
    
    avg_bounce = np.mean(bounce_strengths) if bounce_strengths else 0
    max_bounce = max(bounce_strengths) if bounce_strengths else 0
    
    # 出来高関連の統計
    avg_volume = np.mean(volume_at_touches) if volume_at_touches else 0
    max_volume_spike = max(volume_spikes) if volume_spikes else 1
    avg_volume_spike = np.mean(volume_spikes) if volume_spikes else 1
    
    # 持続期間
    if len(timestamps) > 1:
        time_span = (pd.to_datetime(max(timestamps)) - pd.to_datetime(min(timestamps))).total_seconds() / 3600  # 時間
        recency = (df['timestamp'].max() - pd.to_datetime(max(timestamps))).total_seconds() / 3600  # 最後のタッチからの時間
    else:
        time_span = 0
        recency = float('inf')
    
    # 総合強度スコア（出来高を考慮した重み付け）
    touch_weight = 3  # タッチ回数の重み
    bounce_weight = 50  # 反発強度の重み
    time_weight = 0.05  # 時間の重み
    recency_weight = 0.02  # 最近性の重み
    volume_weight = 10  # 出来高スパイクの重み
    
    strength = (touch_count * touch_weight + 
                avg_bounce * bounce_weight + 
                time_span * time_weight - 
                recency * recency_weight +
                avg_volume_spike * volume_weight)
    
    return {
        'price': level_price,
        'strength': strength,
        'touch_count': touch_count,
        'avg_bounce': avg_bounce,
        'max_bounce': max_bounce,
        'avg_volume': avg_volume,
        'avg_volume_spike': avg_volume_spike,
        'max_volume_spike': max_volume_spike,
        'time_span': time_span,
        'recency': recency,
        'timestamps': timestamps,
        'bounce_details': bounce_details
    }

def find_all_levels(df, min_touches=2):
    """
    すべての価格レベルを検出（最小タッチ回数でフィルタ）
    """
    print(f"  フラクタルレベルを検出中... (データ数: {len(df)}行)")
    # フラクタルレベルを検出
    resistance_levels, support_levels = detect_fractal_levels(df)
    print(f"  → 抵抗線候補: {len(resistance_levels)}個, 支持線候補: {len(support_levels)}個")
    
    # 価格レベルをクラスタリング
    print(f"  価格レベルをクラスタリング中...")
    resistance_clusters = cluster_price_levels(resistance_levels)
    support_clusters = cluster_price_levels(support_levels)
    print(f"  → 抵抗線クラスター: {len(resistance_clusters)}個, 支持線クラスター: {len(support_clusters)}個")
    
    # すべてのレベルの詳細を計算
    print(f"  レベルの詳細を計算中... (min_touches={min_touches})")
    all_levels = []
    
    resistance_count = 0
    for i, cluster in enumerate(resistance_clusters):
        if i % 20 == 0 and i > 0:
            print(f"    抵抗線処理中: {i}/{len(resistance_clusters)}...")
        if len(cluster) >= min_touches:
            level_info = calculate_level_details(cluster, df)
            if level_info:
                level_info['type'] = 'resistance'
                all_levels.append(level_info)
                resistance_count += 1
    
    support_count = 0
    for i, cluster in enumerate(support_clusters):
        if i % 20 == 0 and i > 0:
            print(f"    支持線処理中: {i}/{len(support_clusters)}...")
        if len(cluster) >= min_touches:
            level_info = calculate_level_details(cluster, df)
            if level_info:
                level_info['type'] = 'support'
                all_levels.append(level_info)
                support_count += 1
    
    print(f"  → 有効な抵抗線: {resistance_count}個, 有効な支持線: {support_count}個")
    
    # 強度でソート
    all_levels.sort(key=lambda x: x['strength'], reverse=True)
    
    return all_levels

def visualize_support_resistance(df, levels, symbol, timeframe):
    """
    サポート・レジスタンスの強度を可視化（シンプル版）
    """
    plt.figure(figsize=(16, 10))
    ax1 = plt.gca()
    
    # 現在価格
    current_price = df['close'].iloc[-1]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 上部: 価格チャートとサポレジライン
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # 価格チャート
    ax1.plot(df['timestamp'], df['close'], label='Close Price', 
             color='black', linewidth=1.5, alpha=0.8)
    
    # 現在価格ライン
    ax1.axhline(y=current_price, color='blue', linestyle='-', 
                linewidth=2, alpha=0.8, label=f'Current: ${current_price:.3f}')
    
    # サポート・レジスタンスラインを強度に応じて表示
    max_strength = max([level['strength'] for level in levels]) if levels else 1
    
    for level in levels:
        # 強度に応じた線の太さと透明度
        normalized_strength = level['strength'] / max_strength
        linewidth = 0.5 + normalized_strength * 2.5
        alpha = 0.3 + normalized_strength * 0.5
        
        # 色設定
        color = 'red' if level['type'] == 'resistance' else 'green'
        
        # 価格ライン（実線のみ使用）
        ax1.axhline(y=level['price'], color=color, linestyle='-', 
                   linewidth=linewidth, alpha=alpha)
        
        # タッチポイントをマーク
        for timestamp in level['timestamps']:
            ax1.scatter(timestamp, level['price'], 
                       color=color, s=20, alpha=0.6, zorder=5)
        
        # 重要なレベル（上位10）にラベル追加
        if levels.index(level) < 10:
            # 現在価格からの距離
            distance_pct = ((level['price'] - current_price) / current_price) * 100
            label_text = f"${level['price']:.2f} ({distance_pct:+.1f}%)\n"
            label_text += f"T:{level['touch_count']} S:{level['strength']:.0f}"
            
            # ラベル位置を調整
            x_pos = df['timestamp'].iloc[-len(df)//20]  # 右端から5%の位置
            ax1.text(x_pos, level['price'], label_text,
                    fontsize=8, ha='left', va='center',
                    bbox=dict(boxstyle='round,pad=0.3', 
                             facecolor='white', 
                             edgecolor=color,
                             alpha=0.8))
    
    # 現在価格に最も近いサポート・レジスタンスをハイライト
    nearest_resistance = min([l for l in levels if l['type'] == 'resistance' and l['price'] > current_price],
                           key=lambda x: x['price'] - current_price, default=None)
    nearest_support = max([l for l in levels if l['type'] == 'support' and l['price'] < current_price],
                         key=lambda x: current_price - x['price'], default=None)
    
    if nearest_resistance:
        ax1.axhspan(current_price, nearest_resistance['price'], 
                   alpha=0.1, color='red', label='Next Resistance Zone')
    
    if nearest_support:
        ax1.axhspan(nearest_support['price'], current_price, 
                   alpha=0.1, color='green', label='Next Support Zone')
    
    plt.title(f'{symbol} Support/Resistance Strength Analysis ({timeframe})', 
              fontsize=16, pad=20)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price (USD)', fontsize=12)
    plt.legend(loc='best', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # 保存
    output_filename = f"{symbol.lower()}_{timeframe}_support_resistance_analysis.png"
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_filename

def generate_report(df, levels, symbol, timeframe):
    """
    サポート・レジスタンスのレポート生成
    """
    current_price = df['close'].iloc[-1]
    
    print(f"\n{'='*80}")
    print(f"サポート・レジスタンス分析レポート - {symbol} ({timeframe})")
    print(f"{'='*80}")
    print(f"\n現在価格: ${current_price:.3f}")
    print(f"分析期間: {df['timestamp'].min().strftime('%Y-%m-%d')} ~ {df['timestamp'].max().strftime('%Y-%m-%d')}")
    print(f"検出レベル数: {len(levels)}")
    
    # 現在価格付近の重要レベル
    print(f"\n【現在価格付近の重要レベル】")
    
    # 上方レジスタンス（上位3つ）
    resistances = [l for l in levels if l['type'] == 'resistance' and l['price'] > current_price]
    resistances.sort(key=lambda x: x['price'])
    
    print("\n▼ 直近のレジスタンス:")
    for i, level in enumerate(resistances[:3]):
        distance = level['price'] - current_price
        distance_pct = (distance / current_price) * 100
        print(f"  {i+1}. ${level['price']:.3f} (+{distance_pct:.2f}%) "
              f"- タッチ{level['touch_count']}回, 強度{level['strength']:.0f}")
    
    # 下方サポート（上位3つ）
    supports = [l for l in levels if l['type'] == 'support' and l['price'] < current_price]
    supports.sort(key=lambda x: x['price'], reverse=True)
    
    print("\n▼ 直近のサポート:")
    for i, level in enumerate(supports[:3]):
        distance = current_price - level['price']
        distance_pct = (distance / current_price) * 100
        print(f"  {i+1}. ${level['price']:.3f} (-{distance_pct:.2f}%) "
              f"- タッチ{level['touch_count']}回, 強度{level['strength']:.0f}")
    
    # 最強レベルTOP10
    print(f"\n【最強レベル TOP10】")
    print(f"{'順位':<4} {'価格':>10} {'タイプ':<10} {'タッチ回数':>10} {'反発強度':>10} {'出来高倍率':>10} {'総合強度':>10}")
    print("-" * 75)
    
    for i, level in enumerate(levels[:10]):
        print(f"{i+1:<4} ${level['price']:>9.3f} {level['type']:<10} "
              f"{level['touch_count']:>10} {level['avg_bounce']*100:>9.1f}% "
              f"{level.get('avg_volume_spike', 1):>9.1f}x "
              f"{level['strength']:>10.0f}")
    
    # 統計情報
    print(f"\n【統計情報】")
    resistance_count = len([l for l in levels if l['type'] == 'resistance'])
    support_count = len([l for l in levels if l['type'] == 'support'])
    
    print(f"- レジスタンス数: {resistance_count}")
    print(f"- サポート数: {support_count}")
    print(f"- 平均タッチ回数: {np.mean([l['touch_count'] for l in levels]):.1f}")
    print(f"- 最大タッチ回数: {max([l['touch_count'] for l in levels])}")
    
    # タッチ回数分布
    touch_distribution = {}
    for level in levels:
        touches = level['touch_count']
        touch_distribution[touches] = touch_distribution.get(touches, 0) + 1
    
    print(f"\n【タッチ回数分布】")
    for touches in sorted(touch_distribution.keys()):
        print(f"  {touches}回: {'█' * touch_distribution[touches]} ({touch_distribution[touches]}レベル)")

def main():
    parser = argparse.ArgumentParser(description='サポート・レジスタンス強度可視化')
    parser.add_argument('--symbol', type=str, default='HYPE', help='通貨シンボル')
    parser.add_argument('--timeframe', type=str, default='15m', help='時間足')
    parser.add_argument('--min-touches', type=int, default=2, help='最小タッチ回数')
    args = parser.parse_args()
    
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
        
        print(f"データ読み込み完了: {len(df)}行")
        
    except FileNotFoundError:
        print(f"エラー: {filename} が見つかりません")
        print("先にohlcv_by_claude.pyを実行してください")
        return
    
    # サポート・レジスタンスの検出
    print("\nサポート・レジスタンスを分析中...")
    levels = find_all_levels(df, min_touches=args.min_touches)
    
    print(f"検出されたレベル: {len(levels)}個")
    
    # 可視化
    print("\nチャートを生成中...")
    try:
        output_file = visualize_support_resistance(df, levels, args.symbol, args.timeframe)
        print(f"✓ チャートを保存: {output_file}")
    except Exception as e:
        print(f"× チャート生成エラー: {e}")
        print("レポートのみ生成します...")
    
    # レポート生成
    generate_report(df, levels, args.symbol, args.timeframe)
    
    # CSVエクスポート
    levels_df = pd.DataFrame(levels)
    # 出来高情報を含む列を選択（存在しない列は除外）
    export_cols = ['price', 'type', 'touch_count', 'strength', 'avg_bounce', 
                   'avg_volume_spike', 'max_volume_spike', 'recency']
    available_cols = [col for col in export_cols if col in levels_df.columns]
    levels_df = levels_df[available_cols]
    levels_df.to_csv(f"{args.symbol.lower()}_{args.timeframe}_support_resistance_levels.csv", index=False)
    print(f"\n✓ レベルデータを保存: {args.symbol.lower()}_{args.timeframe}_support_resistance_levels.csv")

if __name__ == "__main__":
    main()