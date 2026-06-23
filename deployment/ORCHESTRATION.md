# Weekly Retraining Orchestration

## Architecture

ASTRaM App → API Ingest → MongoDB → Weekly Trigger → Retrain → Deploy

## Option A: Apache Airflow (Production)

DAG: gridlock_weekly_retrain
Schedule: 0 2 * * 1  (every Monday 2 AM IST)

Tasks:
  1. ingest_new_violations
     Pull new ASTRaM records since last run
     Validate coordinates, clean, feature-engineer
     Append to violations collection

  2. recompute_clusters
     Run DBSCAN on last 90 days of data
     Update cluster_registry if new clusters emerge

  3. weekly_aggregation
     Rebuild weekly_cluster_timeband for new week

  4. temporal_weighted_retrain
     Run global_forecast_model.py with sample weights
     Compare MAE against current production model
     Deploy if improvement > 2%

  5. update_priority_scores
     Recompute CII, volatility, final priority
     Refresh heatmap_data.json

  6. notify_control_rooms
     Send shift-start notification:
     "Model updated · X new violations ingested · 
      Y zones re-prioritized"

## Option B: GitHub Actions + Cron (Hackathon Demo)

.github/workflows/weekly_retrain.yml:
  schedule: cron('0 20 * * 0')  # Sunday 8PM UTC = Monday 1:30AM IST
  
  steps:
    - checkout
    - setup python
    - pip install requirements
    - python run_full_pipeline.py
    - commit updated CSVs back to repo
