import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from supabase import create_client, Client 

class SupabaseLoader:
    def __init__(self):
        # Load .env 
        base_path = Path(__file__).resolve().parent.parent.parent
        load_dotenv(dotenv_path=base_path / '.env') 

        self.url: str = os.getenv("SUPABASE_URL")
        self.key: str = os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("Check your .env file! URL or Key is missing.")

        # Initialize the client
        self.client: Client = create_client(self.url, self.key)

    def upload_dataframe(self, df: pd.DataFrame, table_name: str):
       
        try:
            # Convert NaNs to None 
            df_clean = df.where(pd.notnull(df), None)
            data = df_clean.to_dict(orient='records')
            
            # Upsert 
            response = self.client.table(table_name).upsert(data).execute()
            logging.info(f"Successfully uploaded {len(data)} rows to {table_name}.")
            return response
        except Exception as e:
            logging.error(f"Database upload failed: {e}")
            raise

    def test_connection(self):
        try:
            
            self.client.table("latest_scorecards").select("*").limit(1).execute()
            print("Supabase connection successful!")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

if __name__ == "__main__":
    loader = SupabaseLoader()
    loader.test_connection()