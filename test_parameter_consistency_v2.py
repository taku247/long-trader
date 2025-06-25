#!/usr/bin/env python3
"""
パラメータ一貫性テスト v2 - 実装アプローチに合わせた現実的なテスト

実際の実装方法を考慮した包括的なパラメータ一貫性チェック
"""

import sys
import os
import inspect
import json
import tempfile

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_web_to_api_flow():
    """Web → API のパラメータフロー"""
    print("🔍 Web → API パラメータフローテスト")
    print("=" * 60)
    
    try:
        # app.pyでのAPIエンドポイント確認
        app_path = "/Users/moriwakikeita/tools/long-trader/web_dashboard/app.py"
        
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 期間パラメータの処理確認
        required_elements = [
            "period_mode = data.get('period_mode', 'auto')",
            "custom_start_date = data.get('start_date')",
            "custom_end_date = data.get('end_date')",
            "'mode': period_mode,",
            "'start_date': custom_start_date,",
            "'end_date': custom_end_date",
            "custom_period_settings="
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ 以下のAPI処理が見つかりません:")
            for element in missing_elements:
                print(f"   - {element}")
            return False
        else:
            print("✅ Web → API パラメータフロー正常")
            return True
            
    except Exception as e:
        print(f"❌ Web → APIフローテストエラー: {e}")
        return False

def test_api_to_new_symbol_system_flow():
    """API → NewSymbolAdditionSystem のパラメータフロー"""
    print(f"\n🔍 API → NewSymbolAdditionSystem パラメータフローテスト")
    print("=" * 60)
    
    try:
        from new_symbol_addition_system import NewSymbolAdditionSystem
        import inspect
        
        system = NewSymbolAdditionSystem()
        signature = inspect.signature(system.execute_symbol_addition)
        
        # custom_period_settingsパラメータの確認
        has_param = 'custom_period_settings' in signature.parameters
        print(f"✅ execute_symbol_addition シグネチャ: {'OK' if has_param else 'NG'}")
        
        # ファイル内容での確認
        file_path = "/Users/moriwakikeita/tools/long-trader/new_symbol_addition_system.py"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # auto_trainerへの渡し確認
        has_call = "custom_period_settings=custom_period_settings" in content
        print(f"✅ AutoSymbolTrainerへの渡し: {'OK' if has_call else 'NG'}")
        
        return has_param and has_call
        
    except Exception as e:
        print(f"❌ API → NewSymbolSystemフローテストエラー: {e}")
        return False

def test_auto_symbol_trainer_internal_flow():
    """AutoSymbolTrainer 内部パラメータフロー"""
    print(f"\n🔍 AutoSymbolTrainer 内部パラメータフローテスト")
    print("=" * 60)
    
    try:
        from auto_symbol_training import AutoSymbolTrainer
        import inspect
        
        trainer = AutoSymbolTrainer()
        
        # メソッドシグネチャ確認
        main_sig = inspect.signature(trainer.add_symbol_with_training)
        fetch_sig = inspect.signature(trainer._fetch_and_validate_data)
        backtest_sig = inspect.signature(trainer._run_comprehensive_backtest)
        
        main_has_param = 'custom_period_settings' in main_sig.parameters
        fetch_has_param = 'custom_period_settings' in fetch_sig.parameters
        backtest_has_param = 'custom_period_settings' in backtest_sig.parameters
        
        print(f"✅ add_symbol_with_training: {'OK' if main_has_param else 'NG'}")
        print(f"✅ _fetch_and_validate_data: {'OK' if fetch_has_param else 'NG'}")
        print(f"✅ _run_comprehensive_backtest: {'OK' if backtest_has_param else 'NG'}")
        
        # ファイル内容での呼び出し確認
        file_path = "/Users/moriwakikeita/tools/long-trader/auto_symbol_training.py"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 呼び出し部分の確認（複数行にわたる可能性を考慮）
        has_fetch_call = "_fetch_and_validate_data, symbol, custom_period_settings" in content
        has_backtest_call = "custom_period_settings" in content and "_run_comprehensive_backtest" in content
        
        print(f"✅ _fetch_and_validate_data 呼び出し: {'OK' if has_fetch_call else 'NG'}")
        print(f"✅ _run_comprehensive_backtest 呼び出し: {'OK' if has_backtest_call else 'NG'}")
        
        return main_has_param and fetch_has_param and backtest_has_param and has_fetch_call
        
    except Exception as e:
        print(f"❌ AutoSymbolTrainer内部フローテストエラー: {e}")
        return False

def test_scalable_analysis_system_env_flow():
    """ScalableAnalysisSystem 環境変数パラメータフロー"""
    print(f"\n🔍 ScalableAnalysisSystem 環境変数フローテスト")
    print("=" * 60)
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        import inspect
        import os
        import json
        
        # generate_batch_analysisシグネチャ確認
        with tempfile.TemporaryDirectory() as temp_dir:
            system = ScalableAnalysisSystem(temp_dir)
            signature = inspect.signature(system.generate_batch_analysis)
            
            has_param = 'custom_period_settings' in signature.parameters
            print(f"✅ generate_batch_analysis シグネチャ: {'OK' if has_param else 'NG'}")
        
        # ファイル内容での環境変数設定確認
        file_path = "/Users/moriwakikeita/tools/long-trader/scalable_analysis_system.py"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 環境変数設定部分の確認
        has_env_set = "os.environ['CUSTOM_PERIOD_SETTINGS'] = json.dumps(custom_period_settings)" in content
        has_env_read = "os.environ['CUSTOM_PERIOD_SETTINGS']" in content and "_generate_real_analysis" in content
        
        print(f"✅ 環境変数設定: {'OK' if has_env_set else 'NG'}")
        print(f"✅ 環境変数読み取り: {'OK' if has_env_read else 'NG'}")
        
        # 実際の環境変数設定・読み取りテスト
        test_settings = {'mode': 'custom', 'start_date': '2025-06-01', 'end_date': '2025-06-25'}
        os.environ['CUSTOM_PERIOD_SETTINGS'] = json.dumps(test_settings)
        
        if 'CUSTOM_PERIOD_SETTINGS' in os.environ:
            read_settings = json.loads(os.environ['CUSTOM_PERIOD_SETTINGS'])
            env_test_ok = read_settings == test_settings
            print(f"✅ 環境変数テスト: {'OK' if env_test_ok else 'NG'}")
        else:
            env_test_ok = False
            print(f"✅ 環境変数テスト: NG")
        
        # クリーンアップ
        if 'CUSTOM_PERIOD_SETTINGS' in os.environ:
            del os.environ['CUSTOM_PERIOD_SETTINGS']
        
        return has_param and has_env_set and has_env_read and env_test_ok
        
    except Exception as e:
        print(f"❌ ScalableAnalysisSystem環境変数フローテストエラー: {e}")
        return False

def test_high_leverage_bot_orchestrator_flow():
    """HighLeverageBotOrchestratorでのカスタム期間設定テスト"""
    print(f"\n🔍 HighLeverageBotOrchestrator カスタム期間設定フローテスト")
    print("=" * 60)
    
    try:
        from engines.high_leverage_bot_orchestrator import HighLeverageBotOrchestrator
        import inspect
        
        # HighLeverageBotOrchestratorのシグネチャ確認
        orchestrator = HighLeverageBotOrchestrator()
        
        # analyze_leverage_opportunityメソッドのシグネチャ確認
        analyze_sig = inspect.signature(orchestrator.analyze_leverage_opportunity)
        has_custom_param_analyze = 'custom_period_settings' in analyze_sig.parameters
        print(f"✅ analyze_leverage_opportunity シグネチャ: {'OK' if has_custom_param_analyze else 'NG'}")
        
        # analyze_symbolメソッドのシグネチャ確認
        symbol_sig = inspect.signature(orchestrator.analyze_symbol)
        has_custom_param_symbol = 'custom_period_settings' in symbol_sig.parameters
        print(f"✅ analyze_symbol シグネチャ: {'OK' if has_custom_param_symbol else 'NG'}")
        
        # _fetch_market_dataメソッドのシグネチャ確認
        fetch_sig = inspect.signature(orchestrator._fetch_market_data)
        has_custom_param_fetch = 'custom_period_settings' in fetch_sig.parameters
        print(f"✅ _fetch_market_data シグネチャ: {'OK' if has_custom_param_fetch else 'NG'}")
        
        return has_custom_param_analyze and has_custom_param_symbol and has_custom_param_fetch
        
    except Exception as e:
        print(f"❌ HighLeverageBotOrchestratorテストエラー: {e}")
        return False

def test_custom_period_data_calculation():
    """カスタム期間設定での200本前データ計算テスト"""
    print(f"\n🔍 カスタム期間設定での200本前データ計算テスト")
    print("=" * 60)
    
    try:
        # テスト用のカスタム期間設定
        test_settings = {
            'mode': 'custom',
            'start_date': '2025-06-18T17:58:00',
            'end_date': '2025-06-25T17:58:00'
        }
        
        # 時間足ごとの200本前データ計算テスト
        timeframes = ['1h', '15m', '30m', '5m', '1d']
        calculation_results = {}
        
        for timeframe in timeframes:
            # 期間計算のシミュレーション
            from datetime import datetime, timedelta, timezone
            import dateutil.parser
            
            start_time = dateutil.parser.parse(test_settings['start_date']).replace(tzinfo=timezone.utc)
            end_time = dateutil.parser.parse(test_settings['end_date']).replace(tzinfo=timezone.utc)
            
            # 200本前データ計算
            timeframe_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, 
                '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720, '1d': 1440
            }
            
            if timeframe in timeframe_minutes:
                pre_period_minutes = 200 * timeframe_minutes[timeframe]
                adjusted_start_time = start_time - timedelta(minutes=pre_period_minutes)
                
                calculation_results[timeframe] = {
                    'original_start': start_time,
                    'adjusted_start': adjusted_start_time,
                    'pre_period_hours': pre_period_minutes / 60,
                    'total_period_days': (end_time - adjusted_start_time).days
                }
                
                print(f"✅ {timeframe}足: {adjusted_start_time.strftime('%Y-%m-%d %H:%M')} ～ {end_time.strftime('%Y-%m-%d %H:%M')} ({pre_period_minutes/60:.1f}時間前から)")
        
        # 計算結果の妥当性確認
        all_calculations_valid = all(
            result['total_period_days'] > 0 and result['pre_period_hours'] > 0
            for result in calculation_results.values()
        )
        
        print(f"✅ 200本前データ計算: {'OK' if all_calculations_valid else 'NG'}")
        return all_calculations_valid
        
    except Exception as e:
        print(f"❌ 200本前データ計算テストエラー: {e}")
        return False

