from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
fake = Faker("en_US")
Faker.seed(SEED)

OUTPUT_DIR = Path("data/raw/initial_load")
SAMPLE_DIR = Path("data/sample")

STUDIES = [
    {
        "study_id": "TP-ONC-001",
        "study_name": "OncoPulse Phase II",
        "therapeutic_area": "Oncology",
        "phase": "Phase II",
        "planned_enrolment": 180,
        "start_date": date(2025, 1, 15),
    },
    {
        "study_id": "TP-CAR-002",
        "study_name": "CardioPulse Phase III",
        "therapeutic_area": "Cardiovascular",
        "phase": "Phase III",
        "planned_enrolment": 240,
        "start_date": date(2025, 3, 1),
    },
]

COUNTRIES = ["Sweden", "Denmark", "Germany", "Netherlands", "United Kingdom"]
SITE_STATUSES = ["active", "active", "active", "pending_activation"]
SUBJECT_STATUSES = ["screening", "active", "completed", "withdrawn", "screen_failed"]
VISIT_NAMES = ["Screening", "Baseline", "Week 4", "Week 8", "Week 12"]
LAB_STATUSES = ["complete", "pending", "missing"]
DEVIATION_CATEGORIES = [
    "missed_visit",
    "informed_consent",
    "out_of_window",
    "procedure_error",
]
DEVIATION_STATUSES = ["open", "under_review", "closed"]


def iso(value):
    return value.isoformat() if value else None


def create_sites():
    rows = []
    for study in STUDIES:
        for number in range(1, 11):
            activation_date = study["start_date"] + timedelta(days=random.randint(0, 60))
            rows.append(
                {
                    "site_id": f"{study['study_id']}-SITE-{number:03d}",
                    "study_id": study["study_id"],
                    "country": random.choice(COUNTRIES),
                    "region": random.choice(["Nordics", "DACH", "Benelux", "United Kingdom"]),
                    "target_enrolment": study["planned_enrolment"] // 10,
                    "activation_date": iso(activation_date),
                    "site_status": random.choice(SITE_STATUSES),
                }
            )
    return rows


def create_subjects(sites):
    rows = []
    subject_number = 1

    for site in sites:
        enrolled = random.randint(8, 18)
        activation_date = date.fromisoformat(site["activation_date"])

        for _ in range(enrolled):
            consent_date = activation_date + timedelta(days=random.randint(1, 180))
            status = random.choices(
                SUBJECT_STATUSES,
                weights=[10, 42, 20, 8, 20],
                k=1,
            )[0]

            rows.append(
                {
                    "subject_id": f"SUBJ-{subject_number:05d}",
                    "site_id": site["site_id"],
                    "study_id": site["study_id"],
                    "consent_date": iso(consent_date),
                    "subject_status": status,
                    "age_band": random.choice(["18-34", "35-49", "50-64", "65+"]),
                    "sex": random.choice(["female", "male", "not_reported"]),
                }
            )
            subject_number += 1

    return rows


def create_visits(subjects):
    rows = []
    visit_number = 1

    for subject in subjects:
        if subject["subject_status"] == "screen_failed":
            visit_plan = ["Screening"]
        elif subject["subject_status"] == "withdrawn":
            visit_plan = random.choice(
                [["Screening", "Baseline"], ["Screening", "Baseline", "Week 4"]]
            )
        else:
            visit_plan = VISIT_NAMES

        consent_date = date.fromisoformat(subject["consent_date"])

        for index, visit_name in enumerate(visit_plan):
            scheduled_date = consent_date + timedelta(days=index * 28)
            outcome = random.choices(
                ["completed", "missed", "overdue"],
                weights=[80, 10, 10],
                k=1,
            )[0]

            if outcome == "completed":
                actual_date = scheduled_date + timedelta(days=random.randint(-2, 6))
            else:
                actual_date = None

            rows.append(
                {
                    "visit_id": f"VISIT-{visit_number:06d}",
                    "subject_id": subject["subject_id"],
                    "site_id": subject["site_id"],
                    "study_id": subject["study_id"],
                    "visit_name": visit_name,
                    "scheduled_date": iso(scheduled_date),
                    "actual_date": iso(actual_date),
                    "completion_status": outcome,
                }
            )
            visit_number += 1

    return rows


def create_lab_results(subjects):
    rows = []
    result_number = 1

    for subject in subjects:
        consent_date = date.fromisoformat(subject["consent_date"])

        for test_code in ["HEMOGLOBIN", "CREATININE", "ALT"]:
            collection_date = consent_date + timedelta(days=random.randint(0, 90))
            rows.append(
                {
                    "result_id": f"LAB-{result_number:06d}",
                    "subject_id": subject["subject_id"],
                    "study_id": subject["study_id"],
                    "test_code": test_code,
                    "collection_date": iso(collection_date),
                    "lab_status": random.choices(
                        LAB_STATUSES, weights=[80, 12, 8], k=1
                    )[0],
                }
            )
            result_number += 1

    return rows


def create_protocol_deviations(sites):
    rows = []
    deviation_number = 1

    for site in sites:
        for _ in range(random.randint(0, 5)):
            rows.append(
                {
                    "deviation_id": f"DEV-{deviation_number:05d}",
                    "site_id": site["site_id"],
                    "study_id": site["study_id"],
                    "category": random.choice(DEVIATION_CATEGORIES),
                    "reported_date": iso(
                        date(2025, 3, 1) + timedelta(days=random.randint(0, 365))
                    ),
                    "deviation_status": random.choice(DEVIATION_STATUSES),
                }
            )
            deviation_number += 1

    return rows


def inject_data_quality_issues(subjects, visits, labs):
    subjects.append({**subjects[0]})
    subjects[4]["site_id"] = None

    visits.append({**visits[0]})
    visits[5]["subject_id"] = "SUBJ-99999"
    visits[10]["actual_date"] = "2024-01-01"

    labs[3]["lab_status"] = "unknown"
    labs[8]["subject_id"] = None


def write_csv(name, rows):
    dataframe = pd.DataFrame(rows)
    dataframe.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
    dataframe.head(10).to_csv(SAMPLE_DIR / f"{name}_sample.csv", index=False)
    return len(dataframe)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    sites = create_sites()
    subjects = create_subjects(sites)
    visits = create_visits(subjects)
    labs = create_lab_results(subjects)
    deviations = create_protocol_deviations(sites)

    inject_data_quality_issues(subjects, visits, labs)

    counts = {
        "studies": write_csv("studies", STUDIES),
        "sites": write_csv("sites", sites),
        "subjects": write_csv("subjects", subjects),
        "visits": write_csv("visits", visits),
        "lab_results": write_csv("lab_results", labs),
        "protocol_deviations": write_csv("protocol_deviations", deviations),
    }

    print("TrialPulse source data created:")
    for dataset, count in counts.items():
        print(f"  {dataset}: {count:,} rows")


if __name__ == "__main__":
    main()