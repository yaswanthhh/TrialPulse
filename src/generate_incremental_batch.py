from pathlib import Path

import pandas as pd

INITIAL_VISITS = Path(
    "data/raw/visits/ingestion_date=2026-07-01/visits.csv"
)
OUTPUT_DIR = Path(
    "data/raw/visits/ingestion_date=2026-07-14"
)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    initial_visits = pd.read_csv(INITIAL_VISITS)

    late_arriving = (
        initial_visits[initial_visits["completion_status"] == "completed"]
        .head(15)
        .copy()
    )

    late_arriving["actual_date"] = pd.to_datetime(
        late_arriving["scheduled_date"]
    ) + pd.Timedelta(days=3)

    late_arriving["actual_date"] = late_arriving["actual_date"].dt.strftime(
        "%Y-%m-%d"
    )
    late_arriving["source_system"] = "EDC_v2"
    late_arriving["is_late_arriving"] = True

    duplicate = late_arriving.iloc[[0]].copy()
    incremental_batch = pd.concat(
        [late_arriving, duplicate],
        ignore_index=True,
    )

    output_file = OUTPUT_DIR / "visits_incremental.csv"
    incremental_batch.to_csv(output_file, index=False)

    print(f"Created: {output_file}")
    print(f"Rows written: {len(incremental_batch)}")
    print(f"Duplicate visit IDs: {incremental_batch['visit_id'].duplicated().sum()}")
    print("New columns: source_system, is_late_arriving")


if __name__ == "__main__":
    main()