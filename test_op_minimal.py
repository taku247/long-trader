#!/usr/bin/env python3
"""
OPの最小限テスト - 条件ベース分析で0トレードになる原因を特定
"""

import sys
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# ロギング設定 - ERRORレベルのみ表示
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from scalable_analysis_system import ScalableAnalysisSystem

def test_op_condition_based():
    """OPの条件ベース分析をテスト + NameError検知"""
    print("🔍 OP条件ベース分析テスト + NameError検知")
    print("=" * 60)
    
    system = ScalableAnalysisSystem()
    
    # NameError検知フラグ
    nameerror_detected = False
    original_stderr = None
    
    try:
        # OPの分析を短期間（5日）で実行
        print("📊 OP 15m Aggressive_ML を5日間で分析...")
        print("⚠️ ERRORログに注目してください")
        print("-" * 60)
        
        # ログを監視してNameErrorを検知
        import logging
        import io
        import sys
        
        # ログキャプチャ用のストリーム
        log_capture = io.StringIO()
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.ERROR)
        
        # ルートロガーにハンドラ追加
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        
        trades = system._generate_real_analysis('OP', '15m', 'Aggressive_ML', evaluation_period_days=5)
        
        # ログ内容をチェック
        log_output = log_capture.getvalue()
        if "NameError" in log_output or "name 'market_context' is not defined" in log_output:
            nameerror_detected = True
            print("\n🚨 NameError検知！")
            print("ログ内容:")
            print(log_output)
        
        # ハンドラを削除
        root_logger.removeHandler(log_handler)
        
        print("-" * 60)
        print(f"\n✅ 分析完了")
        print(f"📊 生成されたトレード数: {len(trades) if trades else 0}")
        
        if nameerror_detected:
            print("\n🚨 NameErrorバグが再発しています！")
            print("修正が必要です。")
        else:
            print("\n✅ NameErrorは検知されませんでした")
        
        if not trades:
            print("\n🚨 0トレード - ERRORログを確認してください：")
            print("1. 'RETURN NONE TRIGGERED' → リスク・リワード計算でNone返却")
            print("2. 'OP条件評価詳細' → 条件不満足の詳細")
            print("3. 'OP条件不満足' → 条件評価で失敗")
            if not nameerror_detected:
                print("4. ✅ NameErrorは発生していません（修正済み）")
    
    except Exception as e:
        if "NameError" in str(type(e).__name__) and "market_context" in str(e):
            print(f"\n🚨 NameErrorバグ再発！: {e}")
            nameerror_detected = True
        else:
            print(f"\n❌ 予期しないエラー: {e}")
            import traceback
            traceback.print_exc()
    
    return not nameerror_detected

if __name__ == '__main__':
    test_op_condition_based()