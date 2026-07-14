from pathlib import Path
import shutil

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "outputs" / "trialpulse.duckdb"
SILVER_DIR = PROJECT_ROOT / "outputs" / "silver"
QUARANTINE_DIR = PROJECT_ROOT / "outputs" / "quarantine"


def reset_directories():
    for directory in [SILVER_DIR, QUARANTINE_DIR]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)


def write_parquet(dataframe, directory, name):
    dataframe.to_parquet(
        directory / f"{name}.parquet",
        index=False,
        engine="pyarrow",
        compression="snappy",
    )


def persist_table(connection, table_name, dataframe):
    connection.register(f"{table_name}_df", dataframe)
    connection.execute(
        f"CREATE OR REPLACE TABLE {table_name} AS "
        f"SELECT * FROM {table_name}_df"
    )
    connection.unregister(f"{table_name}_df")


def add_quarantine(records, dataset, rule, dataframe, mask):
    rejected = dataframe.loc[mask].copy()

    if rejected.empty:
        return

    rejected["dataset"] = dataset
    rejected["failure_rule"] = rule
    records.append(rejected)


def parse_dates(dataframe, columns):
    for column in columns:
        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce",
        ).dt.date


def normalize_status(dataframe, column):
    dataframe[column] = (
        dataframe[column]
        .astype("string")
        .str.strip()
        .str.lower()
    )


