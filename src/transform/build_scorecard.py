import glob
import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone


# Section 1: Intelligence recomendations and decision support logic
# ----------------------------------------------------------
# translate raw data points into insights for humanitarian responses.


def generate_recommendation(row):
    
    # High-intensity emergency: focus on rescue
    if row['urgency_level'] == 'Emergency':
        return "Immediate mobilization of search & rescue and emergency medical units."
    
    # Financial strain: prioritize the funding appeal
    if row['funding_gap_usd'] > 1000000:
        return "Prioritize financial appeal; significant resource deficit detected."
    
    # Infrastructure fragility: focus on logistics and energy
    if row['electricity_access_pct'] < 40:
        return "Focus on logistics and off-grid power; local infrastructure is critical."
    
    # Low-risk/Stable: standard monitoring
    return "Monitor situation; routine humanitarian support recommended."

def calculate_resource_gap_flag(row):
  
    # Identifies high-vulnerabilities  where existing aid is  insufficient compared to the predicted disaster impact.
    # $500k is limit for international level disster funds
    # On a 0-100 scale, 60 marks the start of the 'High Intensity' zone.

    return "CRITICAL" if row['funding_gap_usd'] > 500000 and row['vulnerability_index'] > 60 else "MONITOR"



# Section 2: Dynamic file management
# ----------------------------------------------------------
# Most recent data files selection.


def get_latest_csv(folder):
    # GDACS : extracting happenning frequently
    files = glob.glob(folder + "/*.csv")
    return max(files, key=os.path.getmtime) if files else None

def get_latest_csv_with_name(folder, text):
    # World bank indicators : oda, aid, electricity will be names
    files = [f for f in glob.glob(folder + "/*.csv") if text in os.path.basename(f)]
    return max(files, key=os.path.getmtime) if files else None

def get_latest_xlsx(folder):
    # EM-DAT international disaster records : excel format only
    files = glob.glob(folder + "/*.xlsx")
    return max(files, key=os.path.getmtime) if files else None



# Section 3: DATA Loading (GDACS, EM-DAT, WORLD BANK)
# ----------------------------------------------------------

def load_gdacs():
    # real-time disaster alerts collected from the GDACS platform.
    path = get_latest_csv("data/raw/gdacs")
    return pd.read_csv(path)

def load_emdat():
    # historical disaster records from EM-DAT
    # skipping the HXL metadata headers
    path = get_latest_xlsx("data/raw/emdat")
    return pd.read_excel(path, skiprows=1)

def load_worldbank():
    
    # Extracts and merges three distinct economic indicators from World Bank data
    # building a Resilience Profile' for each country.
    # 1. ODA Received (Official Development Assistance)
    # 2. Aid Dependency (as a % of GNI)
    # 3. Electricity Access (% of population)
    
    oda = pd.read_csv(get_latest_csv_with_name("data/raw/worldbank", "oda_received_usd"))
    dep = pd.read_csv(get_latest_csv_with_name("data/raw/worldbank", "aid_dependency_percent_gni"))
    res = pd.read_csv(get_latest_csv_with_name("data/raw/worldbank", "electricity_access_pct"))

    # Convert to numeric for merge
    for df in [oda, dep, res]:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    oda = oda.rename(columns={"value": "aid_received_usd"})
    dep = dep.rename(columns={"value": "aid_dependency_percent_gni"})
    res = res.rename(columns={"value": "electricity_access_pct"})

    return oda[["iso3", "year", "aid_received_usd"]].merge(
        dep[["iso3", "year", "aid_dependency_percent_gni"]], on=["iso3", "year"], how="outer"
    ).merge(
        res[["iso3", "year", "electricity_access_pct"]], on=["iso3", "year"], how="outer"
    )


# Section 4: DATA Preprocessing & Standradization
# ----------------------------------------------------------

def clean_emdat_columns(df):
    # Standardizes EM-DAT column names and extracts core features.
    # Handles the conversion of raw HXL(Exchange Language) tags into usable DataFrame columns.

    df = df.copy()
    df.columns = [col.strip() for col in df.columns]
    df["iso3"] = df["#country +code"]
    df["country"] = df["#country +name"]
    df["year"] = pd.to_numeric(df["#date +occurred"], errors="coerce")
    df["total_deaths"] = pd.to_numeric(df["#affected +ind +killed"], errors="coerce").fillna(0)
    df["total_affected"] = pd.to_numeric(df["#affected +ind"], errors="coerce").fillna(0)
    return df

def prepare_emdat_summary(df):

    # Aggregates decades of disaster history by country
    # frequency (count) and severity (mean deaths/affected).
    
    df = clean_emdat_columns(df)
    return df.groupby(["iso3"]).agg(
        historical_disaster_count=("year", "count"),
        average_deaths=("total_deaths", "mean"),
        average_affected_population=("total_affected", "mean")
    ).reset_index() 


# Section 5: Mapping & Scientific Categorization
# ----------------------------------------------------------