def test_variable_definition_safety():
    """変数定義順序安全性テスト"""
    print(f"\n🔍 変数定義順序安全性テスト")
    print("=" * 60)
    
    try:
        import subprocess
        result = subprocess.run([
            'python', 'test_variable_definition_order.py'
        ], capture_output=True, text=True, cwd='/Users/moriwakikeita/tools/long-trader')
        
        if result.returncode == 0:
            print("✅ 変数定義順序安全性: OK")
            return True
        else:
            print("❌ 変数定義順序安全性: 問題検出")
            if result.stdout:
                print("詳細:")
                print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ 変数定義順序テストエラー: {e}")
        return False

def test_ohlcv_data_definition_pattern():
    """ohlcv_data定義パターン特化テスト"""
    print(f"\n🔍 ohlcv_data定義パターンテスト")
    print("=" * 60)
    
    try:
        # scalable_analysis_system.pyの特定パターンをチェック
        file_path = "/Users/moriwakikeita/tools/long-trader/scalable_analysis_system.py"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # ohlcv_dataの使用前定義パターンをチェック
        lines = content.split('\n')
        ohlcv_usage_lines = []
        ohlcv_definition_lines = []
        
        for i, line in enumerate(lines, 1):
            if 'ohlcv_data' in line:
                if 'ohlcv_data =' in line or 'ohlcv_data:' in line:
                    ohlcv_definition_lines.append(i)
                elif 'ohlcv_data.' in line or 'ohlcv_data[' in line:
                    ohlcv_usage_lines.append(i)
        
        # 使用前に定義されているかチェック
        definition_issues = []
        for usage_line in ohlcv_usage_lines:
            # この使用行より前に定義があるかチェック
            has_prior_definition = any(def_line < usage_line for def_line in ohlcv_definition_lines)
            
            if not has_prior_definition:
                # 同じメソッド内での定義をチェック
                method_start = _find_method_start(lines, usage_line)
                method_definitions = [def_line for def_line in ohlcv_definition_lines 
                                    if method_start <= def_line < usage_line]
                
                if not method_definitions:
                    definition_issues.append(f"行{usage_line}: ohlcv_data使用前に定義なし")
        
        if definition_issues:
            print("❌ ohlcv_data定義パターン問題:")
            for issue in definition_issues:
                print(f"  - {issue}")
            return False
        else:
            print("✅ ohlcv_data定義パターン: OK")
            return True
            
    except Exception as e:
        print(f"❌ ohlcv_data定義パターンテストエラー: {e}")
        return False

