# IPL Analytics — Ball-by-Ball Match Analysis

End-to-end data pipeline for Indian Premier League (IPL) ball-by-ball match analytics: ingests Cricsheet JSON match data into Snowflake, transforms it with dbt Core, and visualizes it in a Streamlit dashboard.
This pipeline is testing on IPL data, can be tested for other formats matches as well.

Data Link: [Cricsheet Website](https://cricsheet.org/matches/)

**Tech stack:** Python · Snowflake · dbt Core · Streamlit · Airflow 

## Architecture

```
                                    ┌──────────────────┐
                                    │  Cricsheet JSON   │
                                    └────────┬─────────┘
                                             │
                              ┌──────────────┴──────────────┐
                              ▼                              ▼
                    ┌─────────────────┐          ┌────────────────────┐
                    │  Local file     │          │  S3 bucket         │
                    │  PUT + COPY INTO│          │  (land/)           │
                    └────────┬────────┘          └────────┬───────────┘
                             │                            │
                             │                   Snowpipe (AUTO_INGEST)
                             │                            │
                             └──────────┬─────────────────┘
                                        ▼
                             ┌───────────────────┐
                             │  Snowflake — RAW  │   raw_match_json
                             └──────┬────────────┘
                                    │  dbt Core
                                    ▼
                    ┌────────────────────────────┐
                    │  Staging (stg_*)           │   stg_deliveries, stg_matches, stg_innings,
                    │                            │   stg_registry (Cricsheet player hashes)
                    └───────────┬────────────────┘
                                │
                                ▼
                    ┌─────────────────────────────┐
                    │  Marts (dim_* / fact_*)     │   dim_match, dim_player, dim_player_team,
                    │                            │   dim_team, dim_season, fact_ball
                    └────────────┬────────────────┘
                                    │
                                    ▼
                        ┌─────────────────────────────┐
                        │  Gold (v_*)                 │   v_match_summary, v_batting, v_bowling,
                        │                             │   v_phase,  v_partnership
                        └────────────┬────────────────┘
                                    │
                                    ▼
                              Streamlit Dashboard
```

## Data Model

| Layer | Contents |
|---|---|
| RAW | Raw match JSON stored as VARIANT, one row per file |
| Staging | Flattened deliveries, innings, match info, and Cricsheet player registry |
| Marts | `dim_match`, `dim_player` (global), `dim_player_team` (bridge), `dim_team`, `dim_season`, `fact_ball` (season-aware, 1-indexed over/ball, extras, wickets) |
| Gold | Analytics views: match summary, batting, bowling, phase, partnerships |

## Data Quality & Testing

dbt ships a data-quality layer on top of the models — **42 tests**, all passing via `DBT_PROFILES_DIR=dbt_project .venv/bin/dbt test`:

| Scope | Tests |
|---|---|
| Raw source `raw_match_json` | `not_null` on all columns; `unique` on `match_id` (5) |
| `dim_match` | `match_id` unique + not-null (2) |
| `dim_team` | `team_id` & `team_name` unique + not-null (4) |
| `dim_player` | `player_id` unique + not-null; `player_name`, `first_season`, `last_season` not-null (5) |
| `dim_player_team` | Composite `check_player_team_uniqueness` on [player_id, match_id]; `player_id` not-null + FK → dim_player; `match_id` not-null; `team_name` not-null (5) |
| `dim_season` | `season` unique + not-null; `total_matches`, `start_date`, `end_date` not-null; `champion` FK → dim_team (6) |
| `fact_ball` | Composite `check_fact_delivery_grain_uniqueness` on (match_id, innings_no, over_no, ball_in_over); 8 `not_null`; `season` not_null; `match_date` not_null; FK `batter_id → dim_player.player_id`; FK `bowler_id → dim_player.player_id` (15) |

The custom generic test `unique_combination_of_columns` lives in `dbt_project/tests/generic/`.

## Quickstart

1. **Set up Snowflake** — run `sql/snowflake_setup.sql` (creates database, warehouses, role, schema, stage, file format, and raw table).
2. **Configure credentials**:
   - Copy `.env.example` to `.env` and fill in your Snowflake connection (used by ingestion and the dashboard).
   - Copy `dbt_project/profiles.example.yml` to `dbt_project/profiles.yml` and fill it in (used by dbt Core — it's gitignored, so credentials never get committed).
3. **Install dependencies**:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Ingest data** (single-file, local PUT + COPY INTO):
   ```bash
   python ingestion/ingest.py data/981017.json
   ```
5. **Bulk ingestion via S3 + Snowpipe** (for continuous multi-file loading):
   ```bash
   aws s3 cp data/<match>.json s3://ipl-raw-ingest/land/
   ```
   Snowpipe auto-loads into `RAW_MATCH_JSON` within seconds.
6. **Run transformations** (from the project root — `profiles.yml` lives inside `dbt_project/`):
   ```bash
   DBT_PROFILES_DIR=dbt_project .venv/bin/dbt run
   DBT_PROFILES_DIR=dbt_project .venv/bin/dbt test
   ```
7. **Launch dashboard**:
   ```bash
   .venv/bin/streamlit run dashboard/app.py
   ```

## Dashboard

`dashboard/app.py` is a Streamlit app on the **Gold layer**:

- Seven tabs — Match Summary, Batting, Bowling, Phases, Partnerships, Player Career, AI Commentary — with season, match, and team filters.
- **Season selector** in sidebar: filter all views by IPL season.
- **Player Career tab**: career batting/bowling aggregates, season-by-season charts, match-by-match detail.
- Plotly charts: runs-per-over trend, top scorers, economy vs wickets, phase run-rates, top partnerships.
- `db.py` abstracts the query layer with two interchangeable backends (snowflake-connector locally, Snowpark session in Snowflake).
- `ai_summary.py` is Cortex-ready: calls `SNOWFLAKE.CORTEX.COMPLETE` with facts from the gold views when the account supports it, otherwise a deterministic template (the UI shows which engine produced it).

## Airflow Orchestration

The pipeline is also orchestrated locally with **Apache Airflow 3.3.1** running in Docker Compose (`orchestration/`). A DAG (`ipl_analytics_pipeline`, **daily at 1 AM IST**, 3 retries, one run at a time) runs the dbt journeys on a schedule:

```
check_new_data ──▶ dbt_run ──▶ dbt_test ──▶ notify_success
      │  ▲
      └──┴──────────────────────▶ notify_failure   (fires on any failure)
```

| Task | What it runs |
|---|---|
| `check_new_data` | `dbt source freshness` — gates on source staleness (warn 1h / **error 24h**) |
| `dbt_run` | `dbt run` — rebuild staging → marts → gold |
| `dbt_test` | `dbt test` — the 42 data-quality tests above |
| `notify_success` / `notify_failure` | pipeline outcome hooks (placeholders for now) |

**Quick start:**

```bash
cd orchestration
cp simple_auth_manager_passwords.example.json simple_auth_manager_passwords.json   # then set your own UI username/password
docker compose up -d
```

- UI at **http://localhost:8181** (default login `admin` / `airflow`).
- `docker compose ps` to check all services are healthy.
- **Notify emails**: the `notify_*` tasks send emails via a local **MailHog** (fake SMTP) — view them at **http://localhost:8025** (no real email is delivered).
- Freshness gate: if the raw data is older than 24h, `check_new_data` fails (STALE) and the failure hook fires — reload source data to go green.

**Troubleshooting gotchas (Airflow 3):**

- **`Connection refused` / tasks never start** — `AIRFLOW__CORE__EXECUTION_API_SERVER_URL` must point at the api-server container, not `localhost` (e.g. `http://airflow-webserver:8080/execution/`).
- **`Invalid auth token` when tasks start** — `AIRFLOW__API_AUTH__JWT_SECRET` is auto-generated *per container*; pin it to one fixed value across all services.
- **DAGs never register** — `airflow-dag-processor` is a required standalone service in Airflow 3 (the scheduler can't spawn it).
- **`SSL: WRONG_VERSION_NUMBER` from EmailOperator** — the smtp provider defaults SSL/STARTTLS **on**; the MailHog connection uses `?disable_ssl=true&disable_tls=true` extras. To use a real provider, replace the `AIRFLOW_CONN_SMTP_DEFAULT` value in `docker-compose.yml` (e.g. `smtp://user:pass@smtp.gmail.com:587`), and add any delivery-SSL options the provider needs.

## Project Structure

```
IPL_Analytics/
├── BRD_IPL_Analytics.md      # Business requirements
├── data/                      # Raw Cricsheet JSON files
├── sql/                       # Snowflake DDL — snowflake_setup.sql, streamlit_deploy.sql
├── ingestion/                 # Python ingestion — config.py, ingest.py (PUT + COPY INTO; S3 + Snowpipe)
├── dbt_project/               # dbt Core models — staging → marts → gold, tests, profiles.example.yml
├── dashboard/                 # Streamlit app — app.py, db.py (backends), ai_summary.py (Cortex-ready)
├── orchestration/             # Airflow 3 local deployment — docker-compose.yml, DAGs, Dev Container
│   ├── dags/ipl_pipeline.py   #    freshness gate → dbt run → dbt test → notify
│   └── simple_auth_manager_passwords.example.json  #    UI credentials template (copy → ...passwords.json)
├── .env / .env.example        # Credentials (gitignored) + template
└── requirements.txt           # Python dependencies
```

## Sample Questions

- What was the final score, result, and margin?
- Which batter scored the most runs, and at what strike rate?
- Which bowler had the best economy rate?
- Run rate in powerplay vs. death overs?
- Top partnership and between which batters?
- Career batting/bowling stats across seasons?
- Which player scored the most runs in a season?

## Future Enhancements

- ~~**S3 bulk ingestion**~~ ✅ — land match JSON files in an S3 bucket and load them via an external stage + Snowpipe for continuous multi-match ingestion (extending the current PUT + COPY INTO single-file flow).
- ~~**Multi-season analytics**~~ ✅ — global player IDs (Cricsheet hashes), season-aware fact_ball, dim_season, season selector + Player Career dashboard tab; aggregate tables (fct_player_season, fct_team_season) pending.
- **Win-probability and prediction models** — e.g., Snowflake Cortex ML (forecasting, anomaly detection) once the dataset grows.
- ~~**Scheduled pipeline runs**~~ — ✅ orchestrated via **Airflow** (`orchestration/`): daily `dbt source freshness → dbt run → dbt test` with failure hooks.
