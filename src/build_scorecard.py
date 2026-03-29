

import glob
import os
import pandas as pd


def get_latest_csv(folder):
    files = glob.glob(folder + "/*.csv")
    if len(files) == 0:
        return None
    return max(files, key=os.path.getmtime)

def get_latest_csv_with_name(folder, text):
    files = glob.glob(folder + "/*.csv")
    files = [f for f in files if text in os.path.basename(f)]
    if len(files) == 0:
        return None
    return max(files, key=os.path.getmtime)

def get_latest_xlsx(folder):
    files = glob.glob(folder + "/*.xlsx")
    if len(files) == 0:
        return None
    return max(files, key=os.path.getmtime)

def load_gdacs():
    file_path = get_latest_csv("data/raw/gdacs")
    df = pd.read_csv(file_path)
    print("Loaded GDACS:", file_path)
    return df

def load_emdat():
    file_path = get_latest_xlsx("data/raw/emdat")
    df = pd.read_excel(file_path, skiprows=1)
    print("Loaded EM-DAT:", file_path)
    return df

def load_worldbank():
    oda_file = get_latest_csv_with_name("data/raw/worldbank", "oda_received_usd")
    dep_file = get_latest_csv_with_name("data/raw/worldbank", "aid_dependency_percent_gni")

    oda_df = pd.read_csv(oda_file)
    dep_df = pd.read_csv(dep_file)

    print("Loaded World Bank ODA:", oda_file)
    print("Loaded World Bank dependency:", dep_file)

    oda_df["year"] = pd.to_numeric(oda_df["year"], errors="coerce")
    dep_df["year"] = pd.to_numeric(dep_df["year"], errors="coerce")

    oda_df["value"] = pd.to_numeric(oda_df["value"], errors="coerce")
    dep_df["value"] = pd.to_numeric(dep_df["value"], errors="coerce")

    oda_df = oda_df.rename(columns={"value": "aid_received_usd"})
    dep_df = dep_df.rename(columns={"value": "aid_dependency_percent_gni"})

    wb_df = oda_df[["country", "iso3", "year", "aid_received_usd"]].merge(
        dep_df[["iso3", "year", "aid_dependency_percent_gni"]],
        on=["iso3", "year"],
        how="outer"
    )

    return wb_df


def prepare_emdat_summary(emdat_df):
    emdat_df.columns = [col.strip() for col in emdat_df.columns]

    # fix mapping issue summary

    emdat_df["iso3"] = emdat_df["#country +code"]

    emdat_df["country"] = emdat_df["#country +name"]

    emdat_df["year"] = pd.to_numeric(emdat_df["#date +occurred"], errors="coerce")

    emdat_df["total_deaths"] = pd.to_numeric(emdat_df["#affected +ind +killed"], errors="coerce")

    emdat_df["total_affected"] = pd.to_numeric(emdat_df["#affected +ind"], errors="coerce")

    summary = emdat_df.groupby(["iso3", "country"]).agg(
        historical_disaster_count=("year", "count"),
        average_deaths=("total_deaths", "mean"),
        average_affected_population=("total_affected", "mean")
    ).reset_index()

    return summary


def build_scorecard():
    gdacs_df = load_gdacs()
    emdat_df = load_emdat()
    wb_df = load_worldbank()

    emdat_summary = prepare_emdat_summary(emdat_df)

    latest_year = wb_df["year"].max()
    wb_latest = wb_df[wb_df["year"] == latest_year].copy()

    scorecard = gdacs_df.merge(emdat_summary, on="iso3", how="left")
    scorecard = scorecard.merge(
        wb_latest[["iso3", "aid_received_usd", "aid_dependency_percent_gni"]],
        on="iso3",
        how="left"
    )

    if "country_x" in scorecard.columns:
        scorecard["country"] = scorecard["country_x"]

    scorecard["historical_disaster_count"] = scorecard["historical_disaster_count"].fillna(0)
    scorecard["average_deaths"] = scorecard["average_deaths"].fillna(0)
    scorecard["average_affected_population"] = scorecard["average_affected_population"].fillna(0)
    scorecard["aid_received_usd"] = scorecard["aid_received_usd"].fillna(0)
    scorecard["aid_dependency_percent_gni"] = scorecard["aid_dependency_percent_gni"].fillna(0)

    scorecard["real_time_severity_score"] = scorecard["alert_level"].map({
        "Green": 1,
        "Orange": 2,
        "Red": 3
    }).fillna(1)

    max_disaster = max(scorecard["historical_disaster_count"].max(), 1)
    max_deaths = max(scorecard["average_deaths"].max(), 1)
    max_affected = max(scorecard["average_affected_population"].max(), 1)
    max_dependency = max(scorecard["aid_dependency_percent_gni"].max(), 1)

    scorecard["historical_risk_score"] = (
        (scorecard["historical_disaster_count"] / max_disaster) * 40 +
        (scorecard["average_deaths"] / max_deaths) * 30 +
        (scorecard["average_affected_population"] / max_affected) * 30
    )

    scorecard["financial_dependency_score"] = (
        scorecard["aid_dependency_percent_gni"] / max_dependency
    ) * 100

    scorecard["vulnerability_index"] = (
        scorecard["historical_risk_score"] * 0.4 +
        scorecard["real_time_severity_score"] * 20 +
        scorecard["financial_dependency_score"] * 0.2
    )

    risk_list = []
    gap_list = []
    rec_list = []

    for i, row in scorecard.iterrows():
        score = row["vulnerability_index"]

        if score >= 70:
            risk = "High"
        elif score >= 40:
            risk = "Medium"
        else:
            risk = "Low"

        if row["alert_level"] == "Red" and row["aid_dependency_percent_gni"] >= 10 and row["historical_disaster_count"] >= 5:
            gap = "Yes"
        else:
            gap = "No"

        if gap == "Yes":
            rec = "Immediate international support recommended"
        elif risk == "High":
            rec = "High priority monitoring and response"
        elif risk == "Medium":
            rec = "Prepare response resources"
        else:
            rec = "Continue routine monitoring"

        risk_list.append(risk)
        gap_list.append(gap)
        rec_list.append(rec)

    scorecard["risk_category"] = risk_list
    scorecard["critical_resource_gap"] = gap_list
    scorecard["response_recommendation"] = rec_list

    final_cols = [
        "country",
        "iso3",
        "disaster_type",
        "alert_level",
        "severity",
        "population",
        "historical_disaster_count",
        "average_deaths",
        "average_affected_population",
        "aid_received_usd",
        "aid_dependency_percent_gni",
        "historical_risk_score",
        "real_time_severity_score",
        "financial_dependency_score",
        "vulnerability_index",
        "risk_category",
        "critical_resource_gap",
        "response_recommendation",
        "start_date",
        "end_date"
    ]

    scorecard = scorecard[final_cols]

    scorecard["historical_risk_score"] = scorecard["historical_risk_score"].round(2)
    scorecard["financial_dependency_score"] = scorecard["financial_dependency_score"].round(2)
    scorecard["vulnerability_index"] = scorecard["vulnerability_index"].round(2)

    return scorecard


