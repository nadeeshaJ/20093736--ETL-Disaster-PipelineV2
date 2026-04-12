
from transform.build_scorecard import build_historical_validation


print("Starting historical validation build")

historical_df = build_historical_validation()
historical_df.to_csv("data/outputs/historical_validation.csv", index=False)
historical_df.to_excel("data/outputs/historical_validation.xlsx", index=False)

print("Historical validation files saved")