def map_alert_to_score(level):
    # Weights GDACS alerts: Red (3), Orange (2), Green (1)
    return {
        "Green": 1, 
        "Orange": 2, 
        "Red": 3
        }.get(level, 1) # default

def classify_risk(score):
    # Standardizes the Vulnerability Index into descriptive risk tiers.
    if score >= 70: return "High"
    return "Medium" if score >= 40 else "Low"

def classify_impact(score):
    # Classifies disaster events by the severity of their predicted consequences.
    if score < 20: return "Low"
    if score < 50: return "Moderate"
    return "High" if score < 100 else "Severe"



# SECTION 6: Main Score Functions
# ----------------------------------------------------------

def build_scorecard():

    # Main function. 
    # performs the complex joining of real-time alerts with historical and economic layers to generate the final 0-100 Triage Score.
    
    # Data Integration : Load extracted data
    gdacs_df = load_gdacs()
    emdat_summary = prepare_emdat_summary(load_emdat())
    wb_df = load_worldbank()
    
    # select most recent year available for each country to prevent null values.
    wb_df = wb_df.sort_values(["iso3", "year"]) # by country, year
    wb_latest = wb_df.groupby("iso3", as_index=False).last() # most recent year from each country bucket

    # Merge data 
    scorecard = gdacs_df.merge(emdat_summary, on="iso3", how="left") # current disaster vs history
    scorecard = scorecard.merge(wb_latest, on="iso3", how="left") # current disaster vs economic history

    # missing value handling
    # assume '0' for missing historical data and '50%' as a median for electricity access.
    fill_cols = ["historical_disaster_count", "average_deaths", "average_affected_population", 
                 "aid_received_usd", "aid_dependency_percent_gni", "electricity_access_pct"]
    scorecard[fill_cols] = scorecard[fill_cols].fillna(0) # since data is merged from diffrent sources : replace NaN with 0
    scorecard["electricity_access_pct"] = scorecard["electricity_access_pct"].replace(0, 50) # use 50 here to keep vulnerability score in line

    # feature engineering : score logic
    # convert GDACS level to weight scores (1-3)
    scorecard["real_time_severity_score"] = scorecard["alert_level"].apply(map_alert_to_score)
    
    # normalize historical risk (0-100 scale)
    # on two different scale fields
    max_d = max(scorecard["historical_disaster_count"].max(), 1) # avoid divide by 0
    max_m = max(scorecard["average_deaths"].max(), 1)
    scorecard["historical_risk_score"] = (

        (scorecard["historical_disaster_count"]/max_d)*50 + 
        (scorecard["average_deaths"]/max_m)*50).round(2) # highest score count could be 100, so each multipy by 50 is fair
    
    # measure economic fragility
    # specific World Bank metric : "Net Official Development Assistance" (aid money) as a percentage of the country's Gross National Income (GNI).
    scorecard["financial_dependency_score"] = scorecard["aid_dependency_percent_gni"].fillna(0).round(2)

    # --- THE VULNERABILITY INDEX ---
    # Weighted Mix: 35% History(0-100 scale) , 20% Severity(1-3 scale) , 20% Financial Gap(0-100 scale) , 25% Infrastructure(0-100 scale)
    scorecard["vulnerability_index"] = (
        scorecard["historical_risk_score"] * 0.35 +
        scorecard["real_time_severity_score"] * 20 +
        scorecard["financial_dependency_score"] * 0.20 +
        ((100 - scorecard["electricity_access_pct"]) * 0.25)
    ).round(2)

    # Label risks : High , Medeium, LKow based on vulnerability_index
    scorecard["risk_category"] = scorecard["vulnerability_index"].apply(classify_risk)

    # Impact estimation : oredictions
    # 1.5x multiplier(Heuristic Multiplie) against historical averages to provide a conservative aid estimate.
    scorecard["estimated_affected_population"] = (scorecard["average_affected_population"].replace(0, 1000) * 1.5).round(0)
    scorecard["estimated_deaths"] = (scorecard["average_deaths"].replace(0, 5) * 1.5).round(0)
    
    # Financial rule: $120(Humanitarian Benchmark) per person affected is the base aid required estimate.
    scorecard["estimated_required_aid_usd"] = (scorecard["estimated_affected_population"] * 120).round(2)
    
    # composite impact score
    # 1 death has roughly the same "weight" as $2,000,000 in damage.
    scorecard["impact_score"] = (scorecard["estimated_deaths"] * 2 + scorecard["estimated_required_aid_usd"] / 1000000).round(2)
    scorecard["estimated_impact_level"] = scorecard["impact_score"].apply(classify_impact)

    # Identifying the actual financial triage gap
    scorecard["funding_gap_usd"] = (scorecard["estimated_required_aid_usd"] - scorecard["aid_received_usd"]).clip(lower=0) # replace negative with 0 
    
    # TRIAGE Score (0-100)
    # priority indicator for the Humanitarian
    # based on live disaster, the country’s history, the economic weakness, and the aid needed

    impact_scaled = scorecard["impact_score"].clip(upper=100) # prevent mega disster having very high score
    gap_scaled = (scorecard["funding_gap_usd"].clip(upper=100000000) / 100000000 * 100) # feature scaling financial into 0-100 scale
    

    # the final Triage Score (0-100) has four factors: 
    # 35% Live Alert level, 25% Country Vulnerability, 
    # 25% Predicted Damage, and 15% Financial Need.
    scorecard["triage_score"] = (
        (scorecard["real_time_severity_score"] / 3 * 35) +
        (scorecard["vulnerability_index"].clip(upper=100) * 0.25) +
        (impact_scaled * 0.25) +
        (gap_scaled * 0.15)
    ).round(2)

   
    # use -0.01 and 105 as 'buffer'  
    # thresholds (30, 60, 85) are weighted to prevent 'Alert Fatigue.'
    scorecard["urgency_level"] = pd.cut(scorecard["triage_score"], bins=[-0.01, 30, 60, 85, 105], 
                                       labels=["Routine", "Heightened", "Urgent", "Emergency"])

    # final database preparation
    scorecard = scorecard.dropna(subset=['event_id']) # drop column row if 'event_id' is 'NAN'
    scorecard['event_id'] = scorecard['event_id'].astype(int) # force id into number
    scorecard = scorecard.drop_duplicates(subset=['event_id'], keep='last') # found duplicates : keep latest only

    # tracks if we successfully matched the ISO3 code to a real country
    # np : search in entire column
    scorecard["location_match_status"] = np.where(
        scorecard["iso3"].astype(str).str.upper().isin(["UNKNOWN", "NONE", "NAN", ""]),
        "Unmatched", "Matched"
    )

    # applying the intelligence recommendations
    # axis = 1 : checking one country raw at a time 
    # split entire row into custom functions : generate_recommendation, calculate_resource_gap_flag

    scorecard["response_recommendation"] = scorecard.apply(generate_recommendation, axis=1)
    scorecard["critical_resource_gap"] = scorecard.apply(calculate_resource_gap_flag, axis=1)

    # final data fix: null value replace with 0 and String-casting for JSON/Cloud 
    num_cols = scorecard.select_dtypes(include=[np.number]).columns
    scorecard[num_cols] = scorecard[num_cols].fillna(0)
    scorecard["urgency_level"] = scorecard["urgency_level"].astype(str).replace('nan', 'Routine')
    str_cols = scorecard.select_dtypes(include=['object']).columns
    scorecard[str_cols] = scorecard[str_cols].fillna('Unknown')

    # pipeline timestamp
    scorecard["processed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return scorecard



# SECTION 7: historical error check (validity check)
# ----------------------------------------------------------

def build_historical_validation():
    # align historical disaster records with their corresponding annual economic data. 
    # 'Left Join' ensures we keep all disaster events, 
    # providing the data needed to validate  model accuracy.
    yearly = clean_emdat_columns(load_emdat())
    wb_df = load_worldbank()
    df = yearly.merge(wb_df, on=["iso3", "year"], how="left").fillna(0)
    
    # logic: calculate a country's historical average deaths, 
    # then 'shift' it to ensure we only use past data to predict the future. 
    # this prevents data leakage and provides an honest baseline for our MAE score.
    df = df.sort_values(["iso3", "year"])
    df["estimated_deaths"] = (
        df.groupby("iso3")["total_deaths"]
        .transform(lambda s: s.expanding().mean().shift())
        .fillna(5)
        .round(0)
    )
    
    # accuracy Calculation: raw difference (error). 
    # take the absolute value so that 'over-estimates' and 
    # 'under-estimates' don't cancel each other out in final score.

    df["deaths_error"] = df["estimated_deaths"] - df["total_deaths"]
    df["mae_deaths"] = df["deaths_error"].abs()

    #Equity Analysis: calculate the total number of historical disasters 
    # for each country and merge it back. This allows us to identify 'hotspots' 
    # where repeated disasters have likely weakened the country's resilience.
    counts = df.groupby('iso3').size().reset_index(name='historical_disaster_count')
    df = df.merge(counts, on='iso3', how='left')

    # Database Prep: generate a unique 'validation_key' to distinguish multiple 
    # events in the same country/year(cumcount number implimentation), add a processing timestamp for version 
    # control, and filter only the essential columns for the final database push.
    df["validation_key"] = (
        df["iso3"].astype(str) + "_" +
        df["year"].astype(str) + "_" +
        df.groupby(["iso3", "year"]).cumcount().astype(str)
    )
    
    df["processed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    
    db_columns = [
        "country", "iso3", "year", "total_deaths", "estimated_deaths", 
        "aid_received_usd", "historical_disaster_count", "mae_deaths", "validation_key", "processed_at"
    ]
    
    return df[db_columns].fillna(0)