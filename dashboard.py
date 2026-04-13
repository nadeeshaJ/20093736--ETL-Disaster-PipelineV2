from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import plotly.io as pio
from supabase import create_client

app = Flask(__name__)

# Cloud Database Credentials
URL = "https://qtmqvenyqbkqjeucqyor.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF0bXF2ZW55cWJrcWpldWNxeW9yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYwMTUzOTQsImV4cCI6MjA5MTU5MTM5NH0.Cgt1juA5_T0b9x4h9ER0lmd-hy9JOgUUxINFGwzItSo" 
supabase = create_client(URL, KEY)

def fetch_data(table):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data)

@app.route("/")
def dashboard():
    # 1. Fetch Data Layers
    live_df = fetch_data("latest_scorecards")
    hist_df = fetch_data("historical_validation")

    # 2. Build Live Map (Operational View)
    fig_map = px.choropleth(
        live_df, locations="iso3", color="vulnerability_index",
        hover_name="country", color_continuous_scale="Reds",
        title="Live Global Vulnerability Monitor"
    )
    map_html = pio.to_html(fig_map, full_html=False)

    # 3. Build Scientific Validation (Analytical View)
    # Re-calculating MAE for the chart: $MAE = |Estimated - Actual|$
    hist_df['mae_deaths'] = (hist_df['estimated_deaths'] - hist_df['total_deaths']).abs()
    fig_accuracy = px.histogram(
        hist_df, x="mae_deaths", nbins=20, 
        title="Scientific Validation: Impact Estimation Accuracy",
        color_discrete_sequence=['#1e3c72']
    )
    accuracy_html = pio.to_html(fig_accuracy, full_html=False)

    # 4. Top Metrics
    total_episodes = len(live_df)
    emergency_count = len(live_df[live_df['urgency_level'] == 'Emergency'])

    return render_template('index.html', 
                           map_plot=map_html, 
                           accuracy_plot=accuracy_html,
                           total_episodes=total_episodes,
                           emergency_count=emergency_count)

if __name__ == "__main__":
    #  for port 8080 and SSL
    app.run(host='0.0.0.0', port=8080, ssl_context=('cert.pem', 'privkey.pem'))