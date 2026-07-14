# TrialPulse

## Clinical Trial Operations Analytics Platform

TrialPulse is an end-to-end clinical-trial operations analytics project built with **Python, Pandas, DuckDB, Parquet, Streamlit, and Plotly**.

It simulates how a clinical operations or data team can ingest raw trial data, validate data quality, preserve rejected records for investigation, create business-ready reporting tables, and present operational insights through an interactive dashboard.

> **Important:** This project uses fully synthetic demonstration data. It is not connected to a real clinical trial, does not contain patient health information, and must not be used for patient care, clinical decision-making, or regulated use.

**Live dashboard:** `trialpulse.streamlit.app`  
**GitHub repository:** `https://github.com/yaswanthhh/TrialPulse`

---

## Table of Contents

- [Business Problem](#business-problem)
- [Project Goal](#project-goal)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Data Model](#data-model)
- [Pipeline Layers](#pipeline-layers)
- [Data Quality Rules](#data-quality-rules)
- [Gold Reporting Models](#gold-reporting-models)
- [Operational Risk Score](#operational-risk-score)
- [Dashboard](#dashboard)
- [Project Results](#project-results)
- [Project Structure](#project-structure)
- [Local Setup](#local-setup)
- [Running the Pipeline](#running-the-pipeline)
- [Running the Dashboard](#running-the-dashboard)
- [Deployment](#deployment)
- [Example SQL Queries](#example-sql-queries)
- [Portfolio Talking Points](#portfolio-talking-points)
- [Future Improvements](#future-improvements)

---

## Business Problem

Clinical trials involve many operational activities across studies, research sites, subjects, visits, laboratory results, and protocol compliance processes.

Clinical operations teams need timely answers to questions such as:

- Are studies meeting planned enrolment targets?
- Which sites are behind on enrolment?
- Which subject visits are overdue or missed?
- Which sites have the highest operational risk?
- Are data-quality issues affecting reporting?
- Can the team trace a reporting record back to its original source file?
- Which records failed validation and why?

Without a structured data pipeline, operational data may arrive in separate files, contain duplicate records, include invalid references, or have late-arriving updates. This can make reliable reporting difficult.

TrialPulse solves this problem by implementing a simplified **Bronze → Silver → Gold** analytics architecture.

---

## Project Goal

The goal of TrialPulse is to demonstrate a production-inspired analytics workflow for clinical-trial operations data.

The project:

1. Ingests raw CSV files into a traceable Bronze layer.
2. Stores raw and processed datasets in Parquet and DuckDB.
3. Validates data quality in a Silver layer.
4. Sends invalid or superseded records to an auditable quarantine dataset.
5. Produces Gold reporting tables for business analysis.
6. Displays operational insights through a Streamlit dashboard.

---

## Key Features

- Bronze–Silver–Gold medallion-style data architecture
- Raw data ingestion from multiple CSV batches
- Source-file and ingestion-date lineage tracking
- Parquet storage for portable analytical datasets
- DuckDB database for local SQL analytics
- Foreign-key validation between studies, sites, subjects, visits, and labs
- Duplicate subject detection
- Late-arriving visit prioritization
- Visit-window validation
- Laboratory status validation
- Quarantine records with explicit failure reasons
- Study enrolment reporting
- Visit-compliance analysis
- Site-level operational risk scoring
- Data-quality audit reporting
- Interactive Streamlit dashboard
- Public deployment support through Streamlit Community Cloud

---

## Architecture

```text
                    ┌──────────────────────┐
                    │ Synthetic Raw CSVs   │
                    │ studies              │
                    │ sites                │
                    │ subjects             │
                    │ visits               │
                    │ lab results          │
                    │ protocol deviations  │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │ Bronze Layer                    │
              │ Raw Parquet files               │
              │ DuckDB bronze_* tables          │
              │ Source lineage metadata         │
              └───────────────┬────────────────┘
                              │
                              ▼
              ┌────────────────────────────────┐
              │ Silver Layer                    │
              │ Validated and cleaned records   │
              │ Deduplication                   │
              │ Referential integrity checks    │
              │ Visit-window validation         │
              │ Quarantine dataset              │
              └───────────────┬────────────────┘
                              │
                              ▼
              ┌────────────────────────────────┐
              │ Gold Layer                      │
              │ Enrolment metrics               │
              │ Visit compliance                │
              │ Site operational risk           │
              │ Data-quality audit              │
              └───────────────┬────────────────┘
                              │
                              ▼
              ┌────────────────────────────────┐
              │ Streamlit Dashboard             │
              │ Clinical Operations Insights    │
              └────────────────────────────────┘
```

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Pandas | CSV ingestion, transformations, and Parquet output |
| DuckDB | Embedded analytical database and SQL processing |
| PyArrow | Parquet serialization |
| Parquet | Columnar data storage format |
| Streamlit | Interactive web dashboard |
| Plotly | Interactive charts |
| Git and GitHub | Version control and source-code hosting |
| Streamlit Community Cloud | Free dashboard deployment |

---

## Data Model

TrialPulse processes six core source datasets.

| Dataset | Description | Primary Identifier |
|---|---|---|
| Studies | Trial-level study information | `study_id` |
| Sites | Clinical research site details | `site_id` |
| Subjects | Enrolled clinical-trial participants | `subject_id` |
| Visits | Scheduled and actual subject visits | `visit_id` |
| Lab Results | Subject laboratory result records | `result_id` |
| Protocol Deviations | Protocol deviation events by site | N/A |

### Entity Relationships

```text
Study
 ├── Sites
 │    ├── Subjects
 │    │    ├── Visits
 │    │    └── Lab Results
 │    └── Protocol Deviations
```

### Important Relationships

| Parent Entity | Child Entity | Relationship |
|---|---|---|
| Study | Site | One study can contain many sites |
| Site | Subject | One site can contain many subjects |
| Subject | Visit | One subject can have many visits |
| Subject | Lab Result | One subject can have many laboratory results |
| Site | Protocol Deviation | One site can report many deviations |

---

## Pipeline Layers

## Bronze Layer

The Bronze layer is the raw landing zone.

It stores the input data with minimal transformation and preserves the original business values. The purpose of Bronze is traceability: every record should be linked to the source file and ingestion batch from which it came.

### Bronze Metadata

Each ingested record receives the following metadata:

| Column | Purpose |
|---|---|
| `ingested_at_utc` | Timestamp when the pipeline ingested the record |
| `source_file` | Original CSV file path |
| `ingestion_date` | Batch date extracted from the source folder |

### Bronze Outputs

```text
outputs/bronze/
├── studies.parquet
├── sites.parquet
├── subjects.parquet
├── visits.parquet
├── lab_results.parquet
└── protocol_deviations.parquet
```

The Bronze datasets are also stored in DuckDB tables:

```text
bronze_studies
bronze_sites
bronze_subjects
bronze_visits
bronze_lab_results
bronze_protocol_deviations
```

### Why Bronze Matters

The Bronze layer makes data lineage possible.

For example, a visit record in the dashboard can be traced back to:

- The source CSV file
- The ingestion batch date
- The ingestion timestamp

This is important when investigating data-quality issues or understanding late-arriving updates.

---

## Silver Layer

The Silver layer contains validated, cleaned, and deduplicated data.

It removes records that fail business rules from the main reporting datasets and sends them to a quarantine dataset. This means invalid data is not silently discarded; it remains available for review.

### Silver Outputs

```text
outputs/silver/
├── studies.parquet
├── sites.parquet
├── subjects.parquet
├── visits.parquet
├── lab_results.parquet
└── protocol_deviations.parquet
```

The validated Silver datasets are also written to DuckDB tables:

```text
silver_studies
silver_sites
silver_subjects
silver_visits
silver_lab_results
silver_protocol_deviations
```

### Quarantine Output

```text
outputs/quarantine/
└── quarantine_records.parquet
```

DuckDB table:

```text
quarantine_records
```

Each quarantined record includes:

| Column | Description |
|---|---|
| `dataset` | Dataset where the record originated |
| `failure_rule` | Validation rule that failed |
| Original source columns | Original record data for investigation |

---

## Data Quality Rules

TrialPulse applies data-quality rules in the Silver layer.

| Dataset | Validation Rule | Description |
|---|---|---|
| Subjects | `missing_site_id` | Reject subjects without a site identifier |
| Subjects | `unknown_site_id` | Reject subjects whose site does not exist |
| Subjects | `duplicate_subject_id` | Flag duplicate subject identifiers |
| Visits | `unknown_subject_id` | Reject visits linked to an unknown subject |
| Visits | `unknown_site_id` | Reject visits linked to an unknown site |
| Visits | `actual_date_outside_early_visit_window` | Reject visits completed more than 3 days before schedule |
| Visits | `duplicate_visit_id_superseded` | Preserve the preferred latest visit record and quarantine duplicates |
| Lab Results | `unknown_subject_id` | Reject laboratory results linked to an unknown subject |
| Lab Results | `invalid_lab_status` | Reject records with an unsupported lab status |
| Protocol Deviations | `unknown_site_id` | Reject deviations linked to an unknown site |

### Visit Window Rule

Clinical visits do not always happen on the exact scheduled date.

TrialPulse allows a visit to occur up to three days early:

```text
Actual visit date >= Scheduled visit date - 3 days
```

A visit completed more than three days before the scheduled date is treated as invalid and sent to quarantine.

### Late-Arriving Records

The visits dataset contains both an original batch and an incremental batch.

When duplicate visit identifiers occur, TrialPulse prioritizes records marked as late-arriving updates. This simulates a realistic operational scenario where corrected or delayed source-system records arrive after an initial load.

---

## Gold Reporting Models

The Gold layer contains dashboard-ready analytical tables.

```text
gold_trial_enrolment
gold_visit_compliance
gold_site_operational_risk
gold_data_quality_audit
```

Gold outputs are written to:

```text
outputs/gold/
```

Dashboard-ready CSV files are written to:

```text
data/demo/
```

The `data/demo/` directory is versioned in Git because the deployed Streamlit dashboard reads these files.

---

### `gold_trial_enrolment`

This table summarizes enrolment performance by study.

| Metric | Description |
|---|---|
| `planned_enrolment` | Target number of enrolled subjects |
| `enrolled_subjects` | Number of validated subject records |
| `active_subjects` | Subjects with active status |
| `completed_subjects` | Subjects who completed the trial |
| `withdrawn_subjects` | Subjects withdrawn from the trial |
| `screen_failed_subjects` | Subjects who did not pass screening |
| `enrolment_progress_pct` | Enrolment achieved as a percentage of the plan |

### Example Result

| Study | Planned Enrolment | Enrolled Subjects | Enrolment Progress |
|---|---:|---:|---:|
| CardioPulse Phase III | 240 | 127 | 52.9% |
| OncoPulse Phase II | 180 | 147 | 81.7% |

---

### `gold_visit_compliance`

This table summarizes visit performance by study, site, and visit type.

| Metric | Description |
|---|---|
| `total_visits` | Total validated visit records |
| `completed_visits` | Visits completed |
| `missed_visits` | Visits missed |
| `overdue_visits` | Visits overdue |
| `on_time_completed_visits` | Completed visits within the expected timing window |
| `completion_rate_pct` | Percentage of visits completed |
| `noncompliance_rate_pct` | Percentage of visits missed or overdue |

This table supports operational questions such as:

- Which visit type has the most missed visits?
- Which sites have the highest overdue visit rate?
- Which study requires follow-up for visit compliance?

---

### `gold_site_operational_risk`

This table ranks clinical sites by operational risk.

| Metric | Description |
|---|---|
| `target_enrolment` | Site recruitment target |
| `enrolled_subjects` | Number of enrolled subjects at the site |
| `enrolment_progress_pct` | Enrolment achievement against target |
| `total_visits` | Number of validated visits |
| `overdue_visits` | Number of overdue visits |
| `missed_visits` | Number of missed visits |
| `protocol_deviations` | Number of reported deviations |
| `overdue_visit_rate_pct` | Overdue visits as a percentage of total visits |
| `screen_failure_rate_pct` | Screen failures as a percentage of enrolled subjects |
| `deviation_rate_pct` | Deviations as a percentage of total visits |
| `operational_risk_score` | Combined operational risk score |

---

### `gold_data_quality_audit`

This table compares record counts across data layers.

| Metric | Description |
|---|---|
| `bronze_records` | Raw records ingested |
| `silver_records` | Validated records retained |
| `quarantine_rule_violations` | Number of validation-rule failures |

This table helps answer:

- How much raw data was retained after validation?
- Which datasets have the highest number of quality issues?
- Which validation rules generate the most quarantined records?

---

## Operational Risk Score

TrialPulse calculates a site-level operational risk score using three components:

```text
Operational Risk Score =
    50% × Overdue Visit Rate
  + 30% × Screen Failure Rate
  + 20% × Protocol Deviation Rate
```

### Formula

```text
risk_score =
    0.50 × overdue_visit_rate_pct
  + 0.30 × screen_failure_rate_pct
  + 0.20 × deviation_rate_pct
```

### Why These Inputs?

| Input | Reason |
|---|---|
| Overdue visit rate | Indicates follow-up and scheduling risk |
| Screen failure rate | Indicates recruitment efficiency issues |
| Protocol deviation rate | Indicates possible compliance or site-process issues |

The score is not a clinical safety score. It is an operational prioritization tool that helps identify sites needing attention.

### Example Site Risk Output

| Site | Risk Score | Overdue Visit Rate | Protocol Deviations |
|---|---:|---:|---:|
| TP-CAR-002-SITE-009 | 25.7 | 14.3% | 5 |
| TP-ONC-001-SITE-005 | 18.8 | 11.7% | 4 |
| TP-CAR-002-SITE-008 | 18.3 | 6.8% | 2 |

---

## Dashboard

The Streamlit dashboard provides four primary views.

### 1. Study Overview

This view shows:

- Planned enrolment
- Enrolled subjects
- Active subjects
- Completed subjects
- Withdrawn subjects
- Screen failures
- Enrolment progress against plan

### 2. Site Risk

This view shows:

- Site-level operational risk ranking
- Enrolment progress by site
- Overdue visits
- Missed visits
- Protocol deviations
- Risk-score drivers

The purpose is to help clinical operations teams prioritize sites requiring monitoring or intervention.

### 3. Visit Compliance

This view shows:

- Completed visits
- Missed visits
- Overdue visits
- Visit compliance by visit type

This supports operational follow-up on subject scheduling and protocol adherence.

### 4. Data Quality

This view shows:

- Bronze record counts
- Silver validated record counts
- Removed records
- Quarantine rule violations
- Silver retention percentage

This provides visibility into how data quality changes as records move through the pipeline.

---

## Project Results

The project pipeline produced the following results.

| Metric | Result |
|---|---:|
| Studies ingested | 2 |
| Clinical sites monitored | 20 |
| Bronze subjects ingested | 277 |
| Silver validated subjects | 274 |
| Bronze visits ingested | 1,087 |
| Silver validated visits | 1,058 |
| Bronze lab results ingested | 828 |
| Silver validated lab results | 820 |
| Bronze protocol deviations ingested | 52 |
| Silver validated protocol deviations | 52 |
| Rule-level quarantine records | 48 |
| Gold reporting tables | 4 |

### Quarantine Rule Summary

| Dataset | Failure Rule | Records |
|---|---|---:|
| Lab Results | Invalid lab status | 1 |
| Lab Results | Unknown subject ID | 7 |
| Subjects | Duplicate subject ID | 2 |
| Subjects | Missing site ID | 1 |
| Visits | Actual date outside early visit window | 1 |
| Visits | Duplicate visit ID superseded | 16 |
| Visits | Unknown subject ID | 20 |

> A single invalid source record can appear multiple times in the quarantine dataset if it fails more than one rule. This is intentional because it creates a more complete audit trail.

---

## Project Structure

```text
TrialPulse/
│
├── app/
│   └── dashboard.py
│
├── data/
│   ├── demo/
│   │   ├── gold_data_quality_audit.csv
│   │   ├── gold_site_operational_risk.csv
│   │   ├── gold_trial_enrolment.csv
│   │   └── gold_visit_compliance.csv
│   │
│   └── raw/
│       ├── studies/
│       ├── sites/
│       ├── subjects/
│       ├── visits/
│       ├── lab_results/
│       └── protocol_deviations/
│
├── outputs/
│   ├── bronze/
│   ├── silver/
│   ├── gold/
│   ├── quarantine/
│   └── trialpulse.duckdb
│
├── src/
│   ├── bronze_ingestion.py
│   ├── silver_validation.py
│   └── gold_reporting.py
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Local Setup

### Prerequisites

Install:

- Python 3.9 or newer
- Git
- A code editor such as Antigravity IDE, VS Code, or PyCharm

### Clone the Repository

```powershell
git clone YOUR_REPOSITORY_URL
cd TrialPulse
```

### Create a Virtual Environment

```powershell
python -m venv .venv
```

### Activate the Virtual Environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation succeeds, your terminal should begin with:

```text
(.venv)
```

### Install Dependencies

```powershell
pip install -r requirements.txt
```

---

## Requirements

Your `requirements.txt` should contain packages similar to the following:

```text
duckdb
pandas
pyarrow
plotly
streamlit
```

To regenerate the requirements file:

```powershell
pip freeze > requirements.txt
```

---

## Running the Pipeline

Run the pipeline layers in this order.

### Step 1: Bronze Ingestion

```powershell
python src\bronze_ingestion.py
```

This command:

- Reads raw CSV files
- Adds ingestion metadata
- Writes Bronze Parquet files
- Creates DuckDB Bronze tables

### Step 2: Silver Validation

```powershell
python src\silver_validation.py
```

This command:

- Validates foreign keys
- Detects duplicates
- Applies visit-window rules
- Validates lab statuses
- Creates Silver Parquet files
- Creates quarantine records
- Creates DuckDB Silver tables

### Step 3: Gold Reporting

```powershell
python src\gold_reporting.py
```

This command:

- Creates enrolment metrics
- Creates visit-compliance metrics
- Calculates site-risk scores
- Creates data-quality audit metrics
- Writes Gold Parquet files
- Writes dashboard-ready CSV files to `data/demo/`

---

## Running the Dashboard

Start the Streamlit application:

```powershell
streamlit run app\dashboard.py
```

Streamlit should display a local URL similar to:

```text
http://localhost:8501
```

Open the URL in your browser.

---

## Deployment

TrialPulse can be deployed using Streamlit Community Cloud.

### Deployment Steps

1. Push the repository to GitHub.
2. Ensure the following files are committed:
   - `app/dashboard.py`
   - `data/demo/*.csv`
   - `requirements.txt`
3. Open Streamlit Community Cloud.
4. Connect your GitHub account.
5. Select the TrialPulse repository.
6. Select the `main` branch.
7. Use the following main file path:

```text
app/dashboard.py
```

8. Click **Deploy**.

### Why `data/demo/` Is Committed

The dashboard is deployed as a public demo. It reads the prepared Gold CSV files from:

```text
data/demo/
```

The raw data and generated local outputs are excluded from Git because they can be recreated by running the pipeline.

---

## Example SQL Queries

You can inspect the DuckDB database directly.

### Open DuckDB from Python

```powershell
python
```

```python
import duckdb

connection = duckdb.connect("outputs/trialpulse.duckdb")
```

### List Tables

```python
connection.execute("SHOW TABLES").df()
```

### View Study Enrolment

```python
connection.execute("""
    SELECT
        study_name,
        planned_enrolment,
        enrolled_subjects,
        enrolment_progress_pct
    FROM gold_trial_enrolment
""").df()
```

### View Highest-Risk Sites

```python
connection.execute("""
    SELECT
        site_id,
        country,
        operational_risk_score,
        overdue_visit_rate_pct,
        protocol_deviations
    FROM gold_site_operational_risk
    ORDER BY operational_risk_score DESC
    LIMIT 10
""").df()
```

### View Quarantine Summary

```python
connection.execute("""
    SELECT
        dataset,
        failure_rule,
        COUNT(*) AS records
    FROM quarantine_records
    GROUP BY dataset, failure_rule
    ORDER BY dataset, failure_rule
""").df()
```

### Close the Database Connection

```python
connection.close()
```

---

## Design Decisions

### Why Pandas?

Pandas is used for file ingestion and dataframe transformations. It is lightweight, widely used, and appropriate for this synthetic dataset size.

### Why DuckDB?

DuckDB provides local analytical SQL processing without requiring a database server. It allows the project to use SQL reporting logic while remaining easy to run on a local machine.

### Why Parquet?

Parquet is a columnar storage format that is efficient for analytics workloads and portable across many data tools.

### Why Streamlit?

Streamlit makes it possible to build and deploy an interactive Python dashboard quickly without developing a separate frontend application.

### Why a Bronze–Silver–Gold Architecture?

The layered architecture separates responsibilities:

| Layer | Responsibility |
|---|---|
| Bronze | Preserve raw source data and lineage |
| Silver | Validate, clean, deduplicate, and quarantine invalid records |
| Gold | Create business-ready reporting datasets |

This improves traceability, maintainability, and confidence in dashboard metrics.

---

## Portfolio Talking Points

Use these talking points when discussing the project in interviews.

### Project Summary

> TrialPulse is a clinical-trial operations analytics platform that ingests synthetic operational data, applies data-quality validation, creates reporting models, and delivers an interactive dashboard for enrolment, visit compliance, site risk, and data-quality monitoring.

### Data Engineering Focus

> I implemented a Bronze–Silver–Gold pipeline where Bronze preserves raw source data and lineage, Silver applies validation and deduplication rules, and Gold creates dashboard-ready analytical models.

### Data Quality Focus

> Instead of deleting bad data, the pipeline sends invalid or superseded records to a quarantine dataset with explicit failure reasons. This creates an auditable process for data-quality investigation.

### Late-Arriving Data Focus

> The visits dataset includes an incremental batch. When duplicate visit IDs occur, the pipeline prioritizes late-arriving records and quarantines superseded versions.

### Business Value Focus

> The dashboard helps a clinical operations team understand recruitment progress, visit compliance, high-risk research sites, protocol deviations, and data-quality issues.

---

## Resume Description

### Two-Line Version

**TrialPulse — Clinical Trial Operations Analytics Platform** | Python, Pandas, DuckDB, Parquet, Streamlit  
Built a Bronze–Silver–Gold data pipeline with validation, deduplication, visit-window rules, and quarantine auditing; deployed a Streamlit dashboard for enrolment, visit compliance, site-risk, and data-quality monitoring across 20 clinical sites.

### Expanded Version

- Built an end-to-end clinical-trial operations analytics platform using Python, Pandas, DuckDB, Parquet, Streamlit, and Plotly.
- Implemented a Bronze–Silver–Gold architecture for raw ingestion, data validation, quarantine handling, and dashboard-ready reporting models.
- Added foreign-key checks, duplicate detection, late-arriving visit prioritization, configurable visit-window validation, and lab-status quality controls.
- Created Gold reporting tables for trial enrolment, visit compliance, site-level operational risk, and data-quality auditing.
- Developed and deployed an interactive Streamlit dashboard monitoring two studies and 20 synthetic clinical sites.

---

## Future Improvements

Potential future enhancements include:

- Add automated unit tests for validation rules
- Add `pytest` and code-coverage reporting
- Add a configurable YAML or JSON file for validation thresholds
- Add a configurable site-risk weighting model
- Add data freshness and pipeline-run monitoring
- Add dbt for SQL model versioning and testing
- Add Docker support for reproducible local execution
- Add GitHub Actions for automated tests and deployment checks
- Add role-based authentication for dashboard access
- Add downloadable CSV reports from the dashboard
- Add site-level drill-down pages
- Add monthly enrolment trend analysis
- Add protocol-deviation category analysis
- Add historical pipeline-run audit tables
- Add cloud object storage integration
- Add database warehouse integration
- Add synthetic data generation scripts as a separate pipeline stage

---

## Disclaimer

This project is a portfolio demonstration only.

- All data is synthetic.
- No real patient information is used.
- No clinical decisions should be made using this application.
- The risk score is an example operational metric, not a clinical safety or regulatory assessment.
- The dashboard is designed to demonstrate data engineering, analytics, SQL, visualization, and pipeline design skills.

---

## Author

**Your Name**  
GitHub: `https://github.com/yaswanthhh`  
Live Demo: `trialpulse.streamlit.app`