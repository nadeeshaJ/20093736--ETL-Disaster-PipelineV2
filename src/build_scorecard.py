

import glob
import os
import pandas as pd


# file folders
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

 # EM-DAT data preparation
def clean_emdat_columns(emdat_df):
    emdat_df = emdat_df.copy()
    emdat_df.columns = [col.strip() for col in emdat_df.columns]

    # fix mapping issue summary

    emdat_df["iso3"] = emdat_df["#country +code"]

    emdat_df["country"] = emdat_df["#country +name"]

    emdat_df["year"] = pd.to_numeric(emdat_df["#date +occurred"], errors="coerce")

    emdat_df["total_deaths"] = pd.to_numeric(emdat_df["#affected +ind +killed"], errors="coerce")

    emdat_df["total_affected"] = pd.to_numeric(emdat_df["#affected +ind"], errors="coerce")

    # fill missing numeric values

    emdat_df["total_deaths"] = emdat_df["total_deaths"].fillna(0)
    emdat_df["total_affected"] = emdat_df["total_affected"].fillna(0)

    return emdat_df

def prepare_emdat_summary(emdat_df):

    emdat_df = clean_emdat_columns(emdat_df)

    summary = emdat_df.groupby(["iso3", "country"]).agg(
        historical_disaster_count=("year", "count"),
        average_deaths=("total_deaths", "mean"),
        average_affected_population=("total_affected", "mean")
    ).reset_index()

    return summary

def prepare_emdat_yearly(emdat_df):

    emdat_df = clean_emdat_columns(emdat_df)

    yearly = emdat_df.groupby(["iso3", "country", "year"]).agg(
        disaster_count=("year", "count"),
        total_deaths=("total_deaths", "sum"),
        total_affected=("total_affected", "sum")
    ).reset_index()

    return yearly

# scorecard logic
def map_alert_to_score(alert_level):
    mapping = {
        "Green": 1,
        "Orange": 2,
        "Red": 3
    }
    return mapping.get(alert_level, 1)

def classify_risk(score):
    if score >= 70:
        return "High"
    elif score >= 40:
        return "Medium"
    else:
        return "Low"
    
def classify_impact(score):
    if score < 20:
        return "Low"
    elif score < 50:
        return "Moderate"
    elif score < 100:
        return "High"
    else:
        return "Severe"
    

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
    elif "country_y" in scorecard.columns and "country" not in scorecard.columns:
        scorecard["country"] = scorecard["country_y"]

    # fill missing values

    scorecard["historical_disaster_count"] = scorecard["historical_disaster_count"].fillna(0)
    scorecard["average_deaths"] = scorecard["average_deaths"].fillna(0)
    scorecard["average_affected_population"] = scorecard["average_affected_population"].fillna(0)
    scorecard["aid_received_usd"] = scorecard["aid_received_usd"].fillna(0)
    scorecard["aid_dependency_percent_gni"] = scorecard["aid_dependency_percent_gni"].fillna(0)
    scorecard["iso3"] = scorecard["iso3"].fillna("UNK")
    scorecard["severity"] = pd.to_numeric(scorecard["severity"], errors="coerce").fillna(0)
    scorecard["population"] = pd.to_numeric(scorecard["population"], errors="coerce").fillna(0)

    # current severity
    scorecard["real_time_severity_score"] = scorecard["alert_level"].apply(map_alert_to_score)

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

    # impact estimation layer

    scorecard["severity_multiplier"] = 1 + (scorecard["real_time_severity_score"] / 3.0)

    max_vulnerability = max(scorecard["vulnerability_index"].max(), 1)
    scorecard["vulnerability_factor"] = 1 + (scorecard["vulnerability_index"] / max_vulnerability)

    scorecard["base_affected"] = scorecard["average_affected_population"].replace(0, 1000)
    scorecard["base_deaths"] = scorecard["average_deaths"].replace(0, 5)

    scorecard["estimated_affected_population"] = (
        scorecard["base_affected"] *
        scorecard["severity_multiplier"] *
        scorecard["vulnerability_factor"]
    ).round(0)

    scorecard["estimated_deaths"] = (
        scorecard["base_deaths"] *
        scorecard["severity_multiplier"] *
        scorecard["vulnerability_factor"]
    ).round(0)

    # aid asumption
    aid_per_person_usd = 120

    scorecard["dependency_factor"] = 1 + (
        scorecard["aid_dependency_percent_gni"] / 100
    )

    scorecard["estimated_required_aid_usd"] = (
        (scorecard["estimated_affected_population"] * aid_per_person_usd) +
        (scorecard["estimated_deaths"] * 10000)
    ) * scorecard["dependency_factor"]

    scorecard["estimated_required_aid_usd"] = scorecard["estimated_required_aid_usd"].round(2)

    scorecard["impact_score"] = (
        (scorecard["estimated_affected_population"] / 10000) +
        (scorecard["estimated_deaths"] * 2) +
        (scorecard["estimated_required_aid_usd"] / 1000000)
    ).round(2)

    scorecard["estimated_impact_level"] = scorecard["impact_score"].apply(classify_impact)

