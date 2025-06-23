# Long Trader Database Schema - Entity Relationship Diagram

## Database Structure Overview

The Long Trader system uses multiple SQLite databases to manage different aspects of the trading analysis workflow:

1. **execution_logs.db** - Execution tracking and monitoring
2. **alert_history_system/data/alert_history.db** - Trading alerts and performance tracking  
3. **large_scale_analysis/analysis.db** - Strategy analysis results and backtest data

---

## Entity Relationship Diagram

```mermaid
erDiagram
    %% Execution Logs Database
    EXECUTION_LOGS {
        text execution_id PK
        text execution_type
        text symbol
        text symbols
        text timestamp_start
        text timestamp_end
        text status
        real duration_seconds
        text triggered_by
        text server_id
        text version
        text current_operation
        real progress_percentage
        text completed_tasks
        integer total_tasks
        real cpu_usage_avg
        integer memory_peak_mb
        integer disk_io_mb
        text metadata
        text errors
        text created_at
        text updated_at
    }

    EXECUTION_STEPS {
        integer id PK
        text execution_id FK
        text step_name
        text status
        text timestamp_start
        text timestamp_end
        real duration_seconds
        text result_data
        text error_message
        text error_traceback
        text created_at
    }

    %% Alert History Database
    ALERTS {
        integer id PK
        varchar alert_id UK
        varchar symbol
        varchar alert_type
        varchar priority
        datetime timestamp
        float leverage
        float confidence
        varchar strategy
        varchar timeframe
        float entry_price
        float target_price
        float stop_loss
        text extra_data
    }

    PRICE_TRACKING {
        integer id PK
        varchar alert_id FK
        varchar symbol
        datetime timestamp
        float price
        integer time_elapsed_hours
        float percentage_change
    }

    PERFORMANCE_SUMMARY {
        integer id PK
        varchar alert_id FK
        varchar symbol
        boolean is_success
        float max_gain
        float max_loss
        float final_return_24h
        float final_return_72h
        text evaluation_note
        datetime created_at
        datetime updated_at
    }

    %% Large Scale Analysis Database
    ANALYSES {
        integer id PK
        text execution_id FK
        text symbol
        text timeframe
        text config
        timestamp generated_at
        integer total_trades
        real win_rate
        real total_return
        real sharpe_ratio
        real max_drawdown
        real avg_leverage
        text chart_path
        text compressed_path
        text status
    }

    BACKTEST_SUMMARY {
        integer id PK
        integer analysis_id FK
        text metric_name
        real metric_value
    }

    LEVERAGE_CALCULATION_DETAILS {
        integer id PK
        integer analysis_id FK
        integer trade_number
        real support_distance_pct
        real support_constraint_leverage
        real risk_reward_ratio
        real risk_reward_constraint_leverage
        real confidence_pct
        real confidence_constraint_leverage
        real btc_correlation
        real btc_constraint_leverage
        real volatility_pct
        real volatility_constraint_leverage
        text trend_strength
        real trend_multiplier
        real min_constraint_leverage
        real safety_margin_pct
        real final_leverage
        timestamp calculation_timestamp
    }

    %% Relationships
    EXECUTION_LOGS ||--o{ EXECUTION_STEPS : "has execution steps"
    EXECUTION_LOGS ||--o{ ANALYSES : "tracks analysis execution"
    ALERTS ||--o{ PRICE_TRACKING : "tracks prices"
    ALERTS ||--o{ PERFORMANCE_SUMMARY : "evaluates performance"
    ANALYSES ||--o{ BACKTEST_SUMMARY : "has metrics"
    ANALYSES ||--o{ LEVERAGE_CALCULATION_DETAILS : "has leverage calculations"
```

---

## Database Details

### 1. Execution Logs Database (`execution_logs.db`)

**Primary Purpose**: Track system execution, monitoring, and orchestration activities

#### Tables:

##### `execution_logs`
- **Purpose**: Master execution tracking table
- **Key Fields**: 
  - `execution_id` (PK): Unique identifier for each execution
  - `execution_type`: Type of operation (SYMBOL_ADDITION, SCHEDULED_TRAINING, etc.)
  - `symbol/symbols`: Target symbol(s) for the operation
  - `status`: Current status (RUNNING, COMPLETED, FAILED, etc.)
  - `progress_percentage`: Completion percentage
- **Indexes**: execution_type, symbol, status, timestamp_start

##### `execution_steps`
- **Purpose**: Detailed step-by-step execution tracking
- **Key Fields**:
  - `execution_id` (FK): References execution_logs
  - `step_name`: Name of the execution step
  - `status`: Step status
  - `result_data`: Step output (JSON)
