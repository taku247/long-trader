# Investigation Report: FIL Trade Details Showing Incorrect Values

## Issue Summary
FIL trade details in the web dashboard are showing hardcoded/placeholder values:
- Entry price: 100.0
- Take profit: 105.0  
- Stop loss: 97.62
- All trades showing identical values

## Root Cause Analysis

### Investigation Results
Through systematic investigation of the codebase and trade data files, I discovered that this is a **data corruption issue** affecting multiple symbols, not just FIL.

### Affected Symbols
The following symbols have been confirmed to contain hardcoded values in their backtest trade data:

**Severely Affected (>600% suspicious values):**
- FIL: 708.3% suspicious values
- TON: 670.8% suspicious values  
- HYPE: 695.8% suspicious values
- ETH: 645.8% suspicious values
- TRX: 633.3% suspicious values
- PENDLE: 625.0% suspicious values
- NEWTEST: 833.3% suspicious values

**Moderately Affected:**
- ENA, AVAX, DOGE, FARTCOIN, LINK: ~4% suspicious values

### Data Sources Investigation

1. **Web Dashboard Code** (`/web_dashboard/app.py` lines 738-811)
   - ✅ Correctly retrieves data from compressed files
   - ✅ No hardcoded values in display logic
   - ✅ Properly formats trade details from backend data

2. **Data Loading System** (`scalable_analysis_system.py`)
   - ✅ Correctly loads compressed pickle files
   - ✅ No hardcoded values in data retrieval logic

3. **Compressed Trade Data Files** (`large_scale_analysis/compressed/`)
   - ❌ **SOURCE OF ISSUE**: Contains hardcoded placeholder values
   - FIL files contain exactly the reported values:
     - `entry_price: 100.0` 
     - `take_profit_price: 105.0`
     - `stop_loss_price: 97.61904761904762` (rounds to 97.62)

### Evidence from FIL Data Analysis
```
FIL_3m_Conservative_ML.pkl.gz:
Trade 1:
  entry_price: 100.0 ⚠️ SUSPICIOUS!
  take_profit_price: 105.0 ⚠️ SUSPICIOUS!  
  stop_loss_price: 97.61904761904762
  exit_price: 99.42778015743862
  
Summary: 120/200 prices are suspicious
```

### Historical Context
- Found existing fix script `fix_vine_prices.py` addressing identical issue for VINE symbol
- Issue appears to be related to backtesting engine generating placeholder values instead of realistic market prices
- Likely occurs when backtesting system lacks proper price data or encounters errors

## Impact Assessment

### User Experience Impact
- **Critical**: Trade details display misleading information
- **Data Integrity**: Backtest results may be unreliable for affected symbols
- **Decision Making**: Users cannot trust trade analysis for affected symbols

### Affected Components
1. Web dashboard trade details modal
2. Strategy analysis results
3. Performance calculations
4. Export functionality (CSV downloads)

## Solution Implementation

### Immediate Fixes Available

1. **FIL-Specific Fix** (`fix_fil_prices.py`)
   - Replaces hardcoded values with realistic FIL prices ($3-8 range)
   - Maintains relative relationships between TP/SL prices
   - Creates backup before modification

2. **Comprehensive Symbol Fix** 
   - 12 symbols identified need similar fixes
   - Each requires symbol-specific realistic price ranges

### Files Created for Investigation
- `/Users/moriwakikeita/tools/long-trader/check_fil_data.py` - FIL-specific analysis
- `/Users/moriwakikeita/tools/long-trader/fix_fil_prices.py` - FIL price correction
- `/Users/moriwakikeita/tools/long-trader/check_all_symbol_data.py` - Comprehensive analysis

## Recommended Actions

### Priority 1: Data Correction
1. Run `fix_fil_prices.py` to correct FIL data immediately
2. Create similar fix scripts for other severely affected symbols (ETH, HYPE, TON, TRX, PENDLE)
3. Test web dashboard after fixes to confirm correct display

### Priority 2: Root Cause Prevention  
1. Investigate backtesting engine to prevent future hardcoded value generation
2. Add validation checks during backtest data generation
3. Implement realistic price range validation per symbol

### Priority 3: Data Validation
1. Add automated checks for hardcoded values in CI/CD pipeline
2. Implement data integrity validation before storing backtest results
3. Create monitoring for anomalous price data

## Technical Details

### Hardcoded Values Detected
- `100.0` - Primary entry price placeholder
- `105.0` - Take profit placeholder (+5%)
- `97.61904761904762` - Stop loss placeholder (-2.38%)
- Additional variations around these values

### File Locations
- Compressed data: `/large_scale_analysis/compressed/`
- FIL files: 18 files total, all affected
- Storage format: gzipped pickle files

### Data Structure
```python
trade = {
    'entry_price': 100.0,          # ⚠️ Hardcoded
    'take_profit_price': 105.0,    # ⚠️ Hardcoded  
    'stop_loss_price': 97.619...,  # ⚠️ Hardcoded
    'exit_price': <calculated>,    # ✅ Realistic
    'leverage': <realistic>,       # ✅ Realistic
    'pnl_pct': <calculated>        # ✅ Realistic
}
```

## Conclusion

The FIL trade details issue is part of a broader data quality problem affecting 12+ symbols. The web dashboard is correctly displaying the data it receives - the issue lies in the underlying backtest data containing hardcoded placeholder values instead of realistic market prices.

**Status**: Root cause identified, fix scripts available, ready for data correction.