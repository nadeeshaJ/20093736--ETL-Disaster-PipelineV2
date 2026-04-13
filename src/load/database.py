import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from supabase import create_client, Client 

# log functions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SupabaseLoader:
    def __init__(self):
        # Load .env 
        base_path = Path(__file__).resolve().parent.parent.parent
        env_path = base_path / '.env'
        
        if not env_path.exists():
            logging.warning(f".env file not found at {env_path}. Falling back to system environment variables.")
        
        load_dotenv(dotenv_path=env_path) 

        self.url: str = os.getenv("SUPABASE_URL")
        self.key: str = os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY missing from environment/env file.")

        # initialize the client
        self.client: Client = create_client(self.url, self.key)

    def upload_dataframe(self, df: pd.DataFrame, table_name: str):
        
        try:
            if df.empty:
                logging.warning(f"DataFrame for {table_name} is empty. Skipping upload.")
                return None

            # convert NaNs/NATs to None
           
            df_clean = df.replace({np.nan: None})
            
            # convert to dictionary records
            data = df_clean.to_dict(orient='records')
            
           
            # updates the record if the event_id already exists
            response = self.client.table(table_name).upsert(
                data, 
                on_conflict="event_id"
            ).execute()
            
            logging.info(f"Successfully processed {len(data)} records in table '{table_name}'.")
            return response

        except Exception as e:
            logging.error(f"Database upload failed for table '{table_name}': {e}")
           
            raise

    def check_health(self):
        # to ensure DB is active before starting the ETL
        try:
            self.client.table("latest_scorecards").select("id").limit(1).execute()
            return True
        except Exception:
            return False

if __name__ == "__main__":
    loader = SupabaseLoader()
    # verify connection health
    if loader.check_health():
        logging.info("Supabase connection is healthy.")
    else:
        logging.error("Supabase connection failed.")