- **Relationship**: Many steps per execution

---

### 2. Alert History Database (`alert_history_system/data/alert_history.db`)

**Primary Purpose**: Store trading alerts and track their real-world performance

#### Tables:

##### `alerts`
- **Purpose**: Store trading signal alerts
- **Key Fields**:
  - `alert_id` (UK): Unique alert identifier
  - `symbol`: Trading symbol
  - `alert_type`: Type of alert (LONG_ENTRY, etc.)
  - `leverage`, `confidence`: Trading parameters
  - `entry_price`, `target_price`, `stop_loss`: Price levels

##### `price_tracking`
- **Purpose**: Track price movements after alerts
- **Key Fields**:
  - `alert_id` (FK): References alerts table
  - `time_elapsed_hours`: Hours since alert
  - `percentage_change`: Price change percentage
- **Relationship**: Multiple price points per alert

##### `performance_summary`
- **Purpose**: Evaluate alert performance over time
- **Key Fields**:
  - `alert_id` (FK): References alerts table
  - `is_success`: Whether alert was successful
  - `max_gain/max_loss`: Peak performance metrics
  - `final_return_24h/72h`: Returns at specific intervals
- **Relationship**: One summary per alert

---

### 3. Large Scale Analysis Database (`large_scale_analysis/analysis.db`)

**Primary Purpose**: Store strategy backtesting results and detailed analysis

#### Tables:

##### `analyses`
- **Purpose**: Store strategy backtest results
- **Key Fields**:
  - `execution_id` (FK): References execution_logs table
  - `symbol`, `timeframe`, `config`: Strategy parameters
  - `sharpe_ratio`, `win_rate`, `total_return`: Performance metrics
  - `chart_path`, `compressed_path`: File references
- **Indexes**: symbol_timeframe, config, sharpe_ratio, execution_id

##### `backtest_summary`
- **Purpose**: Store additional metrics for each analysis
- **Key Fields**:
  - `analysis_id` (FK): References analyses table
  - `metric_name`, `metric_value`: Custom metrics
- **Relationship**: Multiple metrics per analysis

##### `leverage_calculation_details`
- **Purpose**: Store detailed leverage calculation breakdown
- **Key Fields**:
  - `analysis_id` (FK): References analyses table
  - `trade_number`: Trade sequence number
  - Various constraint leverages and calculations
- **Relationship**: Multiple calculations per analysis

---

## Key Relationships

1. **Execution Tracking**: `execution_logs` → `execution_steps` (1:N)
2. **Execution to Analysis**: `execution_logs` → `analyses` (1:N)
3. **Alert Performance**: `alerts` → `price_tracking` (1:N) and `alerts` → `performance_summary` (1:1)
4. **Analysis Details**: `analyses` → `backtest_summary` (1:N) and `analyses` → `leverage_calculation_details` (1:N)

## Data Flow

1. **Symbol Addition**: Creates `execution_logs` entry → Generates `analyses` entries → Stores detailed `leverage_calculation_details`
2. **Alert Generation**: Creates `alerts` → Continuous `price_tracking` → Final `performance_summary`
3. **Strategy Results**: Query `analyses` with filters → Load compressed trade data → Display in web dashboard

## Storage Locations

```
/Users/moriwakikeita/tools/long-trader/
├── execution_logs.db                           # Main execution tracking
├── alert_history_system/data/alert_history.db  # Alert performance tracking
└── large_scale_analysis/analysis.db            # Strategy analysis results
```

---

## Additional Database Indexes

**Performance Optimization Indexes (not shown in ER diagram above):**

### execution_logs.db
- `idx_execution_logs_symbol` on execution_logs(symbol)
- `idx_execution_logs_status` on execution_logs(status)
- `idx_execution_logs_type` on execution_logs(execution_type)
- `idx_execution_logs_timestamp` on execution_logs(timestamp_start)

### analysis.db
- `idx_analyses_execution_id` on analyses(execution_id)
- `idx_analyses_symbol` on analyses(symbol)
- `idx_analyses_generated_at` on analyses(generated_at)
- `idx_analyses_config` on analyses(config)
- `idx_analyses_sharpe_ratio` on analyses(sharpe_ratio)
- `idx_leverage_analysis` on leverage_calculation_details(analysis_id)
- `idx_leverage_trade` on leverage_calculation_details(analysis_id, trade_number)

### alert_history.db
- SQLAlchemy automatically manages indexes for primary keys and unique constraints