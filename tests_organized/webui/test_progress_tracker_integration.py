"""
WebUI integration tests for FileBasedProgressTracker.

Tests verify that the WebUI can correctly access progress data
from ProcessPoolExecutor environments using the file-based tracker.
"""

import sys
import os
import tempfile
import shutil
import uuid
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import unittest

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from file_based_progress_tracker import FileBasedProgressTracker
from web_dashboard.analysis_progress import (
    AnalysisProgress, SupportResistanceResult, MLPredictionResult
)

def simulate_background_analysis(args):
    """Simulate background analysis process like auto_symbol_training.py would do."""
    test_dir, symbol, execution_id = args
    
    # Create tracker in child process (like ProcessPoolExecutor does)
    tracker = FileBasedProgressTracker(base_dir=test_dir)
    
    # Start analysis
    tracker.start_analysis(symbol, execution_id)
    
    # Simulate progressive analysis stages
    stages_and_delays = [
        ("data_fetch", 0.1),
        ("support_resistance", 0.2),
        ("ml_prediction", 0.15),
        ("market_context", 0.1),
        ("leverage_decision", 0.05)
    ]
    
    for stage, delay in stages_and_delays:
        tracker.update_stage(execution_id, stage)
        time.sleep(delay)  # Simulate processing time
        
        # Add some realistic results
        if stage == "support_resistance":
            sr_result = SupportResistanceResult(
                status="success",
                supports_count=3,
                resistances_count=2,
                supports=[{"price": 100.0, "strength": 0.8}],
                resistances=[{"price": 110.0, "strength": 0.9}]
            )
            tracker.update_support_resistance(execution_id, sr_result)
            
        elif stage == "ml_prediction":
            ml_result = MLPredictionResult(
                status="success",
                predictions_count=5,
                confidence=0.82
            )
            tracker.update_ml_prediction(execution_id, ml_result)
    
    # Complete the analysis
    tracker.complete_analysis(execution_id, "buy_signal", "Strong bullish signal detected")
    
    return {
        'execution_id': execution_id,
        'symbol': symbol,
        'final_stage': 'completed',
        'status': 'success'
    }