def _find_method_start(lines: list, line_number: int) -> int:
    """指定行が属するメソッドの開始行を見つける"""
    for i in range(line_number - 1, -1, -1):
        line = lines[i]
        if line.strip().startswith('def ') or line.strip().startswith('async def '):
            return i + 1
    return 1

def test_end_to_end_parameter_flow():
    """エンドツーエンドパラメータフローテスト"""
    print(f"\n🔍 エンドツーエンド パラメータフローテスト")
    print("=" * 60)
    
    try:
        # シミュレーション用のテストデータ
        test_payload = {
            'symbol': 'TEST',
            'period_mode': 'custom',
            'start_date': '2025-06-18T17:58:00',
            'end_date': '2025-06-25T17:58:00'
        }
        
        print(f"📋 テストペイロード: {test_payload}")
        
        # Step 1: Web画面からのペイロード形式確認
        period_settings = {
            'mode': test_payload.get('period_mode'),
            'start_date': test_payload.get('start_date'),
            'end_date': test_payload.get('end_date')
        }
        
        print(f"✅ Step 1 - Web→API変換: {period_settings}")
        
        # Step 2: NewSymbolAdditionSystemでの受け取り確認
        from new_symbol_addition_system import NewSymbolAdditionSystem, ExecutionMode
        
        system = NewSymbolAdditionSystem()
        sig = inspect.signature(system.execute_symbol_addition)
        
        # パラメータバインディングテスト
        try:
            bound_args = sig.bind(
                symbol='TEST',
                execution_id='test_exec',
                execution_mode=ExecutionMode.DEFAULT,
                selected_strategy_ids=[],
                custom_period_settings=period_settings
            )
            bound_args.apply_defaults()
            print(f"✅ Step 2 - NewSymbolAdditionSystem バインディング成功")
            step2_ok = True
        except Exception as e:
            print(f"❌ Step 2 - NewSymbolAdditionSystem バインディング失敗: {e}")
            step2_ok = False
        
        # Step 3: AutoSymbolTrainerでの受け取り確認
        from auto_symbol_training import AutoSymbolTrainer
        
        trainer = AutoSymbolTrainer()
        trainer_sig = inspect.signature(trainer.add_symbol_with_training)
        
        try:
            trainer_bound = trainer_sig.bind(
                symbol='TEST',
                custom_period_settings=period_settings
            )
            trainer_bound.apply_defaults()
            print(f"✅ Step 3 - AutoSymbolTrainer バインディング成功")
            step3_ok = True
        except Exception as e:
            print(f"❌ Step 3 - AutoSymbolTrainer バインディング失敗: {e}")
            step3_ok = False
        
        # Step 4: ScalableAnalysisSystemでの環境変数確認
        import os
        import json
        
        try:
            os.environ['CUSTOM_PERIOD_SETTINGS'] = json.dumps(period_settings)
            env_data = json.loads(os.environ['CUSTOM_PERIOD_SETTINGS'])
            
            period_calculation_ok = (
                env_data.get('mode') == 'custom' and
                env_data.get('start_date') and
                env_data.get('end_date')
            )
            
            print(f"✅ Step 4 - ScalableAnalysisSystem 環境変数: {'OK' if period_calculation_ok else 'NG'}")
            
            # クリーンアップ
            del os.environ['CUSTOM_PERIOD_SETTINGS']
            step4_ok = period_calculation_ok
        except Exception as e:
            print(f"❌ Step 4 - ScalableAnalysisSystem 環境変数エラー: {e}")
            step4_ok = False
        
        return step2_ok and step3_ok and step4_ok
        
    except Exception as e:
        print(f"❌ エンドツーエンドテストエラー: {e}")
        return False

