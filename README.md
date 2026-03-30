Project title
Design and Implementation of a Cloud-Based ETL Pipeline for a Humanitarian Resilience Scorecard
What it does
This pipeline combines:
•	GDACS → live disaster alerts 
•	EM-DAT → historical disaster patterns 
•	World Bank → aid dependency indicators 
Then it builds a Humanitarian Resilience Scorecard to estimate which countries may be more vulnerable during real-time disaster situations.

ETL-Disaster-Pipeline/
│
├── run_gdacs_pipeline.py
├── run_worldbank_update.py
├── run_emdat_update.py
├── requirements.txt
├── README.md
│
├── src/
│   ├── extract_gdacs.py
│   ├── extract_worldbank.py
│   ├── extract_emdat.py
│   ├── build_scorecard.py
│   └── github_versioning.py
│
├── data/
│   ├── raw/
│   │   ├── gdacs/
│   │   ├── worldbank/
│   │   └── emdat/
│   └── outputs/
