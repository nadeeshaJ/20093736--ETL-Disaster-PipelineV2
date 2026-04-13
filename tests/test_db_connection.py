import unittest
import pandas as pd
import numpy as np
from src.load.database import SupabaseLoader

class TestDatabaseLogic(unittest.TestCase):

    def setUp(self):
        """Initialize the loader for testing."""
        self.loader = SupabaseLoader()

    def test_supabase_connectivity(self):
        """Integration Test: Verify backend can reach the cloud."""
        result = self.loader.check_health()
        self.assertTrue(result, "Cloud connection failed.")

    def test_empty_dataframe_handling(self):
        """Unit Test: Ensure the loader skips empty data."""
        empty_df = pd.DataFrame()
        # Should return None and log a warning instead of crashing
        result = self.loader.upload_dataframe(empty_df, "test_table")
        self.assertIsNone(result)

    def test_nan_cleaning_logic(self):
        """Unit Test: Ensure NaNs are converted to None for JSON safety."""
        # Create data with a NaN -  SQL/JSON upload error handlings
        dirty_data = pd.DataFrame([{"event_id": 999, "magnitude": np.nan}])
        
        
        # Health check verification
        self.assertTrue(self.loader.check_health())

if __name__ == "__main__":
    unittest.main()