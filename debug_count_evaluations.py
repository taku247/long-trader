#!/usr/bin/env python3
"""
実際に何回評価が実行されているかを正確にカウント
"""

import re
import subprocess
import time

def count_actual_evaluations():
    """auto_symbol_training.pyで実際の評価回数をカウント"""
    
    print("🔍 実際の評価回数を正確にカウント\n")
    
    try:
        # auto_symbol_training.pyを実行してログをキャプチャ
        print("📊 auto_symbol_training.py を実行してログを解析...")
        
        start_time = time.time()
        
        result = subprocess.run([
            'python', 'auto_symbol_training.py', 
            '--symbol', 'DOGWIFHAT',  # 新しい銘柄で試す
            '--execution-id', 'DEBUG_COUNT'
        ], capture_output=True, text=True, timeout=30)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"⏱️ 実行時間: {total_time:.1f}秒")
        
        # ログから評価回数をカウント
        stdout = result.stdout
        stderr = result.stderr
        all_output = stdout + stderr
        
        # パターン1: "分析エラー (評価X)"
        evaluation_errors = re.findall(r'分析エラー \(評価(\d+)\)', all_output)
        
        # パターン2: "Analysis failed for ... at 2025-XX-XX"
        analysis_failed = re.findall(r'Analysis failed for \w+ at (2025-\d{2}-\d{2} \d{2}:\d{2})', all_output)
        
        # パターン3: "評価間隔" や "評価回数" の設定
        max_eval_match = re.search(r'最大評価回数: (\d+)回', all_output)
        
        print(f"\\n📊 ログ解析結果:")
        print(f"   評価エラーパターン: {len(evaluation_errors)}個")
        print(f"   分析失敗パターン: {len(analysis_failed)}個")
        
        if max_eval_match:
            max_evaluations = int(max_eval_match.group(1))
            print(f"   設定された最大評価回数: {max_evaluations}")
        
        if evaluation_errors:
            max_eval_num = max(int(x) for x in evaluation_errors)
            print(f"   実際の最大評価番号: {max_eval_num}")
            print(f"   評価番号リスト: {sorted(set(int(x) for x in evaluation_errors))}")
        
        if analysis_failed:
            print(f"   分析失敗の時刻範囲:")
            print(f"     最初: {analysis_failed[0]}")
            print(f"     最後: {analysis_failed[-1]}")
        
        # 推定実行回数
        estimated_evaluations = max(len(evaluation_errors), len(analysis_failed))
        print(f"\\n🎯 推定実行回数: {estimated_evaluations}")
        
        if estimated_evaluations > 0:
            avg_time_per_eval = total_time / estimated_evaluations
            print(f"   平均時間/評価: {avg_time_per_eval:.2f}秒")
            
            # 100回実行した場合の推定時間
            estimated_100_time = avg_time_per_eval * 100
            print(f"   100回実行時の推定時間: {estimated_100_time:.0f}秒")
            
            if estimated_100_time > 60:
                print(f"   ❌ 矛盾: 100回なら{estimated_100_time:.0f}秒かかるはず")
            else:
                print(f"   ✅ 妥当: 短時間評価が可能")
        
        # "完了戦略数" のパターンをチェック
        completed_match = re.search(r'完了戦略数: (\d+)/(\d+)', all_output)
        if completed_match:
            completed = int(completed_match.group(1))
            total = int(completed_match.group(2))
            print(f"\\n📊 戦略完了状況:")
            print(f"   完了: {completed}/{total}")
            
            if completed == 0:
                print(f"   ❌ 0戦略完了 = 実際の処理は実行されていない")
        
        # 特定のエラーメッセージをチェック
        if "現在の市場状況では有効な支持線・抵抗線が検出されませんでした" in all_output:
            print(f"\\n🔍 支持線・抵抗線検出失敗を確認")
            print(f"   これが早期終了の原因である可能性が高い")
        
        return estimated_evaluations, total_time
        
    except subprocess.TimeoutExpired:
        print(f"❌ 30秒でタイムアウト（実際の処理が実行されている可能性）")
        return None, 30
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")
        return None, None


def analyze_loop_early_termination():
    """ループ早期終了の具体的なメカニズムを分析"""
    
    print("\\n" + "="*60)
    print("🔍 ループ早期終了メカニズムの分析")
    print("="*60)
    
    # scalable_analysis_system.pyで早期終了につながる条件を探す
    try:
        with open('scalable_analysis_system.py', 'r') as f:
            content = f.read()
        
        # 早期終了に関連するキーワードを探す
        termination_keywords = [
            'return []',
            'break',
            'raise Exception',
            'if not trades:',
            'evaluation_period_days',
            'signals_generated',
            'max_evaluations'
        ]
        
        print("📝 早期終了に関連するコードパターン:")
        lines = content.split('\\n')
        
        for i, line in enumerate(lines):
            for keyword in termination_keywords:
                if keyword in line and not line.strip().startswith('#'):
                    print(f"   Line {i+1}: {line.strip()}")
                    
                    # 特に重要な "return []" を詳しく調査
                    if 'return []' in line:
                        print(f"     ⚠️ 空リスト返却 - これが早期終了の原因か？")
                        
                        # 前後の条件を確認
                        for j in range(max(0, i-3), min(len(lines), i+3)):
                            if j != i:
                                context_line = lines[j].strip()
                                if context_line and not context_line.startswith('#'):
                                    print(f"     Line {j+1}: {context_line}")
        
        # "if not trades:" パターンを特に詳しく調査
        if_not_trades_matches = []
        for i, line in enumerate(lines):
            if 'if not trades:' in line.strip():
                if_not_trades_matches.append(i)
        
        if if_not_trades_matches:
            print(f"\\n🎯 'if not trades:' パターンの詳細:")
            for line_num in if_not_trades_matches:
                print(f"   Line {line_num+1}: {lines[line_num].strip()}")
                
                # 次の数行を確認
                for j in range(line_num+1, min(len(lines), line_num+5)):
                    next_line = lines[j].strip()
                    if next_line:
                        print(f"     Line {j+1}: {next_line}")
                        if 'return' in next_line:
                            print(f"       🔴 ここで早期終了する可能性")
                            break
        
    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {e}")


if __name__ == "__main__":
    evaluations, exec_time = count_actual_evaluations()
    analyze_loop_early_termination()
    
    if evaluations is not None and exec_time is not None:
        print(f"\\n" + "="*60)
        print("📊 最終分析結果")
        print("="*60)
        print(f"実際の評価回数: {evaluations}")
        print(f"実行時間: {exec_time:.1f}秒")
        
        if evaluations and evaluations < 10:
            print(f"\\n✅ 結論: ループは数回で早期終了している")
            print(f"   理由: if not trades: で空リスト返却の可能性")
        elif evaluations and evaluations >= 50:
            print(f"\\n❓ 結論: 多数の評価が実行されているが短時間")
            print(f"   理由: 各評価が非常に高速で失敗している可能性")
        else:
            print(f"\\n🤔 結論: さらなる調査が必要")