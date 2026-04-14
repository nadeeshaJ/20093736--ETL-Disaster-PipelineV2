# Disaster Response ETL & Triage Pipeline

This project is a real-time data engineering pipeline designed to help humanitarian organizations prioritize disaster response. It collects live disaster alerts, compares them with historical records and economic vulnerability indicators, and calculates a **0–100 Triage Score** to identify where help is needed most.

The system is built to support faster, data-driven humanitarian decision-making by transforming raw multi-source data into actionable disaster-response intelligence.

---

## Project Overview

The pipeline combines data from three major global sources to build a disaster resilience and response profile for countries currently facing emergencies:

- **GDACS**: Real-time disaster alerts for floods, storms, earthquakes, and other major hazard events
- **EM-DAT**: Historical disaster records used to estimate likely mortality and impact patterns
- **World Bank**: Economic and infrastructure indicators such as Aid Dependency, ODA Received, and Electricity Access to measure country fragility

Together, these sources allow the pipeline to rank disaster situations based on current severity, historical burden, structural weakness, and projected response needs.

---

## Key Objectives

The main goals of the project are to:

- monitor live disaster alerts in near real time
- enrich alerts with historical and economic context
- estimate likely humanitarian impact before full field reports arrive
- generate a transparent **Triage Score** for prioritization
- support dashboard-driven monitoring and decision-making
- validate estimation quality using historical back-testing

---

## Project Structure

```text
.
├── data/
│   ├── raw/               # Original files from GDACS, EM-DAT, and World Bank
│   └── outputs/           # Final processed CSVs and validation reports
├── docs/                  # Documentation for setup and automation
├── sql/                   # Database scripts
│   └── schema.sql         # SQL script to create tables in Supabase
├── src/
│   ├── extract/           # Scripts to fetch data from APIs and websites
│   ├── transform/         # Scripts that calculate scores and predictions
│   ├── load/              # Scripts to push data to Supabase and GitHub
│   └── utils/             # Helper scripts such as logging utilities
├── tests/                 # Unit and integration tests
├── dashboard.py           # Visualization script for the frontend
├── main.py                # Entry point to run the whole pipeline
└── requirements.txt       # List of required Python libraries
```

---

## Automation & Infrastructure

The pipeline is fully automated and hosted on cloud infrastructure to ensure continuous operation.

- **Azure Ubuntu VM**: The full ETL logic runs on a dedicated Azure Virtual Machine for reliable 24/7 availability
- **Cron Job Scheduling**: Tasks are scheduled to keep the data fresh without manual intervention
  - **Daily**: Updates live GDACS alerts for dashboard monitoring
  - **Monthly**: Refreshes World Bank economic indicators and EM-DAT historical records

This setup ensures that the dashboard always reflects the latest disaster conditions while maintaining updated background indicators for triage calculations.
A lightweight Flask application is also used to serve dashboard-related outputs.
<img width="1025" height="466" alt="image" src="https://github.com/user-attachments/assets/12817fb9-69f7-4cac-873e-08927770e750" />
<img width="1513" height="1083" alt="image" src="https://github.com/user-attachments/assets/14d03244-1052-452c-a78f-2fc026f16a1b" />



---

## Database (Supabase)

The project uses **Supabase (PostgreSQL)** as its central cloud database to store processed outputs and validation results.

- **Table: `latest_scorecards`**  
  Stores the latest triage scores, active disaster alerts, and response-related indicators

- **Table: `historical_validation`**  
  Stores back-testing outputs used to compare estimated disaster impact against historical outcomes

- **Data Integrity**  
  Each record includes a unique fingerprint called `validation_key` to reduce duplication and help preserve consistency across validation runs

Supabase acts as the main data hub powering the dashboard and downstream reporting.

---

## Feature Extraction

The pipeline extracts a set of engineered features from real-time, historical, and economic data sources to calculate the final triage score.

- **Real-Time Severity**  
  GDACS alert levels such as Red, Orange, and Green are converted into numerical severity weights

- **Economic Fragility**  
  Aid dependency as a percentage of GNI and total ODA funds received are used to measure economic vulnerability

- **Structural Resilience**  
  Electricity access percentages are used as a proxy indicator for infrastructure readiness and resilience

- **Historical Burden**  
  Past disaster frequency and average mortality rates per country are used to estimate how severely a country may be affected during future events

