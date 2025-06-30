"""
File-based Analysis Progress Tracker for Multi-Process Environments

This module replaces the singleton-based AnalysisProgressTracker with a file-based
implementation that works correctly in ProcessPoolExecutor environments.

Key Features:
- Cross-process progress sharing via temporary files
- File locking for atomic operations
- Backward compatible with existing AnalysisProgress API
- Automatic cleanup of old progress files
"""

import os
import json
import fcntl
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

# Import existing progress data structures
from web_dashboard.analysis_progress import (
    AnalysisProgress, SupportResistanceResult, MLPredictionResult,
    MarketContextResult, LeverageDecisionResult
)

logger = logging.getLogger(__name__)

class FileBasedProgressTracker:
    """
    File-based progress tracker that works in multi-process environments.
    
    Uses temporary files with file locking to ensure atomic operations
    and cross-process data sharing.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize file-based progress tracker.
        
        Args:
            base_dir: Base directory for progress files (defaults to system temp)
        """
        if base_dir is None:
            base_dir = tempfile.gettempdir()
        
        self.progress_dir = Path(base_dir) / "analysis_progress"
        self.progress_dir.mkdir(exist_ok=True)
        
        # Cleanup old files on initialization
        self._cleanup_old_files()
    
    def _get_progress_file_path(self, execution_id: str) -> Path:
        """Get the file path for a specific execution ID."""
        return self.progress_dir / f"progress_{execution_id}.json"
    
    def _read_progress_file(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Read progress data from file with file locking.
        
        Args:
            execution_id: Execution ID to read
            
        Returns:
            Progress data as dictionary or None if file doesn't exist
        """
        file_path = self._get_progress_file_path(execution_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return data
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read progress file {file_path}: {e}")
            return None
    
    def _write_progress_file(self, execution_id: str, data: Dict[str, Any]) -> bool:
        """
        Write progress data to file with file locking.
        
        Args:
            execution_id: Execution ID
            data: Progress data to write
            
        Returns:
            True if successful, False otherwise
        """
        file_path = self._get_progress_file_path(execution_id)
        
        try:
            # Write to temporary file first, then atomic rename
            temp_path = file_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Acquire exclusive lock for writing
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Atomic rename
            temp_path.rename(file_path)
            return True
            
        except (IOError, OSError) as e:
            logger.error(f"Failed to write progress file {file_path}: {e}")
            # Cleanup temporary file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            return False
    
    def _dict_to_analysis_progress(self, data: Dict[str, Any]) -> AnalysisProgress:
        """Convert dictionary data to AnalysisProgress object."""
        
        # Helper function to create result objects
        def create_result_object(result_class, result_data):
            if result_data is None:
                return result_class(status="pending")
            return result_class(**result_data)
        
        # Convert datetime string back to datetime object
        start_time = datetime.fromisoformat(data['start_time'])
        
        # Create result objects
        support_resistance = create_result_object(
            SupportResistanceResult, data.get('support_resistance')
        )
        ml_prediction = create_result_object(
            MLPredictionResult, data.get('ml_prediction')
        )
        market_context = create_result_object(
            MarketContextResult, data.get('market_context')
        )
        leverage_decision = create_result_object(
            LeverageDecisionResult, data.get('leverage_decision')
        )
        
        return AnalysisProgress(
            symbol=data['symbol'],
            execution_id=data['execution_id'],
            start_time=start_time,
            current_stage=data.get('current_stage', 'initializing'),
            overall_status=data.get('overall_status', 'running'),
            support_resistance=support_resistance,
            ml_prediction=ml_prediction,
            market_context=market_context,
            leverage_decision=leverage_decision,
            final_signal=data.get('final_signal', 'analyzing'),
            failure_stage=data.get('failure_stage', ''),
            final_message=data.get('final_message', '')
        )
    
    def start_analysis(self, symbol: str, execution_id: str) -> AnalysisProgress:
        """
        Start analysis tracking.
        
        Args:
            symbol: Symbol being analyzed
            execution_id: Unique execution identifier
            
        Returns:
            AnalysisProgress object
        """
        progress = AnalysisProgress(
            symbol=symbol,
            execution_id=execution_id,
            start_time=datetime.now()
        )
        
        # Write to file
        data = progress.to_dict()
        self._write_progress_file(execution_id, data)
        
        logger.info(f"Started analysis tracking for {symbol} (execution_id: {execution_id})")
        return progress
    
    def get_progress(self, execution_id: str) -> Optional[AnalysisProgress]:
        """
        Get current progress for an execution.
        
        Args:
            execution_id: Execution ID to query
            
        Returns:
            AnalysisProgress object or None if not found
        """
        data = self._read_progress_file(execution_id)
        if data is None:
            return None
        
        return self._dict_to_analysis_progress(data)
    
    def update_stage(self, execution_id: str, stage: str) -> bool:
        """
        Update current analysis stage.
        
        Args:
            execution_id: Execution ID
            stage: New stage name
            
        Returns:
            True if successful, False otherwise
        """
        data = self._read_progress_file(execution_id)
        if data is None:
            logger.warning(f"Cannot update stage for non-existent execution: {execution_id}")
            return False
        
        data['current_stage'] = stage
        return self._write_progress_file(execution_id, data)
    
    def update_support_resistance(self, execution_id: str, result: SupportResistanceResult) -> bool:
        """Update support/resistance analysis result."""
        data = self._read_progress_file(execution_id)
        if data is None:
            return False
        
        data['support_resistance'] = asdict(result)
        return self._write_progress_file(execution_id, data)
    
    def update_ml_prediction(self, execution_id: str, result: MLPredictionResult) -> bool:
        """Update ML prediction result."""
        data = self._read_progress_file(execution_id)
        if data is None:
            return False
        
        data['ml_prediction'] = asdict(result)
        return self._write_progress_file(execution_id, data)
    
    def update_market_context(self, execution_id: str, result: MarketContextResult) -> bool:
        """Update market context analysis result."""
        data = self._read_progress_file(execution_id)
        if data is None:
            return False
        
        data['market_context'] = asdict(result)
        return self._write_progress_file(execution_id, data)
    
    def update_leverage_decision(self, execution_id: str, result: LeverageDecisionResult) -> bool:
        """Update leverage decision result."""
        data = self._read_progress_file(execution_id)
        if data is None:
            return False
        
        data['leverage_decision'] = asdict(result)
        return self._write_progress_file(execution_id, data)
    
    def complete_analysis(self, execution_id: str, signal: str, message: str = "") -> bool:
        """
        Mark analysis as completed.
        
        Args:
            execution_id: Execution ID
            signal: Final signal result
            message: Optional completion message
            
        Returns:
            True if successful, False otherwise
        """
        data = self._read_progress_file(execution_id)
        if data is None:
            return False
        
        data.update({
            'overall_status': 'success',
            'current_stage': 'completed',
            'final_signal': signal,
            'final_message': message
        })
        
        return self._write_progress_file(execution_id, data)
    
    def fail_analysis(self, execution_id: str, stage: str, message: str) -> bool:
        """
        Mark analysis as failed.
        
        Args:
            execution_id: Execution ID
            stage: Stage where failure occurred
            message: Failure message
            
        Returns:
            True if successful, False otherwise
        """
        data = self._read_progress_file(execution_id)
        if data is None:
            return False
        
        data.update({
            'overall_status': 'failed',
            'failure_stage': stage,
            'final_signal': 'no_signal',
            'final_message': message
        })
        
        return self._write_progress_file(execution_id, data)
    
    def get_all_recent(self, hours: int = 1) -> List[AnalysisProgress]:
        """
        Get all recent analysis progress entries.
        
        Args:
            hours: Number of hours back to look
            
        Returns:
            List of AnalysisProgress objects
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_progress = []
        
        # Scan all progress files
        for file_path in self.progress_dir.glob("progress_*.json"):
            try:
                data = self._read_progress_file(file_path.stem.replace("progress_", ""))
                if data is None:
                    continue
                
                start_time = datetime.fromisoformat(data['start_time'])
                if start_time >= cutoff_time:
                    progress = self._dict_to_analysis_progress(data)
                    recent_progress.append(progress)
                    
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping invalid progress file {file_path}: {e}")
                continue
        
        # Sort by start time (newest first)
        recent_progress.sort(key=lambda p: p.start_time, reverse=True)
        return recent_progress
    
    def cleanup_old(self, hours: int = 24) -> int:
        """
        Clean up old progress files.
        
        Args:
            hours: Files older than this many hours will be deleted
            
        Returns:
            Number of files cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cleaned_count = 0
        
        for file_path in self.progress_dir.glob("progress_*.json"):
            try:
                # Check file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if file_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.debug(f"Cleaned up old progress file: {file_path}")
                    
            except (OSError, ValueError) as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")
        
        return cleaned_count
    
    def _cleanup_old_files(self):
        """Internal cleanup called during initialization."""
        cleaned = self.cleanup_old(hours=24)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old progress files during initialization")
    
    def get_active_executions(self) -> List[str]:
        """
        Get list of currently active execution IDs.
        
        Returns:
            List of execution IDs that are currently running
        """
        active_executions = []
        
        for file_path in self.progress_dir.glob("progress_*.json"):
            try:
                execution_id = file_path.stem.replace("progress_", "")
                data = self._read_progress_file(execution_id)
                
                if data and data.get('overall_status') == 'running':
                    active_executions.append(execution_id)
                    
            except Exception as e:
                logger.warning(f"Error checking execution status for {file_path}: {e}")
        
        return active_executions

# Create global instance for backward compatibility
file_progress_tracker = FileBasedProgressTracker()