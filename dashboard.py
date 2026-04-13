import os
from dotenv import load_dotenv
from flask import Flask, render_template
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
from supabase import create_client, Client

# Load secured credentials
load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------
# DATABASE CONNECTION & SYNC
# ---------------------------------------------------------
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(URL, KEY)

def fetch_and_audit():
    """Retrieves data and extracts the exact pipeline processing timestamp."""
    res_live = supabase.table("latest_scorecards").select("*").execute()
    res_hist = supabase.table("historical_validation").select("*").execute()
    
    live_df = pd.DataFrame(res_live.data)
    hist_df = pd.DataFrame(res_hist.data)
    
    if live_df.empty:
        return pd.DataFrame(), pd.DataFrame(), {"refreshed": "No Data Found"}

    # Extracting the actual Pipeline Stamp
    # We use the first row's processed_at value to represent the batch
    pipeline_time = live_df["processed_at"].iloc[0] if "processed_at" in live_df.columns else "Manual Refresh"
    hist_pipeline_time = hist_df["processed_at"].iloc[0] if not hist_df.empty and "processed_at" in hist_df.columns else "N/A"

    # Numeric formatting and simplified triage logic
    num_cols = ["vulnerability_index", "triage_score", "funding_gap_usd", "electricity_access_pct", 
                "estimated_deaths", "impact_score", "estimated_required_aid_usd", "historical_disaster_count"]
    live_df[num_cols] = live_df[num_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # Recalculating Balanced Triage for the web view
    impact_scaled = live_df["impact_score"].clip(upper=100)
    gap_scaled = (live_df["funding_gap_usd"].clip(upper=100000000) / 100000000 * 100)
    live_df["triage_score"] = ((live_df["real_time_severity_score"] / 3 * 35) + 
                                (live_df["vulnerability_index"].clip(upper=100) * 0.25) + 
                                (impact_scaled * 0.25) + (gap_scaled * 0.15)).round(2)
    
    live_df["urgency_level"] = pd.cut(live_df["triage_score"], bins=[-0.01, 30, 60, 85, 105], labels=["Routine", "Heightened", "Urgent", "Emergency"])

    kpis = {
        "total": len(live_df),
        "high_risk": (live_df['vulnerability_index'] > 50).sum(),
        "gap_b": live_df['funding_gap_usd'].sum() / 1e9,
        "refreshed": pipeline_time,
        "hist_refreshed": hist_pipeline_time
    }
    
    return live_df, hist_df, kpis

@app.route("/")
def index():
    live_df, hist_df, kpis = fetch_and_audit()

    # 1. GDACS-Style Satellite Scatter Map
    fig_map = px.scatter_mapbox(live_df, lat="latitude", lon="longitude", color="disaster_type",
                                size="vulnerability_index", hover_name="country",
                                mapbox_style="satellite-streets", # High-detail professional view
                                color_discrete_sequence=px.colors.qualitative.Set1,
                                size_max=30, zoom=1.2, height=650)
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    # 2. Intensity Heatmap
    pivot = live_df.pivot_table(values="vulnerability_index", index="country", columns="disaster_type", aggfunc="mean").fillna(0)
    fig_heat = px.imshow(pivot.sort_values(pivot.columns[0], ascending=False).head(10), color_continuous_scale="YlOrRd")

    # 3. Scientific Accuracy (Log-Scale)
    fig_acc = px.scatter(hist_df, x="total_deaths", y="estimated_deaths", log_x=True, log_y=True, opacity=0.6,
                         title="<b>Scientific Accuracy (Log-Scale)</b>", labels={"total_deaths": "Observed", "estimated_deaths": "Estimated"})
    fig_acc.add_shape(type="line", x0=1, y0=1, x1=100000, y1=100000, line=dict(color="Red", dash="dash"))

    # 4. Resilience Quadrants with Labels
    fig_res = px.scatter(live_df, x="vulnerability_index", y="electricity_access_pct", size="estimated_required_aid_usd",
                         color="urgency_level", hover_name="country", text="iso3")
    fig_res.add_hline(y=50, line_dash="dot"); fig_res.add_vline(x=50, line_dash="dot")
    fig_res.add_annotation(x=80, y=10, text="<b>FRAGILE</b>", showarrow=False, font=dict(color="red"))
    fig_res.add_annotation(x=20, y=90, text="<b>STABLE</b>", showarrow=False, font=dict(color="green"))

    # 5. Preparing 24h Alerts (Card Format)
    live_df["start_date"] = pd.to_datetime(live_df["start_date"], utc=True)
    alerts = live_df[live_df["start_date"] >= (pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=24))].sort_values("triage_score", ascending=False).head(3).to_dict('records')

    return render_template("index.html", kpis=kpis, alerts=alerts,
                           map_plot=pio.to_html(fig_map, full_html=False),
                           heat_plot=pio.to_html(fig_heat, full_html=False),
                           acc_plot=pio.to_html(fig_acc, full_html=False),
                           res_plot=pio.to_html(fig_res, full_html=False))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, ssl_context=('cert.pem', 'privkey.pem'))