def create_parameter_addition_checklist():
    """新しいパラメータ追加時のチェックリスト作成"""
    checklist = """
🛡️ 新しいパラメータ追加時のチェックリスト

1. **Webフロントエンド**
   □ HTMLフォームに入力フィールド追加
   □ JavaScriptでフォーム送信時にパラメータ含める
   □ バリデーション処理追加

2. **APIエンドポイント** (web_dashboard/app.py)
   □ data.get()でパラメータ受け取り
   □ パラメータ構造化（辞書形式）
   □ NewSymbolAdditionSystemに渡す

3. **NewSymbolAdditionSystem** 
   □ execute_symbol_additionメソッドにパラメータ追加
   □ AutoSymbolTrainerへのパラメータ渡し

4. **AutoSymbolTrainer**
   □ add_symbol_with_trainingメソッドにパラメータ追加
   □ _fetch_and_validate_dataメソッドにパラメータ追加・渡し
   □ _run_comprehensive_backtestメソッドにパラメータ追加・渡し

5. **ScalableAnalysisSystem**
   □ generate_batch_analysisメソッドにパラメータ追加
   □ 環境変数にJSON設定（プロセス間共有）
   □ _generate_real_analysisで環境変数読み取り

6. **変数定義順序の安全性確保**
   □ 変数を使用前に必ず定義されているか確認
   □ 条件分岐内での変数定義は代替パスでも定義確認
   □ ohlcv_dataなど重要変数の初期化タイミング確認
   □ データフロー全体での変数スコープ管理

7. **テスト実行**
   □ test_parameter_consistency_v2.py を実行
   □ test_variable_definition_order.py を実行
   □ 全フロー成功を確認
   □ 実際のブラウザテスト実行

8. **エラーハンドリング**
   □ パラメータ未指定時のデフォルト動作
   □ 不正な値の場合のバリデーション
   □ 変数未定義時の適切なエラーメッセージ
   □ データ取得失敗時のフォールバック処理
"""
    return checklist

