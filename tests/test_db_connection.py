import unittest
from src.load.database import SupabaseLoader


class TestDatabaseConnection(unittest.TestCase):

    def setUp(self):
       # loader
        self.loader = SupabaseLoader()

    def test_supabase_connectivity(self):
        # verify that pipeline can connect and DB table is available
        result = self.loader.test_connection()
        self.assertTrue(result, "Database connection should be successful.")

if __name__ == "__main__":
    unittest.main()