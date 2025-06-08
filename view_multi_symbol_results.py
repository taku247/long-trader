"""
Multi-Symbol Analysis Results Viewer
複数銘柄分析の結果を表示
"""
import json
import pandas as pd
from pathlib import Path

def load_latest_results():
    """最新の分析結果を読み込み"""
    results_dir = Path("real_market_analysis/results")
    
    # 最新のファイルを探す
    json_files = list(results_dir.glob("multi_symbol_analysis_*.json"))
    if not json_files:
        print("❌ 分析結果ファイルが見つかりません")
        return None
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"📊 結果ファイル: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def display_comprehensive_results(results):
    """包括的な結果表示"""
    print("=" * 80)
    print("マルチシンボル実市場分析結果 - 包括レポート")
    print("=" * 80)
    
    # 基本情報
    print(f"\n📅 分析ID: {results['analysis_id']}")
    print(f"🎯 対象銘柄: {', '.join(results['symbols_analyzed'])}")
    
    # サマリー統計
    summary = results['summary']
    print(f"\n=== 📊 総合サマリー ===")
    print(f"テスト銘柄数: {summary['symbols_tested']}")
    print(f"成功パイプライン: {summary['successful_pipelines']}")
    print(f"成功率: {summary['pipeline_success_rate']:.1%}")
    print(f"平均ML精度: {summary['avg_ml_accuracy']:.3f}")
    print(f"平均データ品質: {summary['avg_data_quality']:.3f}")
    print(f"ML精度範囲: {summary['ml_accuracy_range']['min']:.3f} - {summary['ml_accuracy_range']['max']:.3f}")
    print(f"ML精度標準偏差: {summary['ml_accuracy_range']['std']:.3f}")
    
    # 銘柄別詳細分析
    print(f"\n=== 🔍 銘柄別詳細分析 ===")
    for symbol in results['symbols_analyzed']:
        perf = results['performance_comparison'][symbol]
        print(f"\n💎 {symbol}:")
        
        data_quality_str = f"{perf['data_quality']:.3f}" if perf['data_quality'] is not None else "N/A"
        print(f"  📈 データ品質: {data_quality_str}")
        print(f"  🎯 サポレジ分析: {'✅ 成功' if perf['sr_success'] else '❌ 失敗'}")
        
        ml_accuracy_str = f"{perf['ml_accuracy']:.3f}" if perf['ml_accuracy'] is not None else "N/A"
        print(f"  🤖 ML精度: {ml_accuracy_str}")
        print(f"  ⚡ パイプライン: {'🟢 完全成功' if perf['pipeline_success'] else '🔴 失敗'}")
        
        # 詳細データ情報
        data_info = next((d for d in results['data_analysis'] if d['symbol'] == symbol), None)
        if data_info:
            print(f"    📋 レコード数: {data_info['records']:,}")
            print(f"    🔧 特徴量数: {data_info['features']}")
    
    # ML精度ランキング
    print(f"\n=== 🏆 ML精度ランキング ===")
    ml_ranking = [(symbol, perf['ml_accuracy']) for symbol, perf in results['performance_comparison'].items() 
                 if perf['ml_accuracy'] is not None]
    ml_ranking.sort(key=lambda x: x[1], reverse=True)
    
    for i, (symbol, accuracy) in enumerate(ml_ranking, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        print(f"{emoji} {i}位: {symbol} - {accuracy:.3f}")
    
    # 技術的分析
    print(f"\n=== 🔬 技術的分析 ===")
    
    # データ品質分析
    data_qualities = [perf['data_quality'] for perf in results['performance_comparison'].values() 
                     if perf['data_quality'] is not None]
    
    print(f"📊 データ品質統計:")
    print(f"  最高: {max(data_qualities):.4f}")
    print(f"  最低: {min(data_qualities):.4f}")
    print(f"  平均: {sum(data_qualities)/len(data_qualities):.4f}")
    print(f"  標準偏差: {pd.Series(data_qualities).std():.6f}")
    
    # ML性能分析
    ml_accuracies = [perf['ml_accuracy'] for perf in results['performance_comparison'].values() 
                    if perf['ml_accuracy'] is not None]
    
    print(f"\n🤖 ML性能統計:")
    print(f"  最高精度: {max(ml_accuracies):.3f}")
    print(f"  最低精度: {min(ml_accuracies):.3f}")
    print(f"  平均精度: {sum(ml_accuracies)/len(ml_accuracies):.3f}")
    print(f"  性能範囲: {max(ml_accuracies) - min(ml_accuracies):.3f}")
    
    # 堅牢性評価
    print(f"\n=== 🛡️ システム堅牢性評価 ===")
    
    pipeline_success_rate = summary['pipeline_success_rate']
    if pipeline_success_rate == 1.0:
        robustness = "🟢 極めて高い"
        robustness_desc = "全銘柄で完璧な動作"
    elif pipeline_success_rate >= 0.8:
        robustness = "🟡 高い" 
        robustness_desc = "大部分の銘柄で正常動作"
    elif pipeline_success_rate >= 0.5:
        robustness = "🟠 中程度"
        robustness_desc = "半数以上の銘柄で動作"
    else:
        robustness = "🔴 低い"
        robustness_desc = "多くの銘柄で問題発生"
    
    print(f"システム堅牢性: {robustness}")
    print(f"評価: {robustness_desc}")
    
    # ML性能の一貫性
    accuracy_std = summary['ml_accuracy_range']['std']
    if accuracy_std < 0.01:
        consistency = "🟢 非常に一貫"
        consistency_desc = "銘柄間の性能差が極めて小さい"
    elif accuracy_std < 0.03:
        consistency = "🟡 一貫"
        consistency_desc = "銘柄間の性能差が小さい"
    elif accuracy_std < 0.05:
        consistency = "🟠 やや不一致"
        consistency_desc = "銘柄間で性能にやや差がある"
    else:
        consistency = "🔴 不一致"
        consistency_desc = "銘柄間で性能に大きな差がある"
    
    print(f"ML性能一貫性: {consistency}")
    print(f"評価: {consistency_desc}")
    
    # 生成されたファイル
    print(f"\n=== 📁 生成されたファイル ===")
    for symbol in results['symbols_analyzed']:
        print(f"\n{symbol}:")
        
        # サポレジチャート
        sr_info = next((sr for sr in results['support_resistance'] if sr['symbol'] == symbol), None)
        if sr_info and sr_info['status'] == 'success':
            print(f"  📈 サポレジチャート: {sr_info['chart_path']}")
        
        # MLモデルファイル
        ml_info = next((ml for ml in results['ml_training'] if ml['symbol'] == symbol), None)
        if ml_info and ml_info['status'] == 'success':
            print(f"  🤖 MLモデル: {symbol.lower()}_1h_sr_breakout_model.pkl")
            print(f"  🔧 スケーラー: {symbol.lower()}_1h_sr_breakout_scaler.pkl")
            print(f"  📊 相互作用データ: {symbol.lower()}_1h_sr_interactions.csv")
    
    print(f"\n=== 📝 結論 ===")
    
    if pipeline_success_rate == 1.0 and accuracy_std < 0.03:
        conclusion = "🎉 システムは複数銘柄において高い堅牢性と一貫した性能を実証"
        recommendation = "✅ 本番環境での運用に適している"
    elif pipeline_success_rate >= 0.8:
        conclusion = "✅ システムは概ね良好な性能を示している"
        recommendation = "⚠️ 一部調整を行った上で運用可能"
    else:
        conclusion = "⚠️ システムの堅牢性に改善の余地がある"
        recommendation = "🔧 さらなる最適化が必要"
    
    print(conclusion)
    print(recommendation)
    
    print(f"\n✅ マルチシンボル分析完了 - 分析ID: {results['analysis_id']}")

def main():
    """メイン実行"""
    results = load_latest_results()
    if results:
        display_comprehensive_results(results)

if __name__ == "__main__":
    main()