# risk, gap, recommandation

    risk_list = []
    gap_list = []
    rec_list = []

    for _, row in scorecard.iterrows():
        risk = classify_risk(row["vulnerability_index"])

        if (
            row["alert_level"] == "Red" and
            row["aid_dependency_percent_gni"] >= 10 and
            row["historical_disaster_count"] >= 5
        ):
            gap = "Yes"
        else:
            gap = "No"

        if gap == "Yes":
            rec = "Immediate international support recommended"
        elif row["estimated_impact_level"] == "Severe":
            rec = "Urgent humanitarian mobilization recommended"
        elif row["estimated_impact_level"] == "High":
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
        "estimated_affected_population",
        "estimated_deaths",
        "estimated_required_aid_usd",
        "estimated_impact_level",
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

# historical validation layer
def build_historical_validation():
    emdat_df = load_emdat()
    wb_df = load_worldbank()

    yearly = prepare_emdat_yearly(emdat_df)

    # merge WB by same year
    df = yearly.merge(
        wb_df[["iso3", "year", "aid_received_usd", "aid_dependency_percent_gni"]],
        on=["iso3", "year"],
        how="left"
    )

    df["aid_received_usd"] = df["aid_received_usd"].fillna(0)
    df["aid_dependency_percent_gni"] = df["aid_dependency_percent_gni"].fillna(0)

    df = df.sort_values(["iso3", "year"]).reset_index(drop=True)

    # prior information 
    df["prior_disaster_count"] = df.groupby("iso3").cumcount()

    df["prior_avg_deaths"] = (
        df.groupby("iso3")["total_deaths"]
        .expanding()
        .mean()
        .shift()
        .reset_index(level=0, drop=True)
    )

    df["prior_avg_affected"] = (
        df.groupby("iso3")["total_affected"]
        .expanding()
        .mean()
        .shift()
        .reset_index(level=0, drop=True)
    )

    df["prior_avg_deaths"] = df["prior_avg_deaths"].fillna(0)
    df["prior_avg_affected"] = df["prior_avg_affected"].fillna(0)

    # vulnerability based on aid dependency
    df["vulnerability_factor"] = 1 + (df["aid_dependency_percent_gni"] / 100)

    # fallback values
    df["base_est_deaths"] = df["prior_avg_deaths"].replace(0, 5)
    df["base_est_affected"] = df["prior_avg_affected"].replace(0, 1000)

    df["estimated_deaths"] = (
        df["base_est_deaths"] * df["vulnerability_factor"]
    ).round(0)

    df["estimated_affected_population"] = (
        df["base_est_affected"] * df["vulnerability_factor"]
    ).round(0)

    aid_per_person_usd = 120

    df["estimated_required_aid_usd"] = (
        (df["estimated_affected_population"] * aid_per_person_usd) +
        (df["estimated_deaths"] * 10000)
    ) * (1 + df["aid_dependency_percent_gni"] / 100)

    df["estimated_required_aid_usd"] = df["estimated_required_aid_usd"].round(2)

    df["impact_score"] = (
        (df["estimated_affected_population"] / 10000) +
        (df["estimated_deaths"] * 2) +
        (df["estimated_required_aid_usd"] / 1000000)
    ).round(2)

    df["estimated_impact_level"] = df["impact_score"].apply(classify_impact)

    # optional validation measures
    df["deaths_error"] = df["estimated_deaths"] - df["total_deaths"]
    df["affected_error"] = df["estimated_affected_population"] - df["total_affected"]

    final_cols = [
        "country",
        "iso3",
        "year",
        "disaster_count",
        "total_deaths",
        "total_affected",
        "aid_received_usd",
        "aid_dependency_percent_gni",
        "prior_disaster_count",
        "prior_avg_deaths",
        "prior_avg_affected",
        "estimated_deaths",
        "estimated_affected_population",
        "estimated_required_aid_usd",
        "estimated_impact_level",
        "deaths_error",
        "affected_error"
    ]

    df = df[final_cols]

    return df



