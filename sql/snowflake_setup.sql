-- ============================================================
-- IPL Analytics — Snowflake Setup
-- Creates warehouses, database, role, and RAW-layer objects.
-- Safe to re-run (IF NOT EXISTS / OR REPLACE throughout).
-- SYSADMIN creates warehouses + database, SECURITYADMIN transfers DB ownership to the role, role creates schema/file format/stage/table — clean delegation.
-- ============================================================
USE ROLE SYSADMIN;
-- ---------- 1. Warehouses ----------
CREATE WAREHOUSE IF NOT EXISTS IPL_INGEST_WH
    WITH WAREHOUSE_SIZE    = 'X-SMALL'
         AUTO_SUSPEND      = 60
         AUTO_RESUME       = TRUE
         INITIALLY_SUSPENDED = TRUE
         COMMENT           = 'Ingestion: PUT + COPY INTO raw layer';

CREATE WAREHOUSE IF NOT EXISTS IPL_TRANSFORM_WH
    WITH WAREHOUSE_SIZE    = 'X-SMALL'
         AUTO_SUSPEND      = 60
         AUTO_RESUME       = TRUE
         INITIALLY_SUSPENDED = TRUE
         COMMENT           = 'Transformation: dbt Core runs (staging/marts/gold)';

CREATE WAREHOUSE IF NOT EXISTS IPL_QUERY_WH
    WITH WAREHOUSE_SIZE    = 'X-SMALL'
         AUTO_SUSPEND      = 60
         AUTO_RESUME       = TRUE
         INITIALLY_SUSPENDED = TRUE
         COMMENT           = 'Querying: Streamlit dashboard + ad-hoc analytics';

USE ROLE USERADMIN;
-- ---------- 2. Role ----------
CREATE ROLE IF NOT EXISTS IPL_ENGINEER_ROLE
    COMMENT = 'Dedicated role for the IPL Analytics pipeline';

GRANT ROLE IPL_ENGINEER_ROLE TO USER "ADMIN";
ALTER USER "ADMIN" SET DEFAULT_ROLE = IPL_ENGINEER_ROLE;

USE ROLE SECURITYADMIN;
-- ---------- 3. Warehouse access ----------
GRANT USAGE   ON WAREHOUSE IPL_INGEST_WH     TO ROLE IPL_ENGINEER_ROLE;
GRANT OPERATE ON WAREHOUSE IPL_INGEST_WH     TO ROLE IPL_ENGINEER_ROLE;

GRANT USAGE   ON WAREHOUSE IPL_TRANSFORM_WH  TO ROLE IPL_ENGINEER_ROLE;
GRANT OPERATE ON WAREHOUSE IPL_TRANSFORM_WH  TO ROLE IPL_ENGINEER_ROLE;

GRANT USAGE   ON WAREHOUSE IPL_QUERY_WH      TO ROLE IPL_ENGINEER_ROLE;
GRANT OPERATE ON WAREHOUSE IPL_QUERY_WH      TO ROLE IPL_ENGINEER_ROLE;

USE ROLE SYSADMIN;
-- ---------- 4. Database & schema ----------
CREATE DATABASE IF NOT EXISTS IPL_ANALYTICS_DB
    COMMENT = 'IPL ball-by-ball analytics';



USE ROLE SECURITYADMIN;
-- Ownership gives the role full control (incl. creating
-- STAGING/MARTS/GOLD schemas via dbt):
GRANT OWNERSHIP ON DATABASE IPL_ANALYTICS_DB TO ROLE IPL_ENGINEER_ROLE;

USE ROLE IPL_ENGINEER_ROLE;
CREATE SCHEMA IF NOT EXISTS IPL_ANALYTICS_DB.RAW
    COMMENT = 'Raw ingested match JSON';

-- ---------- 5. File format & stage ----------
CREATE FILE FORMAT IF NOT EXISTS IPL_ANALYTICS_DB.RAW.IPL_JSON_FORMAT
    TYPE = JSON
    STRIP_OUTER_ARRAY = TRUE
    COMMENT = 'Cricsheet match JSON';

-- Internal (Snowflake-managed) stage — files are stored in Snowflake,
-- not in external cloud storage (S3/GCS/Azure):
CREATE STAGE IF NOT EXISTS IPL_ANALYTICS_DB.RAW.IPL_STAGE
    FILE_FORMAT = IPL_ANALYTICS_DB.RAW.IPL_JSON_FORMAT
    COMMENT = 'Internal landing area for match JSON files';

-- ---------- 6. Raw table ----------
CREATE TABLE IF NOT EXISTS IPL_ANALYTICS_DB.RAW.RAW_MATCH_JSON (
    match_id      VARCHAR(512),
    file_name     VARCHAR(2000),
    raw_variant   VARIANT,
    loaded_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'One row per ingested match file';



---------------7. PIPE ---------------
CREATE PIPE IPL_ANALYTICS_DB.RAW.PIPE_INGEST_FILES
    AUTO_INGEST = TRUE
AS
COPY INTO IPL_ANALYTICS_DB.RAW.RAW_MATCH_JSON
FROM (
SELECT 
    REGEXP_SUBSTR(METADATA$FILENAME, '\\d+')  AS MATCH_ID,
    METADATA$FILENAME AS FILE_NAME,
    $1 AS RAW_VARIANT,
    CURRENT_TIMESTAMP() AS LOADED_AT
FROM @IPL_ANALYTICS_DB.RAW.IPL_STAGE
)
;
