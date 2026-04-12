import argparse
import logging
import sys
from src.load.versioning import rotate_files
from src.extract.emdat_extract import emdat_extraction
from src.extract.worldbank_extract import worldbank_extraction
from src.load.database import SupabaseLoader
from src.extract.gdacs_extract import gdcs_extraction
from src.transform.build_scorecard import build_scorecard


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
        gdcs_extraction() #
        
        # transformation
        rotate_files() #
        scorecard_df = build_scorecard() #
        
        # loading to DB and GitHub
        save_new_files(scorecard_df) # git
        db.upload_dataframe(scorecard_df, "latest_scorecards") # db
        
        logging.info("Pipeline executed successfully.")

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="MSc Disaster ETL Pipeline")
    parser.add_argument('--task', choices=['realtime', 'worldbank', 'emdat'], required=True)
    args = parser.parse_args()

    if args.task == 'realtime':
        run_realtime_pipeline()
    elif args.task == 'worldbank':
        worldbank_extraction() 
    elif args.task == 'emdat':
        emdat_extraction() 

if __name__ == "__main__":
    main()