class TestWebUIProgressIntegration(unittest.TestCase):
    """Test WebUI integration with FileBasedProgressTracker."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="webui_test_")
        self.tracker = FileBasedProgressTracker(base_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_webui_can_track_background_process(self):
        """Test that WebUI can track progress of background ProcessPoolExecutor task."""
        symbol = "HYPE"
        execution_id = str(uuid.uuid4())
        
        # Start background analysis (simulating auto_symbol_training.py)
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(simulate_background_analysis, (self.test_dir, symbol, execution_id))
            
            # While analysis is running, simulate WebUI checking progress
            webui_tracker = FileBasedProgressTracker(base_dir=self.test_dir)
            
            # Give the background process a moment to start
            time.sleep(0.05)
            
            # WebUI should be able to see the progress
            seen_stages = set()
            max_attempts = 20
            attempt = 0
            
            while attempt < max_attempts:
                progress = webui_tracker.get_progress(execution_id)
                
                if progress is not None:
                    seen_stages.add(progress.current_stage)
                    
                    # Check if we can see intermediate results
                    if progress.current_stage == "support_resistance" and progress.support_resistance.status == "success":
                        self.assertEqual(progress.support_resistance.supports_count, 3)
                        self.assertEqual(progress.support_resistance.resistances_count, 2)
                    
                    if progress.current_stage == "ml_prediction" and progress.ml_prediction.status == "success":
                        self.assertEqual(progress.ml_prediction.confidence, 0.82)
                    
                    # If completed, break
                    if progress.overall_status == "success":
                        self.assertEqual(progress.final_signal, "buy_signal")
                        break
                
                time.sleep(0.05)
                attempt += 1
            
            # Wait for background process to complete
            result = future.result(timeout=10)
            
            # Verify background process completed successfully
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['final_stage'], 'completed')
            
            # Verify WebUI saw multiple stages during execution
            expected_stages = {"initializing", "data_fetch", "support_resistance", "ml_prediction"}
            self.assertTrue(expected_stages.intersection(seen_stages), 
                          f"WebUI should have seen some of these stages: {expected_stages}, but saw: {seen_stages}")
    
    def test_webui_multiple_concurrent_analyses(self):
        """Test WebUI can track multiple concurrent analyses."""
        symbols = ["BTC", "ETH", "HYPE"]
        execution_ids = [str(uuid.uuid4()) for _ in symbols]
        
        # Start multiple background analyses
        with ProcessPoolExecutor(max_workers=3) as executor:
            futures = []
            for symbol, execution_id in zip(symbols, execution_ids):
                future = executor.submit(simulate_background_analysis, (self.test_dir, symbol, execution_id))
                futures.append(future)
            
            # WebUI tracker to monitor all
            webui_tracker = FileBasedProgressTracker(base_dir=self.test_dir)
            
            # Monitor all executions
            completed_count = 0
            max_checks = 50
            check_count = 0
            
            while completed_count < len(symbols) and check_count < max_checks:
                for execution_id in execution_ids:
                    progress = webui_tracker.get_progress(execution_id)
                    if progress and progress.overall_status == "success":
                        completed_count += 1
                
                time.sleep(0.1)
                check_count += 1
            
            # Wait for all to complete
            results = []
            for future in futures:
                result = future.result(timeout=15)
                results.append(result)
            
            # Verify all completed successfully
            self.assertEqual(len(results), len(symbols))
            for result in results:
                self.assertEqual(result['status'], 'success')
            
            # Verify WebUI can see all final states
            for execution_id in execution_ids:
                final_progress = webui_tracker.get_progress(execution_id)
                self.assertIsNotNone(final_progress)
                self.assertEqual(final_progress.overall_status, "success")
    
    def test_webui_recent_analyses_api(self):
        """Test WebUI's get_all_recent functionality with background processes."""
        # Start a background analysis
        symbol = "SOL"
        execution_id = str(uuid.uuid4())
        
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(simulate_background_analysis, (self.test_dir, symbol, execution_id))
            
            # Let it run for a bit
            time.sleep(0.2)
            
            # WebUI checks recent analyses
            webui_tracker = FileBasedProgressTracker(base_dir=self.test_dir)
            recent_analyses = webui_tracker.get_all_recent(hours=1)
            
            # Should find the running analysis
            self.assertGreater(len(recent_analyses), 0)
            
            # Find our analysis
            our_analysis = None
            for analysis in recent_analyses:
                if analysis.execution_id == execution_id:
                    our_analysis = analysis
                    break
            
            self.assertIsNotNone(our_analysis)
            self.assertEqual(our_analysis.symbol, symbol)
            
            # Wait for completion
            result = future.result(timeout=10)
            self.assertEqual(result['status'], 'success')
            
            # Check recent analyses again - should show completed
            recent_analyses = webui_tracker.get_all_recent(hours=1)
            our_analysis = None
            for analysis in recent_analyses:
                if analysis.execution_id == execution_id:
                    our_analysis = analysis
                    break
            
            self.assertIsNotNone(our_analysis)
            self.assertEqual(our_analysis.overall_status, "success")
    
    def test_webui_active_executions_tracking(self):
        """Test WebUI can track active vs completed executions."""
        webui_tracker = FileBasedProgressTracker(base_dir=self.test_dir)
        
        # Start multiple analyses with different completion times
        quick_execution_id = str(uuid.uuid4())
        slow_execution_id = str(uuid.uuid4())
        
        with ProcessPoolExecutor(max_workers=2) as executor:
            # Quick analysis (will complete first)
            webui_tracker.start_analysis("QUICK", quick_execution_id)
            webui_tracker.complete_analysis(quick_execution_id, "signal", "Quick completion")
            
            # Slow analysis (will run longer)
            future = executor.submit(simulate_background_analysis, (self.test_dir, "SLOW", slow_execution_id))
            
            # Give slow analysis time to start and be detectable
            time.sleep(0.2)
            
            # Check active executions (retry a few times to handle timing)
            active_executions = []
            for _ in range(5):
                active_executions = webui_tracker.get_active_executions()
                if slow_execution_id in active_executions:
                    break
                time.sleep(0.1)
            
            # Should include slow execution but not quick (already completed)
            self.assertIn(slow_execution_id, active_executions)
            self.assertNotIn(quick_execution_id, active_executions)
            
            # Wait for slow to complete
            result = future.result(timeout=10)
            self.assertEqual(result['status'], 'success')
            
            # Now no executions should be active
            active_executions = webui_tracker.get_active_executions()
            self.assertNotIn(slow_execution_id, active_executions)

if __name__ == '__main__':
    # Create test directory
    os.makedirs('tests_organized/webui', exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2)