import unittest
import pandas as pd
from src.transform.build_scorecard import (
    map_alert_to_score, 
    classify_risk, 
    generate_recommendation
)

class TestDisasterTransformations(unittest.TestCase):

    def test_map_alert_to_score(self):
        """Test if alert levels and numeric scores maps."""
        self.assertEqual(map_alert_to_score("Red"), 3)
        self.assertEqual(map_alert_to_score("Green"), 1)
        self.assertEqual(map_alert_to_score("Unknown"), 1) # Default case

    def test_classify_risk(self):
        """Test vulnerability vs index risk categorization."""
        self.assertEqual(classify_risk(85), "High")
        self.assertEqual(classify_risk(50), "Medium")
        self.assertEqual(classify_risk(20), "Low")

    def test_recommendation_logic(self):
        """Test if recommendations trigger for emergency levels."""
        # a test row
        emergency_row = pd.Series({
            'urgency_level': 'Emergency',
            'funding_gap_usd': 0,
            'electricity_access_pct': 100
        })
        rec = generate_recommendation(emergency_row)
        self.assertIn("Immediate mobilization", rec)

if __name__ == '__main__':
    unittest.main(argv=[''], exit=False)