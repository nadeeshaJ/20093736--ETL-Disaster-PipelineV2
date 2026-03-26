# Step 3 – Pipeline Automation using Azure VM

The ETL pipeline was automated using cron scheduling on the Azure VM.

A cron job was configured to execute the pipeline daily at midnight.

# Cron job

```bash
0 0 * * * cd /home/20093736/20093736--ETL-Disaster-PipelineV2 && /home/20093736/20093736--ETL-Disaster-PipelineV2/.venv/bin/python run_pipeline.py >> /home/20093736/etl_log.txt 2>&1
