# TrialPulse

**TrialPulse** is a clinical-trial operations analytics platform built with Python, Pandas, DuckDB, Parquet, and Streamlit.

It demonstrates a production-inspired **Bronze → Silver → Gold** data architecture using entirely synthetic clinical-operations data.

> This project uses synthetic data only. It is not intended for patient care, clinical decision-making, or regulated use.

**Live dashboard:** https://trialpulse.streamlit.app

## Dashboard

The Streamlit dashboard provides:

- Study enrolment progress versus plan
- Site-level operational risk ranking
- Completed, missed, and overdue visit compliance
- Data-quality audit metrics across pipeline layers

## Architecture

```text
Synthetic CSV files
        |
        v
Bronze: Raw Parquet + DuckDB tables
        |
        v
Silver: Validated datasets + quarantine records
        |
        v
Gold: Dashboard-ready reporting tables
        |
        v
Streamlit clinical-operations dashboard
```

## Data quality controls

The Silver layer applies these controls:

- Subject foreign-key validation against sites
- Visit and laboratory foreign-key validation against subjects
- Duplicate subject detection
- Late-arriving visit prioritisation and visit deduplication
- Configurable 3-day early clinical-visit window
- Lab-status validation
- Quarantine records with explicit failure rules

## Technology

- Python
- Pandas
- DuckDB
- PyArrow / Parquet
- Streamlit
- Plotly

## Local setup

```powershell
git clone <YOUR-REPOSITORY-URL>
cd TrialPulse

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Run the pipeline

Run the layers in order:

```powershell
python src\bronze_ingestion.py
python src\silver_validation.py
python src\gold_reporting.py
```

## Run the dashboard

```powershell
streamlit run app\dashboard.py
```

Then open `http://localhost:8501`.

## Project structure

```text
TrialPulse/
├── app/
│   └── dashboard.py
├── data/
│   └── demo/                  # Versioned synthetic Gold CSVs for deployment
├── outputs/                   # Local generated artifacts, ignored by Git
├── src/
│   ├── bronze_ingestion.py
│   ├── silver_validation.py
│   └── gold_reporting.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Example results

| Metric | Result |
|---|---:|
| Bronze visits ingested | 1,087 |
| Silver visits validated | 1,058 |
| Quarantine rule violations | 48 |
| Studies monitored | 2 |
| Sites monitored | 20 |

## Portfolio talking points

- Built a reproducible medallion-style analytics pipeline for clinical-trial operations data.
- Implemented validation, foreign-key checks, configurable visit-window logic, late-arrival handling, and quarantined rule violations.
- Created Gold-layer enrolment, visit-compliance, site-risk, and data-quality reporting models.
- Delivered an interactive Streamlit dashboard backed by synthetic, version-controlled demo data.