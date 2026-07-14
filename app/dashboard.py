from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "data" / "demo"

st.set_page_config(
    page_title="TrialPulse",
    page_icon="🧬",
    layout="wide",
)


@st.cache_data
def load_data():
    enrolment = pd.read_csv(
        DEMO_DIR / "gold_trial_enrolment.csv"
    )
    compliance = pd.read_csv(
        DEMO_DIR / "gold_visit_compliance.csv"
    )
    site_risk = pd.read_csv(
        DEMO_DIR / "gold_site_operational_risk.csv"
    )
    quality = pd.read_csv(
        DEMO_DIR / "gold_data_quality_audit.csv"
    )

    return enrolment, compliance, site_risk, quality


def metric_percent(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.1f}%"


enrolment, compliance, site_risk, quality = load_data()

st.title("TrialPulse")
st.caption(
    "Clinical Trial Operations Command Center | "
    "Synthetic demonstration data"
)

st.divider()

study_options = ["All studies"] + sorted(
    enrolment["study_name"].unique().tolist()
)

selected_study_name = st.sidebar.selectbox(
    "Study",
    study_options,
)

if selected_study_name == "All studies":
    selected_study_ids = enrolment["study_id"].tolist()
else:
    selected_study_ids = enrolment.loc[
        enrolment["study_name"] == selected_study_name,
        "study_id",
    ].tolist()

filtered_enrolment = enrolment[
    enrolment["study_id"].isin(selected_study_ids)
].copy()

filtered_compliance = compliance[
    compliance["study_id"].isin(selected_study_ids)
].copy()

filtered_site_risk = site_risk[
    site_risk["study_id"].isin(selected_study_ids)
].copy()

total_planned = filtered_enrolment[
    "planned_enrolment"
].sum()

total_enrolled = filtered_enrolment[
    "enrolled_subjects"
].sum()

overall_enrolment_pct = (
    100 * total_enrolled / total_planned
    if total_planned
    else 0
)

total_visits = filtered_compliance["total_visits"].sum()
completed_visits = filtered_compliance[
    "completed_visits"
].sum()

overall_completion_pct = (
    100 * completed_visits / total_visits
    if total_visits
    else 0
)

overdue_visits = filtered_compliance["overdue_visits"].sum()
missed_visits = filtered_compliance["missed_visits"].sum()

total_quality_violations = quality[
    "quarantine_rule_violations"
].sum()

top_risk_score = (
    filtered_site_risk["operational_risk_score"].max()
    if not filtered_site_risk.empty
    else 0
)

metric_1, metric_2, metric_3, metric_4, metric_5 = st.columns(5)

metric_1.metric(
    "Enrolled subjects",
    f"{total_enrolled:,}",
    f"{overall_enrolment_pct:.1f}% of plan",
)

metric_2.metric(
    "Visit completion",
    metric_percent(overall_completion_pct),
    f"{completed_visits:,} of {total_visits:,}",
)

metric_3.metric(
    "Overdue visits",
    f"{overdue_visits:,}",
)

metric_4.metric(
    "Missed visits",
    f"{missed_visits:,}",
)

metric_5.metric(
    "Quality violations",
    f"{total_quality_violations:,}",
)

overview_tab, risk_tab, compliance_tab, quality_tab = st.tabs(
    [
        "Study Overview",
        "Site Risk",
        "Visit Compliance",
        "Data Quality",
    ]
)

with overview_tab:
    st.subheader("Study enrolment progress")

    enrolment_chart = px.bar(
        filtered_enrolment,
        x="study_name",
        y="enrolment_progress_pct",
        color="therapeutic_area",
        text="enrolment_progress_pct",
        hover_data=[
            "planned_enrolment",
            "enrolled_subjects",
            "active_subjects",
            "completed_subjects",
            "withdrawn_subjects",
        ],
        labels={
            "study_name": "Study",
            "enrolment_progress_pct": "Enrolment progress (%)",
            "therapeutic_area": "Therapeutic area",
        },
        title="Enrolment against plan",
    )

    enrolment_chart.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )

    enrolment_chart.update_yaxes(range=[0, 110])

    st.plotly_chart(
        enrolment_chart,
        use_container_width=True,
    )

    display_enrolment = filtered_enrolment[
        [
            "study_name",
            "phase",
            "therapeutic_area",
            "planned_enrolment",
            "enrolled_subjects",
            "active_subjects",
            "completed_subjects",
            "withdrawn_subjects",
            "screen_failed_subjects",
            "enrolment_progress_pct",
        ]
    ].copy()

    st.dataframe(
        display_enrolment,
        use_container_width=True,
        hide_index=True,
    )

