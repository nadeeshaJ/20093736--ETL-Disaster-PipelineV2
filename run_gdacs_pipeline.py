from src.extract.gdacs_extract import gdcs_extraction
from src.versioning import rotate_files, save_new_files
from src.build_scorecard import build_scorecard


print("Starting GDACS pipeline...")

gdcs_extraction()

rotate_files()

final_df = build_scorecard()

save_new_files(final_df)

print("Pipeline finished successfully")