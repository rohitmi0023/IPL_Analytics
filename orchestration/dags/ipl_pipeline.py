from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.smtp.operators.smtp import EmailOperator

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

NOTIFY_EMAIL = ["team@example.com"]
WEB_UI_BASE = "http://localhost:8181"

# shared config: retries, timeout, owner
default_args = {
    "owner": "airflow",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
    "email_on_failure": False,
    "email_on_retry": False,
    "from_email": "airflow@ipl-analytics.local",
}

# DAG definition with schedule, tags, catchup
with DAG(
    dag_id="ipl_analytics_pipeline",
    description="IPL Analytics: ingest -> dbt build -> dbt test",
    schedule="0 1 * * *",
    max_active_runs=1,
    start_date=datetime(2026, 8, 23, tzinfo=ZoneInfo("Asia/Kolkata")),
    catchup=False,
    tags=["ipl", "analytics"],
    default_args=default_args       
) as dag:
    
    check_new_data = BashOperator(
        task_id="check_new_data",
        bash_command=(
            "cd /opt/airflow/dbt_project "
            "&& dbt source freshness --profiles-dir /opt/airflow/dbt_project"
        ),
    )
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /opt/airflow/dbt_project "
            "&& dbt run --profiles-dir /opt/airflow/dbt_project"
        ),
    )
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd /opt/airflow/dbt_project "
            "&& dbt test --profiles-dir /opt/airflow/dbt_project"
        ),
    )
    notify_success = EmailOperator(
        task_id="notify_success",
        to=NOTIFY_EMAIL,
        subject="IPL pipeline succeeded — {{ dag.dag_id }} ({{ run_id }})",
        html_content=(
            "<h3>IPL Analytics pipeline succeeded</h3>"
            "<p>DAG: <b>{{ dag.dag_id }}</b></p>"
            "<p>Run: <code>{{ run_id }}</code></p>"
            "<p>Execution date: <b>{{ ds }}</b> at {{ ts }}</p>"
            f'<p><a href="{WEB_UI_BASE}/dags/{{{{ dag.dag_id }}}}">Open in Airflow UI</a></p>'
        ),
    )
    notify_failure = EmailOperator(
        task_id="notify_failure",
        to=NOTIFY_EMAIL,
        trigger_rule="one_failed",
        subject="IPL pipeline FAILED — {{ dag.dag_id }} ({{ run_id }})",
        html_content=(
            "<h3>IPL Analytics pipeline failed</h3>"
            "<p>DAG: <b>{{ dag.dag_id }}</b></p>"
            "<p>Run: <code>{{ run_id }}</code></p>"
            "<p>Execution date: <b>{{ ds }}</b> at {{ ts }}</p>"
            "<p>One or more tasks failed — check the run grid in the Airflow UI for details.</p>"
            f'<p><a href="{WEB_UI_BASE}/dags/{{{{ dag.dag_id }}}}">Open in Airflow UI</a></p>'
        ),
    )
    
    # Task dependencies
    check_new_data >> dbt_run >> dbt_test >> notify_success
    [check_new_data, dbt_run, dbt_test] >> notify_failure