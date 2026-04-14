# AI-Generated Out-put content
import os
import sys
from dotenv import load_dotenv
from flask import Flask, render_template
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
from supabase import create_client, Client
from datetime import datetime

# Load secured credentials
load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_PUBLIC_KEY")

if not URL or not KEY:
    print("❌ ERROR: Supabase credentials missing from environment.")
    sys.exit(1)

supabase: Client = create_client(URL, KEY)

def fetch_and_process():
    """Retrieves data and applies scientific logic fixes."""
    try:
        res_live = supabase.table("latest_scorecards").select("*").execute()
        res_hist = supabase.table("historical_validation").select("*").execute()
        live_df, hist_df = pd.DataFrame(res_live.data), pd.DataFrame(res_hist.data)
        
        if live_df.empty:
            return None, None, {"refreshed": "Sync Required"}

        # 1. Pipeline Sync & Recommendation Fallbacks
        sync_time = live_df["processed_at"].iloc[0] if "processed_at" in live_df.columns else "Manual Refresh"
        hist_sync = hist_df["processed_at"].iloc[0] if not hist_df.empty and "processed_at" in hist_df.columns else "N/A"
        
        if "response_recommendation" in live_df.columns:
            live_df["response_recommendation"] = live_df["response_recommendation"].replace([None, 'None', 'nan', ''], "Prioritize Resource Triage.")
        else:
            live_df["response_recommendation"] = "Model Analysis Pending..."

        # 2. Numeric Formatting
        num_cols = ["vulnerability_index", "triage_score", "funding_gap_usd", "electricity_access_pct", 
                    "estimated_deaths", "impact_score", "estimated_required_aid_usd", "historical_disaster_count"]
        live_df[num_cols] = live_df[num_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

        # 3. Recalculate Triage & Urgency (Colab Consistency)
        impact_scaled = live_df["impact_score"].clip(upper=100)
        gap_scaled = (live_df["funding_gap_usd"].clip(upper=1e8) / 1e8 * 100)
        live_df["triage_score"] = ((live_df["real_time_severity_score"] / 3 * 35) + 
                                   (live_df["vulnerability_index"].clip(upper=100) * 0.25) + 
                                   (impact_scaled * 0.25) + (gap_scaled * 0.15)).round(2)
        
        live_df["urgency_level"] = pd.cut(live_df["triage_score"], bins=[-0.1, 30, 60, 85, 105], 
                                         labels=["Routine", "Heightened", "Urgent", "Emergency"])

        kpis = {
            "total": len(live_df),
            "high_risk": (live_df['vulnerability_index'] > 50).sum(),
            "gap_b": live_df['funding_gap_usd'].sum() / 1e9,
            "refreshed": sync_time,
            "hist_refreshed": hist_sync
        }
        return live_df, hist_df, kpis
    except Exception as e:
        print(f"❌ Data Processing Error: {e}")
        return None, None, {"refreshed": "Error"}

@app.route("/")
def index():
    live_df, hist_df, kpis = fetch_and_process()
    if live_df is None: return "Check Console for Database Errors."

    # --- CHART 1: MAP (Colab Colors) ---
    map_df = live_df[live_df['latitude'] != 0].copy()
    fig_map = px.scatter_mapbox(map_df, lat="latitude", lon="longitude", color="disaster_type",
                                size="vulnerability_index", hover_name="country", 
                                mapbox_style="open-street-map",
                                color_discrete_map={'EQ': '#e74c3c', 'FL': '#3498db', 'TC': '#f1c40f', 'WF': '#e67e22'},
                                size_max=22, zoom=1.1, height=600)
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    # --- CHART 2: INTENSITY HEATMAP ---
    pivot = live_df.pivot_table(values="vulnerability_index", index="country", columns="disaster_type", aggfunc="mean").fillna(0)
    fig_heat = px.imshow(pivot.sort_values(pivot.columns[0], ascending=False).head(10), color_continuous_scale="YlOrRd")

    # --- CHART 3: ACCURACY validation ---
    fig_acc = px.scatter(hist_df, x="total_deaths", y="estimated_deaths", log_x=True, log_y=True, opacity=0.6)
    fig_acc.add_shape(type="line", x0=1, y0=1, x1=100000, y1=100000, line=dict(color="Red", dash="dash"))

    # --- CHART 4: RESILIENCE QUADRANTS ---
    fig_res = px.scatter(live_df, x="vulnerability_index", y="electricity_access_pct", size="estimated_required_aid_usd",
                         color="urgency_level", hover_name="country", text="iso3")
    fig_res.add_hline(y=50, line_dash="dot"); fig_res.add_vline(x=50, line_dash="dot")
    fig_res.add_annotation(x=80, y=10, text="<b>FRAGILE</b>", showarrow=False, font=dict(color="red"))

    # --- CHART 5: TOP 5 FUNDING GAPS ---
    top_gap = live_df.groupby("country")["funding_gap_usd"].sum().sort_values(ascending=False).head(5).reset_index()
    fig_gap = px.bar(top_gap, x="funding_gap_usd", y="country", orientation='h', color="funding_gap_usd", color_continuous_scale="Reds")

    # --- CHART 6: HISTORICAL AID EQUITY (KeyError Fixed) ---
    if not hist_df.empty:
        d_col = 'historical_disaster_count' if 'historical_disaster_count' in hist_df.columns else 'disaster_count'
        hist_df["aid_per"] = (pd.to_numeric(hist_df["aid_received_usd"]) / pd.to_numeric(hist_df[d_col])).fillna(0)
        aid_avg = hist_df.groupby("country")["aid_per"].mean().sort_values(ascending=False).head(10).reset_index()
        fig_eq = px.bar(aid_avg, x="aid_per", y="country", orientation='h', color_continuous_scale="Blues")
        fig_eq.add_vline(x=hist_df["aid_per"].mean(), line_dash="dash", line_color="red")
    else:
        fig_eq = px.bar(title="Data Pending...")

    # --- LEADERBOARD & ALERTS ---
    leaderboard = live_df.groupby(["country", "iso3"], as_index=False).agg(risk=("vulnerability_index", "mean")).sort_values("risk", ascending=False).head(10)
    leader_html = leaderboard.to_html(classes="table table-hover table-bordered", index=False)
    
    alerts = live_df[pd.to_datetime(live_df["start_date"], utc=True) >= (pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=24))].sort_values("triage_score", ascending=False).to_dict('records')

    return render_template("index.html", kpis=kpis, alerts=alerts, leader_html=leader_html,
                           map_p=pio.to_html(fig_map, full_html=False), 
                           heat_p=pio.to_html(fig_heat, full_html=False),
                           acc_p=pio.to_html(fig_acc, full_html=False), 
                           res_p=pio.to_html(fig_res, full_html=False),
                           gap_p=pio.to_html(fig_gap, full_html=False), 
                           eq_p=pio.to_html(fig_eq, full_html=False))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, ssl_context=('cert.pem', 'privkey.pem'))
