import glob
import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# intelligence layer fuctions
def generate_recommendation(row):
    if row['urgency_level'] == 'Emergency':
        return "Immediate mobilization of search & rescue and emergency medical units."
    if row['funding_gap_usd'] > 1000000:
        return "Prioritize financial appeal; significant resource deficit detected."
    if row['electricity_access_pct'] < 40:
        return "Focus on logistics and off-grid power; local infrastructure is critical."
    return "Monitor situation; routine humanitarian support recommended."

def calculate_resource_gap_flag(row):
    return "CRITICAL" if row['funding_gap_usd'] > 500000 and row['vulnerability_index'] > 60 else "MONITOR"

# file folders
def get_latest_csv(folder):
    files = glob.glob(folder + "/*.csv")
    return max(files, key=os.path.getmtime) if files else None

def get_latest_csv_with_name(folder, text):
    files = [f for f in glob.glob(folder + "/*.csv") if text in os.path.basename(f)]
    return max(files, key=os.path.getmtime) if files else None

def get_latest_xlsx(folder):
    files = glob.glob(folder + "/*.xlsx")
    return max(files, key=os.path.getmtime) if files else None

# load data
def load_gdacs():
    path = get_latest_csv("data/raw/gdacs")
    return pd.read_csv(path)

def load_emdat():
    path = get_latest_xlsx("data/raw/emdat")
    return pd.read_excel(path, skiprows=1)

def load_worldbank():
    # load all indicators
    oda = pd.read_csv(get_latest_csv_with_name("data/raw/worldbank", "oda_received_usd"))
    dep = pd.read_csv(get_latest_csv_with_name("data/raw/worldbank", "aid_dependency_percent_gni"))
    res = pd.read_csv(get_latest_csv_with_name("data/raw/worldbank", "electricity_access_pct"))

    for df in [oda, dep, res]:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    oda = oda.rename(columns={"value": "aid_received_usd"})
    dep = dep.rename(columns={"value": "aid_dependency_percent_gni"})
    res = res.rename(columns={"value": "electricity_access_pct"})

    # merge into single economic df
    return oda[["iso3", "year", "aid_received_usd"]].merge(
        dep[["iso3", "year", "aid_dependency_percent_gni"]], on=["iso3", "year"], how="outer"
    ).merge(
        res[["iso3", "year", "electricity_access_pct"]], on=["iso3", "year"], how="outer"
    )

# data preparation : cleaning
def clean_emdat_columns(df):
    df = df.copy()
    df.columns = [col.strip() for col in df.columns]
    df["iso3"] = df["#country +code"]
    df["country"] = df["#country +name"]
    df["year"] = pd.to_numeric(df["#date +occurred"], errors="coerce")
    df["total_deaths"] = pd.to_numeric(df["#affected +ind +killed"], errors="coerce").fillna(0)
    df["total_affected"] = pd.to_numeric(df["#affected +ind"], errors="coerce").fillna(0)
    return df

def prepare_emdat_summary(df):
    df = clean_emdat_columns(df)
    return df.groupby(["iso3"]).agg(
        historical_disaster_count=("year", "count"),
        average_deaths=("total_deaths", "mean"),
        average_affected_population=("total_affected", "mean")
    ).reset_index()

# mapping and classification
def map_alert_to_score(level):
    return {"Green": 1, "Orange": 2, "Red": 3}.get(level, 1)

def classify_risk(score):
    if score >= 70: return "High"
    return "Medium" if score >= 40 else "Low"

def classify_impact(score):
    if score < 20: return "Low"
    if score < 50: return "Moderate"
    return "High" if score < 100 else "Severe"

