import argparse
import logging
import sys
import os
import pandas as pd 
from datetime import datetime, timezone

from src.load.versioning import rotate_files, save_new_files
from src.extract.emdat_extract import emdat_extraction
from src.extract.worldbank_extract import worldbank_extraction
from src.load.database import SupabaseLoader
from src.extract.gdacs_extract import gdcs_extraction
from src.transform.build_scorecard import build_historical_validation, build_scorecard

# Log setup: Save errors to a file and show them in the terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("etl_debug.log"), logging.StreamHandler(sys.stdout)]
)

def run_realtime_pipeline():
    # Process live disaster alerts
    try:
        db = SupabaseLoader()
        
        # Check if the database is working
        if not db.check_health():
            raise Exception("Supabase connection failed")
        
        # Get new GDACS data and archive old files
        gdcs_extraction() 
        rotate_files() 
        
        # Calculate scores for the dashboard
        scorecard_df = build_scorecard() 

        # Delete old rows in the database so the map only shows new alerts
        try:
            db.client.table("latest_scorecards").delete().neq("country", "0").execute()
            logging.info("Cleared old database records.")
        except Exception as e:
            logging.warning(f"Database was already empty or could not be cleared: {e}")

        # Add a timestamp so  know when this was run
        scorecard_df["processed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Fix column types: Force IDs and counts to be whole numbers
        int_cols = ["year", "historical_disaster_count", "estimated_deaths", "population"]
        for col in int_cols:
            if col in scorecard_df.columns:
                scorecard_df[col] = pd.to_numeric(scorecard_df[col], errors='coerce').fillna(0).astype(int)
        
        # Save to local folder and upload to Supabase
        save_new_files(scorecard_df) 
        db.upload_dataframe(scorecard_df, "latest_scorecards", on_conflict="event_id") 
        
        logging.info("Real-time pipeline finished.")

    except Exception as e:
        logging.error(f"Real-time pipeline failed: {e}")

def run_historical_pipeline():
    # Process old disaster data for accuracy checking
    try:
        db = SupabaseLoader()
        
        if not db.check_health():
            raise Exception("Supabase connection failed")
        
        # Build the historical table
        logging.info("Starting historical processing...")
        historical_df = build_historical_validation()
        
        historical_df["processed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Clean up numbers (no decimals for deaths or years)
        hist_int_cols = ["year", "total_deaths", "estimated_deaths", "historical_disaster_count"]
        for col in hist_int_cols:
            if col in historical_df.columns:
                historical_df[col] = pd.to_numeric(historical_df[col], errors='coerce').fillna(0).astype(int)
        
        # Save a backup CSV locally
        output_path = "data/outputs/historical_validation.csv"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        historical_df.to_csv(output_path, index=False)
        
        # Upload historical data to the database
        db.upload_dataframe(historical_df, "historical_validation", on_conflict="validation_key")
        
        logging.info("Historical pipeline finished.")

    except Exception as e:
        logging.error(f"Historical pipeline failed: {e}")

def run_full_pipeline():
    # Run everything in order: World Bank -> EM-DAT -> History -> Live Alerts
    logging.info("Starting the full integrated pipeline...")
    
    worldbank_extraction() # Task 1
    emdat_extraction()      # Task 2
    run_historical_pipeline() # Task 3
    run_realtime_pipeline()   # Task 4
    
    logging.info("Full pipeline finished successfully.")

def main():
    # Terminal command handler: choose which task to run
    parser = argparse.ArgumentParser(description="MSc Disaster ETL Pipeline")
    parser.add_argument('--task', choices=['realtime', 'worldbank', 'emdat', 'historical', 'all'], required=True)
    args = parser.parse_args()

    # Route the command to the right function
    if args.task == 'all':
        run_full_pipeline()
    elif args.task == 'realtime':
        run_realtime_pipeline()
    elif args.task == 'worldbank':
        worldbank_extraction() 
    elif args.task == 'emdat':
        emdat_extraction() 
    elif args.task == 'historical':
        run_historical_pipeline()

if __name__ == "__main__":
    main()