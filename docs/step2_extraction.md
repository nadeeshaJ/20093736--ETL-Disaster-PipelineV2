Step 2 – Data Extraction

In this step, collect raw data from different sources and store it in a structured way for further processing.

data sources:

EM-DAT dataset for disaster data (manually downloaded and stored in the raw folder)
World Bank API to get financial aid data
GDACS API to get recent disaster alerts

For each source, created a separate Python script. These scripts connect to the data source, pull the data, and save it as files inside the data/raw/ folder.

Each file is saved with a timestamp so that every pipeline run creates a new version. This helps with tracking data over time and makes the pipeline more reproducible.

All extraction scripts are connected through a main file called run_pipeline.py, so I can run everything using a single command.
