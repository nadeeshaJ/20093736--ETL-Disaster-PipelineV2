import argparse
import logging
import sys
import os

from src.load.versioning import rotate_files, save_new_files
from src.extract.emdat_extract import emdat_extraction
from src.extract.worldbank_extract import worldbank_extraction
from src.load.database import SupabaseLoader
from src.extract.gdacs_extract import gdcs_extraction
from src.transform.build_scorecard import build_historical_validation, build_scorecard


# log functions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("etl_debug.log"), logging.StreamHandler(sys.stdout)]
)

def run_realtime_pipeline():
     # real-time alert function loading
    try:
        db = SupabaseLoader()
        
        
        if not db.check_health():
            raise Exception("Supabase connection failed")
        
       # extraction
        gdcs_extraction() 
        
        # transformation
        rotate_files() 
        scorecard_df = build_scorecard() 
        
        # loading to DB and GitHub
        save_new_files(scorecard_df) 
        db.upload_dataframe(scorecard_df, "latest_scorecards", on_conflict="event_id") 
        
        logging.info("Pipeline executed successfully.")

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")

def run_historical_pipeline():
    
    try:
        db = SupabaseLoader()
        
       
        if not db.check_health():
            raise Exception("Supabase connection failed")
        
        # build historical validation data
        logging.info("Building historical validation data...")
        historical_df = build_historical_validation()
        
        
        output_path = "data/outputs/historical_validation.csv"
       
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        historical_df.to_csv(output_path, index=False)
        logging.info(f"Historical data saved locally to {output_path}")
        
        # database Loading 
        db.upload_dataframe(historical_df, "historical_validation", on_conflict="validation_key")
        
        logging.info("Historical validation pipeline executed successfully.")

    except Exception as e:
        logging.error(f"Historical pipeline failed: {e}")

def run_full_pipeline():
    # master function to run all 4 tasks in logical sequence
    logging.info("Starting full integrated disaster pipeline")
    
    # Reference Indicators
    logging.info("Task 1: World Bank extraction")
    worldbank_extraction()
    
    # Historical Records
    logging.info("Task 2: EM-DAT extraction")
    emdat_extraction()
    
    # Build Validation Intelligence
    logging.info("Task 3: Historical validation processing")
    run_historical_pipeline()
    
    # Build Live Scorecards
    logging.info("Task 4 : Real-time triage processing")
    run_realtime_pipeline()
    
    logging.info("Full pipeline completed successfully")

def main():
    parser = argparse.ArgumentParser(description="MSc Disaster ETL Pipeline")
    
    
    parser.add_argument('--task', choices=['realtime', 'worldbank', 'emdat', 'historical', 'all'], required=True)
    args = parser.parse_args()

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