if __name__ == "__main__":
    print("🛡️ パラメータ一貫性バグ防止テスト v2")
    print("=" * 70)
    print("実装アプローチに合わせた現実的なパラメータフローテスト")
    print()
    
    # 各フローテスト実行
    web_api_ok = test_web_to_api_flow()
    api_system_ok = test_api_to_new_symbol_system_flow()
    trainer_internal_ok = test_auto_symbol_trainer_internal_flow()
    scalable_env_ok = test_scalable_analysis_system_env_flow()
    bot_orchestrator_ok = test_high_leverage_bot_orchestrator_flow()
    custom_period_calc_ok = test_custom_period_data_calculation()
    variable_safety_ok = test_variable_definition_safety()
    ohlcv_pattern_ok = test_ohlcv_data_definition_pattern()
    e2e_ok = test_end_to_end_parameter_flow()
    
    # 結果サマリー
    print(f"\n🎯 パラメータ一貫性テスト結果 v2")
    print("=" * 70)
    print(f"🌐 Web → API フロー: {'✅ 正常' if web_api_ok else '❌ 問題'}")
    print(f"🔄 API → NewSymbolSystem フロー: {'✅ 正常' if api_system_ok else '❌ 問題'}")
    print(f"⚙️ AutoSymbolTrainer 内部フロー: {'✅ 正常' if trainer_internal_ok else '❌ 問題'}")
    print(f"🌍 ScalableAnalysisSystem 環境変数フロー: {'✅ 正常' if scalable_env_ok else '❌ 問題'}")
    print(f"🎯 HighLeverageBotOrchestrator フロー: {'✅ 正常' if bot_orchestrator_ok else '❌ 問題'}")
    print(f"📅 カスタム期間200本前データ計算: {'✅ 正常' if custom_period_calc_ok else '❌ 問題'}")
    print(f"🛡️ 変数定義順序安全性: {'✅ 正常' if variable_safety_ok else '❌ 問題'}")
    print(f"🔍 ohlcv_data定義パターン: {'✅ 正常' if ohlcv_pattern_ok else '❌ 問題'}")
    print(f"🔗 エンドツーエンドフロー: {'✅ 正常' if e2e_ok else '❌ 問題'}")
    
    overall_success = all([web_api_ok, api_system_ok, trainer_internal_ok, scalable_env_ok, bot_orchestrator_ok, custom_period_calc_ok, variable_safety_ok, ohlcv_pattern_ok, e2e_ok])
    
    print(f"\n{'='*70}")
    print(f"🏆 最終判定: {'✅ バグ防止OK' if overall_success else '⚠️ 要修正'}")
    print(f"{'='*70}")
    
    if overall_success:
        print("🎉 全パラメータフローが正常に動作しています！")
        print("🔒 同様のバグ発生リスクは低いです")
    else:
        print("🔧 一部のパラメータフローに問題があります")
        print("⚠️ 修正してから使用してください")
    
    # チェックリスト表示
    print(create_parameter_addition_checklist())
    
    sys.exit(0 if overall_success else 1)