def main():
    reset_directories()
    connection = duckdb.connect(DATABASE_PATH.as_posix())

    try:
        studies = connection.execute(
            "SELECT * FROM bronze_studies"
        ).df()

        sites = connection.execute(
            "SELECT * FROM bronze_sites"
        ).df()

        subjects = connection.execute(
            "SELECT * FROM bronze_subjects"
        ).df()

        visits = connection.execute(
            "SELECT * FROM bronze_visits"
        ).df()

        labs = connection.execute(
            "SELECT * FROM bronze_lab_results"
        ).df()

        deviations = connection.execute(
            "SELECT * FROM bronze_protocol_deviations"
        ).df()

        parse_dates(studies, ["start_date"])
        parse_dates(sites, ["activation_date"])
        parse_dates(subjects, ["consent_date"])
        parse_dates(visits, ["scheduled_date", "actual_date"])
        parse_dates(labs, ["collection_date"])
        parse_dates(deviations, ["reported_date"])

        normalize_status(sites, "site_status")
        normalize_status(subjects, "subject_status")
        normalize_status(visits, "completion_status")
        normalize_status(labs, "lab_status")
        normalize_status(deviations, "deviation_status")

        quarantine_records = []

        valid_site_ids = set(sites["site_id"].dropna())

        subject_missing_site = subjects["site_id"].isna()
        subject_unknown_site = (
            subjects["site_id"].notna()
            & ~subjects["site_id"].isin(valid_site_ids)
        )
        subject_duplicate = subjects["subject_id"].duplicated(keep=False)

        add_quarantine(
            quarantine_records,
            "subjects",
            "missing_site_id",
            subjects,
            subject_missing_site,
        )
        add_quarantine(
            quarantine_records,
            "subjects",
            "unknown_site_id",
            subjects,
            subject_unknown_site,
        )
        add_quarantine(
            quarantine_records,
            "subjects",
            "duplicate_subject_id",
            subjects,
            subject_duplicate,
        )

        invalid_subjects = (
            subject_missing_site
            | subject_unknown_site
            | subject_duplicate
        )

        subjects_silver = subjects.loc[~invalid_subjects].copy()
        subjects_silver = subjects_silver.drop_duplicates(
            subset=["subject_id"],
            keep="first",
        )

        valid_subject_ids = set(subjects_silver["subject_id"].dropna())

        visits["is_late_arriving"] = (
            visits["is_late_arriving"]
            .fillna("False")
            .astype("string")
            .str.lower()
            .eq("true")
        )

        visit_unknown_subject = ~visits["subject_id"].isin(
            valid_subject_ids
        )
        visit_unknown_site = ~visits["site_id"].isin(valid_site_ids)
        VISIT_EARLY_WINDOW_DAYS = 3

        visit_invalid_date = (
            visits["actual_date"].notna()
            & (
                visits["actual_date"]
                < (
                    visits["scheduled_date"]
                    - pd.Timedelta(days=VISIT_EARLY_WINDOW_DAYS)
                )
            )
        )

        add_quarantine(
            quarantine_records,
            "visits",
            "unknown_subject_id",
            visits,
            visit_unknown_subject,
        )
        add_quarantine(
            quarantine_records,
            "visits",
            "unknown_site_id",
            visits,
            visit_unknown_site,
        )
        add_quarantine(
            quarantine_records,
            "visits",
            "actual_date_outside_early_visit_window",
            visits,
            visit_invalid_date,
        )

        valid_visits_mask = (
            ~visit_unknown_subject
            & ~visit_unknown_site
            & ~visit_invalid_date
        )

        visits_valid = visits.loc[valid_visits_mask].copy()
        visits_valid["_priority"] = visits_valid[
            "is_late_arriving"
        ].astype(int)

        visits_valid = visits_valid.sort_values(
            by=["visit_id", "_priority", "ingested_at_utc"],
            ascending=[True, False, False],
        )

        duplicate_visits = visits_valid.loc[
            visits_valid["visit_id"].duplicated(keep=False)
        ].copy()

        if not duplicate_visits.empty:
            duplicate_visits["dataset"] = "visits"
            duplicate_visits[
                "failure_rule"
            ] = "duplicate_visit_id_superseded"
            quarantine_records.append(duplicate_visits)

        visits_silver = visits_valid.drop_duplicates(
            subset=["visit_id"],
            keep="first",
        ).drop(columns="_priority")

        lab_unknown_subject = ~labs["subject_id"].isin(
            valid_subject_ids
        )
        lab_invalid_status = ~labs["lab_status"].isin(
            ["complete", "pending", "missing"]
        )

        add_quarantine(
            quarantine_records,
            "lab_results",
            "unknown_subject_id",
            labs,
            lab_unknown_subject,
        )
        add_quarantine(
            quarantine_records,
            "lab_results",
            "invalid_lab_status",
            labs,
            lab_invalid_status,
        )

        labs_silver = labs.loc[
            ~lab_unknown_subject
            & ~lab_invalid_status
        ].copy()

        deviation_unknown_site = ~deviations["site_id"].isin(
            valid_site_ids
        )

        add_quarantine(
            quarantine_records,
            "protocol_deviations",
            "unknown_site_id",
            deviations,
            deviation_unknown_site,
        )

        deviations_silver = deviations.loc[
            ~deviation_unknown_site
        ].copy()

        studies_silver = studies.drop_duplicates(
            subset=["study_id"],
            keep="first",
        ).copy()

        sites_silver = sites.drop_duplicates(
            subset=["site_id"],
            keep="first",
        ).copy()

        silver_datasets = {
            "studies": studies_silver,
            "sites": sites_silver,
            "subjects": subjects_silver,
            "visits": visits_silver,
            "lab_results": labs_silver,
            "protocol_deviations": deviations_silver,
        }

        for name, dataframe in silver_datasets.items():
            write_parquet(dataframe, SILVER_DIR, name)
            persist_table(connection, f"silver_{name}", dataframe)
            print(f"silver_{name}: {len(dataframe):,} validated records")

        if quarantine_records:
            quarantine = pd.concat(
                quarantine_records,
                ignore_index=True,
                sort=False,
            )

            for column in quarantine.columns:
                quarantine[column] = quarantine[column].astype("string")
        else:
            quarantine = pd.DataFrame(
                columns=["dataset", "failure_rule"],
                dtype="string",
            )

        write_parquet(
            quarantine,
            QUARANTINE_DIR,
            "quarantine_records",
        )
        persist_table(
            connection,
            "quarantine_records",
            quarantine,
        )

        print(
            f"\nquarantine_records: {len(quarantine):,} "
            "rejected records"
        )
        print(f"Silver output: {SILVER_DIR}")
        print(f"Quarantine output: {QUARANTINE_DIR}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()