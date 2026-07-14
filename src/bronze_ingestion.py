from datetime import datetime, timezone
from pathlib import Path
import shutil

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
BRONZE_DIR = PROJECT_ROOT / "outputs" / "bronze"
DATABASE_PATH = PROJECT_ROOT / "outputs" / "trialpulse.duckdb"

DATASETS = [
    "studies",
    "sites",
    "subjects",
    "visits",
    "lab_results",
    "protocol_deviations",
]


def reset_bronze_layer():
    if BRONZE_DIR.exists():
        shutil.rmtree(BRONZE_DIR)
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(dataset, ingested_at_utc):
    files = sorted((RAW_DIR / dataset).glob("**/*.csv"))

    if not files:
        raise FileNotFoundError(f"No CSV files found for dataset: {dataset}")

    frames = []

    for file_path in files:
        dataframe = pd.read_csv(file_path, dtype="string")

        dataframe["ingested_at_utc"] = ingested_at_utc
        dataframe["source_file"] = file_path.relative_to(PROJECT_ROOT).as_posix()

        ingestion_date = next(
            (
                parent.name.split("=", 1)[1]
                for parent in file_path.parents
                if parent.name.startswith("ingestion_date=")
            ),
            None,
        )

        dataframe["ingestion_date"] = ingestion_date
        frames.append(dataframe)

    return pd.concat(frames, ignore_index=True)


def write_bronze_dataset(connection, dataset, dataframe):
    dataset_path = BRONZE_DIR / f"{dataset}.parquet"

    dataframe.to_parquet(
        dataset_path,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )

    connection.register(f"{dataset}_df", dataframe)
    connection.execute(
        f"CREATE OR REPLACE TABLE bronze_{dataset} AS "
        f"SELECT * FROM {dataset}_df"
    )
    connection.unregister(f"{dataset}_df")


def main():
    reset_bronze_layer()
    batch_timestamp = datetime.now(timezone.utc).isoformat()

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(DATABASE_PATH.as_posix())

    print("\nTrialPulse Bronze ingestion started\n")
    print(f"Batch timestamp (UTC): {batch_timestamp}\n")

    try:
        for dataset in DATASETS:
            dataframe = load_dataset(dataset, batch_timestamp)
            write_bronze_dataset(connection, dataset, dataframe)

            print(f"{dataset}: {len(dataframe):,} records written")
            print(f"  Columns: {', '.join(dataframe.columns)}")

        print("\nBronze ingestion completed successfully.")
        print(f"Parquet output: {BRONZE_DIR}")
        print(f"DuckDB database: {DATABASE_PATH}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()