"""
新しい分析結果検証メソッドの実装
auto_symbol_training.pyに追加するメソッド群
"""

def _verify_analysis_results_detailed(self, symbol: str, execution_id: str) -> Dict[str, Any]:
    """分析結果の詳細確認（Early Exit結果を含む）"""
    try:
        from engines.analysis_result import AnalysisResult
        import sqlite3
        from pathlib import Path
        
        # 結果サマリー初期化
        summary = {
            'has_results': False,
            'has_early_exits': False,
            'signal_count': 0,
            'early_exit_count': 0,
            'early_exit_reasons': {},
            'total_evaluations': 0,
            'detailed_breakdown': []
        }
        
        analysis_db_path = Path(__file__).parent / "large_scale_analysis" / "analysis.db"
        if not analysis_db_path.exists():
            self.logger.warning(f"Analysis database not found: {analysis_db_path}")
            return summary
            
        with sqlite3.connect(analysis_db_path) as conn:
            # 1. 該当execution_idの分析結果を確認
            cursor = conn.execute('''
                SELECT COUNT(*), SUM(total_trades), COUNT(CASE WHEN total_trades > 0 THEN 1 END) as signal_count
                FROM analyses 
                WHERE symbol = ? AND execution_id = ?
            ''', (symbol, execution_id))
            
            result = cursor.fetchone()
            total_records, total_trades, signal_count = result if result else (0, 0, 0)
            
            summary['total_evaluations'] = total_records or 0
            summary['signal_count'] = signal_count or 0
            summary['has_results'] = (signal_count or 0) > 0
            
            if total_records > 0:
                self.logger.info(f"✅ {symbol} の分析結果確認（execution_id一致）: {total_records} 件 (シグナル: {signal_count}件)")
            
            # 2. 過去10分以内の分析結果を確認（バックテスト処理が完了している場合）
            if summary['total_evaluations'] == 0:
                cursor = conn.execute('''
                    SELECT COUNT(*), SUM(total_trades), COUNT(CASE WHEN total_trades > 0 THEN 1 END) as signal_count
                    FROM analyses 
                    WHERE symbol = ? 
                    AND generated_at > datetime('now', '-10 minutes')
                ''', (symbol,))
                
                result = cursor.fetchone()
                recent_records, recent_trades, recent_signals = result if result else (0, 0, 0)
                
                if recent_records > 0:
                    summary['total_evaluations'] = recent_records
                    summary['signal_count'] = recent_signals or 0
                    summary['has_results'] = (recent_signals or 0) > 0
                    self.logger.info(f"✅ {symbol} の最近の分析結果確認: {recent_records} 件 (シグナル: {recent_signals}件)")
            
            # 3. Early Exit結果の推定（記録なし = Early Exitの可能性）
            if summary['total_evaluations'] == 0:
                # ファイルベース進捗トラッカーでEarly Exit結果を確認
                early_exit_summary = self._check_early_exit_from_progress(execution_id)
                summary.update(early_exit_summary)
            
            return summary
            
    except Exception as e:
        self.logger.error(f"分析結果確認エラー: {e}")
        summary['error'] = str(e)
        return summary

def _check_early_exit_from_progress(self, execution_id: str) -> Dict[str, Any]:
    """進捗トラッカーからEarly Exit情報を取得"""
    early_exit_info = {
        'has_early_exits': False,
        'early_exit_count': 0,
        'early_exit_reasons': {},
        'detailed_breakdown': []
    }
    
    try:
        from file_based_progress_tracker import FileBasedProgressTracker
        tracker = FileBasedProgressTracker()
        progress_data = tracker.get_progress(execution_id)
        
        if progress_data and progress_data.get('ml_prediction', {}).get('status') == 'failed':
            # Early Exitのケースを検出
            error_msg = progress_data.get('ml_prediction', {}).get('error_message', '')
            
            if 'サポート・レジスタンスレベルが検出されませんでした' in error_msg:
                early_exit_info['has_early_exits'] = True
                early_exit_info['early_exit_count'] = 1
                early_exit_info['early_exit_reasons']['no_support_resistance'] = 1
                early_exit_info['detailed_breakdown'].append({
                    'stage': 'support_resistance',
                    'reason': 'no_support_resistance_levels',
                    'message': error_msg
                })
                self.logger.info(f"✅ Early Exit情報を進捗トラッカーから検出")
        
    except Exception as e:
        self.logger.warning(f"進捗トラッカーからのEarly Exit情報取得失敗: {e}")
    
    return early_exit_info

def _display_analysis_summary(self, summary: Dict[str, Any]):
    """分析結果サマリーを表示"""
    self.logger.info("\n" + "=" * 60)
    self.logger.info("📊 分析結果サマリー")
    self.logger.info("=" * 60)
    
    total_evals = summary.get('total_evaluations', 0)
    signal_count = summary.get('signal_count', 0)
    early_exit_count = summary.get('early_exit_count', 0)
    
    self.logger.info(f"🔍 総評価数: {total_evals}回")
    
    if signal_count > 0:
        self.logger.info(f"✅ シグナル検出: {signal_count}回")
    
    if early_exit_count > 0:
        self.logger.info(f"⏭️ Early Exit: {early_exit_count}回")
        
        # Early Exit理由の詳細
        for reason, count in summary.get('early_exit_reasons', {}).items():
            reason_names = {
                'no_support_resistance': 'サポート・レジスタンスレベル未検出',
                'insufficient_data': 'データ不足',
                'ml_prediction_failed': 'ML予測失敗',
                'btc_correlation_failed': 'BTC相関分析失敗',
                'market_context_failed': '市場コンテキスト失敗',
                'leverage_conditions_not_met': 'レバレッジ条件未達'
            }
            reason_name = reason_names.get(reason, reason)
            self.logger.info(f"  • {reason_name}: {count}回")
    
    if total_evals == 0 and early_exit_count == 0:
        self.logger.warning("⚠️ 分析結果が未検出 - 処理が完了していない可能性があります")
    
    self.logger.info("=" * 60)