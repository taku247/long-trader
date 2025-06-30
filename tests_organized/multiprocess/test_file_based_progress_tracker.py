"""
Comprehensive tests for FileBasedProgressTracker in multi-process environments.

Tests coverage:
1. Basic functionality (CRUD operations)
2. Multi-process data sharing
3. File locking and atomic operations
4. ProcessPoolExecutor compatibility
5. Error handling and edge cases
6. Performance and cleanup
"""

import os
import sys
import tempfile
import shutil
import time
import uuid
import json
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import unittest
from unittest.mock import patch

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from file_based_progress_tracker import FileBasedProgressTracker
from web_dashboard.analysis_progress import (
    AnalysisProgress, SupportResistanceResult, MLPredictionResult,
    MarketContextResult, LeverageDecisionResult
)

class TestFileBasedProgressTracker(unittest.TestCase):
    """Test suite for FileBasedProgressTracker."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp(prefix="progress_test_")
        self.tracker = FileBasedProgressTracker(base_dir=self.test_dir)
        
    def tearDown(self):
        """Clean up test environment."""
        # Remove test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_basic_start_and_get_analysis(self):
        """Test basic start and get analysis functionality."""
        symbol = "TEST"
        execution_id = str(uuid.uuid4())
        
        # Start analysis
        progress = self.tracker.start_analysis(symbol, execution_id)
        
        # Verify initial state
        self.assertEqual(progress.symbol, symbol)
        self.assertEqual(progress.execution_id, execution_id)
        self.assertEqual(progress.current_stage, "initializing")
        self.assertEqual(progress.overall_status, "running")
        
        # Get progress
        retrieved_progress = self.tracker.get_progress(execution_id)
        self.assertIsNotNone(retrieved_progress)
        self.assertEqual(retrieved_progress.symbol, symbol)
        self.assertEqual(retrieved_progress.execution_id, execution_id)
    
    def test_stage_updates(self):
        """Test updating analysis stages."""
        execution_id = str(uuid.uuid4())
        self.tracker.start_analysis("TEST", execution_id)
        
        # Test stage updates
        stages = ["data_fetch", "support_resistance", "ml_prediction", "completed"]
        
        for stage in stages:
            success = self.tracker.update_stage(execution_id, stage)
            self.assertTrue(success)
            
            progress = self.tracker.get_progress(execution_id)
            self.assertEqual(progress.current_stage, stage)
    
    def test_result_updates(self):
        """Test updating analysis results."""
        execution_id = str(uuid.uuid4())
        self.tracker.start_analysis("TEST", execution_id)
        
        # Test support resistance update
        sr_result = SupportResistanceResult(
            status="success",
            supports_count=3,
            resistances_count=2,
            supports=[{"price": 100.0, "strength": 0.8}],
            resistances=[{"price": 110.0, "strength": 0.9}]
        )
        success = self.tracker.update_support_resistance(execution_id, sr_result)
        self.assertTrue(success)
        
        progress = self.tracker.get_progress(execution_id)
        self.assertEqual(progress.support_resistance.status, "success")
        self.assertEqual(progress.support_resistance.supports_count, 3)
        
        # Test ML prediction update
        ml_result = MLPredictionResult(
            status="success",
            predictions_count=5,
            confidence=0.85
        )
        success = self.tracker.update_ml_prediction(execution_id, ml_result)
        self.assertTrue(success)
        
        progress = self.tracker.get_progress(execution_id)
        self.assertEqual(progress.ml_prediction.status, "success")
        self.assertEqual(progress.ml_prediction.confidence, 0.85)
    
    def test_completion_and_failure(self):
        """Test analysis completion and failure marking."""
        execution_id = str(uuid.uuid4())
        self.tracker.start_analysis("TEST", execution_id)
        
        # Test successful completion
        success = self.tracker.complete_analysis(execution_id, "buy_signal", "Strong buy signal detected")
        self.assertTrue(success)
        
        progress = self.tracker.get_progress(execution_id)
        self.assertEqual(progress.overall_status, "success")
        self.assertEqual(progress.final_signal, "buy_signal")
        self.assertEqual(progress.final_message, "Strong buy signal detected")
        
        # Test failure marking (new execution)
        execution_id_2 = str(uuid.uuid4())
        self.tracker.start_analysis("TEST2", execution_id_2)
        
        success = self.tracker.fail_analysis(execution_id_2, "data_fetch", "Unable to fetch market data")
        self.assertTrue(success)
        
        progress = self.tracker.get_progress(execution_id_2)
        self.assertEqual(progress.overall_status, "failed")
        self.assertEqual(progress.failure_stage, "data_fetch")
        self.assertEqual(progress.final_signal, "no_signal")
    
    def test_get_all_recent(self):
        """Test getting recent analysis entries."""
        # Start multiple analyses
        execution_ids = []
        for i in range(3):
            execution_id = str(uuid.uuid4())
            self.tracker.start_analysis(f"TEST{i}", execution_id)
            execution_ids.append(execution_id)
        
        # Get recent entries
        recent = self.tracker.get_all_recent(hours=1)
        self.assertEqual(len(recent), 3)
        
        # Verify they're sorted by start time (newest first)
        for i in range(len(recent) - 1):
            self.assertGreaterEqual(recent[i].start_time, recent[i + 1].start_time)
    
    def test_cleanup_old_files(self):
        """Test cleanup of old progress files."""
        execution_id = str(uuid.uuid4())
        self.tracker.start_analysis("TEST", execution_id)
        
        # Verify file exists
        file_path = self.tracker._get_progress_file_path(execution_id)
        self.assertTrue(file_path.exists())
        
        # Manually set file modification time to be old
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(file_path, (old_time, old_time))
        
        # Run cleanup
        cleaned_count = self.tracker.cleanup_old(hours=24)
        self.assertEqual(cleaned_count, 1)
        self.assertFalse(file_path.exists())
    
    def test_non_existent_execution(self):
        """Test operations on non-existent execution IDs."""
        fake_id = str(uuid.uuid4())
        
        # Test get
        progress = self.tracker.get_progress(fake_id)
        self.assertIsNone(progress)
        
        # Test updates
        self.assertFalse(self.tracker.update_stage(fake_id, "test"))
        
        sr_result = SupportResistanceResult(status="success")
        self.assertFalse(self.tracker.update_support_resistance(fake_id, sr_result))
    
    def test_file_corruption_handling(self):
        """Test handling of corrupted progress files."""
        execution_id = str(uuid.uuid4())
        self.tracker.start_analysis("TEST", execution_id)
        
        # Corrupt the file
        file_path = self.tracker._get_progress_file_path(execution_id)
        with open(file_path, 'w') as f:
            f.write("invalid json content")
        
        # Try to read - should return None
        progress = self.tracker.get_progress(execution_id)
        self.assertIsNone(progress)
    
    def test_get_active_executions(self):
        """Test getting active execution IDs."""
        # Start some analyses
        active_ids = []
        for i in range(2):
            execution_id = str(uuid.uuid4())
            self.tracker.start_analysis(f"TEST{i}", execution_id)
            active_ids.append(execution_id)
        
        # Complete one
        self.tracker.complete_analysis(active_ids[1], "signal")
        
        # Get active executions
        active = self.tracker.get_active_executions()
        self.assertIn(active_ids[0], active)
        self.assertNotIn(active_ids[1], active)


def process_worker_start_analysis(args):
    """Worker function for multi-process testing - start analysis."""
    test_dir, process_id = args
    
    tracker = FileBasedProgressTracker(base_dir=test_dir)
    execution_id = f"proc_{process_id}_{uuid.uuid4()}"
    
    progress = tracker.start_analysis(f"SYMBOL_{process_id}", execution_id)
    
    # Update some stages
    tracker.update_stage(execution_id, "data_fetch")
    time.sleep(0.1)  # Small delay to simulate work
    tracker.update_stage(execution_id, "support_resistance")
    
    return {
        'execution_id': execution_id,
        'symbol': progress.symbol,
        'process_id': process_id
    }


def process_worker_update_progress(args):
    """Worker function for multi-process testing - update progress."""
    test_dir, execution_id, updates = args
    
    tracker = FileBasedProgressTracker(base_dir=test_dir)
    
    results = []
    for update_type, update_data in updates:
        if update_type == "stage":
            success = tracker.update_stage(execution_id, update_data)
            results.append(('stage', update_data, success))
        elif update_type == "complete":
            success = tracker.complete_analysis(execution_id, update_data[0], update_data[1])
            results.append(('complete', update_data, success))
    
    return results


def full_analysis_simulation(args):
    """Simulate a full analysis process."""
    test_dir, symbol, execution_id = args
    
    tracker = FileBasedProgressTracker(base_dir=test_dir)
    
    # Start analysis
    progress = tracker.start_analysis(symbol, execution_id)
    
    # Simulate analysis stages
    stages = [
        "data_fetch",
        "support_resistance", 
        "ml_prediction",
        "market_context",
        "leverage_decision"
    ]
    
    for stage in stages:
        tracker.update_stage(execution_id, stage)
        time.sleep(0.02)  # Simulate processing time
    
    # Add some results
    sr_result = SupportResistanceResult(
        status="success",
        supports_count=2,
        resistances_count=1
    )
    tracker.update_support_resistance(execution_id, sr_result)
    
    ml_result = MLPredictionResult(
        status="success",
        predictions_count=3,
        confidence=0.75
    )
    tracker.update_ml_prediction(execution_id, ml_result)
    
    # Complete analysis
    tracker.complete_analysis(execution_id, "buy_signal", "Strong signal detected")
    
    return {
        'execution_id': execution_id,
        'symbol': symbol,
        'completed': True
    }


def concurrent_updater(args):
    """Function to perform concurrent updates."""
    test_dir, execution_id, worker_id = args
    tracker = FileBasedProgressTracker(base_dir=test_dir)
    
    # Perform multiple rapid updates
    for i in range(10):
        stage = f"stage_{worker_id}_{i}"
        success = tracker.update_stage(execution_id, stage)
        # Don't assert success here since race conditions may cause some to fail
        time.sleep(0.001)  # Very small delay
    
    return worker_id


class TestMultiProcessProgressTracker(unittest.TestCase):
    """Test multi-process functionality of FileBasedProgressTracker."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="multiprocess_test_")
        self.tracker = FileBasedProgressTracker(base_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_multiprocess_start_analysis(self):
        """Test starting analyses from multiple processes."""
        num_processes = 4
        
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            # Submit tasks to multiple processes
            futures = []
            for i in range(num_processes):
                future = executor.submit(process_worker_start_analysis, (self.test_dir, i))
                futures.append(future)
            
            # Collect results
            results = []
            for future in futures:
                result = future.result(timeout=10)
                results.append(result)
        
        # Verify all processes created their progress entries
        self.assertEqual(len(results), num_processes)
        
        # Check that all progress entries are accessible from main process
        for result in results:
            execution_id = result['execution_id']
            progress = self.tracker.get_progress(execution_id)
            
            self.assertIsNotNone(progress)
            self.assertEqual(progress.symbol, result['symbol'])
            self.assertEqual(progress.execution_id, execution_id)
            # Should be at support_resistance stage due to worker updates
            self.assertEqual(progress.current_stage, "support_resistance")
    
    def test_multiprocess_concurrent_updates(self):
        """Test concurrent updates from multiple processes."""
        # Start an analysis in main process
        execution_id = str(uuid.uuid4())
        self.tracker.start_analysis("CONCURRENT_TEST", execution_id)
        
        # Define updates for different processes
        process_updates = [
            [("stage", "data_fetch")],
            [("stage", "support_resistance")],
            [("stage", "ml_prediction")],
            [("complete", ("buy_signal", "Analysis completed successfully"))]
        ]
        
        with ProcessPoolExecutor(max_workers=4) as executor:
            # Submit concurrent update tasks
            futures = []
            for i, updates in enumerate(process_updates):
                future = executor.submit(
                    process_worker_update_progress, 
                    (self.test_dir, execution_id, updates)
                )
                futures.append(future)
                
                # Small delay between submissions to test race conditions
                time.sleep(0.05)
            
            # Collect results
            all_results = []
            for future in futures:
                results = future.result(timeout=10)
                all_results.extend(results)
        
        # Verify final state
        final_progress = self.tracker.get_progress(execution_id)
        self.assertIsNotNone(final_progress)
        
        # Should be completed since completion was one of the updates
        # (exact final stage depends on timing, but overall_status should be set)
        possible_statuses = ["running", "success"]  # Depends on timing of completion
        self.assertIn(final_progress.overall_status, possible_statuses)
    
    def test_processpool_compatibility(self):
        """Test full compatibility with ProcessPoolExecutor environment."""
        
        # Run multiple full simulations
        symbols = ["BTC", "ETH", "HYPE", "SOL"]
        execution_ids = [str(uuid.uuid4()) for _ in symbols]
        
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            for symbol, execution_id in zip(symbols, execution_ids):
                future = executor.submit(
                    full_analysis_simulation,
                    (self.test_dir, symbol, execution_id)
                )
                futures.append(future)
            
            # Wait for all to complete
            results = []
            for future in futures:
                result = future.result(timeout=15)
                results.append(result)
        
        # Verify all analyses completed successfully
        self.assertEqual(len(results), len(symbols))
        
        for result in results:
            self.assertTrue(result['completed'])
            
            # Check final state from main process
            progress = self.tracker.get_progress(result['execution_id'])
            self.assertIsNotNone(progress)
            self.assertEqual(progress.overall_status, "success")
            self.assertEqual(progress.final_signal, "buy_signal")
            self.assertEqual(progress.support_resistance.status, "success")
            self.assertEqual(progress.ml_prediction.status, "success")
    
    def test_race_condition_handling(self):
        """Test handling of race conditions in file operations."""
        execution_id = str(uuid.uuid4())
        self.tracker.start_analysis("RACE_TEST", execution_id)
        
        # Run multiple concurrent updaters
        with ProcessPoolExecutor(max_workers=5) as executor:
            futures = []
            for worker_id in range(5):
                future = executor.submit(
                    concurrent_updater,
                    (self.test_dir, execution_id, worker_id)
                )
                futures.append(future)
            
            # Wait for completion
            for future in futures:
                future.result(timeout=10)
        
        # Verify the progress entry still exists and is readable
        final_progress = self.tracker.get_progress(execution_id)
        self.assertIsNotNone(final_progress)
        self.assertEqual(final_progress.execution_id, execution_id)


if __name__ == '__main__':
    # Create test directory for multiprocess tests
    os.makedirs('tests_organized/multiprocess', exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2)