These features help transform raw disaster and development data into interpretable indicators for response prioritization.

---

## Core Calculations

The pipeline uses several equations to convert raw data into operational disaster-response intelligence.

### 1. Financial Aid Estimate

A standard humanitarian benchmark is used to estimate likely response cost before formal field assessments are complete.

```text
Estimated Aid (USD) = Affected Population × 120
```

> **Note:** `$120` is used as an approximate benchmark for providing food, water, and shelter to one person for around **3–6 months**.

### 2. Impact Score

This balances human loss against economic cost. Estimated deaths are weighted more heavily because life-saving response is the highest priority.

```text
Impact Score = (Estimated Deaths × 2) + (Estimated Required Aid / 1,000,000)
```

### 3. Master Triage Score (0–100)

```text
Triage Score = (Live Alert Score × 35%) + (Vulnerability Index × 25%) + (Predicted Impact × 25%) + (Financial Gap × 15%)
```

This is the final priority score. It combines four weighted dimensions:

- **35% – Live Alert Level**: How severe is the event right now?
- **25% – Country Vulnerability**: How fragile is the country’s structural and economic condition?
- **25% – Predicted Impact**: How many people are likely to be affected?
- **15% – Funding Gap**: How much additional humanitarian support may be required?

### 4. Mean Absolute Error (MAE)

To evaluate mortality estimation quality, the project uses **Mean Absolute Error (MAE)**:

```math
MAE = \frac{1}{n} \sum_{i=1}^{n} |Estimated\ Deaths - Actual\ Deaths|
```

This measures the average absolute difference between predicted and actual deaths across historical disaster records. Lower MAE values indicate better predictive consistency.

---

## Urgency Levels

After calculating the final triage score, the pipeline groups countries into four urgency bands to support fast operational decisions.

| Score Range | Urgency Level | Action Required |
|-------------|---------------|-----------------|
| 85–100 | Emergency | Immediate deployment of rescue units |
| 60–84 | Urgent | Major international aid appeal |
| 30–59 | Heightened | Regional teams on standby |
| 0–29 | Routine | Standard monitoring only |

These categories make it easier for humanitarian teams to interpret the score quickly and decide on response intensity.

---

## Results Generated

The pipeline produces several key forms of disaster-response intelligence:

1. **Triage Score**  
   A 0–100 ranking that identifies which countries require the most urgent humanitarian attention

2. **Mortality Predictions**  
   Conservative estimates of deaths and affected populations using a **1.5× heuristic multiplier**

3. **Actionable Recommendations**  
   Automated response guidance such as *“Immediate mobilization of search & rescue units”*

4. **Critical Resource Flags**  
   A **CRITICAL** label for countries showing major funding gaps or extremely low electricity access

5. **Scientific Validation**  
   Historical back-testing outputs and **MAE** metrics that help evaluate whether the estimation logic is reasonable and consistent

---

## Output & Visualization (Google Colab)

While the core ETL pipeline handles extraction, transformation, loading, and automation, **Google Colab** is used to display, explore, and evaluate the processed outputs.

- **Equity Analysis**  
  Colab is used to identify and visualize **disaster hotspots** so that aid prioritization can be interpreted in the context of each country’s historical burden

- **Scientific Validation**  
  Colab generates comparison charts between **Estimated Deaths** and **Actual Deaths** from historical disaster records

- **Error Tracking**  
  Colab is used to calculate and visualize **Mean Absolute Error (MAE)** so the reliability of the mathematical estimation logic can be assessed clearly

This separation keeps the pipeline operationally focused while allowing flexible, notebook-based analysis and presentation of results.

---

## How to Run

The pipeline is modular. You can run specific tasks from the terminal using the `--task` flag.

### Run the full pipeline

```bash
python main.py --task all
```

### Check live disaster alerts only

```bash
python main.py --task realtime
```

### Update historical validation data only

```bash
python main.py --task historical
```

---

## Purpose

This project demonstrates how modern ETL architecture, cloud automation, and applied analytics can be combined to support humanitarian operations.

By integrating:

- **real-time disaster alerts**
- **historical disaster patterns**
- **economic vulnerability indicators**
- **infrastructure resilience signals**

the system helps humanitarian organizations identify where support may be needed first, estimate possible impact earlier, and allocate limited resources more effectively.
