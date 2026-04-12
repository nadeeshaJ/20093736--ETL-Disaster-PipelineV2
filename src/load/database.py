# src/load/database.py
import os
from supabase import create_client, Client
import pandas as pd
import logging

class SupabaseLoader:
    def __init__(self):
        # These should be in an .env file for security
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        self.client: Client = create_client(self.url, self.key)

    def upload_dataframe(self, df: pd.DataFrame, table_name: str):
        """Upserts data into Supabase to prevent duplicates."""
        try:
            # Clean data: Convert NaNs to None for Postgres compatibility
            df_clean = df.where(pd.notnull(df), None)
            data = df_clean.to_dict(orient='records')
            
            # Upsert ensures that if an event_id already exists, it updates instead of failing
            response = self.client.table(table_name).upsert(data).execute()
            logging.info(f"Successfully uploaded {len(data)} rows to {table_name}.")
            return response
        except Exception as e:
            logging.error(f"Database upload failed: {e}")
            raise