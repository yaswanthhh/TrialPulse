# TrialPulse Lakehouse

An AWS and Databricks lakehouse project for synthetic clinical-trial operations data.

The pipeline incrementally ingests raw operational data from Amazon S3, applies PySpark validation and quarantine rules, and publishes curated Delta tables for trial enrolment, site performance, visit compliance, and data-quality reporting.

## Planned stack

- AWS S3
- Databricks on AWS
- PySpark
- Delta Lake
- Databricks Auto Loader
- Databricks Lakeflow Jobs
- Databricks SQL
- Python and GitHub

## Disclaimer

This educational portfolio project uses synthetic, non-identifiable data only. It demonstrates audit-oriented metadata, lineage-aware architecture, and data-quality controls; it is not a validated GxP or regulated clinical system.