def build_scorecard():
    gdacs_df = load_gdacs()
    emdat_summary = prepare_emdat_summary(load_emdat())
    wb_df = load_worldbank()
    
    # most recent year available for each country to prevent nulls
    wb_df = wb_df.sort_values(["iso3", "year"])
    wb_latest = wb_df.groupby("iso3", as_index=False).last()

    # merge all 3 sources
    scorecard = gdacs_df.merge(emdat_summary, on="iso3", how="left")
    scorecard = scorecard.merge(wb_latest, on="iso3", how="left")

    
    fill_cols = ["historical_disaster_count", "average_deaths", "average_affected_population", 
                 "aid_received_usd", "aid_dependency_percent_gni", "electricity_access_pct"]
    scorecard[fill_cols] = scorecard[fill_cols].fillna(0)
    scorecard["electricity_access_pct"] = scorecard["electricity_access_pct"].replace(0, 50)

    
    scorecard["real_time_severity_score"] = scorecard["alert_level"].apply(map_alert_to_score)
    
    max_d = max(scorecard["historical_disaster_count"].max(), 1)
    max_m = max(scorecard["average_deaths"].max(), 1)
    scorecard["historical_risk_score"] = ((scorecard["historical_disaster_count"]/max_d)*50 + (scorecard["average_deaths"]/max_m)*50).round(2)
    
   
    scorecard["financial_dependency_score"] = scorecard["aid_dependency_percent_gni"].fillna(0).round(2)

    # valunability index
    scorecard["vulnerability_index"] = (
        scorecard["historical_risk_score"] * 0.35 +
        scorecard["real_time_severity_score"] * 20 +
        scorecard["financial_dependency_score"] * 0.20 +
        ((100 - scorecard["electricity_access_pct"]) * 0.25)
    ).round(2)
    scorecard["risk_category"] = scorecard["vulnerability_index"].apply(classify_risk)

    # impact estimation
    scorecard["estimated_affected_population"] = (scorecard["average_affected_population"].replace(0, 1000) * 1.5).round(0)
    scorecard["estimated_deaths"] = (scorecard["average_deaths"].replace(0, 5) * 1.5).round(0)
    scorecard["estimated_required_aid_usd"] = (scorecard["estimated_affected_population"] * 120).round(2)
    
    scorecard["impact_score"] = (scorecard["estimated_deaths"] * 2 + scorecard["estimated_required_aid_usd"] / 1000000).round(2)
    scorecard["estimated_impact_level"] = scorecard["impact_score"].apply(classify_impact)

    
    scorecard["funding_gap_usd"] = (scorecard["estimated_required_aid_usd"] - scorecard["aid_received_usd"]).clip(lower=0)
    
    # triage score
   
    impact_scaled = scorecard["impact_score"].clip(upper=100)
    gap_scaled = (scorecard["funding_gap_usd"].clip(upper=100000000) / 100000000 * 100)
    
    scorecard["triage_score"] = (
        (scorecard["real_time_severity_score"] / 3 * 35) +
        (scorecard["vulnerability_index"].clip(upper=100) * 0.25) +
        (impact_scaled * 0.25) +
        (gap_scaled * 0.15)
    ).round(2)

   
    scorecard["urgency_level"] = pd.cut(scorecard["triage_score"], bins=[-0.01, 30, 60, 85, 105], 
                                       labels=["Routine", "Heightened", "Urgent", "Emergency"])

    
    # event_id is unique and clean for database push
    
    scorecard = scorecard.dropna(subset=['event_id'])
    scorecard['event_id'] = scorecard['event_id'].astype(int)
    # keep the last entry for each event_id to ensure a single unique batch
    scorecard = scorecard.drop_duplicates(subset=['event_id'], keep='last')

    # data qulity flags
    scorecard["location_match_status"] = np.where(
        scorecard["iso3"].astype(str).str.upper().isin(["UNKNOWN", "NONE", "NAN", ""]),
        "Unmatched", "Matched"
    )

   # recomandations
    scorecard["response_recommendation"] = scorecard.apply(generate_recommendation, axis=1)
    scorecard["critical_resource_gap"] = scorecard.apply(calculate_resource_gap_flag, axis=1)

    # fill numeric NaNs with 0 to prevent JSON errors
    num_cols = scorecard.select_dtypes(include=[np.number]).columns
    scorecard[num_cols] = scorecard[num_cols].fillna(0)

    # convert categorical to string for JSON compliance
    scorecard["urgency_level"] = scorecard["urgency_level"].astype(str).replace('nan', 'Routine')

    # handle string NaNs
    str_cols = scorecard.select_dtypes(include=['object']).columns
    scorecard[str_cols] = scorecard[str_cols].fillna('Unknown')

    # last updated time
    scorecard["processed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return scorecard

def build_historical_validation():
    
    yearly = clean_emdat_columns(load_emdat())
    wb_df = load_worldbank()
    df = yearly.merge(wb_df, on=["iso3", "year"], how="left").fillna(0)
    
   
    df = df.sort_values(["iso3", "year"])
    df["estimated_deaths"] = (
        df.groupby("iso3")["total_deaths"]
        .transform(lambda s: s.expanding().mean().shift())
        .fillna(5)
        .round(0)
    )
    
   
    df["deaths_error"] = df["estimated_deaths"] - df["total_deaths"]
    df["mae_deaths"] = df["deaths_error"].abs()

    # calculate historical disaster counts for equity analysis
    counts = df.groupby('iso3').size().reset_index(name='historical_disaster_count')
    df = df.merge(counts, on='iso3', how='left')

    # prevent database duplication
    df["validation_key"] = (
        df["iso3"].astype(str) + "_" +
        df["year"].astype(str) + "_" +
        df.groupby(["iso3", "year"]).cumcount().astype(str)
    )
    
    # last updated time
    df["processed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # cleanup for historical data
    db_columns = [
        "country", "iso3", "year", "total_deaths", "estimated_deaths", 
        "aid_received_usd", "historical_disaster_count", "mae_deaths", "validation_key", "processed_at"
    ]
    
    
    df = df[db_columns].fillna(0)
    
    return df