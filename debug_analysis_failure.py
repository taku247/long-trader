#!/usr/bin/env python3
"""
Debug script to identify why analysis results are not being saved to database
"""

import os
import sys
import traceback
import logging
from pathlib import Path

# Setup logging to capture all errors
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_analysis_step_by_step():
    """Test each step of the analysis process to identify failure point"""
    
    try:
        print("=== Testing ScalableAnalysisSystem Analysis Process ===")
        
        # Import system
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem()
        
        # Test symbol and config
        symbol = "ETH"
        timeframe = "1h"
        config = "Conservative_ML"
        
        print(f"\n1. Testing analysis existence check...")
        analysis_id = f"{symbol}_{timeframe}_{config}"
        exists = system._analysis_exists(analysis_id)
        print(f"   Analysis exists: {exists}")
        
        print(f"\n2. Testing real analysis generation...")
        try:
            # Set execution ID environment variable
            os.environ['CURRENT_EXECUTION_ID'] = 'debug_test_12345'
            
            trades_data = system._generate_real_analysis(symbol, timeframe, config)
            print(f"   Real analysis result: {len(trades_data) if trades_data else 0} trades generated")
            
            if trades_data:
                print(f"   Sample trade data: {trades_data[:2] if len(trades_data) >= 2 else trades_data}")
                
                print(f"\n3. Testing metrics calculation...")
                metrics = system._calculate_metrics(trades_data)
                print(f"   Metrics: {metrics}")
                
                print(f"\n4. Testing compressed data save...")
                compressed_path = system._save_compressed_data(analysis_id, trades_data)
                print(f"   Compressed path: {compressed_path}")
                
                print(f"\n5. Testing database save...")
                execution_id = os.environ.get('CURRENT_EXECUTION_ID')
                system._save_to_database(symbol, timeframe, config, metrics, None, compressed_path, execution_id)
                print(f"   Database save: SUCCESS")
                
                print(f"\n6. Verifying database entry...")
                # Check if data was actually saved
                import sqlite3
                with sqlite3.connect(system.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM analyses WHERE symbol=? AND timeframe=? AND config=?",
                        (symbol, timeframe, config)
                    )
                    count = cursor.fetchone()[0]
                    print(f"   Database entries for {symbol} {timeframe} {config}: {count}")
                    
                    # Get the actual record
                    cursor = conn.execute(
                        "SELECT * FROM analyses WHERE symbol=? AND timeframe=? AND config=? ORDER BY generated_at DESC LIMIT 1",
                        (symbol, timeframe, config)
                    )
                    record = cursor.fetchone()
                    if record:
                        print(f"   Latest record: ID={record[0]}, trades={record[5]}, sharpe={record[8]}")
                    else:
                        print(f"   No record found!")
            else:
                print("   No trades data generated - this is the likely cause of empty analyses table")
                
        except Exception as analysis_error:
            print(f"   Real analysis FAILED: {analysis_error}")
            print(f"   Traceback: {traceback.format_exc()}")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
    
    return True

def check_database_schema():
    """Check if database schema matches expectations"""
    print("\n=== Checking Database Schema ===")
    
    try:
        from scalable_analysis_system import ScalableAnalysisSystem
        system = ScalableAnalysisSystem()
        
        import sqlite3
        with sqlite3.connect(system.db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(analyses)")
            columns = cursor.fetchall()
            
            print("Current analyses table columns:")
            for col in columns:
                print(f"   {col[1]} ({col[2]}) - NOT NULL: {col[3]} - DEFAULT: {col[4]}")
                
            # Check if execution_id column exists
            column_names = [col[1] for col in columns]
            if 'execution_id' in column_names:
                print("✅ execution_id column exists")
            else:
                print("❌ execution_id column missing")
                
            if 'status' in column_names:
                print("✅ status column exists")
            else:
                print("❌ status column missing")
                
    except Exception as e:
        print(f"Schema check failed: {e}")

def main():
    print("Debug Analysis Failure Script")
    print("="*50)
    
    # Check database schema first
    check_database_schema()
    
    # Test the analysis process step by step
    success = test_analysis_step_by_step()
    
    if success:
        print("\n✅ All analysis steps completed successfully")
    else:
        print("\n❌ Analysis process failed at some step")

if __name__ == "__main__":
    main()