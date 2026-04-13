import unittest
from src.load.database import SupabaseLoader

class TestSystemIntegration(unittest.TestCase):

    def setUp(self):
        """Initialize the database loader."""
        self.loader = SupabaseLoader()

    def test_database_connectivity(self):
        """Verify connection between code an supabase."""
        is_healthy = self.loader.check_health()
        self.assertTrue(is_healthy, "Integration Error: Backend cannot reach Supabase.")

    def test_data_schema_retrieval(self):
        """Verify that the dashboard can pull the required alert columns."""
        # test with one record
        response = self.loader.client.table("latest_scorecards").select("*").limit(1).execute()
        
        # check data existance with one column
        if response.data:
            record = response.data[0]
            self.assertIn('triage_score', record, "Schema Error: triage_score column missing from DB.")
            self.assertIn('event_id', record, "Schema Error: event_id column missing from DB.")

if __name__ == '__main__':
    unittest.main(argv=[''], exit=False)