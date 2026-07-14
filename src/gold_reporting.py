from pathlib import Path
import shutil

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "outputs" / "trialpulse.duckdb"
GOLD_DIR = PROJECT_ROOT / "outputs" / "gold"
DEMO_DIR = PROJECT_ROOT / "data" / "demo"


def reset_directories():
    for directory in [GOLD_DIR, DEMO_DIR]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)


def write_output(connection, table_name):
    dataframe = connection.execute(
        f"SELECT * FROM {table_name}"
    ).df()

    dataframe.to_parquet(
        GOLD_DIR / f"{table_name}.parquet",
        index=False,
        engine="pyarrow",
        compression="snappy",
    )

    dataframe.to_csv(
        DEMO_DIR / f"{table_name}.csv",
        index=False,
    )

    print(f"{table_name}: {len(dataframe):,} records written")


def main():
    reset_directories()
    connection = duckdb.connect(DATABASE_PATH.as_posix())

    try:
        connection.execute("""
            CREATE OR REPLACE TABLE gold_trial_enrolment AS
            SELECT
                st.study_id,
                st.study_name,
                st.therapeutic_area,
                st.phase,
                TRY_CAST(
                    st.planned_enrolment AS INTEGER
                ) AS planned_enrolment,
                COUNT(su.subject_id) AS enrolled_subjects,
                COUNT(*) FILTER (
                    WHERE su.subject_status = 'active'
                ) AS active_subjects,
                COUNT(*) FILTER (
                    WHERE su.subject_status = 'completed'
                ) AS completed_subjects,
                COUNT(*) FILTER (
                    WHERE su.subject_status = 'withdrawn'
                ) AS withdrawn_subjects,
                COUNT(*) FILTER (
                    WHERE su.subject_status = 'screen_failed'
                ) AS screen_failed_subjects,
                ROUND(
                    100.0 * COUNT(su.subject_id)
                    / NULLIF(
                        TRY_CAST(
                            st.planned_enrolment AS INTEGER
                        ),
                        0
                    ),
                    1
                ) AS enrolment_progress_pct
            FROM silver_studies st
            LEFT JOIN silver_subjects su
                ON st.study_id = su.study_id
            GROUP BY
                st.study_id,
                st.study_name,
                st.therapeutic_area,
                st.phase,
                st.planned_enrolment
            ORDER BY st.study_id
        """)

        connection.execute("""
            CREATE OR REPLACE TABLE gold_visit_compliance AS
            SELECT
                study_id,
                site_id,
                visit_name,
                COUNT(*) AS total_visits,
                COUNT(*) FILTER (
                    WHERE completion_status = 'completed'
                ) AS completed_visits,
                COUNT(*) FILTER (
                    WHERE completion_status = 'missed'
                ) AS missed_visits,
                COUNT(*) FILTER (
                    WHERE completion_status = 'overdue'
                ) AS overdue_visits,
                COUNT(*) FILTER (
                    WHERE completion_status = 'completed'
                    AND actual_date <= scheduled_date + INTERVAL 3 DAY
                ) AS on_time_completed_visits,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE completion_status = 'completed'
                    ) / NULLIF(COUNT(*), 0),
                    1
                ) AS completion_rate_pct,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE completion_status IN ('missed', 'overdue')
                    ) / NULLIF(COUNT(*), 0),
                    1
                ) AS noncompliance_rate_pct
            FROM silver_visits
            GROUP BY study_id, site_id, visit_name
            ORDER BY study_id, site_id, visit_name
        """)

        connection.execute("""
            CREATE OR REPLACE TABLE gold_site_operational_risk AS
            WITH site_subjects AS (
                SELECT
                    study_id,
                    site_id,
                    COUNT(*) AS enrolled_subjects,
                    COUNT(*) FILTER (
                        WHERE subject_status = 'screen_failed'
                    ) AS screen_failed_subjects,
                    COUNT(*) FILTER (
                        WHERE subject_status = 'withdrawn'
                    ) AS withdrawn_subjects
                FROM silver_subjects
                GROUP BY study_id, site_id
            ),
            site_visits AS (
                SELECT
                    study_id,
                    site_id,
                    COUNT(*) AS total_visits,
                    COUNT(*) FILTER (
                        WHERE completion_status = 'overdue'
                    ) AS overdue_visits,
                    COUNT(*) FILTER (
                        WHERE completion_status = 'missed'
                    ) AS missed_visits
                FROM silver_visits
                GROUP BY study_id, site_id
            ),
            site_deviations AS (
                SELECT
                    study_id,
                    site_id,
                    COUNT(*) AS protocol_deviations
                FROM silver_protocol_deviations
                GROUP BY study_id, site_id
            )
            SELECT
                si.study_id,
                si.site_id,
                si.country,
                si.region,
                TRY_CAST(
                    si.target_enrolment AS INTEGER
                ) AS target_enrolment,
                COALESCE(ss.enrolled_subjects, 0) AS enrolled_subjects,
                ROUND(
                    100.0 * COALESCE(ss.enrolled_subjects, 0)
                    / NULLIF(
                        TRY_CAST(
                            si.target_enrolment AS INTEGER
                        ),
                        0
                    ),
                    1
                ) AS enrolment_progress_pct,
                COALESCE(sv.total_visits, 0) AS total_visits,
                COALESCE(sv.overdue_visits, 0) AS overdue_visits,
                COALESCE(sv.missed_visits, 0) AS missed_visits,
                COALESCE(
                    sd.protocol_deviations,
                    0
                ) AS protocol_deviations,
                ROUND(
                    100.0 * COALESCE(sv.overdue_visits, 0)
                    / NULLIF(sv.total_visits, 0),
                    1
                ) AS overdue_visit_rate_pct,
                ROUND(
                    100.0 * COALESCE(
                        ss.screen_failed_subjects,
                        0
                    )
                    / NULLIF(ss.enrolled_subjects, 0),
                    1
                ) AS screen_failure_rate_pct,
                ROUND(
                    100.0 * COALESCE(
                        sd.protocol_deviations,
                        0
                    )
                    / NULLIF(sv.total_visits, 0),
                    1
                ) AS deviation_rate_pct,
                ROUND(
                    0.50 * COALESCE(
                        100.0 * sv.overdue_visits
                        / NULLIF(sv.total_visits, 0),
                        0
                    )
                    + 0.30 * COALESCE(
                        100.0 * ss.screen_failed_subjects
                        / NULLIF(ss.enrolled_subjects, 0),
                        0
                    )
                    + 0.20 * COALESCE(
                        100.0 * sd.protocol_deviations
                        / NULLIF(sv.total_visits, 0),
                        0
                    ),
                    1
                ) AS operational_risk_score
            FROM silver_sites si
            LEFT JOIN site_subjects ss
                ON si.study_id = ss.study_id
                AND si.site_id = ss.site_id
            LEFT JOIN site_visits sv
                ON si.study_id = sv.study_id
                AND si.site_id = sv.site_id
            LEFT JOIN site_deviations sd
                ON si.study_id = sd.study_id
                AND si.site_id = sd.site_id
            ORDER BY operational_risk_score DESC, si.site_id
        """)

        connection.execute("""
            CREATE OR REPLACE TABLE gold_data_quality_audit AS
            SELECT
                'studies' AS dataset,
                (SELECT COUNT(*) FROM bronze_studies) AS bronze_records,
                (SELECT COUNT(*) FROM silver_studies) AS silver_records,
                (
                    SELECT COUNT(*)
                    FROM quarantine_records
                    WHERE dataset = 'studies'
                ) AS quarantine_rule_violations

            UNION ALL

            SELECT
                'sites',
                (SELECT COUNT(*) FROM bronze_sites),
                (SELECT COUNT(*) FROM silver_sites),
                (
                    SELECT COUNT(*)
                    FROM quarantine_records
                    WHERE dataset = 'sites'
                )

            UNION ALL

            SELECT
                'subjects',
                (SELECT COUNT(*) FROM bronze_subjects),
                (SELECT COUNT(*) FROM silver_subjects),
                (
                    SELECT COUNT(*)
                    FROM quarantine_records
                    WHERE dataset = 'subjects'
                )

            UNION ALL

            SELECT
                'visits',
                (SELECT COUNT(*) FROM bronze_visits),
                (SELECT COUNT(*) FROM silver_visits),
                (
                    SELECT COUNT(*)
                    FROM quarantine_records
                    WHERE dataset = 'visits'
                )

            UNION ALL

            SELECT
                'lab_results',
                (SELECT COUNT(*) FROM bronze_lab_results),
                (SELECT COUNT(*) FROM silver_lab_results),
                (
                    SELECT COUNT(*)
                    FROM quarantine_records
                    WHERE dataset = 'lab_results'
                )

            UNION ALL

            SELECT
                'protocol_deviations',
                (
                    SELECT COUNT(*)
                    FROM bronze_protocol_deviations
                ),
                (
                    SELECT COUNT(*)
                    FROM silver_protocol_deviations
                ),
                (
                    SELECT COUNT(*)
                    FROM quarantine_records
                    WHERE dataset = 'protocol_deviations'
                )

            ORDER BY dataset
        """)

        gold_tables = [
            "gold_trial_enrolment",
            "gold_visit_compliance",
            "gold_site_operational_risk",
            "gold_data_quality_audit",
        ]

        for table_name in gold_tables:
            write_output(connection, table_name)

        print(f"\nGold Parquet output: {GOLD_DIR}")
        print(f"Dashboard demo CSVs: {DEMO_DIR}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()