# IPL Analytics — Ball-by-Ball Match Analysis

End-to-end data pipeline for Indian Premier League (IPL) ball-by-ball match analytics: ingests Cricsheet JSON match data into Snowflake, transforms it with dbt Core, and visualizes it in a Streamlit dashboard.

**Tech stack:** Python · Snowflake · dbt Core · Streamlit

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

dbt ships a data-quality layer on top of the models — **38 tests**, all passing via `DBT_PROFILES_DIR=dbt_project .venv/bin/dbt test`:

| Scope | Tests |
|---|---|
| Raw source `raw_match_json` | `not_null` on all columns; `unique` on `match_id` (5) |
| `dim_match` | `match_id` unique + not-null (2) |
| `dim_team` | `team_id` & `team_name` unique + not-null (4) |
| `dim_player` | `player_id` unique + not-null; `player_name`, `first_season`, `last_season` not-null (4) |
| `dim_player_team` | Composite `check_player_team_uniqueness` on [player_id, match_id]; `player_id` not-null + FK → dim_player; `match_id` not-null; `team_name` not-null (6) |
| `dim_season` | `season` unique + not-null; `total_matches`, `start_date`, `end_date` not-null; `champion` FK → dim_team (6) |
| `fact_ball` | Composite `check_fact_delivery_grain_uniqueness` on (match_id, innings_no, over_no, ball_in_over); 8 `not_null`; `season` not_null; `match_date` not_null; FK `batter_id → dim_player.player_id`; FK `bowler_id → dim_player.player_id` (13) |

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

## Project Structure

```
IPL_Analytics/
├── BRD_IPL_Analytics.md      # Business requirements
├── data/                      # Raw Cricsheet JSON files
├── sql/                       # Snowflake DDL — snowflake_setup.sql, streamlit_deploy.sql
├── ingestion/                 # Python ingestion — config.py, ingest.py (PUT + COPY INTO; S3 + Snowpipe)
├── dbt_project/               # dbt Core models — staging → marts → gold, tests, profiles.example.yml
├── dashboard/                 # Streamlit app — app.py, db.py (backends), ai_summary.py (Cortex-ready)
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
- **Scheduled pipeline runs** — orchestrate ingestion + dbt via Snowflake tasks or an orchestrator like Airflow.
