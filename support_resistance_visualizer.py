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
import logging
warnings.filterwarnings('ignore')

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
    
    # 生の強度計算
    raw_strength = (touch_count * touch_weight + 
                    avg_bounce * bounce_weight + 
                    time_span * time_weight - 
                    recency * recency_weight +
                    avg_volume_spike * volume_weight)
    
    # 強度を0.0-1.0の範囲に正規化
    # 一般的に強度は0-200の範囲になるため、適切にスケーリング
    strength = min(max(raw_strength / 200.0, 0.0), 1.0)
    
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
    import os
    from datetime import datetime
    
    # デバッグログ設定（並列プロセス対応）
    debug_mode = os.environ.get('SUPPORT_RESISTANCE_DEBUG', 'false').lower() == 'true'
    debug_log_path = None
    if debug_mode:
        debug_log_path = f"/tmp/sr_debug_{os.getpid()}.log"
        with open(debug_log_path, 'a') as f:
            f.write(f"\n--- Support/Resistance Visualizer Debug (PID: {os.getpid()}) ---\n")
            f.write(f"find_all_levels called with {len(df)} rows, min_touches={min_touches}\n")
            f.write(f"Starting at {datetime.now()}\n")
    
    print(f"  🔍 フラクタルレベル検出開始 (データ数: {len(df)}行, min_touches={min_touches})")
    
    # データ最小要件チェック
    if len(df) < 10:
        print(f"  ❌ データ不足: {len(df)}本 < 10本 (最小要件)")
        if debug_mode:
            with open(debug_log_path, 'a') as f:
                f.write(f"❌ Insufficient data: {len(df)} < 10 candles\n")
        return []
    
    # 価格範囲の確認
    if not df.empty:
        price_min = df['close'].min()
        price_max = df['close'].max()
        price_range_pct = (price_max - price_min) / price_min * 100
        print(f"  📊 価格範囲: {price_min:.4f} - {price_max:.4f} (レンジ{price_range_pct:.1f}%)")
    
    # フラクタルレベルを検出
    resistance_levels, support_levels = detect_fractal_levels(df)
    print(f"  📈 フラクタル検出完了: 抵抗線候補{len(resistance_levels)}個, 支持線候補{len(support_levels)}個")
    
    if debug_mode:
        with open(debug_log_path, 'a') as f:
            f.write(f"Fractal detection: {len(resistance_levels)} resistance candidates, {len(support_levels)} support candidates\n")
    
    if not resistance_levels and not support_levels:
        print(f"  ⚠️ フラクタル検出結果0個 → 局所最高値・最安値が検出されず")
        if debug_mode:
            with open(debug_log_path, 'a') as f:
                f.write(f"❌ No fractal levels detected - no local maxima/minima found\n")
        return []
    
    # 価格レベルをクラスタリング
    print(f"  🔗 価格レベルクラスタリング開始...")
    resistance_clusters = cluster_price_levels(resistance_levels)
    support_clusters = cluster_price_levels(support_levels)
    print(f"  📊 クラスタリング完了: 抵抗線{len(resistance_clusters)}クラスター, 支持線{len(support_clusters)}クラスター")
    
    if debug_mode:
        with open(debug_log_path, 'a') as f:
            f.write(f"Clustering completed: {len(resistance_clusters)} resistance clusters, {len(support_clusters)} support clusters\n")
    
    # クラスター統計
    if resistance_clusters:
        cluster_sizes = [len(cluster) for cluster in resistance_clusters]
        valid_resistance_clusters = sum(1 for size in cluster_sizes if size >= min_touches)
        print(f"  📋 抵抗線クラスター詳細: 平均サイズ{np.mean(cluster_sizes):.1f}, 有効{valid_resistance_clusters}個 (>={min_touches}タッチ)")
    
    if support_clusters:
        cluster_sizes = [len(cluster) for cluster in support_clusters]
        valid_support_clusters = sum(1 for size in cluster_sizes if size >= min_touches)
        print(f"  📋 支持線クラスター詳細: 平均サイズ{np.mean(cluster_sizes):.1f}, 有効{valid_support_clusters}個 (>={min_touches}タッチ)")
    
    # すべてのレベルの詳細を計算
    print(f"  ⚙️ レベル詳細計算開始...")
    all_levels = []
    
    resistance_count = 0
    for i, cluster in enumerate(resistance_clusters):
        cluster_size = len(cluster)
        if cluster_size >= min_touches:
            level_info = calculate_level_details(cluster, df)
            if level_info:
                level_info['type'] = 'resistance'
                all_levels.append(level_info)
                resistance_count += 1
                if resistance_count <= 3:  # 最初の3個のみ詳細表示
                    print(f"    ✅ 抵抗線{resistance_count}: 価格{level_info['price']:.4f}, 強度{level_info['strength']:.3f}, {cluster_size}タッチ")
        else:
            if i < 5:  # 最初の5個のみ表示
                print(f"    ❌ 抵抗線除外: {cluster_size}タッチ < {min_touches} (不足)")
    
    support_count = 0
    for i, cluster in enumerate(support_clusters):
        cluster_size = len(cluster)
        if cluster_size >= min_touches:
            level_info = calculate_level_details(cluster, df)
            if level_info:
                level_info['type'] = 'support'
                all_levels.append(level_info)
                support_count += 1
                if support_count <= 3:  # 最初の3個のみ詳細表示
                    print(f"    ✅ 支持線{support_count}: 価格{level_info['price']:.4f}, 強度{level_info['strength']:.3f}, {cluster_size}タッチ")
        else:
            if i < 5:  # 最初の5個のみ表示
                print(f"    ❌ 支持線除外: {cluster_size}タッチ < {min_touches} (不足)")
    
    print(f"  📊 有効レベル集計: 抵抗線{resistance_count}個, 支持線{support_count}個")
    
    if debug_mode:
        with open(debug_log_path, 'a') as f:
            f.write(f"Valid level count: {resistance_count} resistances, {support_count} supports\n")
    
    if not all_levels:
        print(f"  🚨 最終結果: 有効レベル0個 → 検出条件を満たすレベルなし")
        print(f"  📋 シグナルなしの理由:")
        print(f"    - min_touches={min_touches}の条件を満たすクラスターなし")
        print(f"    - または強度計算でraw_strength/200が0.0になった")
        
        if debug_mode:
            with open(debug_log_path, 'a') as f:
                f.write(f"❌ FINAL RESULT: 0 valid levels\n")
                f.write(f"Reasons for no signal:\n")
                f.write(f"  - No clusters meeting min_touches={min_touches} requirement\n")
                f.write(f"  - Or strength calculation resulted in raw_strength/200 = 0.0\n")
                f.write(f"Cluster analysis:\n")
                for i, cluster in enumerate(resistance_clusters + support_clusters):
                    cluster_size = len(cluster)
                    f.write(f"  Cluster {i+1}: {cluster_size} touches ({'✓' if cluster_size >= min_touches else '✗'})\n")
        
        return []
    
    # 強度でソート
    all_levels.sort(key=lambda x: x['strength'], reverse=True)
    
    print(f"  🎯 最終レベル一覧 (強度順):")
    for i, level in enumerate(all_levels[:5]):  # 上位5個のみ表示
        print(f"    {i+1}. {level['type']} {level['price']:.4f} (強度{level['strength']:.3f}, {level['touch_count']}タッチ)")
    
    if len(all_levels) > 5:
        print(f"    ... 他{len(all_levels)-5}個のレベル")
    
    # サーバーログにも記録
    support_count = sum(1 for l in all_levels if l['type'] == 'support')
    resistance_count = sum(1 for l in all_levels if l['type'] == 'resistance')
    
    if support_count > 0 or resistance_count > 0:
        logger.info(f"✅ 支持線・抵抗線検出成功 (support_resistance_visualizer):")
        logger.info(f"   📊 支持線: {support_count}個検出")
        if support_count > 0:
            support_levels = [l for l in all_levels if l['type'] == 'support']
            for i, s in enumerate(support_levels[:3], 1):  # 上位3個表示
                logger.info(f"      {i}. 価格: ${s['price']:.2f} 強度: {s['strength']:.2f} タッチ数: {s['touch_count']}")
            if support_count > 3:
                logger.info(f"      ... 他{support_count-3}個")
                
        logger.info(f"   📈 抵抗線: {resistance_count}個検出")
        if resistance_count > 0:
            resistance_levels = [l for l in all_levels if l['type'] == 'resistance']
            for i, r in enumerate(resistance_levels[:3], 1):  # 上位3個表示
                logger.info(f"      {i}. 価格: ${r['price']:.2f} 強度: {r['strength']:.2f} タッチ数: {r['touch_count']}")
            if resistance_count > 3:
                logger.info(f"      ... 他{resistance_count-3}個")
    else:
        logger.warning(f"⚠️  支持線・抵抗線が検出されませんでした (support_resistance_visualizer)")
    
    if debug_mode:
        with open(debug_log_path, 'a') as f:
            f.write(f"✅ FINAL LEVEL LIST (sorted by strength):\n")
            for i, level in enumerate(all_levels):
                f.write(f"  {i+1}. {level['type']} {level['price']:.4f} (strength {level['strength']:.3f}, {level['touch_count']} touches)\n")
            f.write(f"find_all_levels completed at {datetime.now()}\n")
            f.write(f"--- End of Support/Resistance Visualizer Debug ---\n")
    
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