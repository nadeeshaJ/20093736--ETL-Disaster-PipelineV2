
import os
import shutil


def rotate_files(): 

    os.makedirs("data/outputs", exist_ok=True)

    latest_csv = "data/outputs/latest_scorecard.csv"
    previous_csv = "data/outputs/previous_scorecard.csv"

    latest_xlsx = "data/outputs/latest_scorecard.xlsx"
    previous_xlsx = "data/outputs/previous_scorecard.xlsx"

    if os.path.exists(latest_csv):
        shutil.copy(latest_csv, previous_csv)

    if os.path.exists(latest_xlsx):
        shutil.copy(latest_xlsx, previous_xlsx)

def save_new_files(df):

    csv_path = "data/outputs/latest_scorecard.csv"
    xlsx_path = "data/outputs/latest_scorecard.xlsx"

    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False)

    print("Latest files saved")