with risk_tab:
    st.subheader("Operational site risk")

    risk_chart_data = filtered_site_risk.sort_values(
        "operational_risk_score",
        ascending=True,
    )

    risk_chart = px.bar(
        risk_chart_data,
        x="operational_risk_score",
        y="site_id",
        color="operational_risk_score",
        orientation="h",
        color_continuous_scale="Reds",
        hover_data=[
            "country",
            "region",
            "enrolled_subjects",
            "enrolment_progress_pct",
            "overdue_visits",
            "missed_visits",
            "protocol_deviations",
            "overdue_visit_rate_pct",
            "deviation_rate_pct",
        ],
        labels={
            "operational_risk_score": "Operational risk score",
            "site_id": "Site",
        },
        title="Sites ranked by operational risk",
    )

    st.plotly_chart(
        risk_chart,
        use_container_width=True,
    )

    st.caption(
        "Risk score = 50% overdue-visit rate + "
        "30% screen-failure rate + 20% deviation rate."
    )

    risk_display = filtered_site_risk[
        [
            "site_id",
            "country",
            "region",
            "enrolled_subjects",
            "enrolment_progress_pct",
            "overdue_visits",
            "missed_visits",
            "protocol_deviations",
            "operational_risk_score",
        ]
    ].sort_values(
        "operational_risk_score",
        ascending=False,
    )

    st.dataframe(
        risk_display,
        use_container_width=True,
        hide_index=True,
    )

with compliance_tab:
    st.subheader("Visit compliance by visit type")

    compliance_summary = (
        filtered_compliance
        .groupby("visit_name", as_index=False)
        .agg(
            total_visits=("total_visits", "sum"),
            completed_visits=("completed_visits", "sum"),
            missed_visits=("missed_visits", "sum"),
            overdue_visits=("overdue_visits", "sum"),
        )
    )

    compliance_summary["completion_rate_pct"] = (
        100
        * compliance_summary["completed_visits"]
        / compliance_summary["total_visits"]
    )

    compliance_summary["noncompliance_rate_pct"] = (
        100
        * (
            compliance_summary["missed_visits"]
            + compliance_summary["overdue_visits"]
        )
        / compliance_summary["total_visits"]
    )

    compliance_chart = px.bar(
        compliance_summary,
        x="visit_name",
        y=[
            "completed_visits",
            "missed_visits",
            "overdue_visits",
        ],
        barmode="stack",
        labels={
            "visit_name": "Visit",
            "value": "Visits",
            "variable": "Status",
        },
        title="Completed, missed, and overdue visits",
        color_discrete_map={
            "completed_visits": "#2E8B57",
            "missed_visits": "#DC143C",
            "overdue_visits": "#F4A261",
        },
    )

    st.plotly_chart(
        compliance_chart,
        use_container_width=True,
    )

    st.dataframe(
        compliance_summary.sort_values(
            "noncompliance_rate_pct",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

with quality_tab:
    st.subheader("Pipeline data-quality audit")

    quality_display = quality.copy()

    quality_display["records_removed"] = (
        quality_display["bronze_records"]
        - quality_display["silver_records"]
    )

    quality_display["silver_retention_pct"] = (
        100
        * quality_display["silver_records"]
        / quality_display["bronze_records"]
    ).round(1)

    quality_chart = px.bar(
        quality_display,
        x="dataset",
        y=[
            "bronze_records",
            "silver_records",
        ],
        barmode="group",
        labels={
            "dataset": "Dataset",
            "value": "Records",
            "variable": "Pipeline layer",
        },
        title="Raw records compared with validated records",
        color_discrete_map={
            "bronze_records": "#A66CFF",
            "silver_records": "#2E8B57",
        },
    )

    st.plotly_chart(
        quality_chart,
        use_container_width=True,
    )

    st.dataframe(
        quality_display[
            [
                "dataset",
                "bronze_records",
                "silver_records",
                "records_removed",
                "quarantine_rule_violations",
                "silver_retention_pct",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.caption(
    "TrialPulse is a portfolio project using synthetic clinical "
    "operations data. It is not intended for patient care or "
    "regulated clinical decision-making."
)