import argparse
import logging
import sys
import pandas as pd
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
        
        # build historical validation data
        logging.info("Building historical validation data...")
        historical_df = build_historical_validation()
        
        
        output_path = "data/outputs/historical_validation.csv"
        historical_df.to_csv(output_path, index=False)
        logging.info(f"Historical data saved locally to {output_path}")
        
        # database Loading
        
        db.upload_dataframe(historical_df, "historical_validation", on_conflict="id")
        
        logging.info("Historical validation pipeline executed successfully.")

    except Exception as e:
        logging.error(f"Historical pipeline failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="MSc Disaster ETL Pipeline")
    
    parser.add_argument('--task', choices=['realtime', 'worldbank', 'emdat', 'historical'], required=True)
    args = parser.parse_args()

    if args.task == 'realtime':
        run_realtime_pipeline()
    elif args.task == 'worldbank':
        worldbank_extraction() 
    elif args.task == 'emdat':
        emdat_extraction() 
    elif args.task == 'historical':
        run_historical_pipeline()

if __name__ == "__main__":
    main()